"""Explicit browser installer acceptance is fully mocked in default pytest."""

from contextlib import nullcontext
import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts.dev import verify_browser_runtime as check


@pytest.fixture
def browser_api(monkeypatch):
    page = Mock()
    page.title.return_value = "netwatch install check"
    page.locator.return_value.inner_text.return_value = "ready"
    page.evaluate.return_value = 4
    context = Mock()
    context.new_page.return_value = page
    browser = Mock()
    browser.new_context.return_value = context
    chromium = Mock()
    chromium.launch.return_value = browser
    api = ModuleType("playwright.sync_api")
    api.sync_playwright = lambda: nullcontext(SimpleNamespace(chromium=chromium))
    package = ModuleType("playwright")
    package.__path__ = []
    monkeypatch.setitem(sys.modules, "playwright", package)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", api)
    return chromium, browser, context, page


def test_only_shell_acceptance_requires_an_explicit_cache(monkeypatch):
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    monkeypatch.setattr(sys, "argv", ["check", "--require-only-shell"])
    with pytest.raises(AssertionError, match="explicit browser cache"):
        check.main()


@pytest.mark.parametrize("entries", [[], ["chromium-123"], ["chromium_headless_shell-123", "chromium-123"]])
def test_only_shell_acceptance_rejects_missing_shell_or_full_browser(tmp_path, monkeypatch, entries):
    for name in entries:
        (tmp_path / name).mkdir()
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["check", "--require-only-shell"])
    with pytest.raises(AssertionError, match="headless shell|full Chromium"):
        check.main()


@pytest.mark.parametrize("only_shell", [False, True])
def test_local_browser_smoke_keeps_network_blocked_and_closes_browser(tmp_path, monkeypatch, browser_api, only_shell):
    output = tmp_path / "result.json"
    args = ["check", "--output", str(output)]
    if only_shell:
        (tmp_path / "chromium_headless_shell-123").mkdir()
        (tmp_path / "ffmpeg-123").mkdir()
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
        args.append("--require-only-shell")
    monkeypatch.setattr(sys, "argv", args)
    assert check.main() == 0
    chromium, browser, context, page = browser_api
    chromium.launch.assert_called_once_with(headless=True)
    context.set_offline.assert_called_once_with(True)
    context.route.assert_called_once()
    pattern, deny = context.route.call_args.args
    assert pattern == "**/*"
    route = Mock()
    deny(route)
    route.abort.assert_called_once()
    page.goto.assert_not_called()
    browser.close.assert_called_once()
    result = json.loads(output.read_text())
    assert result["public_navigation"] is False
    assert result["only_shell_cache_verified"] is only_shell


def test_local_browser_failure_also_closes_browser(monkeypatch, browser_api):
    monkeypatch.setattr(sys, "argv", ["check"])
    _, browser, _, page = browser_api
    page.evaluate.side_effect = KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        check.main()
    browser.close.assert_called_once()
