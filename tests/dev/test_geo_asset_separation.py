"""P5 moves developer inputs and helpers, never runtime location capabilities."""

from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[2]

def test_geo_helpers_are_outside_the_runtime_package():
    from scripts.geo import boundary_tools, boundary_stress
    assert callable(boundary_tools.probe_boundary)
    assert callable(boundary_stress.run_boundary_stress)
    assert not (ROOT / "netwatch/location/admin/boundary_tools.py").exists()
    assert not (ROOT / "netwatch/location/admin/boundary_stress.py").exists()

def test_runtime_centers_and_developer_input_are_byte_preserved():
    from scripts.geo.build_china_district_centers import RAW_PATH, OUT_PATH
    assert RAW_PATH == ROOT / "scripts/geo/data/ok_data_level3.csv"
    assert OUT_PATH == ROOT / "netwatch/location/data/china_district_centers.csv"
    assert hashlib.sha256(OUT_PATH.read_bytes()).hexdigest() == 'c6b2f0893e15aaf18e652efbfb5e4814e6e9ec7087315fa10cd6e6a9ab74bc19'
    assert hashlib.sha256(RAW_PATH.read_bytes()).hexdigest() == 'dd5a1594565b65fa3fea5ce4b9935e0b28908226949ae44f07ebfd533428e8ff'
