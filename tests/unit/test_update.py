"""Unit tests for skill update functionality."""


from skillport.modules.skills import (
    check_update_available,
    detect_local_modification,
    update_skill,
)
from skillport.modules.skills.internal import (
    compute_content_hash,
    record_origin,
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
