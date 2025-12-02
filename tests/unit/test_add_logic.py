"""Unit tests for add command logic (SPEC2-CLI Section 3.3)."""

import pytest
from pathlib import Path

from skillport.modules.skills.internal.manager import (
    detect_skills,
    add_local,
    add_builtin,
    BUILTIN_SKILLS,
    _validate_skill_file,
)
from skillport.shared.config import Config


def _create_skill(path: Path, name: str, description: str = "Test description") -> Path:
    """Helper to create a valid skill directory."""
    skill_dir = path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\nBody content",
        encoding="utf-8"
    )
    return skill_dir


class TestDetectSkills:
    """Skill detection tests."""

    def test_single_skill_at_root(self, tmp_path: Path):
        """Single SKILL.md at root → 1 skill."""
        (tmp_path / "SKILL.md").write_text(
            "---\nname: root-skill\ndescription: Root skill\n---\nbody",
            encoding="utf-8"
        )
        skills = detect_skills(tmp_path)
        assert len(skills) == 1
        assert skills[0].name == "root-skill"

    def test_multiple_skills_in_children(self, tmp_path: Path):
        """Multiple child dirs with SKILL.md → N skills."""
        _create_skill(tmp_path, "skill-a")
        _create_skill(tmp_path, "skill-b")
        _create_skill(tmp_path, "skill-c")

        skills = detect_skills(tmp_path)
        assert len(skills) == 3
        names = {s.name for s in skills}
        assert names == {"skill-a", "skill-b", "skill-c"}

    def test_no_skill_md_returns_empty(self, tmp_path: Path):
        """No SKILL.md → empty list."""
        (tmp_path / "some-file.txt").write_text("hello", encoding="utf-8")
        (tmp_path / "subdir").mkdir()

        skills = detect_skills(tmp_path)
        assert len(skills) == 0

    def test_mixed_dirs_only_detects_skills(self, tmp_path: Path):
        """Only dirs with SKILL.md are detected."""
        _create_skill(tmp_path, "valid-skill")
        (tmp_path / "not-a-skill").mkdir()
        (tmp_path / "not-a-skill" / "README.md").write_text("readme", encoding="utf-8")

        skills = detect_skills(tmp_path)
        assert len(skills) == 1
        assert skills[0].name == "valid-skill"

    def test_detects_skill_name_from_frontmatter(self, tmp_path: Path):
        """Skill name comes from frontmatter, not dir name."""
        skill_dir = tmp_path / "dir-name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: frontmatter-name\ndescription: desc\n---\nbody",
            encoding="utf-8"
        )
        skills = detect_skills(tmp_path)
        assert len(skills) == 1
        # Note: name comes from frontmatter
        assert skills[0].name == "frontmatter-name"

    def test_missing_required_frontmatter_is_fatal(self, tmp_path: Path):
        """Missing name/description should raise at validation time."""
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: \n---\nbody",
            encoding="utf-8"
        )
        target = tmp_path / "target"
        cfg = Config(skills_dir=target)
        skills = detect_skills(tmp_path)

        with pytest.raises(ValueError):
            _validate_skill_file(skill_dir)

        results = add_local(
            source_path=tmp_path,
            skills=skills,
            config=cfg,
            keep_structure=False,
            force=False,
        )
        assert len(results) == 1
        assert not results[0].success
        assert "Invalid SKILL.md" in results[0].message

    def test_source_not_found_raises(self, tmp_path: Path):
        """Non-existent path → FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            detect_skills(tmp_path / "nonexistent")

    def test_source_is_file_raises(self, tmp_path: Path):
        """File path → ValueError."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content", encoding="utf-8")
        with pytest.raises(ValueError, match="directory"):
            detect_skills(file_path)


class TestAddLocalNamespace:
    """Namespace handling in add_local."""

    def test_keep_structure_true_uses_namespace(self, tmp_path: Path):
        """keep_structure=True → skills/<namespace>/<skill>/"""
        source = tmp_path / "source"
        _create_skill(source, "skill-a")
        _create_skill(source, "skill-b")

        target = tmp_path / "target"
        cfg = Config(skills_dir=target)
        skills = detect_skills(source)

        results = add_local(
            source_path=source,
            skills=skills,
            config=cfg,
            keep_structure=True,
            force=False,
        )

        assert all(r.success for r in results)
        # Default namespace is source dir name
        assert (target / "source" / "skill-a" / "SKILL.md").exists()
        assert (target / "source" / "skill-b" / "SKILL.md").exists()

    def test_keep_structure_false_flattens(self, tmp_path: Path):
        """keep_structure=False → skills/<skill>/"""
        source = tmp_path / "source"
        _create_skill(source, "skill-a")
        _create_skill(source, "skill-b")

        target = tmp_path / "target"
        cfg = Config(skills_dir=target)
        skills = detect_skills(source)

        results = add_local(
            source_path=source,
            skills=skills,
            config=cfg,
            keep_structure=False,
            force=False,
        )

        assert all(r.success for r in results)
        assert (target / "skill-a" / "SKILL.md").exists()
        assert (target / "skill-b" / "SKILL.md").exists()
        # No namespace directory
        assert not (target / "source").exists()

    def test_custom_namespace_override(self, tmp_path: Path):
        """namespace_override → uses custom namespace."""
        source = tmp_path / "source"
        _create_skill(source, "skill-a")

        target = tmp_path / "target"
        cfg = Config(skills_dir=target)
        skills = detect_skills(source)

        results = add_local(
            source_path=source,
            skills=skills,
            config=cfg,
            keep_structure=True,
            force=False,
            namespace_override="my-team",
        )

        assert all(r.success for r in results)
        assert results[0].skill_id == "my-team/skill-a"
        assert (target / "my-team" / "skill-a" / "SKILL.md").exists()


class TestAddLocalOverwrite:
    """Overwrite behavior in add_local."""

    def test_existing_skill_without_force_skipped(self, tmp_path: Path):
        """Existing skill without --force → skipped."""
        source = tmp_path / "source"
        _create_skill(source, "skill-a")

        target = tmp_path / "target"
        # Pre-create existing skill
        _create_skill(target, "skill-a")
        original_content = (target / "skill-a" / "SKILL.md").read_text()

        cfg = Config(skills_dir=target)
        skills = detect_skills(source)

        results = add_local(
            source_path=source,
            skills=skills,
            config=cfg,
            keep_structure=False,
            force=False,
        )

        assert len(results) == 1
        assert not results[0].success
        assert "exists" in results[0].message.lower()
        # Content unchanged
        assert (target / "skill-a" / "SKILL.md").read_text() == original_content

    def test_existing_skill_with_force_overwritten(self, tmp_path: Path):
        """Existing skill with --force → overwritten."""
        source = tmp_path / "source"
        source_skill = _create_skill(source, "skill-a")
        new_content = "---\nname: skill-a\ndescription: Updated\n---\nNew body"
        (source_skill / "SKILL.md").write_text(new_content, encoding="utf-8")

        target = tmp_path / "target"
        _create_skill(target, "skill-a")

        cfg = Config(skills_dir=target)
        skills = detect_skills(source)

        results = add_local(
            source_path=source,
            skills=skills,
            config=cfg,
            keep_structure=False,
            force=True,
        )

        assert len(results) == 1
        assert results[0].success
        # Content updated
        assert "Updated" in (target / "skill-a" / "SKILL.md").read_text()

    def test_mixed_new_and_existing(self, tmp_path: Path):
        """Some new, some existing → partial success."""
        source = tmp_path / "source"
        _create_skill(source, "skill-a")
        _create_skill(source, "skill-b")
        _create_skill(source, "skill-c")

        target = tmp_path / "target"
        _create_skill(target, "skill-a")  # exists

        cfg = Config(skills_dir=target)
        skills = detect_skills(source)

        results = add_local(
            source_path=source,
            skills=skills,
            config=cfg,
            keep_structure=False,
            force=False,
        )

        success = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        assert len(success) == 2  # skill-b, skill-c
        assert len(failed) == 1  # skill-a
        assert failed[0].skill_id == "skill-a"


class TestAddBuiltin:
    """Built-in skill add tests."""

    @pytest.mark.parametrize("builtin_name", list(BUILTIN_SKILLS.keys()))
    def test_add_builtin_skills(self, tmp_path: Path, builtin_name: str):
        """All built-in skills can be added."""
        cfg = Config(skills_dir=tmp_path)
        result = add_builtin(builtin_name, config=cfg, force=False)

        assert result.success
        assert (tmp_path / builtin_name / "SKILL.md").exists()

    def test_add_unknown_builtin_raises(self, tmp_path: Path):
        """Unknown built-in name → ValueError."""
        cfg = Config(skills_dir=tmp_path)
        with pytest.raises(ValueError, match="Unknown"):
            add_builtin("nonexistent-builtin", config=cfg, force=False)

    def test_builtin_exists_without_force_fails(self, tmp_path: Path):
        """Existing built-in without --force → fails."""
        cfg = Config(skills_dir=tmp_path)

        # Add first time
        result1 = add_builtin("hello-world", config=cfg, force=False)
        assert result1.success

        # Add again without force
        result2 = add_builtin("hello-world", config=cfg, force=False)
        assert not result2.success
        assert "exists" in result2.message.lower()

    def test_builtin_exists_with_force_overwrites(self, tmp_path: Path):
        """Existing built-in with --force → overwrites."""
        cfg = Config(skills_dir=tmp_path)

        # Add first time
        add_builtin("hello-world", config=cfg, force=False)

        # Modify the file
        (tmp_path / "hello-world" / "SKILL.md").write_text("modified", encoding="utf-8")

        # Add again with force
        result = add_builtin("hello-world", config=cfg, force=True)
        assert result.success
        # Content restored to original
        content = (tmp_path / "hello-world" / "SKILL.md").read_text()
        assert "Hello World Skill" in content


class TestSkillRenameSingle:
    """Single skill rename with --name option."""

    def test_rename_single_skill(self, tmp_path: Path):
        """--name renames single skill."""
        source = tmp_path / "source"
        _create_skill(source, "original-name")

        target = tmp_path / "target"
        cfg = Config(skills_dir=target)
        skills = detect_skills(source)

        results = add_local(
            source_path=source,
            skills=skills,
            config=cfg,
            keep_structure=False,
            force=False,
            rename_single_to="new-name",
        )

        assert len(results) == 1
        assert results[0].success
        assert results[0].skill_id == "new-name"
        assert (target / "new-name" / "SKILL.md").exists()
        # frontmatter.name should be updated
        content = (target / "new-name" / "SKILL.md").read_text()
        assert "name: new-name" in content

    def test_rename_ignored_for_multiple(self, tmp_path: Path):
        """--name ignored when multiple skills."""
        source = tmp_path / "source"
        _create_skill(source, "skill-a")
        _create_skill(source, "skill-b")

        target = tmp_path / "target"
        cfg = Config(skills_dir=target)
        skills = detect_skills(source)

        results = add_local(
            source_path=source,
            skills=skills,
            config=cfg,
            keep_structure=False,
            force=False,
            rename_single_to="ignored-name",
        )

        # Names not changed because len(skills) > 1
        skill_ids = {r.skill_id for r in results}
        assert skill_ids == {"skill-a", "skill-b"}


class TestSymlinkRejection:
    """Symlink security tests."""

    def test_symlink_in_skill_rejected(self, tmp_path: Path):
        """Symlinks in skill directory → rejected."""
        source = tmp_path / "source"
        skill_dir = _create_skill(source, "skill-with-link")

        # Create a symlink
        link_path = skill_dir / "link.txt"
        target_file = tmp_path / "outside.txt"
        target_file.write_text("secret", encoding="utf-8")
        link_path.symlink_to(target_file)

        target = tmp_path / "target"
        cfg = Config(skills_dir=target)
        skills = detect_skills(source)

        results = add_local(
            source_path=source,
            skills=skills,
            config=cfg,
            keep_structure=False,
            force=False,
        )

        # Should fail due to symlink
        assert len(results) == 1
        assert not results[0].success
        assert "symlink" in results[0].message.lower()
