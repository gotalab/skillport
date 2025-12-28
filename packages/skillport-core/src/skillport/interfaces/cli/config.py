"""Project-level configuration resolution for CLI.

Implements SPEC2-CLI Section 4.2: Configuration resolution order.
Priority: env var → .skillportrc → pyproject.toml → default

Note: MCP Server uses environment variables only. This module is CLI-only.
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Optional

import yaml


def _expanduser_cross_platform(value: str) -> Path:
    raw = (value or "").strip()
    if raw == "~":
        return Path.home()
    if raw.startswith("~/") or raw.startswith("~\\"):
        rest = raw[2:]
        if not rest:
            return Path.home()
        parts = PurePosixPath(rest.replace("\\", "/")).parts
        return Path.home().joinpath(*parts)
    return Path(raw).expanduser()


@dataclass(frozen=True)
class ProjectConfig:
    """Project-level configuration from .skillportrc or pyproject.toml.

    Attributes:
        skills_dir: Path to skills directory.
        instructions: List of instruction files to update on sync.
        source: Where the config was loaded from (for display).
    """

    skills_dir: Path
    instructions: list[str]
    source: str  # e.g., ".skillportrc", "pyproject.toml", "default"

    @classmethod
    def from_skillportrc(cls, path: Path) -> Optional["ProjectConfig"]:
        """Load config from .skillportrc YAML file.

        Args:
            path: Path to .skillportrc file.

        Returns:
            ProjectConfig if valid, None otherwise.
        """
        if not path.exists():
            return None

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError:
            return None

        skills_dir = data.get("skills_dir")
        if not skills_dir:
            return None

        # Resolve relative paths from config file location
        skills_path = _expanduser_cross_platform(str(skills_dir))
        if not skills_path.is_absolute():
            skills_path = (path.parent / skills_path).resolve()

        instructions = data.get("instructions", [])
        if isinstance(instructions, str):
            instructions = [instructions]

        return cls(
            skills_dir=skills_path,
            instructions=instructions,
            source=".skillportrc",
        )

    @classmethod
    def from_pyproject(cls, path: Path) -> Optional["ProjectConfig"]:
        """Load config from pyproject.toml [tool.skillport] section.

        Args:
            path: Path to pyproject.toml file.

        Returns:
            ProjectConfig if valid, None otherwise.
        """
        if not path.exists():
            return None

        # Python 3.10 doesn't have tomllib, skip pyproject.toml support
        if sys.version_info < (3, 11):
            return None

        try:
            import tomllib

            with open(path, "rb") as f:
                data = tomllib.load(f)
        except Exception:
            return None

        tool_config = data.get("tool", {}).get("skillport", {})
        if not tool_config:
            return None

        skills_dir = tool_config.get("skills_dir")
        if not skills_dir:
            return None

        # Resolve relative paths from config file location
        skills_path = _expanduser_cross_platform(str(skills_dir))
        if not skills_path.is_absolute():
            skills_path = (path.parent / skills_path).resolve()

        instructions = tool_config.get("instructions", [])
        if isinstance(instructions, str):
            instructions = [instructions]

        return cls(
            skills_dir=skills_path,
            instructions=instructions,
            source="pyproject.toml",
        )

    @classmethod
    def from_env(cls) -> Optional["ProjectConfig"]:
        """Load config from environment variable.

        Returns:
            ProjectConfig if SKILLPORT_SKILLS_DIR is set, None otherwise.
        """
        skills_dir = os.getenv("SKILLPORT_SKILLS_DIR")
        if not skills_dir:
            return None

        return cls(
            skills_dir=_expanduser_cross_platform(skills_dir).resolve(),
            instructions=[],  # Env var doesn't specify instructions
            source="environment",
        )

    @classmethod
    def default(cls) -> "ProjectConfig":
        """Return default configuration.

        Returns:
            ProjectConfig with default values.
        """
        return cls(
            skills_dir=(Path.home() / ".skillport" / "skills").resolve(),
            instructions=["AGENTS.md"],
            source="default",
        )


def load_project_config(cwd: Path | None = None) -> ProjectConfig:
    """Load project configuration with priority resolution.

    Resolution order (SPEC2-CLI Section 4.2.1):
    1. Environment variable (SKILLPORT_SKILLS_DIR)
    2. .skillportrc in current directory
    3. pyproject.toml [tool.skillport] in current directory
    4. Default (~/.skillport/skills)

    Args:
        cwd: Current working directory. Defaults to Path.cwd().

    Returns:
        ProjectConfig from highest priority source.
    """
    if cwd is None:
        cwd = Path.cwd()

    # 1. Environment variable (highest priority)
    if config := ProjectConfig.from_env():
        return config

    # 2. .skillportrc
    if config := ProjectConfig.from_skillportrc(cwd / ".skillportrc"):
        return config

    # 3. pyproject.toml [tool.skillport]
    if config := ProjectConfig.from_pyproject(cwd / "pyproject.toml"):
        return config

    # 4. Default
    return ProjectConfig.default()


__all__ = ["ProjectConfig", "load_project_config"]
