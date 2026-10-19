#!/usr/bin/env python3
"""Inspect a freshly built wheel without installing or importing its contents."""

from __future__ import annotations

import argparse
from email.parser import Parser
import hashlib
import json
from pathlib import Path
import zipfile

BASE_REQUIRES = {"psutil>=5.9", "requests>=2.31", "rich>=13.0", "speedtest-cli>=2.1", "reverse-geocoder>=1.5.1"}
REQUIRED_DATA = {
    "netwatch/location/data/china_district_centers.csv",
    "netwatch/location/data/boundaries/china_districts.sample.geojson",
    "netwatch/location/data/roads/roads.sample.geojson",
}


def inspect_wheel(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        assert REQUIRED_DATA <= names, "missing runtime location data"
        assert not any(".." in Path(name).parts or "__pycache__" in name or name.endswith(".pyc") for name in names)
        assert not any(name.startswith(("scripts/", "tests/")) or "/data/raw/" in name or name.endswith(("/boundary_tools.py", "/boundary_stress.py")) for name in names), "developer assets leaked into wheel"
        metadata_name = next(n for n in names if n.endswith(".dist-info/METADATA"))
        metadata = Parser().parsestr(archive.read(metadata_name).decode())
        requires = metadata.get_all("Requires-Dist", [])
        assert {item for item in requires if ";" not in item} == BASE_REQUIRES, "base dependency contract changed"
        assert set(metadata.get_all("Provides-Extra", [])) == {"browser", "dev", "geo", "all"}
        entry = archive.read(metadata_name.replace("METADATA", "entry_points.txt")).decode()
        assert "netwatch = netwatch.cli:main" in entry, "CLI entrypoint changed"
        return {
            "wheel": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "compressed_bytes": path.stat().st_size,
            "uncompressed_runtime_bytes": sum(len(archive.read(n)) for n in names if n.startswith("netwatch/")),
            "requires_dist": sorted(requires),
            "data_sha256": {n: hashlib.sha256(archive.read(n)).hexdigest() for n in sorted(REQUIRED_DATA)},
            "developer_assets_absent": True,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(inspect_wheel(args.wheel), indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
