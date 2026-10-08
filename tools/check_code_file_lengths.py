"""Kontrollera att projektets Python-filer följer policyn för filstorlek."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


TARGET_LINES = 500
STRONG_WARNING_LINES = 800
MANDATORY_SPLIT_LINES = 1000
CODE_DIRECTORIES = ("src", "tests", "tools")


@dataclass(frozen=True)
class FileLengthAssessment:
    path: Path
    lines: int
    level: str


def line_count(path: Path) -> int:
    with path.open(encoding="utf-8") as source:
        return sum(1 for _ in source)


def assess(path: Path, lines: int) -> FileLengthAssessment:
    if lines >= MANDATORY_SPLIT_LINES:
        level = "ERROR"
    elif lines >= STRONG_WARNING_LINES:
        level = "STRONG WARNING"
    elif lines > TARGET_LINES:
        level = "NOTICE"
    else:
        level = "OK"
    return FileLengthAssessment(path=path, lines=lines, level=level)


def find_python_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for directory in CODE_DIRECTORIES:
        root = repo_root / directory
        if root.is_dir():
            files.extend(root.rglob("*.py"))
    return sorted(files)


def check(repo_root: Path) -> list[FileLengthAssessment]:
    return [
        assess(path.relative_to(repo_root), line_count(path))
        for path in find_python_files(repo_root)
    ]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    assessments = check(repo_root)
    for item in assessments:
        if item.level != "OK":
            print(f"{item.level}: {item.path} has {item.lines} lines.")

    errors = [item for item in assessments if item.level == "ERROR"]
    if errors:
        print(
            f"{len(errors)} Python file(s) reached {MANDATORY_SPLIT_LINES} lines and must be split.",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK: {len(assessments)} Python files checked; target <={TARGET_LINES}, "
        f"strong warning at {STRONG_WARNING_LINES}, mandatory split at {MANDATORY_SPLIT_LINES}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
