"""Prove tripwires fail before I/O and survive catches, threads and teardown."""

from pathlib import Path
import os
import socket
import subprocess
from threading import Thread
import urllib.request
import webbrowser

import pytest
import requests

from _io_guard import ExternalIOGuard, UnmockedIO


@pytest.mark.parametrize("action,kind", [
    (lambda: subprocess.run(["curl", "https://example.invalid"]), "subprocess.run"),
    (lambda: subprocess.Popen(["speedtest"]), "subprocess.Popen"),
    (lambda: os.system("speedtest"), "os.system"),
    (lambda: requests.get("https://example.invalid"), "requests.request"),
    (lambda: urllib.request.urlopen("http://example.invalid", timeout=0.1), "socket.getaddrinfo"),
    (lambda: socket.getaddrinfo("example.invalid", 80), "socket.getaddrinfo"),
    (lambda: socket.gethostbyname("example.invalid"), "socket.gethostbyname"),
    (lambda: socket.gethostbyaddr("192.0.2.1"), "socket.gethostbyaddr"),
    (lambda: webbrowser.open("https://example.invalid"), "webbrowser.open"),
])
def test_unmocked_calls_are_blocked_and_recorded(action, kind):
    # This inner guard owns expected violations; the suite guard stays clean.
    guard = ExternalIOGuard()
    with guard.installed():
        with pytest.raises(UnmockedIO, match=kind):
            action()
        assert guard.events == (kind,)
        with pytest.raises(AssertionError, match=kind):
            guard.assert_clean()


@pytest.mark.parametrize("method,args", [
    ("connect", (("192.0.2.1", 80),)),
    ("connect_ex", (("127.0.0.1", 80),)),
    ("bind", (("0.0.0.0", 0),)),
    ("sendto", (b"fixture", ("192.0.2.1", 53))),
])
def test_socket_methods_block_before_system_call(method, args):
    guard = ExternalIOGuard()
    with guard.installed(), socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        with pytest.raises(UnmockedIO, match="socket." + method):
            getattr(sock, method)(*args)
    assert guard.events == ("socket." + method,)


def test_browser_loader_is_guarded():
    from netwatch.speedtest import speedtest_cn_browser

    guard = ExternalIOGuard()
    with guard.installed(), pytest.raises(UnmockedIO, match="playwright.load"):
        speedtest_cn_browser.load_sync_playwright()
    assert guard.events == ("playwright.load",)


def test_mocks_are_allowed_and_guard_restores_bindings():
    original_run = subprocess.run
    original_connect = socket.socket.connect
    guard = ExternalIOGuard()
    with guard.installed():
        assert subprocess.run is not original_run
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(subprocess, "run", lambda *a, **kw: "mocked")
            assert subprocess.run(["speedtest"]) == "mocked"
        with pytest.raises(UnmockedIO):
            subprocess.run(["speedtest"])
    assert subprocess.run is original_run
    assert socket.socket.connect is original_connect
    assert ExternalIOGuard().events == ()
    assert ExternalIOGuard().allow_localhost is False


def test_localhost_opt_in_does_not_allow_external_hosts():
    guard = ExternalIOGuard()
    assert not guard.permits("127.0.0.1")
    guard.allow_localhost = True
    assert guard.permits("127.0.0.1")
    assert guard.permits("::1")
    assert guard.permits("localhost")
    for host in ("192.0.2.1", "0.0.0.0", "example.invalid", "localhost.example.invalid"):
        assert not guard.permits(host)
    with guard.installed(), pytest.raises(UnmockedIO, match="socket.getaddrinfo"):
        socket.getaddrinfo("example.invalid", 80)


def test_caught_thread_attempt_is_still_recorded():
    guard = ExternalIOGuard()

    def worker():
        try:
            socket.getaddrinfo("example.invalid", 80)
        except UnmockedIO:
            pass

    with guard.installed():
        thread = Thread(target=worker)
        thread.start()
        thread.join(timeout=2)
        assert not thread.is_alive()
    with pytest.raises(AssertionError, match="socket.getaddrinfo"):
        guard.assert_clean()


def test_default_fixture_fails_swallowed_attempt_and_resets_next_test(pytester):
    # Nested pytest runs in this process: no subprocess escape hatch for the guard.
    source = Path(__file__).parent
    pytester.makeconftest((source / "conftest.py").read_text())
    pytester.makepyfile(_io_guard=(source / "_io_guard.py").read_text())
    pytester.makepyfile('''
        import socket
        import time
        from threading import Thread

        def test_caught_attempt(allow_localhost):
            def worker():
                time.sleep(0.02)
                try:
                    socket.gethostbyname("example.invalid")
                except RuntimeError:
                    pass
            thread = Thread(target=worker)
            thread.start()
            # Deliberately return before the worker; teardown must own the event.

        def test_next_is_clean(external_io_guard):
            assert external_io_guard.events == ()
            assert external_io_guard.allow_localhost is False
    ''')
    result = pytester.runpytest_inprocess("-q", "--tb=short")
    result.assert_outcomes(passed=2, errors=1)
    result.stdout.fnmatch_lines(["*unmocked external I/O attempts: socket.gethostbyname*",
                               "NETWATCH_UNMOCKED_IO_ATTEMPTS=1"])


def test_default_preferences_are_synthetic():
    from netwatch.core.config import get_config_path, load_config

    assert get_config_path().is_relative_to(Path.home())
    assert load_config() == {}
