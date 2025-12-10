"""Unit tests for project-level config resolution (SPEC2-CLI Section 4.2)."""

import sys
from pathlib import Path

import pytest

from skillport.interfaces.cli.config import (
    ProjectConfig,
    load_project_config,
)


class TestProjectConfigFromSkillportrc:
    """Tests for .skillportrc loading."""

    def test_loads_skills_dir(self, tmp_path: Path):
        """Loads skills_dir from .skillportrc."""
        rc_path = tmp_path / ".skillportrc"
        rc_path.write_text("skills_dir: .agent/skills\n")

        config = ProjectConfig.from_skillportrc(rc_path)

        assert config is not None
        assert config.skills_dir == (tmp_path / ".agent/skills").resolve()
        assert config.source == ".skillportrc"

    def test_loads_instructions(self, tmp_path: Path):
        """Loads instructions list from .skillportrc."""
        rc_path = tmp_path / ".skillportrc"
        rc_path.write_text(
            "skills_dir: .agent/skills\ninstructions:\n  - AGENTS.md\n  - GEMINI.md\n"
        )

        config = ProjectConfig.from_skillportrc(rc_path)

        assert config is not None
        assert config.instructions == ["AGENTS.md", "GEMINI.md"]

    def test_single_instruction_as_string(self, tmp_path: Path):
        """Single instruction can be a string (not list)."""
        rc_path = tmp_path / ".skillportrc"
        rc_path.write_text("skills_dir: .agent/skills\ninstructions: AGENTS.md\n")

        config = ProjectConfig.from_skillportrc(rc_path)

        assert config is not None
        assert config.instructions == ["AGENTS.md"]

    def test_expands_tilde(self, tmp_path: Path):
        """Expands ~ in skills_dir path."""
        rc_path = tmp_path / ".skillportrc"
        rc_path.write_text("skills_dir: ~/.skillport/skills\n")

        config = ProjectConfig.from_skillportrc(rc_path)

        assert config is not None
        assert "~" not in str(config.skills_dir)
        assert config.skills_dir == Path.home() / ".skillport/skills"

    def test_returns_none_if_missing(self, tmp_path: Path):
        """Returns None if .skillportrc doesn't exist."""
        rc_path = tmp_path / ".skillportrc"

        config = ProjectConfig.from_skillportrc(rc_path)

        assert config is None

    def test_returns_none_if_no_skills_dir(self, tmp_path: Path):
        """Returns None if skills_dir is missing."""
        rc_path = tmp_path / ".skillportrc"
        rc_path.write_text("instructions:\n  - AGENTS.md\n")

        config = ProjectConfig.from_skillportrc(rc_path)

        assert config is None

    def test_returns_none_on_invalid_yaml(self, tmp_path: Path):
        """Returns None on invalid YAML."""
        rc_path = tmp_path / ".skillportrc"
        rc_path.write_text("skills_dir: [\ninvalid yaml")

        config = ProjectConfig.from_skillportrc(rc_path)

        assert config is None

    def test_empty_instructions_defaults_to_empty_list(self, tmp_path: Path):
        """Empty instructions defaults to empty list."""
        rc_path = tmp_path / ".skillportrc"
        rc_path.write_text("skills_dir: .agent/skills\n")

        config = ProjectConfig.from_skillportrc(rc_path)

        assert config is not None
        assert config.instructions == []


class TestProjectConfigFromPyproject:
    """Tests for pyproject.toml loading."""

    @pytest.mark.skipif(
        sys.version_info < (3, 11),
        reason="tomllib requires Python 3.11+",
    )
    def test_loads_from_tool_skillport(self, tmp_path: Path):
        """Loads from [tool.skillport] section."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.skillport]\nskills_dir = ".agent/skills"\ninstructions = ["AGENTS.md"]\n'
        )

        config = ProjectConfig.from_pyproject(pyproject)

        assert config is not None
        assert config.skills_dir == (tmp_path / ".agent/skills").resolve()
        assert config.instructions == ["AGENTS.md"]
        assert config.source == "pyproject.toml"

    @pytest.mark.skipif(
        sys.version_info < (3, 11),
        reason="tomllib requires Python 3.11+",
    )
    def test_returns_none_if_no_tool_skillport(self, tmp_path: Path):
        """Returns None if [tool.skillport] missing."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.other]\nfoo = "bar"\n')

        config = ProjectConfig.from_pyproject(pyproject)

        assert config is None

    def test_returns_none_if_missing(self, tmp_path: Path):
        """Returns None if pyproject.toml doesn't exist."""
        pyproject = tmp_path / "pyproject.toml"

        config = ProjectConfig.from_pyproject(pyproject)

        assert config is None


class TestProjectConfigFromEnv:
    """Tests for environment variable loading."""

    def test_loads_from_env(self, monkeypatch, tmp_path: Path):
        """Loads skills_dir from SKILLPORT_SKILLS_DIR."""
        monkeypatch.setenv("SKILLPORT_SKILLS_DIR", str(tmp_path / "skills"))

        config = ProjectConfig.from_env()

        assert config is not None
        assert config.skills_dir == tmp_path / "skills"
        assert config.source == "environment"

    def test_returns_none_if_not_set(self, monkeypatch):
        """Returns None if env var not set."""
        monkeypatch.delenv("SKILLPORT_SKILLS_DIR", raising=False)

        config = ProjectConfig.from_env()

        assert config is None

    def test_instructions_empty_from_env(self, monkeypatch, tmp_path: Path):
        """Instructions are empty when loading from env."""
        monkeypatch.setenv("SKILLPORT_SKILLS_DIR", str(tmp_path / "skills"))

        config = ProjectConfig.from_env()

        assert config is not None
        assert config.instructions == []


class TestProjectConfigDefault:
    """Tests for default configuration."""

    def test_default_skills_dir(self):
        """Default skills_dir is ~/.skillport/skills."""
        config = ProjectConfig.default()

        assert config.skills_dir == Path.home() / ".skillport/skills"

    def test_default_instructions(self):
        """Default instructions is AGENTS.md."""
        config = ProjectConfig.default()

        assert config.instructions == ["AGENTS.md"]

    def test_default_source(self):
        """Default source is 'default'."""
        config = ProjectConfig.default()

        assert config.source == "default"


class TestLoadProjectConfig:
    """Tests for load_project_config resolution order."""

    def test_env_takes_priority(self, monkeypatch, tmp_path: Path):
        """Environment variable takes highest priority."""
        # Set up .skillportrc
        rc_path = tmp_path / ".skillportrc"
        rc_path.write_text("skills_dir: .agent/skills\n")

        # Set env var
        monkeypatch.setenv("SKILLPORT_SKILLS_DIR", str(tmp_path / "env-skills"))

        config = load_project_config(tmp_path)

        assert config.source == "environment"
        assert config.skills_dir == tmp_path / "env-skills"

    def test_skillportrc_over_pyproject(self, tmp_path: Path, monkeypatch):
        """skillportrc takes priority over pyproject.toml."""
        monkeypatch.delenv("SKILLPORT_SKILLS_DIR", raising=False)

        # Set up both files
        rc_path = tmp_path / ".skillportrc"
        rc_path.write_text("skills_dir: .skillportrc-skills\n")

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.skillport]\nskills_dir = ".pyproject-skills"\n')

        config = load_project_config(tmp_path)

        assert config.source == ".skillportrc"

    def test_falls_back_to_default(self, tmp_path: Path, monkeypatch):
        """Falls back to default when no config exists."""
        monkeypatch.delenv("SKILLPORT_SKILLS_DIR", raising=False)

        config = load_project_config(tmp_path)

        assert config.source == "default"
        assert config.skills_dir == Path.home() / ".skillport/skills"
