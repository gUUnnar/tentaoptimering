"""Pre-check of a source directory: which of the expected Excel files are there, before a long preparation is started."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import SourceFiles


def file_facts(path: Path) -> dict[str, Any]:
    """Size and modification time of a file, as recorded in a manifest and compared when checking staleness."""
    info = path.stat()
    modified = datetime.fromtimestamp(info.st_mtime, tz=timezone.utc).isoformat(timespec="seconds")
    return {"bytes": info.st_size, "modified_ns": info.st_mtime_ns, "modified": modified}


def inspect_source_dir(source_dir: Path | str | None) -> dict[str, Any]:
    """Expected source files of `source_dir` with what was found; `ready` only when all of them exist."""
    if not source_dir:
        return {"source_dir": None, "exists": False, "ready": False, "files": []}
    folder = Path(source_dir)
    if not folder.is_dir():
        return {"source_dir": str(folder), "exists": False, "ready": False, "files": []}
    files = []
    for role, label, path in SourceFiles(source_dir=folder).roles():
        found = path.is_file()
        files.append({"role": role, "label": label, "filename": path.name, "found": found, **(file_facts(path) if found else {})})
    return {"source_dir": str(folder), "exists": True, "ready": all(item["found"] for item in files), "files": files}
