from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SourceFiles:
    source_dir: Path

    @property
    def bookings(self) -> Path:
        return self.source_dir / "Tentaplaceringar_Export_2025-09-01-2026-08-31.xlsx"

    @property
    def ladok(self) -> Path:
        return self.source_dir / "Utsökning Ladok tentander från tidigare termin.xlsx"

    @property
    def leases(self) -> Path:
        return self.source_dir / "2026 Tentamenslokaler.xlsx"

    def validate(self) -> None:
        missing = [path for path in (self.bookings, self.ladok, self.leases) if not path.is_file()]
        if missing:
            names = "\n".join(f"- {path}" for path in missing)
            raise FileNotFoundError(f"Källfiler saknas:\n{names}")


def default_source_dir() -> Path:
    configured = os.environ.get("TENTA_SOURCE_DIR")
    return Path(configured) if configured else REPO_ROOT.parent / "underlag"
