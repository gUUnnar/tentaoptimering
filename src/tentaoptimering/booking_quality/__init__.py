"""Data quality and classification layer for room bookings.

Freestanding: it reads the prepared booking data and its configuration and describes the data along independent dimensions
(resource identification, data quality, source coverage, link certainty). It does not influence the optimisation engine.
See `docs/ARKITEKTURPRINCIPER_DATAKVALITET.md`.
"""

from .classify import IDENTIFICATIONS, LINKS, classify, ladok_window
from .config import QualityConfig, Rule, default_config_path, load_config
from .report import assess, build_report, load_inputs

__all__ = ["IDENTIFICATIONS", "LINKS", "QualityConfig", "Rule", "assess", "build_report", "classify", "default_config_path", "ladok_window", "load_config", "load_inputs"]
