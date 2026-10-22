"""Copied installed data and the real local lookup; no pip, network or browser."""

import importlib.util
import json
from pathlib import Path
import sys

import pytest

from scripts.dev import verify_installed

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "scripts/dev/location_data_contract.json").read_text(encoding="utf-8"))


@pytest.fixture
def installed_package(tmp_path):
    package = tmp_path / "installed" / "netwatch"
    for member in CONTRACT["files"]:
        target = package / Path(member).relative_to("netwatch")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / member).read_bytes())
    return package


def test_installed_data_matches_fixed_authority(installed_package):
    assert verify_installed.inspect_installed_data(installed_package) == CONTRACT["files"]


@pytest.mark.parametrize("member", sorted(CONTRACT["files"]))
@pytest.mark.parametrize("mode", ["missing", "empty", "truncated", "replacement"])
def test_installed_data_corruption_is_rejected(installed_package, member, mode):
    target = installed_package / Path(member).relative_to("netwatch")
    if mode == "missing":
        target.unlink()
    else:
        data = target.read_bytes()
        replacements = {"empty": b"", "truncated": data[:len(data) // 2], "replacement": b"replacement fixture"}
        target.write_bytes(replacements[mode])
    with pytest.raises(AssertionError, match="runtime location data"):
        verify_installed.inspect_installed_data(installed_package)


@pytest.fixture
def installed_lookup(installed_package, monkeypatch):
    # Execute an actual copy so its __file__ and data path are naturally local.
    from netwatch.location import admin
    path = installed_package / "location/admin/china_admin_lookup.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((ROOT / "netwatch/location/admin/china_admin_lookup.py").read_bytes())
    spec = importlib.util.spec_from_file_location("netwatch.location.admin.china_admin_lookup", path)
    lookup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lookup)
    monkeypatch.setitem(sys.modules, spec.name, lookup)
    monkeypatch.setattr(admin, "china_admin_lookup", lookup, raising=False)
    return lookup


def test_real_local_lookup_uses_installed_centers(installed_package, installed_lookup):
    assert installed_lookup._cache is None
    result = verify_installed.verify_center_lookup(installed_package)
    assert result["result"] == CONTRACT["center_probe"]["expected"]
    assert result["record_count"] == CONTRACT["center_probe"]["record_count"]
    assert installed_lookup._cache is not None


def test_center_lookup_rejects_a_source_tree_import(installed_package):
    with pytest.raises(AssertionError, match="lookup module outside installed package"):
        verify_installed.verify_center_lookup(installed_package)


def test_center_lookup_rejects_external_data_path(installed_package, installed_lookup, monkeypatch):
    monkeypatch.setattr(installed_lookup, "_DISTRICT_CSV", ROOT / "netwatch/location/data/china_district_centers.csv")
    with pytest.raises(AssertionError, match="lookup data outside installed package"):
        verify_installed.verify_center_lookup(installed_package)


def test_center_lookup_rejects_wrong_result(installed_package, installed_lookup, monkeypatch):
    monkeypatch.setattr(installed_lookup, "lookup_nearest_district", lambda **kwargs: None)
    with pytest.raises(AssertionError, match="installed center lookup result"):
        verify_installed.verify_center_lookup(installed_package)


def test_center_lookup_rejects_wrong_count(installed_package, installed_lookup, monkeypatch):
    monkeypatch.setattr(installed_lookup, "get_cache_info", lambda: {"record_count": 1})
    with pytest.raises(AssertionError, match="installed center record count"):
        verify_installed.verify_center_lookup(installed_package)
