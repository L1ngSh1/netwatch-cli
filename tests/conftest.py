"""Default tests use synthetic preferences and explicitly mocked external I/O."""

from pathlib import Path
import tempfile
import threading
import time

import pytest

from _io_guard import ExternalIOGuard

pytest_plugins = ["pytester"]


def pytest_configure(config):
    # Do this before collection: some location modules compute Path.home() at import.
    config._netwatch_home = tempfile.TemporaryDirectory(prefix="netwatch-tests-")
    config._netwatch_env = pytest.MonkeyPatch()
    config._netwatch_env.setenv("HOME", config._netwatch_home.name)
    config._netwatch_env.setenv("USERPROFILE", config._netwatch_home.name)
    config._netwatch_env.setenv("NETWATCH_CONFIG_PATH", str(Path(config._netwatch_home.name) / "config.json"))
    for name in ("NETWATCH_BOUNDARY_GEOJSON", "NETWATCH_ROADS_GEOJSON", "NETWATCH_USE_SAMPLE_GEO"):
        config._netwatch_env.delenv(name, raising=False)
    config._netwatch_io_events = []


def pytest_unconfigure(config):
    config._netwatch_env.undo()
    config._netwatch_home.cleanup()


@pytest.fixture(autouse=True)
def external_io_guard(tmp_path, request):
    guard = ExternalIOGuard()
    previous_threads = set(threading.enumerate())
    with guard.installed(), pytest.MonkeyPatch.context() as env:
        home = tmp_path / "home"
        home.mkdir()
        env.setenv("HOME", str(home))
        env.setenv("USERPROFILE", str(home))
        env.setenv("NETWATCH_CONFIG_PATH", str(home / ".netwatch" / "config.json"))
        yield guard
        # Keep tripwires active while test-owned workers finish; never let a
        # delayed call silently become the next test's event (or escape teardown).
        deadline = time.monotonic() + 1
        workers = set(threading.enumerate()) - previous_threads
        for thread in workers:
            thread.join(timeout=max(0, deadline - time.monotonic()))
        lingering = [thread for thread in workers if thread.is_alive()]
    request.config._netwatch_io_events.extend(guard.events)
    guard.assert_clean()
    assert not lingering, "test left running worker threads"


@pytest.fixture
def allow_localhost(external_io_guard):
    """Opt in only for geolocation's loopback HTTP callback tests."""
    external_io_guard.allow_localhost = True


def pytest_terminal_summary(terminalreporter):
    events = terminalreporter.config._netwatch_io_events
    terminalreporter.write_line(f"NETWATCH_UNMOCKED_IO_ATTEMPTS={len(events)}")
