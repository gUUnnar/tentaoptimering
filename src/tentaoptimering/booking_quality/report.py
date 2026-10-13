"""A report on the quality of a booking extract: counts per dimension, where findings sit, and what the data owner could confirm.

Pure description. It never states why something is missing and never says what should be done about it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .classify import IDENTIFICATIONS, LINKS, classify, ladok_window
from .config import QualityConfig, load_config


def read_source(processed_dir: Path, name: str) -> pd.DataFrame | None:
    path = processed_dir / name
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False) if path.is_file() else None


def load_inputs(processed_dir: Path, config: QualityConfig, bookings_file: str = "bookings.csv") -> dict[str, pd.DataFrame | None]:
    bookings = read_source(processed_dir, bookings_file)
    if bookings is None:
        raise FileNotFoundError("Bokningsunderlaget är inte förberett. Förbered underlaget under Underlag först.")
    return {"bookings": bookings, "register": read_source(processed_dir, config.register["file"]), "linkage": read_source(processed_dir, config.linkage["file"]),
            "ladok": read_source(processed_dir, config.coverage.get("file", "ladok_activities.csv"))}


def build_report(bookings: pd.DataFrame, classified: pd.DataFrame, config: QualityConfig, window: dict[str, Any], missing_sources: list[str]) -> dict[str, Any]:
    col = config.columns
    frame = classified.assign(address=bookings[col["address"]].str.strip(), status=bookings[col["status"]].str.strip())
    flag_counts = pd.Series([f for flags in frame["flags"] for f in flags], dtype=str).value_counts().to_dict()
    candidate_counts = pd.Series([c for ids in frame["candidate_rule_ids"] for c in ids], dtype=str).value_counts().to_dict()
    by_address = {}
    for address, group in frame.groupby("address"):
        counts = group["resource_identification"].value_counts().to_dict()
        by_address[address or "(tom adress)"] = {"rows": int(len(group)), **{name: int(counts.get(name, 0)) for name in IDENTIFICATIONS}}
    live = frame[frame["status_class"] != "cancelled"]
    return {
        "config": {"version": config.version, "path": config.path, "sha256": config.digest,
                   "verified_rules": [r.id for r in config.rules if r.verified], "unverified_rules": [r.id for r in config.rules if not r.verified]},
        "rows": int(len(frame)), "rows_not_cancelled": int(len(live)), "missing_sources": missing_sources,
        "resource_identification": {name: int((live["resource_identification"] == name).sum()) for name in IDENTIFICATIONS},
        "resource_identification_by_address": by_address,
        "declared_address_level_rows": int(live["declared_address_level"].sum()),
        "flags": {name: int(count) for name, count in flag_counts.items()},
        "status_classes": {name: int(count) for name, count in frame["status_class"].value_counts().items()},
        "unclassified_statuses": {name: int(count) for name, count in frame[frame["status_class"] == "unclassified"]["status"].value_counts().items()},
        "source_coverage": {"ladok": {**window, "rows_within": int((live["ladok_coverage"] == "within").sum()), "rows_outside": int((live["ladok_coverage"] == "outside").sum()),
                                      "rows_unknown": int((live["ladok_coverage"] == "unknown").sum())}},
        "link_certainty": {name: int((live["link_certainty"] == name).sum()) for name in LINKS},
        "candidate_rule_matches": {name: int(count) for name, count in candidate_counts.items()},
        "note": ("Rapporten beskriver vad datat identifierar och hur säkert det är. Den säger inte varför uppgifter saknas och styr inget i planeringen. "
                 "Overifierade regler har inte klassificerat något; de visas bara som kandidater."),
    }


def assess(processed_dir: Path, config_path: Path | None = None, bookings_file: str = "bookings.csv") -> dict[str, Any]:
    """Classify the booking extract in `processed_dir` and report it. Missing optional sources are named, not guessed."""
    config = load_config(config_path)
    inputs = load_inputs(processed_dir, config, bookings_file)
    classified = classify(inputs["bookings"], config, inputs["register"], inputs["linkage"], inputs["ladok"])
    missing = [name for name in ("register", "linkage", "ladok") if inputs[name] is None]
    return build_report(inputs["bookings"], classified, config, ladok_window(config, inputs["ladok"]), missing)
