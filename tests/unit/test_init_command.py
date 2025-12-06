"""Unit tests for init command (SPEC2-CLI Section 3.1)."""

from pathlib import Path

import yaml

from skillport.interfaces.cli.commands.init import (
    DEFAULT_INSTRUCTIONS,
    DEFAULT_SKILLS_DIRS,
    _create_skillportrc,
)


class TestCreateSkillportrc:
    """Tests for .skillportrc file creation."""

    def test_creates_file(self, tmp_path: Path):
        """Creates .skillportrc file."""
        rc_path = tmp_path / ".skillportrc"
        skills_dir = Path(".agent/skills")
        instructions = ["AGENTS.md"]

        _create_skillportrc(rc_path, skills_dir, instructions)

        assert rc_path.exists()

    def test_writes_skills_dir(self, tmp_path: Path):
        """Writes skills_dir to file."""
        rc_path = tmp_path / ".skillportrc"
        skills_dir = Path(".agent/skills")
        instructions = ["AGENTS.md"]

        _create_skillportrc(rc_path, skills_dir, instructions)

        with open(rc_path) as f:
            data = yaml.safe_load(f)
        assert data["skills_dir"] == ".agent/skills"

    def test_writes_instructions(self, tmp_path: Path):
        """Writes instructions list to file."""
        rc_path = tmp_path / ".skillportrc"
        skills_dir = Path(".agent/skills")
        instructions = ["AGENTS.md"]

        _create_skillportrc(rc_path, skills_dir, instructions)

        with open(rc_path) as f:
            data = yaml.safe_load(f)
        assert data["instructions"] == ["AGENTS.md"]

    def test_includes_comments(self, tmp_path: Path):
        """File includes helpful comments."""
        rc_path = tmp_path / ".skillportrc"
        skills_dir = Path(".agent/skills")
        instructions = ["AGENTS.md"]

        _create_skillportrc(rc_path, skills_dir, instructions)

        content = rc_path.read_text()
        assert "# SkillPort Configuration" in content

    def test_shortens_home_path(self, tmp_path: Path):
        """Converts home directory to ~ in output."""
        rc_path = tmp_path / ".skillportrc"
        skills_dir = Path.home() / ".skillport/skills"
        instructions = ["AGENTS.md"]

        _create_skillportrc(rc_path, skills_dir, instructions)

        with open(rc_path) as f:
            data = yaml.safe_load(f)
        assert data["skills_dir"].startswith("~")


class TestDefaultConstants:
    """Tests for default constants."""

    def test_default_skills_dirs_has_options(self):
        """DEFAULT_SKILLS_DIRS has multiple options."""
        assert len(DEFAULT_SKILLS_DIRS) >= 2
        # Check that at least one option exists with a recognizable path
        displays = [display for display, _ in DEFAULT_SKILLS_DIRS]
        assert any(".agent/skills" in d or ".claude/skills" in d for d in displays)

    def test_default_skills_dirs_tuple_format(self):
        """DEFAULT_SKILLS_DIRS uses (display, actual) tuple format."""
        for item in DEFAULT_SKILLS_DIRS:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_default_instructions_has_agents_md(self):
        """DEFAULT_INSTRUCTIONS includes AGENTS.md."""
        names = [name for name, _ in DEFAULT_INSTRUCTIONS]
        assert "AGENTS.md" in names

    def test_default_instructions_has_gemini_md(self):
        """DEFAULT_INSTRUCTIONS includes GEMINI.md."""
        names = [name for name, _ in DEFAULT_INSTRUCTIONS]
        assert "GEMINI.md" in names

    def test_default_instructions_has_skip_option(self):
        """DEFAULT_INSTRUCTIONS includes None (skip) option."""
        names = [name for name, _ in DEFAULT_INSTRUCTIONS]
        assert None in names
