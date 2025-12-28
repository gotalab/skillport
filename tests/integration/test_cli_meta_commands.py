"""Integration tests for skillport meta commands."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from skillport.interfaces.cli.app import app
from skillport.shared.utils import parse_frontmatter

runner = CliRunner()


def _create_skill_with_frontmatter(
    skills_dir: Path,
    name: str,
    *,
    description: str = "Test skill",
    metadata_block: str = "",
) -> Path:
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    frontmatter = f"---\nname: {name}\ndescription: {description}\n"
    if metadata_block:
        frontmatter += f"{metadata_block}\n"
    frontmatter += "---\n# Title\n\nBody."
    (skill_dir / "SKILL.md").write_text(frontmatter, encoding="utf-8")
    return skill_dir


@pytest.fixture
def skills_env(tmp_path: Path, monkeypatch):
    skills = tmp_path / "skills"
    skills.mkdir()
    monkeypatch.setenv("SKILLPORT_SKILLS_DIR", str(skills))
    monkeypatch.setenv("SKILLPORT_EMBEDDING_PROVIDER", "none")
    return skills


class TestMetaSet:
    def test_set_creates_metadata_block(self, skills_env: Path):
        _create_skill_with_frontmatter(skills_env, "skill-a")

        result = runner.invoke(app, ["meta", "set", "skill-a", "author", "gota", "--json"])

        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        assert payload["summary"]["updated"] == 1

        meta, _body = parse_frontmatter(skills_env / "skill-a" / "SKILL.md")
        assert meta["metadata"]["author"] == "gota"

    def test_set_nested_path_preserves_other_metadata(self, skills_env: Path):
        metadata_block = "metadata:\n  author: gota\n  skillport:\n    category: old"
        _create_skill_with_frontmatter(skills_env, "skill-b", metadata_block=metadata_block)

        result = runner.invoke(
            app,
            ["meta", "set", "skill-b", "skillport.category", "new", "--json"],
        )

        assert result.exit_code == 0, result.stdout
        meta, _body = parse_frontmatter(skills_env / "skill-b" / "SKILL.md")
        assert meta["metadata"]["author"] == "gota"
        assert meta["metadata"]["skillport"]["category"] == "new"

    def test_set_dry_run_does_not_write(self, skills_env: Path):
        metadata_block = "metadata:\n  author: old"
        _create_skill_with_frontmatter(skills_env, "skill-c", metadata_block=metadata_block)

        result = runner.invoke(
            app,
            ["meta", "set", "skill-c", "author", "new", "--dry-run", "--json"],
        )

        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        assert payload["results"][0]["status"] == "would_update"

        meta, _body = parse_frontmatter(skills_env / "skill-c" / "SKILL.md")
        assert meta["metadata"]["author"] == "old"

    def test_set_allows_empty_string(self, skills_env: Path):
        metadata_block = "metadata:\n  author: old"
        _create_skill_with_frontmatter(skills_env, "skill-empty", metadata_block=metadata_block)

        result = runner.invoke(
            app,
            ["meta", "set", "skill-empty", "author", "", "--json"],
        )

        assert result.exit_code == 0, result.stdout
        meta, _body = parse_frontmatter(skills_env / "skill-empty" / "SKILL.md")
        assert meta["metadata"]["author"] == ""


class TestMetaBump:
    @pytest.mark.parametrize(
        ("initial", "flag", "expected"),
        [
            ("1.2.3", "--patch", "1.2.4"),
            ("1.2.3", "--minor", "1.3.0"),
            ("1.2.3", "--major", "2.0.0"),
            ("1.2", "--minor", "1.3"),
            ("v1.2.3", "--patch", "v1.2.4"),
        ],
    )
    def test_bump_semver_variants(self, skills_env: Path, initial: str, flag: str, expected: str):
        metadata_block = f'metadata:\n  version: "{initial}"'
        skill_name = f"skill-bump-{initial.replace('.', '-').replace('v', 'v')}"
        _create_skill_with_frontmatter(skills_env, skill_name, metadata_block=metadata_block)

        result = runner.invoke(
            app,
            ["meta", "bump", skill_name, "version", flag, "--json"],
        )

        assert result.exit_code == 0, result.stdout
        meta, _body = parse_frontmatter(skills_env / skill_name / "SKILL.md")
        assert meta["metadata"]["version"] == expected

    def test_bump_patch_two_segments(self, skills_env: Path):
        metadata_block = 'metadata:\n  version: "1.2"'
        _create_skill_with_frontmatter(skills_env, "skill-d", metadata_block=metadata_block)

        result = runner.invoke(
            app,
            ["meta", "bump", "skill-d", "version", "--patch", "--json"],
        )

        assert result.exit_code == 0, result.stdout
        meta, _body = parse_frontmatter(skills_env / "skill-d" / "SKILL.md")
        assert meta["metadata"]["version"] == "1.2.1"

    def test_bump_missing_key_skipped(self, skills_env: Path):
        _create_skill_with_frontmatter(skills_env, "skill-e")

        result = runner.invoke(
            app,
            ["meta", "bump", "skill-e", "version", "--patch", "--json"],
        )

        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        assert payload["summary"]["skipped"] == 1

    def test_bump_non_string_value_skipped(self, skills_env: Path):
        metadata_block = "metadata:\n  version: 1"
        _create_skill_with_frontmatter(skills_env, "skill-nonstr", metadata_block=metadata_block)

        result = runner.invoke(
            app,
            ["meta", "bump", "skill-nonstr", "version", "--patch", "--json"],
        )

        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        assert payload["summary"]["skipped"] == 1
        meta, _body = parse_frontmatter(skills_env / "skill-nonstr" / "SKILL.md")
        assert meta["metadata"]["version"] == 1

    def test_bump_invalid_version_errors(self, skills_env: Path):
        metadata_block = 'metadata:\n  version: "alpha"'
        _create_skill_with_frontmatter(skills_env, "skill-f", metadata_block=metadata_block)

        result = runner.invoke(
            app,
            ["meta", "bump", "skill-f", "version", "--patch", "--json"],
        )

        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload["summary"]["errors"] == 1


class TestMetaShow:
    def test_show_json_metadata(self, skills_env: Path):
        metadata_block = "metadata:\n  author: gota"
        _create_skill_with_frontmatter(skills_env, "skill-g", metadata_block=metadata_block)

        result = runner.invoke(app, ["meta", "show", "skill-g", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["results"][0]["metadata"]["author"] == "gota"

    def test_show_multiple_human_includes_ids(self, skills_env: Path):
        _create_skill_with_frontmatter(skills_env, "skill-h")
        _create_skill_with_frontmatter(skills_env, "skill-i")

        result = runner.invoke(app, ["meta", "show", "skill-h", "skill-i"])

        assert result.exit_code == 0
        assert "skill-h" in result.stdout
        assert "skill-i" in result.stdout

    def test_show_json_date_metadata_is_string(self, skills_env: Path):
        metadata_block = "metadata:\n  released: 2024-01-01"
        _create_skill_with_frontmatter(skills_env, "skill-date", metadata_block=metadata_block)

        result = runner.invoke(app, ["meta", "show", "skill-date", "--json"])

        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        assert payload["results"][0]["metadata"]["released"] == "2024-01-01"

    def test_show_invalid_skill_id_reports_error(self, skills_env: Path):
        result = runner.invoke(app, ["meta", "show", "../evil", "--json"])

        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload["summary"]["errors"] == 1
        assert "path traversal" in payload["results"][0]["error"].lower()


class TestMetaUnset:
    def test_unset_removes_key(self, skills_env: Path):
        metadata_block = "metadata:\n  author: gota\n  version: \"1.0\""
        _create_skill_with_frontmatter(skills_env, "skill-unset", metadata_block=metadata_block)

        result = runner.invoke(
            app,
            ["meta", "unset", "skill-unset", "author", "--json"],
        )

        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        assert payload["summary"]["updated"] == 1

        meta, _body = parse_frontmatter(skills_env / "skill-unset" / "SKILL.md")
        assert "author" not in meta["metadata"]
        assert meta["metadata"]["version"] == "1.0"

    def test_unset_missing_key_skips(self, skills_env: Path):
        _create_skill_with_frontmatter(skills_env, "skill-unset-missing")

        result = runner.invoke(
            app,
            ["meta", "unset", "skill-unset-missing", "author", "--json"],
        )

        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        assert payload["summary"]["skipped"] == 1

    def test_unset_dry_run_does_not_write(self, skills_env: Path):
        metadata_block = "metadata:\n  author: gota"
        _create_skill_with_frontmatter(skills_env, "skill-unset-dry", metadata_block=metadata_block)

        result = runner.invoke(
            app,
            ["meta", "unset", "skill-unset-dry", "author", "--dry-run", "--json"],
        )

        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        assert payload["results"][0]["status"] == "would_update"

        meta, _body = parse_frontmatter(skills_env / "skill-unset-dry" / "SKILL.md")
        assert meta["metadata"]["author"] == "gota"
