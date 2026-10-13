"""`python -m tentaoptimering.booking_quality`: assess a prepared booking extract and print or save the report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..paths import REPO_ROOT
from . import assess


def main() -> None:
    parser = argparse.ArgumentParser(description="Beskriv datakvaliteten i det förberedda bokningsuttaget (ändrar ingenting).")
    parser.add_argument("--processed-dir", type=Path, default=REPO_ROOT / "data" / "processed")
    parser.add_argument("--config", type=Path, help="Konfiguration; standard config/booking_data_quality.toml.")
    parser.add_argument("--bookings-file", default="bookings.csv")
    parser.add_argument("--output", type=Path, help="Skriv rapporten som JSON hit i stället för att skriva ut den.")
    args = parser.parse_args()
    report = assess(args.processed_dir, args.config, args.bookings_file)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"Rapport sparad: {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
