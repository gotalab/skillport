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


def test_split_package_versions_stay_synchronized():
    root = Path(__file__).resolve().parents[2]
    cli = _read_toml(root / "pyproject.toml")
    core = _read_toml(root / "packages" / "skillport-core" / "pyproject.toml")
    mcp = _read_toml(root / "packages" / "skillport-mcp" / "pyproject.toml")

    version = cli["project"]["version"]
    assert core["project"]["version"] == version
    assert mcp["project"]["version"] == version
    assert f"skillport-core=={version}" in cli["project"]["dependencies"]
    assert f"skillport-core=={version}" in mcp["project"]["dependencies"]


def test_root_dev_environment_installs_mcp_workspace_command():
    root = Path(__file__).resolve().parents[2]
    data = _read_toml(root / "pyproject.toml")
    version = data["project"]["version"]

    dev_deps = data["dependency-groups"]["dev"]
    assert f"skillport-mcp=={version}" in dev_deps
    assert data["tool"]["uv"]["sources"]["skillport-mcp"] == {"workspace": True}
    assert "packages/skillport-mcp" in data["tool"]["uv"]["workspace"]["members"]


def test_workspace_uses_single_root_lockfile():
    root = Path(__file__).resolve().parents[2]
    nested_locks = sorted(root.glob("packages/*/uv.lock"))
    assert not nested_locks, f"Nested package lockfiles drift from root uv.lock: {nested_locks}"
