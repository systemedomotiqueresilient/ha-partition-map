"""Manifest et hacs.json conformes au modèle commun de ha-sdr."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[1]


def test_check_manifest_passes() -> None:
    """tools/check_manifest.py est la copie du vérificateur de ha-sdr (manifest/)."""
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/check_manifest.py"),
            str(ROOT / "custom_components/partition_map/manifest.json"),
            str(ROOT / "VERSION"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_hacs_json_follows_template() -> None:
    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert hacs == {
        "name": "Partition Map",
        "homeassistant": "2026.2.0",
        "zip_release": True,
        "filename": "partition_map.zip",
    }
