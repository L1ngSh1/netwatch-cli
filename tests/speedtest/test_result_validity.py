"""N1-A: diagnostic validity only; all inputs and external calls are synthetic."""

from io import StringIO

import pytest
from rich.console import Console

from netwatch.cli_modules import speedtest as ui
from netwatch.network.proxy_probe import ExitIPInfo
from netwatch.speedtest import analysis, runner
from netwatch.speedtest.backends.models import SpeedtestResult


def clean_result(**changes):
    fields = dict(
        backend="fixture", ping_ms=20, jitter_ms=2, packet_loss=0,
        download_mbps=96, download_MBps=12, upload_mbps=80, upload_MBps=10,
    )
    fields.update(changes)
    return SpeedtestResult(**fields)


@pytest.mark.parametrize("field", [
    "ping_ms", "jitter_ms", "packet_loss", "download_mbps",
    "download_MBps", "upload_mbps", "upload_MBps",
])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), -1])
def test_invalid_numeric_result_is_unknown_in_all_diagnostic_consumers(field, value):
    result = clean_result(**{field: value})
    confidence, reasons = analysis.get_result_confidence(result)
    assert confidence == "UNKNOWN"
    assert field in " ".join(reasons)
    assert analysis.analyze_speedtest_consistency(result) == []
    assert not analysis.has_high_loss_high_throughput(result)
    assert not analysis.has_high_ping_to_asia_server(result)
    summary = analysis.build_network_path_summary(result)
    assert summary["likely_represents"] == "未知"
    assert summary["high_latency_route"] == "unknown"
    assert summary["metric_contradiction"] == "unknown"
    assert "未检测到明显" not in analysis.get_analysis_summary(result)
    assert runner.get_speedtest_quality_warnings(result) == []
    assert runner.get_speedtest_quality_details(result) == []
    assert runner.summarize_speedtest_raw(result)["confidence"] == "UNKNOWN"


@pytest.mark.parametrize("result", [
    SpeedtestResult("fixture"),
    clean_result(error="synthetic failure", ping_ms=140, packet_loss=59, server_location="Tokyo"),
    clean_result(packet_loss=100.1),
])
def test_failed_empty_and_out_of_range_results_do_not_claim_quality(result):
    assert analysis.get_result_confidence(result)[0] == "UNKNOWN"
    assert analysis.analyze_speedtest_consistency(result) == []
    assert analysis.build_network_path_summary(result)["likely_represents"] == "未知"
    assert "未检测到明显" not in analysis.get_analysis_summary(result)
    assert runner.get_speedtest_quality_warnings(result) == []
    assert runner.get_speedtest_quality_details(result) == []
    assert runner.summarize_speedtest_raw(result)["confidence"] == "UNKNOWN"


@pytest.mark.parametrize("entrypoint", [
    "print_speedtest_result", "print_speedtest_result_table", "print_speedtest_results_extra",
    "print_speedtest_quality_warning", "print_speedtest_path_analysis", "print_proxy_exit_judgment",
])
@pytest.mark.parametrize("result", [
    clean_result(error="synthetic failure"), SpeedtestResult("fixture"),
    clean_result(download_mbps=float("nan")),
])
def test_public_cli_displays_stop_before_success_diagnosis(entrypoint, result, monkeypatch):
    output = StringIO()
    monkeypatch.setattr(ui, "console", Console(file=output, width=140))
    getattr(ui, entrypoint)(result)
    rendered = output.getvalue()
    assert "HIGH" not in rendered and "MEDIUM" not in rendered
    assert "网络路径分析" not in rendered
    assert "更接近当前直连" not in rendered
    assert "更可能代表" not in rendered
    assert "触发条件" not in rendered
    assert "Speedtest 测速结果" not in rendered
    assert "诊断不可用" in rendered or "未知" in rendered or "synthetic failure" in rendered


@pytest.mark.parametrize("result", [SpeedtestResult("fixture"), clean_result(upload_MBps=-1)])
def test_proxy_entry_does_not_announce_completion_or_prompt_for_invalid_result(result, monkeypatch):
    output = StringIO()
    monkeypatch.setattr(ui, "console", Console(file=output, width=140))
    monkeypatch.setattr(ui, "probe_exit_ip", lambda: ExitIPInfo(ip=None, country=None, region=None, city=None, org=None))
    monkeypatch.setattr(ui.time, "sleep", lambda _: None)
    monkeypatch.setattr(ui, "run_best_speedtest", lambda use_interface: result)
    prompts = []
    monkeypatch.setattr(ui.Prompt, "ask", lambda *a, **kw: prompts.append(a) or "n")
    ui.show_proxy_exit_speedtest()
    assert prompts == []
    assert "测速完成。" not in output.getvalue()
    assert "当前测速代表" not in output.getvalue()


def test_raw_interface_facts_survive_without_claiming_a_completed_measurement(monkeypatch):
    result = SpeedtestResult("fixture", raw={"interface": {"name": "utun8", "internalIp": "198.18.0.1"}})
    assert analysis.detect_vpn_tun(result)
    assert analysis.get_result_confidence(result)[0] == "UNKNOWN"
    messages = analysis.analyze_speedtest_consistency(result)
    assert any("TUN/VPN 虚拟网卡" in message for message in messages)
    assert not any("测速结果代表" in message for message in messages)
    summary = analysis.build_network_path_summary(result)
    assert summary["vpn_tun"] == "yes"
    assert summary["likely_represents"] == "未知"
    assert runner.get_speedtest_quality_details(result)  # Existing raw-only fact contract.
    output = StringIO()
    monkeypatch.setattr(ui, "console", Console(file=output, width=140))
    ui.print_speedtest_results_extra(result)
    assert "UNKNOWN" in output.getvalue()
    assert "VPN/TUN" in output.getvalue()
    assert "当前结果更可能代表" not in output.getvalue()


@pytest.mark.parametrize("fields,expected", [
    ({"ping_ms": 20}, "MEDIUM"),
    ({"download_mbps": 96}, "MEDIUM"),
    ({"ping_ms": 140}, "LOW"),
    ({"packet_loss": 59, "download_mbps": 96}, "LOW"),
    ({"ping_ms": 0, "jitter_ms": 0, "packet_loss": 0}, "HIGH"),
    ({"ping_ms": 70, "jitter_ms": 12, "packet_loss": 0.5}, "MEDIUM"),
])
def test_partial_and_zero_measurements_keep_existing_confidence_semantics(fields, expected):
    result = SpeedtestResult("fixture", **fields)
    assert analysis.get_result_confidence(result)[0] == expected
    assert result.error is None


def test_missing_optional_metrics_still_display_a_successful_partial_result(monkeypatch):
    result = SpeedtestResult("fixture", ping_ms=20, download_mbps=96)
    output = StringIO()
    monkeypatch.setattr(ui, "console", Console(file=output, width=140))
    ui.print_speedtest_result(result)
    assert "Speedtest 测速结果" in output.getvalue()
    assert "网络路径分析" in output.getvalue()
    assert "MEDIUM" in output.getvalue()
    assert "100 Mbps" in output.getvalue()


def test_zero_bandwidth_is_valid_and_high_loss_boundary_remains_measured():
    zero = clean_result(ping_ms=0, jitter_ms=0, packet_loss=0,
                        download_mbps=0, download_MBps=0, upload_mbps=0, upload_MBps=0)
    assert analysis.get_result_confidence(zero)[0] == "HIGH"
    assert any(d["condition"] == "download < 50 Mbps" for d in runner.get_speedtest_quality_details(zero))
    assert analysis.get_result_confidence(clean_result(packet_loss=100))[0] == "LOW"
