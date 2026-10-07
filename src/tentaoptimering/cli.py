from __future__ import annotations

import argparse
from pathlib import Path

from .paths import REPO_ROOT, default_source_dir
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Läs källdata, skapa normaliserade tabeller och skriv en baslinjerapport."
    )
    parser.add_argument("--source-dir", type=Path, default=default_source_dir())
    parser.add_argument("--processed-dir", type=Path, default=REPO_ROOT / "data" / "processed")
    parser.add_argument("--report-dir", type=Path, default=REPO_ROOT / "reports")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outputs = run_pipeline(args.source_dir, args.processed_dir, args.report_dir)
    print("Baslinjen är skapad:")
    for path in outputs.__dict__.values():
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
