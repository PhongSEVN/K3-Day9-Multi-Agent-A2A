"""Create and verify the submission ZIP with exactly 50 root-level JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def package(output_dir: Path | str = "output", zip_path: Path | str = "output.zip") -> None:
    output_dir, zip_path = Path(output_dir), Path(zip_path)
    expected = {f"EC_{number:03d}.json" for number in range(1, 51)}
    paths = sorted(output_dir.glob("EC_*.json"))
    actual = {path.name for path in paths}
    if actual != expected:
        raise ValueError(
            f"Expected exactly EC_001..EC_050; "
            f"missing={sorted(expected-actual)}, extra={sorted(actual-expected)}"
        )

    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("case_id") != path.stem:
            raise ValueError(f"case_id does not match filename: {path.name}")

    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, arcname=path.name)

    with ZipFile(zip_path) as archive:
        names = archive.namelist()
        if len(names) != 50 or set(names) != expected:
            raise ValueError("ZIP is not a flat archive containing exactly 50 outputs")
        if any("/" in name or "\\" in name for name in names):
            raise ValueError("ZIP contains a directory entry")

    print(f"Created verified flat ZIP: {zip_path} (50 JSON files)")


if __name__ == "__main__":
    package()

