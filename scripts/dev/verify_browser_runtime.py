#!/usr/bin/env python3
"""Explicit installation smoke check, outside pytest; no public website access."""

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-only-shell", action="store_true")
    args = parser.parse_args()
    if args.require_only_shell:
        cache = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
        assert cache and Path(cache).is_absolute(), "explicit browser cache required"
        names = [p.name for p in Path(cache).iterdir() if p.is_dir()]
        assert any(name.startswith("chromium_headless_shell-") for name in names), "missing headless shell"
        assert not any(name.startswith("chromium-") for name in names), "full Chromium present"
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context()
            context.route("**/*", lambda route: route.abort())
            context.set_offline(True)
            page = context.new_page()
            page.set_content("<title>netwatch install check</title><main>ready</main>")
            assert page.title() == "netwatch install check"
            assert page.locator("main").inner_text() == "ready"
            assert page.evaluate("2 + 2") == 4
        finally:
            browser.close()
    result = json.dumps({"headless_launch": "PASS", "local_dom": "PASS", "javascript": 4,
                         "public_navigation": False, "only_shell_cache_verified": args.require_only_shell}, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
