from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import unquote


MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "data:")

CANONICAL_DOCUMENTS = (
    "docs/README.md",
    "docs/KRAV_OCH_STATUS.md",
    "docs/ABC_SCENARIOMODELL.md",
    "docs/KONCEPTUELL_KRAVSPECIFIKATION.md",
    "docs/GEMENSAM_OPTIMERINGSDESIGN.md",
    "docs/OBEROENDE_EFTERVALIDERING.md",
    "docs/DATAMODELL.md",
    "docs/KOSTNADSMODELL.md",
    "docs/BLOCKERANDE_DATAGAP.md",
)

RETIRED_PATHS = (
    "Slutsatser_tentalokaler_2026-10-06.md",
    "Uppdrag_Claude_Codex_tentalokaler_PoC.md",
    "docs/DOMANMODELL.md",
    "docs/GAP_ANALYS_MOT_KRAVSPECIFIKATION.md",
    "docs/KAPACITETSFORTECKNING.md",
    "docs/KODGRANSKNING_OCH_CODEX_UPPDRAG_2026-10-08.md",
    "docs/KRAVUPPFYLLNAD.md",
    "docs/MALARKITEKTUR_ANALYS_2026-10-09.md",
    "docs/OPTIMERINGSUNDERLAG.md",
    "docs/OVERLAMNING_CLAUDE_2026-10-12.md",
    "docs/prototyp/index.html",
)


@dataclass(frozen=True)
class DocumentationIssue:
    source: Path
    message: str


def markdown_files(repo_root: Path) -> list[Path]:
    files = [repo_root / "README.md", repo_root / "AGENTS.md"]
    files.extend(sorted((repo_root / "docs").rglob("*.md")))
    return [path for path in files if path.is_file()]


def _link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    # A quoted Markdown title follows the path. Project paths do not contain spaces.
    return target.split(maxsplit=1)[0]


def check_links(repo_root: Path) -> list[DocumentationIssue]:
    issues: list[DocumentationIssue] = []
    for source in markdown_files(repo_root):
        text = source.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            target = _link_target(match.group(1))
            if not target or target.startswith("#") or target.lower().startswith(EXTERNAL_PREFIXES):
                continue
            path_part = unquote(target.split("#", 1)[0])
            if not path_part:
                continue
            resolved = (source.parent / path_part).resolve()
            if not resolved.exists():
                issues.append(
                    DocumentationIssue(
                        source.relative_to(repo_root),
                        f"bruten lokal länk: {target}",
                    )
                )
    return issues


def check_structure(repo_root: Path) -> list[DocumentationIssue]:
    issues: list[DocumentationIssue] = []
    for relative_path in CANONICAL_DOCUMENTS:
        if not (repo_root / relative_path).is_file():
            issues.append(DocumentationIssue(Path(relative_path), "kanoniskt dokument saknas"))
    for relative_path in RETIRED_PATHS:
        if (repo_root / relative_path).exists():
            issues.append(DocumentationIssue(Path(relative_path), "pensionerad fil har återinförts"))
    history_root = repo_root / "docs" / "historik"
    for path in sorted(history_root.rglob("*.md")):
        if path == history_root / "README.md":
            continue
        if "historisk" not in path.read_text(encoding="utf-8").lower():
            issues.append(
                DocumentationIssue(path.relative_to(repo_root), "historikmärkning saknas")
            )
    return issues


def check(repo_root: Path) -> list[DocumentationIssue]:
    return check_structure(repo_root) + check_links(repo_root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Kontrollera dokumentationsstruktur och länkar.")
    parser.add_argument("repo_root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    issues = check(repo_root)
    if issues:
        for issue in issues:
            print(f"ERROR {issue.source}: {issue.message}")
        return 1
    print(f"OK: {len(markdown_files(repo_root))} Markdown-filer kontrollerade.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
