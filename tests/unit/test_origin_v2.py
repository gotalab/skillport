"""Unit tests for origin.json v2 functionality."""

from skillport.modules.skills.internal import (
    compute_content_hash,
    get_all_origins,
    get_origin,
    migrate_origin_v2,
    prune_orphan_origins,
    record_origin,
    update_origin,
)
from skillport.shared.config import Config


class TestMigrateOriginV2:
    """Tests for origin v1 to v2 migration."""

    def test_migrate_adds_new_fields(self):
        """v1 origin should get new v2 fields."""
        v1_origin = {
            "source": "https://github.com/user/repo",
            "kind": "github",
            "added_at": "2025-01-01T00:00:00Z",
            "skills_dir": "/path/to/skills",
            "ref": "main",
        }

        v2_origin = migrate_origin_v2(v1_origin)

        assert "content_hash" in v2_origin
        assert "commit_sha" in v2_origin
        assert "local_modified" in v2_origin
        assert "update_history" in v2_origin
        assert "updated_at" in v2_origin

        # Default values
        assert v2_origin["content_hash"] == ""
        assert v2_origin["commit_sha"] == ""
        assert v2_origin["local_modified"] is False
        assert v2_origin["update_history"] == []
        assert v2_origin["updated_at"] == "2025-01-01T00:00:00Z"  # From added_at

    def test_migrate_preserves_existing_v2_fields(self):
        """Already v2 origin should not be modified."""
        v2_origin = {
            "source": "https://github.com/user/repo",
            "kind": "github",
            "added_at": "2025-01-01T00:00:00Z",
            "content_hash": "sha256:abc123",
            "commit_sha": "abc1234",
            "local_modified": True,
            "update_history": [{"from_commit": "old", "to_commit": "new"}],
            "updated_at": "2025-01-02T00:00:00Z",
        }

        result = migrate_origin_v2(v2_origin)

        assert result["content_hash"] == "sha256:abc123"
        assert result["commit_sha"] == "abc1234"
        assert result["local_modified"] is True
        assert len(result["update_history"]) == 1


class TestComputeContentHash:
    """Tests for content hash computation."""

    def test_compute_hash_for_skill(self, tmp_path):
        """Compute SHA256 hash of skill directory."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: test\n---\nbody")

        hash_value = compute_content_hash(skill_dir)

        assert hash_value.startswith("sha256:")
        assert len(hash_value) == 7 + 64  # "sha256:" + 64 hex chars

    def test_compute_hash_changes_with_other_files(self, tmp_path):
        """Hash includes other files (not SKILL.md only)."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: test\n---\nbody")

        hash1 = compute_content_hash(skill_dir)

        # Add another file
        (skill_dir / "helper.py").write_text("def foo(): pass")
        hash2 = compute_content_hash(skill_dir)

        # Hash should change because helper.py is included
        assert hash1 != hash2

    def test_compute_hash_includes_subdirectories(self, tmp_path):
        """Hash changes when files in subdirectories change."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: test\n---\nbody")

        hash1 = compute_content_hash(skill_dir)

        # Add file in subdirectory
        lib_dir = skill_dir / "lib"
        lib_dir.mkdir()
        (lib_dir / "utils.py").write_text("# utils")
        hash2 = compute_content_hash(skill_dir)

        assert hash1 != hash2

    def test_compute_hash_excludes_hidden_files(self, tmp_path):
        """Hash excludes hidden files and __pycache__."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: test\n---\nbody")

        hash1 = compute_content_hash(skill_dir)

        # Add hidden file and __pycache__
        (skill_dir / ".hidden").write_text("hidden")
        pycache = skill_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "module.pyc").write_bytes(b"\x00\x00")

        hash2 = compute_content_hash(skill_dir)

        # Hash should be same (hidden files excluded)
        assert hash1 == hash2

    def test_compute_hash_returns_empty_for_missing_skill(self, tmp_path):
        """Missing SKILL.md returns empty string."""
        skill_dir = tmp_path / "no-skill"
        skill_dir.mkdir()

        hash_value = compute_content_hash(skill_dir)

        assert hash_value == ""

    def test_compute_hash_is_deterministic(self, tmp_path):
        """Same content produces same hash."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: test\n---\nbody")

        hash1 = compute_content_hash(skill_dir)
        hash2 = compute_content_hash(skill_dir)

        assert hash1 == hash2

    def test_different_content_different_hash(self, tmp_path):
        """Different content produces different hash."""
        skill1 = tmp_path / "skill1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("content A")

        skill2 = tmp_path / "skill2"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("content B")

        assert compute_content_hash(skill1) != compute_content_hash(skill2)


class TestGetOrigin:
    """Tests for get_origin function."""

    def test_get_origin_returns_none_for_missing(self, tmp_path):
        """Non-existent skill returns None."""
        config = Config(skills_dir=tmp_path / "skills", db_path=tmp_path / "db.lancedb")

        result = get_origin("nonexistent", config=config)

        assert result is None

    def test_get_origin_returns_migrated_v2(self, tmp_path):
        """Returned origin is migrated to v2."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        # Record a v1-style origin
        record_origin("my-skill", {"source": "test", "kind": "local"}, config=config)

        result = get_origin("my-skill", config=config)

        assert result is not None
        assert "content_hash" in result  # v2 field present


class TestUpdateOrigin:
    """Tests for update_origin function."""

    def test_update_origin_merges_fields(self, tmp_path):
        """Update origin merges new fields into existing."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        # Record initial origin
        record_origin("my-skill", {"source": "test", "kind": "github"}, config=config)

        # Update with new fields
        update_origin(
            "my-skill",
            {"content_hash": "sha256:new", "commit_sha": "abc123"},
            config=config,
        )

        result = get_origin("my-skill", config=config)

        assert result["source"] == "test"  # Preserved
        assert result["kind"] == "github"  # Preserved
        assert result["content_hash"] == "sha256:new"  # Updated
        assert result["commit_sha"] == "abc123"  # Updated

    def test_update_origin_adds_history_entry(self, tmp_path):
        """History entry is prepended correctly."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("my-skill", {"source": "test", "kind": "github"}, config=config)

        update_origin(
            "my-skill",
            {"commit_sha": "new123"},
            config=config,
            add_history_entry={"from_commit": "old", "to_commit": "new123"},
        )

        result = get_origin("my-skill", config=config)

        assert len(result["update_history"]) == 1
        assert result["update_history"][0]["from_commit"] == "old"
        assert result["update_history"][0]["to_commit"] == "new123"

    def test_update_origin_history_rotation(self, tmp_path):
        """History is limited to MAX_UPDATE_HISTORY entries."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("my-skill", {"source": "test", "kind": "github"}, config=config)

        # Add 15 history entries
        for i in range(15):
            update_origin(
                "my-skill",
                {"commit_sha": f"commit{i}"},
                config=config,
                add_history_entry={"from_commit": f"from{i}", "to_commit": f"to{i}"},
            )

        result = get_origin("my-skill", config=config)

        # Should be limited to 10
        assert len(result["update_history"]) == 10
        # Most recent should be first
        assert result["update_history"][0]["to_commit"] == "to14"


class TestGetAllOrigins:
    """Tests for get_all_origins function."""

    def test_get_all_origins_empty(self, tmp_path):
        """Empty origins returns empty dict."""
        config = Config(skills_dir=tmp_path / "skills", db_path=tmp_path / "db.lancedb")

        result = get_all_origins(config=config)

        assert result == {}

    def test_get_all_origins_returns_all_migrated(self, tmp_path):
        """All origins are returned and migrated to v2."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("skill-a", {"source": "a", "kind": "github"}, config=config)
        record_origin("skill-b", {"source": "b", "kind": "local"}, config=config)

        result = get_all_origins(config=config)

        assert "skill-a" in result
        assert "skill-b" in result
        assert "content_hash" in result["skill-a"]  # v2 migrated
        assert "content_hash" in result["skill-b"]  # v2 migrated


class TestPruneOrphanOrigins:
    """Tests for pruning orphan origins."""

    def test_prune_removes_missing_skill_dirs(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        # existing skill
        skill_a = skills_dir / "skill-a"
        skill_a.mkdir()
        (skill_a / "SKILL.md").write_text("a")

        config = Config(skills_dir=skills_dir, db_path=tmp_path / "db.lancedb")

        record_origin("skill-a", {"source": "a", "kind": "local"}, config=config)
        record_origin("skill-b", {"source": "b", "kind": "github"}, config=config)

        removed = prune_orphan_origins(config=config)

        assert "skill-b" in removed
        assert get_origin("skill-b", config=config) is None
        assert get_origin("skill-a", config=config) is not None
