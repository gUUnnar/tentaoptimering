"""Static inventory of the code base for the re-architecture (development tool, not product code).

Reports, from the source tree only:
  * import graph between ``tentaoptimering`` modules,
  * reachability from the production entry points,
  * modules that only tests import,
  * public functions/classes that nothing in ``src`` references,
  * API routes, CLI commands and frontend source files (the capability surface).

Usage: ``python tools/inventory.py [--json]``. Standard library only.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "tentaoptimering"
TESTS = ROOT / "tests"
FRONTEND = ROOT / "frontend" / "src"
ENTRY_POINTS = ("api", "cli", "desktop")


def _modules() -> dict[str, Path]:
    return {path.stem: path for path in sorted(SRC.glob("*.py"))}


def _imports(path: Path, known: set[str]) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            if node.module:
                found.add(node.module.split(".")[0])
            else:
                found.update(alias.name for alias in node.names)
    return found & known


def _reachable(graph: dict[str, set[str]], roots: tuple[str, ...]) -> set[str]:
    seen: set[str] = set()
    stack = [root for root in roots if root in graph]
    while stack:
        module = stack.pop()
        if module not in seen:
            seen.add(module)
            stack.extend(graph.get(module, ()))
    return seen


def _test_imports(known: set[str]) -> dict[str, set[str]]:
    used: dict[str, set[str]] = {}
    for path in sorted(TESTS.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("tentaoptimering"):
                parts = node.module.split(".")
                names = [parts[1]] if len(parts) > 1 else [alias.name for alias in node.names]
                for name in names:
                    if name in known:
                        used.setdefault(name, set()).add(path.stem)
    return used


def _public_defs(modules: dict[str, Path]) -> list[tuple[str, str, int]]:
    text = {name: path.read_text(encoding="utf-8") for name, path in modules.items()}
    corpus = "\n".join(text.values())
    tests = "\n".join(path.read_text(encoding="utf-8") for path in TESTS.glob("*.py"))
    result = []
    for name, path in modules.items():
        for node in ast.parse(text[name]).body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
                if len(re.findall(rf"\b{re.escape(node.name)}\b", corpus)) <= 1:
                    result.append((name, node.name, len(re.findall(rf"\b{re.escape(node.name)}\b", tests))))
    return result


def _routes() -> list[str]:
    text = (SRC / "api.py").read_text(encoding="utf-8")
    return [f"{m.group(1).upper()} {m.group(2)}" for m in re.finditer(r'@app\.(get|post|put|delete|patch)\("([^"]+)"', text)]


def _cli_commands() -> list[str]:
    text = (SRC / "cli.py").read_text(encoding="utf-8")
    block = re.search(r'"command",.*?choices=\((.*?)\)', text, re.S)
    return re.findall(r'"([a-z-]+)"', block.group(1)) if block else []


def _frontend_files() -> list[str]:
    return sorted(str(path.relative_to(ROOT)).replace("\\", "/") for path in FRONTEND.rglob("*") if path.is_file())


def build_report() -> dict[str, object]:
    modules = _modules()
    known = set(modules)
    graph = {name: _imports(path, known) for name, path in modules.items()}
    reachable = _reachable(graph, ENTRY_POINTS)
    test_use = _test_imports(known)
    imported_by_src = {dep for deps in graph.values() for dep in deps}
    return {
        "modules": sorted(known),
        "import_graph": {name: sorted(deps) for name, deps in graph.items()},
        "unreachable_from_entry_points": sorted(known - reachable - {"__init__"}),
        "only_tests_import": sorted(name for name in known if name not in imported_by_src and name in test_use and name not in ENTRY_POINTS),
        "importers": {name: sorted(name2 for name2, deps in graph.items() if name in deps) for name in sorted(known)},
        "test_importers": {name: sorted(files) for name, files in sorted(test_use.items())},
        "unreferenced_public_defs": [
            {"module": module, "name": name, "test_references": count} for module, name, count in _public_defs(modules)
        ],
        "api_routes": _routes(),
        "cli_commands": _cli_commands(),
        "frontend_files": _frontend_files(),
    }


def main(argv: list[str]) -> int:
    report = build_report()
    if "--json" in argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print(f"Moduler: {len(report['modules'])}")
    print("Utan väg från produktionsingångar:", ", ".join(report["unreachable_from_entry_points"]) or "-")
    print("Importeras bara av tester:", ", ".join(report["only_tests_import"]) or "-")
    print("Oreferererade publika symboler:")
    for item in report["unreferenced_public_defs"]:
        print(f"  {item['module']}.{item['name']} (tester: {item['test_references']})")
    print(f"API-rutter: {len(report['api_routes'])}; CLI-kommandon: {len(report['cli_commands'])}; frontendfiler: {len(report['frontend_files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
