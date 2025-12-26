"""Dependency boundary checks for CLI-only install path."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _read_toml(path: Path) -> dict:
    try:
        import tomllib
    except ModuleNotFoundError:  # Python <3.11
        import tomli as tomllib

    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_cli_import_does_not_load_index_deps():
    code = r"""
import sys
import skillport.interfaces.cli.app  # noqa: F401
blocked = {"lancedb", "fastmcp", "tantivy", "openai", "skillport.modules.indexing"}
loaded = set(sys.modules)
found = sorted(name for name in blocked if name in loaded)
if found:
    raise SystemExit(f"Unexpected imports: {found}")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_cli_source_has_no_index_imports():
    cli_root = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "skillport-core"
        / "src"
        / "skillport"
        / "interfaces"
        / "cli"
    )
    blocked_markers = {
        "modules.indexing",
        "interfaces.mcp",
        "fastmcp",
        "lancedb",
        "tantivy",
        "openai",
    }
    offenders: list[Path] = []
    for path in cli_root.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in blocked_markers):
            offenders.append(path)

    assert not offenders, f"Blocked imports found in CLI files: {offenders}"


def test_cli_dependencies_do_not_include_server_deps():
    root = Path(__file__).resolve().parents[2]
    data = _read_toml(root / "pyproject.toml")
    deps = {d.split(";")[0].strip() for d in data["project"]["dependencies"]}
    blocked = {"lancedb", "fastmcp", "tantivy", "openai"}
    assert not {d for d in deps for b in blocked if d.startswith(b)}


def test_core_dependencies_do_not_include_server_deps():
    root = Path(__file__).resolve().parents[2]
    data = _read_toml(root / "packages" / "skillport-core" / "pyproject.toml")
    deps = {d.split(";")[0].strip() for d in data["project"]["dependencies"]}
    blocked = {"lancedb", "fastmcp", "tantivy", "openai"}
    assert not {d for d in deps for b in blocked if d.startswith(b)}
