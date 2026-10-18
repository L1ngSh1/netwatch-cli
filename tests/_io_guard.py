"""Reversible test tripwires, not a sandbox. Record event kinds, never payloads."""

from contextlib import contextmanager
import ipaddress
import os
import socket
import subprocess
from threading import Lock
from urllib.parse import urlsplit
import webbrowser

import pytest
import requests


class UnmockedIO(RuntimeError):
    pass


class ExternalIOGuard:
    def __init__(self):
        self.allow_localhost = False
        self._events = []
        self._lock = Lock()

    @property
    def events(self):
        with self._lock:
            return tuple(self._events)

    def block(self, kind):
        with self._lock:
            self._events.append(kind)
        raise UnmockedIO("unmocked external I/O: " + kind)

    def assert_clean(self):
        if self.events:
            raise AssertionError("unmocked external I/O attempts: " + ", ".join(self.events))

    def permits(self, host):
        if not self.allow_localhost:
            return False
        if host in ("localhost", b"localhost"):
            return True
        try:
            if isinstance(host, bytes):
                host = host.decode("ascii")
            return ipaddress.ip_address(host).is_loopback
        except (ValueError, TypeError, UnicodeError):
            return False

    @contextmanager
    def installed(self):
        # An independent context restores the guard after mocks, and originals
        # after each test. No permanent audit hook or thread-local exemptions.
        with pytest.MonkeyPatch.context() as patch:
            def denied(kind):
                def call(*args, **kwargs):
                    self.block(kind)
                return call

            for name in ("Popen", "run", "call", "check_call", "check_output"):
                patch.setattr(subprocess, name, denied("subprocess." + name))
            for name in ("system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp",
                         "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe"):
                if hasattr(os, name):
                    patch.setattr(os, name, denied("os." + name))
            for name in ("open", "open_new", "open_new_tab"):
                patch.setattr(webbrowser, name, denied("webbrowser." + name))
            patch.setattr(webbrowser.BaseBrowser, "open", denied("webbrowser.BaseBrowser.open"))
            patch.setattr(webbrowser.GenericBrowser, "open", denied("webbrowser.GenericBrowser.open"))
            patch.setattr(webbrowser.BackgroundBrowser, "open", denied("webbrowser.BackgroundBrowser.open"))

            def guard_dns(original, kind):
                def call(host, *args, **kwargs):
                    if not self.permits(host):
                        self.block(kind)
                    # Never ask the system resolver for even a loopback PTR.
                    if kind == "socket.gethostbyaddr":
                        return ("localhost", [], [host])
                    if host in ("localhost", b"localhost"):
                        host = "127.0.0.1"
                    return original(host, *args, **kwargs)
                return call

            for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"):
                patch.setattr(socket, name, guard_dns(getattr(socket, name), "socket." + name))
            original_getnameinfo = socket.getnameinfo

            def getnameinfo(address, flags):
                if not self.permits(address[0]) or not flags & socket.NI_NUMERICHOST:
                    self.block("socket.getnameinfo")
                return original_getnameinfo(address, flags)

            patch.setattr(socket, "getnameinfo", getnameinfo)

            def guard_address(original, kind):
                def call(sock, address, *args, **kwargs):
                    if sock.family in (socket.AF_INET, socket.AF_INET6):
                        if not isinstance(address, tuple) or not self.permits(address[0]):
                            self.block(kind)
                    else:
                        self.block(kind)
                    return original(sock, address, *args, **kwargs)
                return call

            for name in ("connect", "connect_ex", "bind"):
                patch.setattr(socket.socket, name, guard_address(getattr(socket.socket, name), "socket." + name))
            original_sendto = socket.socket.sendto

            def sendto(sock, data, *args):
                address = args[-1]
                if not isinstance(address, tuple) or not self.permits(address[0]):
                    self.block("socket.sendto")
                return original_sendto(sock, data, *args)

            patch.setattr(socket.socket, "sendto", sendto)
            if hasattr(socket.socket, "sendmsg"):
                patch.setattr(socket.socket, "sendmsg", denied("socket.sendmsg"))

            original_request = requests.sessions.Session.request

            def request(session, method, url, *args, **kwargs):
                if not self.permits(urlsplit(url).hostname):
                    self.block("requests.request")
                return original_request(session, method, url, *args, **kwargs)

            patch.setattr(requests.sessions.Session, "request", request)
            # Playwright starts a driver subprocess even before BrowserType.launch.
            # Blocking this loader also protects installations without Playwright.
            from netwatch.speedtest import speedtest_cn_browser
            patch.setattr(speedtest_cn_browser, "load_sync_playwright", denied("playwright.load"))
            yield self
