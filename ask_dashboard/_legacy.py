"""Load the historical single-file Ask Dashboard implementation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
LEGACY_PATH = REPOSITORY_ROOT / "ask_dashboard.py"
SPEC = importlib.util.spec_from_file_location("_svs_ask_dashboard_legacy", LEGACY_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise ImportError(f"Unable to load legacy Ask Dashboard module at {LEGACY_PATH}")

legacy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = legacy
SPEC.loader.exec_module(legacy)
