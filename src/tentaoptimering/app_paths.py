"""Paths for the desktop application and its user-writable state."""

from __future__ import annotations

import os
from pathlib import Path
import sys

from .paths import REPO_ROOT


def application_root() -> Path:
    """Return bundled resources when frozen, otherwise the repository root."""
    return Path(getattr(sys, "_MEIPASS", REPO_ROOT))


def default_app_data_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base / "Uppsala universitet" / "Tentaoptimering"


def bundled_scenarios_dir() -> Path:
    return application_root() / "config" / "scenarios"


def bundled_parameters_path() -> Path:
    return application_root() / "config" / "parameters.toml"


def frontend_dist_dir() -> Path:
    return application_root() / "frontend" / "dist"
