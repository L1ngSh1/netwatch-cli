"""Packaging verifier negative cases use synthetic zip files, not builds or pip."""

import zipfile

import pytest

from scripts.dev.verify_wheel import BASE_REQUIRES, REQUIRED_DATA, inspect_wheel


def make_wheel(tmp_path, *, omit=None, add=None, bad_dependency=False):
    path = tmp_path / "synthetic.whl"
    with zipfile.ZipFile(path, "w") as wheel:
        for name in REQUIRED_DATA - {omit}:
            wheel.writestr(name, "synthetic data")
        for name in add or []: wheel.writestr(name, "synthetic developer asset")
        dependencies = BASE_REQUIRES - ({"reverse-geocoder>=1.5.1"} if bad_dependency else set())
        text = "Metadata-Version: 2.1\n" + "\n".join("Requires-Dist: " + value for value in dependencies)
        text += "\n" + "\n".join("Provides-Extra: " + value for value in ["all", "browser", "dev", "geo"])
        wheel.writestr("netwatch_cli-0.9.3.dist-info/METADATA", text)
        wheel.writestr("netwatch_cli-0.9.3.dist-info/entry_points.txt", "[console_scripts]\nnetwatch = netwatch.cli:main\n")
    return path


def test_clean_wheel_preserves_default_capabilities(tmp_path):
    assert inspect_wheel(make_wheel(tmp_path))["developer_assets_absent"]


@pytest.mark.parametrize("name", sorted(REQUIRED_DATA))
def test_missing_runtime_data_is_rejected(tmp_path, name):
    with pytest.raises(AssertionError, match="runtime location data"):
        inspect_wheel(make_wheel(tmp_path, omit=name))


@pytest.mark.parametrize("name", ["scripts/geo/boundary_tools.py", "netwatch/location/admin/boundary_tools.py", "netwatch/location/data/raw/source.csv", "tests/test_example.py"])
def test_development_assets_are_rejected(tmp_path, name):
    with pytest.raises(AssertionError, match="developer assets"):
        inspect_wheel(make_wheel(tmp_path, add=[name]))


def test_removing_base_location_dependency_is_rejected(tmp_path):
    with pytest.raises(AssertionError, match="base dependency"):
        inspect_wheel(make_wheel(tmp_path, bad_dependency=True))
