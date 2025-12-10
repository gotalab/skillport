"""Unit tests for skill update functionality."""

import json

from skillport.modules.skills import (
    check_update_available,
    detect_local_modification,
    update_skill,
)
from skillport.modules.skills.internal import (
    compute_content_hash,
    get_missing_skill_ids,
    get_tracked_skill_ids,
    get_untracked_skill_ids,
    record_origin,
    scan_installed_skill_ids,
)
from skillport.shared.config import Config


class TestDetectLocalModification:
    """Tests for local modification detection."""

    def test_no_origin_returns_false(self, tmp_path):
        """No origin info means no tracking, returns False."""
        config = Config(skills_dir=tmp_path / "skills", db_path=tmp_path / "db.lancedb")

        result = detect_local_modification("nonexistent", config=config)

        assert result is False

    def test_no_content_hash_returns_false(self, tmp_path):
        """Origin without content_hash (v1) returns False."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        # Record origin without content_hash (simulating v1)
        record_origin("my-skill", {"source": "test", "kind": "local"}, config=config)

        result = detect_local_modification("my-skill", config=config)

        # Migration adds empty content_hash, which means "unknown", so no modification detected
        assert result is False

    def test_matching_hash_returns_false(self, tmp_path):
        """Matching content_hash means no modification."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        content_hash = compute_content_hash(skill_dir)
        record_origin(
            "my-skill",
            {"source": str(skill_dir), "kind": "local", "content_hash": content_hash},
            config=config,
        )

        result = detect_local_modification("my-skill", config=config)

        assert result is False

    def test_different_hash_returns_true(self, tmp_path):
        """Different content_hash means modification detected."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin(
            "my-skill",
            {"source": str(skill_dir), "kind": "local", "content_hash": "sha256:old_hash"},
            config=config,
        )

        result = detect_local_modification("my-skill", config=config)

        assert result is True


class TestCheckUpdateAvailable:
    """Tests for check_update_available function."""

    def test_no_origin_not_available(self, tmp_path):
        """No origin info means not updatable."""
        config = Config(skills_dir=tmp_path / "skills", db_path=tmp_path / "db.lancedb")

        result = check_update_available("nonexistent", config=config)

        assert result["available"] is False
        assert "no origin" in result["reason"].lower()

    def test_builtin_not_available(self, tmp_path):
        """Builtin skills cannot be updated."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("hello-world", {"source": "hello-world", "kind": "builtin"}, config=config)

        result = check_update_available("hello-world", config=config)

        assert result["available"] is False
        assert "built-in" in result["reason"].lower()

    def test_local_missing_source_not_available(self, tmp_path):
        """Local skill with missing source path is not updatable."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin(
            "my-skill",
            {"source": "/nonexistent/path", "kind": "local"},
            config=config,
        )

        result = check_update_available("my-skill", config=config)

        assert result["available"] is False
        assert "not found" in result["reason"].lower()

    def test_local_with_source_available(self, tmp_path):
        """Local skill with valid source is updatable."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "SKILL.md").write_text("source body")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        # installed copy differs
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("installed body")

        record_origin(
            "my-skill",
            {"source": str(source_dir), "kind": "local"},
            config=config,
        )

        result = check_update_available("my-skill", config=config)

        assert result["available"] is True

    def test_github_same_content_not_available(self, tmp_path, monkeypatch):
        """GitHub skill with same tree hash is up to date."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin(
            "my-skill",
            {
                "source": "https://github.com/user/repo",
                "kind": "github",
                "commit_sha": "abc1234567890",
            },
            config=config,
        )

        # create installed content
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("body")

        def mock_get_remote_tree_hash(parsed, token, path=None):
            return compute_content_hash(skill_dir)

        from skillport.modules.skills.public import update as update_module

        monkeypatch.setattr(update_module, "get_remote_tree_hash", mock_get_remote_tree_hash)

        result = check_update_available("my-skill", config=config)

        assert result["available"] is False
        assert "latest" in result["reason"].lower()

    def test_github_different_content_available(self, tmp_path, monkeypatch):
        """GitHub skill with different tree hash has update available."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin(
            "my-skill",
            {
                "source": "https://github.com/user/repo",
                "kind": "github",
                "commit_sha": "abc1234567890",
            },
            config=config,
        )

        # create installed content
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("old")

        from skillport.modules.skills.public import update as update_module

        def mock_get_remote_tree_hash(parsed, token, path=None):
            return "sha256:remotehash"

        monkeypatch.setattr(update_module, "get_remote_tree_hash", mock_get_remote_tree_hash)

        result = check_update_available("my-skill", config=config)

        assert result["available"] is True
        assert "remote" in result["reason"].lower()

    def test_github_api_failure_not_available(self, tmp_path, monkeypatch):
        """GitHub API failure should not mark as available immediately after add."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin(
            "my-skill",
            {
                "source": "https://github.com/user/repo",
                "kind": "github",
                "commit_sha": "abc1234567890",
            },
            config=config,
        )

        # Mock get_remote_tree_hash to return empty string (API failure)
        def mock_get_remote_tree_hash(parsed, token, path=None):
            return ""

        from skillport.modules.skills.public import update as update_module

        monkeypatch.setattr(update_module, "get_remote_tree_hash", mock_get_remote_tree_hash)

        result = check_update_available("my-skill", config=config)

        assert result["available"] is False
        assert "remote tree" in result["reason"].lower()


class TestUpdateSkill:
    """Tests for update_skill function."""

    def test_update_nonexistent_skill_fails(self, tmp_path):
        """Updating non-existent skill fails."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        result = update_skill("nonexistent", config=config)

        assert result.success is False
        assert "not found" in result.message.lower()

    def test_update_skill_without_origin_fails(self, tmp_path):
        """Updating skill without origin fails."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        result = update_skill("my-skill", config=config)

        assert result.success is False
        assert "no origin" in result.message.lower()

    def test_update_builtin_fails(self, tmp_path):
        """Updating builtin skill fails."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "hello-world"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: hello-world\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("hello-world", {"source": "hello-world", "kind": "builtin"}, config=config)

        result = update_skill("hello-world", config=config)

        assert result.success is False
        assert "built-in" in result.message.lower()

    def test_update_local_modified_without_force_fails(self, tmp_path):
        """Updating locally modified skill without force fails."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nmodified body")

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "SKILL.md").write_text("---\nname: my-skill\n---\noriginal body")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        # Record with original hash
        original_hash = compute_content_hash(source_dir)
        record_origin(
            "my-skill",
            {"source": str(source_dir), "kind": "local", "content_hash": original_hash},
            config=config,
        )

        result = update_skill("my-skill", config=config)

        assert result.success is False
        assert result.local_modified is True
        assert "--force" in result.message

    def test_update_local_modified_with_force_succeeds(self, tmp_path):
        """Updating locally modified skill with force succeeds."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nmodified body")

        source_dir = tmp_path / "source" / "my-skill"
        source_dir.mkdir(parents=True)
        (source_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nnew body")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        # Record with different hash
        record_origin(
            "my-skill",
            {"source": str(source_dir), "kind": "local", "content_hash": "sha256:old"},
            config=config,
        )

        result = update_skill("my-skill", config=config, force=True)

        assert result.success is True
        assert "my-skill" in result.updated

        # Verify content was updated
        assert (skill_dir / "SKILL.md").read_text() == "---\nname: my-skill\n---\nnew body"

    def test_update_local_already_up_to_date(self, tmp_path):
        """Local skill with matching hash is already up to date."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nbody")

        source_dir = tmp_path / "source" / "my-skill"
        source_dir.mkdir(parents=True)
        (source_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nbody")  # Same content

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        content_hash = compute_content_hash(skill_dir)
        record_origin(
            "my-skill",
            {"source": str(source_dir), "kind": "local", "content_hash": content_hash},
            config=config,
        )

        result = update_skill("my-skill", config=config)

        assert result.success is True
        assert "my-skill" in result.skipped
        assert "up to date" in result.message.lower()

    def test_update_dry_run_no_changes(self, tmp_path):
        """Dry run shows what would be updated without changes."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nold body")

        source_dir = tmp_path / "source" / "my-skill"
        source_dir.mkdir(parents=True)
        (source_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nnew body")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        content_hash = compute_content_hash(skill_dir)
        record_origin(
            "my-skill",
            {"source": str(source_dir), "kind": "local", "content_hash": content_hash},
            config=config,
        )

        result = update_skill("my-skill", config=config, dry_run=True)

        assert result.success is True
        assert "my-skill" in result.updated
        assert "would" in result.message.lower()

        # Content should NOT be changed
        assert (skill_dir / "SKILL.md").read_text() == "---\nname: my-skill\n---\nold body"


class TestScanInstalledSkillIds:
    """Tests for scan_installed_skill_ids function (T1)."""

    def test_flat_skill_detected(self, tmp_path):
        """Flat skill (my-skill/) is detected."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        result = scan_installed_skill_ids(config=config)

        assert result == {"my-skill"}

    def test_nested_skill_detected(self, tmp_path):
        """Nested skill (ns/my-skill/) is detected."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "ns" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        result = scan_installed_skill_ids(config=config)

        assert result == {"ns/my-skill"}

    def test_hidden_directories_skipped(self, tmp_path):
        """Hidden directories (.git, .venv) are skipped."""
        skills_dir = tmp_path / "skills"
        # Valid skill
        valid_skill = skills_dir / "valid-skill"
        valid_skill.mkdir(parents=True)
        (valid_skill / "SKILL.md").write_text("---\nname: valid\n---\nbody")
        # Hidden directory skill (should be skipped)
        hidden_skill = skills_dir / ".git" / "hooks-skill"
        hidden_skill.mkdir(parents=True)
        (hidden_skill / "SKILL.md").write_text("---\nname: hidden\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        result = scan_installed_skill_ids(config=config)

        assert result == {"valid-skill"}

    def test_node_modules_skipped(self, tmp_path):
        """node_modules directory is skipped."""
        skills_dir = tmp_path / "skills"
        # Valid skill
        valid_skill = skills_dir / "valid-skill"
        valid_skill.mkdir(parents=True)
        (valid_skill / "SKILL.md").write_text("---\nname: valid\n---\nbody")
        # node_modules skill (should be skipped)
        node_skill = skills_dir / "node_modules" / "some-skill"
        node_skill.mkdir(parents=True)
        (node_skill / "SKILL.md").write_text("---\nname: node\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        result = scan_installed_skill_ids(config=config)

        assert result == {"valid-skill"}

    def test_nonexistent_skills_dir_returns_empty(self, tmp_path):
        """Non-existent skills_dir returns empty set."""
        config = Config(skills_dir=tmp_path / "nonexistent", db_path=tmp_path / "db.lancedb")

        result = scan_installed_skill_ids(config=config)

        assert result == set()

    def test_empty_skills_dir_returns_empty(self, tmp_path):
        """Existing but empty skills_dir returns empty set."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        result = scan_installed_skill_ids(config=config)

        assert result == set()


class TestGetTrackedSkillIds:
    """Tests for get_tracked_skill_ids function (T1)."""

    def test_tracked_skill_returned(self, tmp_path):
        """Skills in origins.json are returned."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("my-skill", {"source": "test", "kind": "local"}, config=config)

        result = get_tracked_skill_ids(config=config)

        assert result == {"my-skill"}

    def test_different_skills_dir_excluded(self, tmp_path):
        """Skills with different skills_dir are excluded."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)
        other_dir = tmp_path / "other"
        other_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        # Record skill for current skills_dir
        record_origin("my-skill", {"source": "test", "kind": "local"}, config=config)

        # Manually add skill for different skills_dir
        origins_path = config.meta_dir / "origins.json"
        with open(origins_path, encoding="utf-8") as f:
            data = json.load(f)
        data["other-skill"] = {"source": "test", "kind": "local", "skills_dir": str(other_dir)}
        with open(origins_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        result = get_tracked_skill_ids(config=config)

        assert result == {"my-skill"}

    def test_legacy_entry_without_skills_dir_included(self, tmp_path):
        """Legacy entries without skills_dir field are included."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        # Manually create legacy entry without skills_dir
        origins_path = config.meta_dir / "origins.json"
        origins_path.parent.mkdir(parents=True, exist_ok=True)
        with open(origins_path, "w", encoding="utf-8") as f:
            json.dump({"legacy-skill": {"source": "test", "kind": "local"}}, f)

        result = get_tracked_skill_ids(config=config)

        assert result == {"legacy-skill"}


class TestGetUntrackedSkillIds:
    """Tests for get_untracked_skill_ids function (T1)."""

    def test_tracked_skill_not_in_untracked(self, tmp_path):
        """Skills in origins.json are not in untracked list."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("my-skill", {"source": "test", "kind": "local"}, config=config)

        result = get_untracked_skill_ids(config=config)

        assert result == []

    def test_untracked_skill_in_list(self, tmp_path):
        """Skills not in origins.json are in untracked list."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "untracked-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: untracked\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        result = get_untracked_skill_ids(config=config)

        assert result == ["untracked-skill"]

    def test_untracked_sorted_alphabetically(self, tmp_path):
        """Untracked skills are sorted alphabetically."""
        skills_dir = tmp_path / "skills"
        for name in ["zebra", "alpha", "beta"]:
            skill_dir = skills_dir / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        result = get_untracked_skill_ids(config=config)

        assert result == ["alpha", "beta", "zebra"]

    def test_mixed_tracked_and_untracked(self, tmp_path):
        """Mix of tracked and untracked skills returns only untracked."""
        skills_dir = tmp_path / "skills"
        for name in ["tracked-1", "untracked-1", "tracked-2", "untracked-2"]:
            skill_dir = skills_dir / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("tracked-1", {"source": "test", "kind": "local"}, config=config)
        record_origin("tracked-2", {"source": "test", "kind": "local"}, config=config)

        result = get_untracked_skill_ids(config=config)

        assert result == ["untracked-1", "untracked-2"]


class TestGetMissingSkillIds:
    """Tests for get_missing_skill_ids function (T1)."""

    def test_missing_skill_detected(self, tmp_path):
        """Tracked but not installed skills are detected."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("missing-skill", {"source": "test", "kind": "local"}, config=config)

        result = get_missing_skill_ids(config=config)

        assert result == {"missing-skill"}

    def test_installed_skill_not_missing(self, tmp_path):
        """Installed skills are not in missing set."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("my-skill", {"source": "test", "kind": "local"}, config=config)

        result = get_missing_skill_ids(config=config)

        assert result == set()

    def test_untracked_and_missing_coexist(self, tmp_path):
        """Untracked and missing skills can exist simultaneously."""
        skills_dir = tmp_path / "skills"

        # Create untracked skill
        untracked_dir = skills_dir / "untracked-skill"
        untracked_dir.mkdir(parents=True)
        (untracked_dir / "SKILL.md").write_text("---\nname: untracked\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        # Record missing skill (tracked but not installed)
        record_origin("missing-skill", {"source": "test", "kind": "local"}, config=config)

        untracked = get_untracked_skill_ids(config=config)
        missing = get_missing_skill_ids(config=config)

        assert untracked == ["untracked-skill"]
        assert missing == {"missing-skill"}


class TestShowAvailableUpdatesJSON:
    """Tests for CLI JSON output with untracked field (T2)."""

    def test_untracked_field_in_json_output(self, tmp_path):
        """JSON output includes untracked field with expected skill IDs."""
        from skillport.interfaces.cli.commands.update import _show_available_updates

        skills_dir = tmp_path / "skills"

        # Create untracked skill
        untracked_dir = skills_dir / "untracked-skill"
        untracked_dir.mkdir(parents=True)
        (untracked_dir / "SKILL.md").write_text("---\nname: untracked\n---\nbody")

        # Create tracked skill
        tracked_dir = skills_dir / "tracked-skill"
        tracked_dir.mkdir(parents=True)
        (tracked_dir / "SKILL.md").write_text("---\nname: tracked\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("tracked-skill", {"source": "test", "kind": "local"}, config=config)

        # Get the data directly (skip actual JSON printing)
        result = _show_available_updates(config, json_output=False)

        assert "untracked" in result
        assert result["untracked"] == ["untracked-skill"]

    def test_untracked_empty_list_when_none(self, tmp_path):
        """JSON output has empty untracked list when no untracked skills."""
        from skillport.interfaces.cli.commands.update import _show_available_updates

        skills_dir = tmp_path / "skills"

        # Create only tracked skill
        tracked_dir = skills_dir / "tracked-skill"
        tracked_dir.mkdir(parents=True)
        (tracked_dir / "SKILL.md").write_text("---\nname: tracked\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("tracked-skill", {"source": "test", "kind": "local"}, config=config)

        result = _show_available_updates(config, json_output=False)

        assert "untracked" in result
        assert result["untracked"] == []

    def test_json_output_preserves_other_fields(self, tmp_path):
        """Adding untracked field does not affect other fields."""
        from skillport.interfaces.cli.commands.update import _show_available_updates

        skills_dir = tmp_path / "skills"

        # Create tracked builtin skill
        builtin_dir = skills_dir / "hello-world"
        builtin_dir.mkdir(parents=True)
        (builtin_dir / "SKILL.md").write_text("---\nname: hello-world\n---\nbody")

        # Create untracked skill
        untracked_dir = skills_dir / "untracked-skill"
        untracked_dir.mkdir(parents=True)
        (untracked_dir / "SKILL.md").write_text("---\nname: untracked\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("hello-world", {"source": "hello-world", "kind": "builtin"}, config=config)

        result = _show_available_updates(config, json_output=False)

        # Check all expected fields exist
        assert "updates_available" in result
        assert "up_to_date" in result
        assert "not_updatable" in result
        assert "untracked" in result

        # Verify structure
        assert isinstance(result["updates_available"], list)
        assert isinstance(result["up_to_date"], list)
        assert isinstance(result["not_updatable"], list)
        assert isinstance(result["untracked"], list)

        # Verify builtin is in not_updatable
        not_updatable_ids = [item["skill_id"] for item in result["not_updatable"]]
        assert "hello-world" in not_updatable_ids

        # Verify untracked skill
        assert result["untracked"] == ["untracked-skill"]


class TestCheckUpdateAvailableZip:
    """Tests for check_update_available with zip sources."""

    def test_zip_missing_source_not_available(self, tmp_path):
        """Zip skill with missing source file is not updatable."""

        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        # Record origin pointing to non-existent zip
        record_origin(
            "my-skill",
            {
                "source": str(tmp_path / "nonexistent.zip"),
                "kind": "zip",
                "source_mtime": 123456789,
            },
            config=config,
        )

        result = check_update_available("my-skill", config=config)

        assert result["available"] is False
        assert "not found" in result["reason"].lower()

    def test_zip_unchanged_mtime_not_available(self, tmp_path):
        """Zip skill with unchanged mtime is up to date."""
        import zipfile

        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nbody")

        # Create zip file
        zip_path = tmp_path / "my-skill.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("SKILL.md", "---\nname: my-skill\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        # Record origin with matching mtime and hash
        content_hash = compute_content_hash(skill_dir)
        record_origin(
            "my-skill",
            {
                "source": str(zip_path),
                "kind": "zip",
                "source_mtime": zip_path.stat().st_mtime_ns,
                "content_hash": content_hash,
            },
            config=config,
        )

        result = check_update_available("my-skill", config=config)

        assert result["available"] is False
        assert "latest" in result["reason"].lower()


class TestUpdateSkillZip:
    """Tests for update_skill with zip sources."""

    def test_update_zip_skill_success(self, tmp_path):
        """Updating zip skill when zip content changed succeeds."""
        import zipfile

        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nold body")

        # Create zip with new content
        zip_path = tmp_path / "my-skill.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("SKILL.md", "---\nname: my-skill\n---\nnew body")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        # Record origin with matching hash (no local modifications)
        # The hash should match the installed skill's content
        installed_hash = compute_content_hash(skill_dir)
        record_origin(
            "my-skill",
            {
                "source": str(zip_path),
                "kind": "zip",
                "source_mtime": 0,  # Different from current to trigger re-check
                "content_hash": installed_hash,
            },
            config=config,
        )

        result = update_skill("my-skill", config=config)

        assert result.success
        assert "my-skill" in result.updated

        # Verify content was updated
        content = (skill_dir / "SKILL.md").read_text()
        assert "new body" in content

    def test_update_zip_with_nested_dir_does_not_double_nest(self, tmp_path):
        """Zip packaged with top-level directory updates without nested output."""
        import zipfile

        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nold")

        zip_path = tmp_path / "my-skill.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("my-skill/SKILL.md", "---\nname: my-skill\n---\nupdated content")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")
        installed_hash = compute_content_hash(skill_dir)
        record_origin(
            "my-skill",
            {
                "source": str(zip_path),
                "kind": "zip",
                "source_mtime": 0,
                "content_hash": installed_hash,
            },
            config=config,
        )

        result = update_skill("my-skill", config=config)

        assert result.success
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "SKILL.md").read_text().strip().endswith("updated content")
        # No extra nested copy
        assert not (skill_dir / "my-skill" / "SKILL.md").exists()

    def test_update_zip_already_up_to_date(self, tmp_path):
        """Zip skill with matching content is already up to date."""
        import zipfile

        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        content = "---\nname: my-skill\n---\nsame body"
        (skill_dir / "SKILL.md").write_text(content)

        # Create zip with same content
        zip_path = tmp_path / "my-skill.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("SKILL.md", content)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        content_hash = compute_content_hash(skill_dir)
        record_origin(
            "my-skill",
            {
                "source": str(zip_path),
                "kind": "zip",
                "source_mtime": zip_path.stat().st_mtime_ns,
                "content_hash": content_hash,
            },
            config=config,
        )

        result = update_skill("my-skill", config=config)

        assert result.success
        assert "my-skill" in result.skipped
        assert "up to date" in result.message.lower()

    def test_update_zip_with_multiple_skills_rejected(self, tmp_path):
        """Zip containing multiple skills is rejected (1 zip = 1 skill)."""
        import zipfile

        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "skill-a"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: skill-a\n---\nold")

        zip_path = tmp_path / "bundle.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("skill-a/SKILL.md", "---\nname: skill-a\n---\nnew")
            zf.writestr("skill-b/SKILL.md", "---\nname: skill-b\n---\nother")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")
        record_origin(
            "skill-a",
            {
                "source": str(zip_path),
                "kind": "zip",
                "source_mtime": 0,
                "content_hash": compute_content_hash(skill_dir),
            },
            config=config,
        )

        result = update_skill("skill-a", config=config)

        assert not result.success
        assert "exactly one skill" in result.message.lower()

    def test_update_zip_missing_source_fails(self, tmp_path):
        """Updating zip skill with missing source fails."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nbody")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin(
            "my-skill",
            {
                "source": str(tmp_path / "nonexistent.zip"),
                "kind": "zip",
            },
            config=config,
        )

        result = update_skill("my-skill", config=config)

        assert not result.success
        assert "not found" in result.message.lower()

    def test_update_zip_local_modified_without_force_fails(self, tmp_path):
        """Updating locally modified zip skill without force fails."""
        import zipfile

        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nlocally modified")

        # Create zip with different content
        zip_path = tmp_path / "my-skill.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("SKILL.md", "---\nname: my-skill\n---\nnew content")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        # Record origin with original hash (different from current)
        record_origin(
            "my-skill",
            {
                "source": str(zip_path),
                "kind": "zip",
                "source_mtime": 0,
                "content_hash": "sha256:original_hash",
            },
            config=config,
        )

        result = update_skill("my-skill", config=config)

        assert not result.success
        assert result.local_modified is True
        assert "--force" in result.message

    def test_update_zip_local_modified_with_force_succeeds(self, tmp_path):
        """Updating locally modified zip skill with force succeeds."""
        import zipfile

        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nlocally modified")

        # Create zip with different content
        zip_path = tmp_path / "my-skill.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("SKILL.md", "---\nname: my-skill\n---\nfrom zip")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin(
            "my-skill",
            {
                "source": str(zip_path),
                "kind": "zip",
                "source_mtime": 0,
                "content_hash": "sha256:original_hash",
            },
            config=config,
        )

        result = update_skill("my-skill", config=config, force=True)

        assert result.success
        assert "my-skill" in result.updated

        # Verify content was updated
        content = (skill_dir / "SKILL.md").read_text()
        assert "from zip" in content
