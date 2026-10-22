"""The CLI may announce waiting, but backend phases need actual observations."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from netwatch.cli_modules import speedtest as ui
from netwatch.speedtest.backends.models import SpeedtestResult


@pytest.mark.parametrize("cancel", [False, True])
def test_waiting_tracks_backend_call_without_fabricated_phases(monkeypatch, cancel):
    events, printed = [], []
    result = SpeedtestResult("fixture", download_mbps=100)

    @contextmanager
    def status(message):
        events.append("waiting")
        try:
            yield
        finally:
            events.append("end-wait")

    def backend():
        events.append("backend-called")
        if cancel:
            raise KeyboardInterrupt
        events.append("backend-returned")
        return result

    monkeypatch.setattr(ui, "console", SimpleNamespace(status=status, print=printed.append))
    returned = ui.run_speedtest_with_status(backend)
    assert returned is (None if cancel else result)
    assert events == (["waiting", "backend-called", "end-wait"] if cancel else
                      ["waiting", "backend-called", "backend-returned", "end-wait"])
    text = " ".join(printed)
    assert "正在执行下载测速" not in text
    assert "正在执行上传测速" not in text
    assert "正在连接测速服务器" not in text
    assert ("已取消当前测速" in text) is cancel
