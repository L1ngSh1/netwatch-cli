"""One diagnostic path decision across platforms; no route or network discovery."""

from io import StringIO

import pytest
from rich.console import Console

from netwatch.cli_modules import speedtest as ui
from netwatch.platform import LinuxBackend, MacOSBackend, WindowsBackend
from netwatch.speedtest import analysis, runner
from netwatch.speedtest.backends.models import SpeedtestResult


@pytest.mark.parametrize("platform", [LinuxBackend, MacOSBackend, WindowsBackend])
@pytest.mark.parametrize("name,address,expected", [
    ("utun8", "10.0.0.2", True),
    ("Wintun Userspace Tunnel", "10.0.0.2", True),
    ("bridge0", "192.168.1.2", False),
    ("vEthernet", "192.168.1.2", False),
    ("eth0", "192.168.1.2", False),
    ("eth0", "198.18.0.0", True),
    ("eth0", "198.19.0.2", True),
    ("eth0", "198.19.255.255", True),
    ("eth0", "198.17.255.255", False),
    ("eth0", "198.20.0.0", False),
    ("eth0", "198.18.invalid", False),
    ("eth0", "198.18.0.999", False),
    ("eth0", "100.64.0.2", False),
    ("eth0", "2001:db8::1", False),
])
def test_all_consumers_agree_on_path_evidence(platform, name, address, expected, monkeypatch):
    monkeypatch.setattr(analysis, "get_backend", platform)
    monkeypatch.setattr(runner, "get_backend", platform)
    result = SpeedtestResult("fixture", ping_ms=20, jitter_ms=2, packet_loss=0,
                             raw={"interface": {"name": name, "internalIp": address}})
    assert analysis.detect_vpn_tun(result) is expected
    assert bool(runner.get_speedtest_quality_details(result)) is expected
    confidence, _ = analysis.get_result_confidence(result)
    assert confidence == ("LOW" if expected else "HIGH")
    expected_flag = "yes" if expected else "no"
    assert analysis.build_network_path_summary(result)["vpn_tun"] == expected_flag
    assert runner.summarize_speedtest_raw(result)["vpn_tun"] == expected_flag
    output = StringIO()
    monkeypatch.setattr(ui, "console", Console(file=output, width=160))
    ui.print_proxy_exit_judgment(result)
    assert ("检测到当前可能经过代理/TUN" in output.getvalue()) is expected
    assert "更接近当前直连出口质量" not in output.getvalue()


@pytest.mark.parametrize("raw", [None, "fixture", {}, {"interface": None}, {"interface": {}},
                                  {"interface": {"name": "bridge0"}}])
def test_no_vpn_evidence_is_not_proof_of_direct_path(raw, monkeypatch):
    result = SpeedtestResult("fixture", ping_ms=20, raw=raw)
    output = StringIO()
    monkeypatch.setattr(ui, "console", Console(file=output, width=160))
    ui.print_proxy_exit_judgment(result)
    assert "未检测到明显 TUN/VPN" in output.getvalue()
    assert "未证实物理直连" in output.getvalue()


def test_failed_result_keeps_summary_unknown_even_with_vpn_raw():
    result = SpeedtestResult("fixture", error="synthetic failure",
                             raw={"interface": {"name": "utun0"}})
    assert runner.summarize_speedtest_raw(result)["vpn_tun"] == "unknown"


def test_benchmark_address_is_a_hint_not_proof_of_vpn():
    result = SpeedtestResult("fixture", ping_ms=20,
                             raw={"interface": {"name": "eth0", "internalIp": "198.19.0.2"}})
    assert analysis.get_interface_evidence(result) == "benchmark"
    messages = " ".join(analysis.analyze_speedtest_consistency(result))
    assert "线索" in messages
    assert "当前测速经过" not in messages


def test_regular_virtual_interface_is_distinct_from_absent_evidence(monkeypatch):
    # Test each platform's native fixture, rather than interpreting a Unix bridge
    # through whichever platform happens to host pytest.
    for platform, name in [(LinuxBackend, "bridge0"), (MacOSBackend, "bridge0"),
                           (WindowsBackend, "vEthernet")]:
        monkeypatch.setattr(analysis, "get_backend", platform)
        result = SpeedtestResult("fixture", raw={"interface": {"name": name}})
        assert analysis.get_interface_evidence(result) == "virtual"
        assert analysis.get_interface_evidence(SpeedtestResult("fixture")) == "unknown"
