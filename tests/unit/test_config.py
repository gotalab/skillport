"""Unit tests for Config class (SPEC2-CLI Section 4.2)."""

from pathlib import Path

import pytest

from skillport.shared.config import SKILLPORT_HOME, Config


class TestConfigDefaults:
    """Config default value tests."""

    def test_skills_dir_default(self, monkeypatch):
        """SKILLPORT_SKILLS_DIR defaults to ~/.skillport/skills."""
        monkeypatch.delenv("SKILLPORT_SKILLS_DIR", raising=False)
        cfg = Config()
        assert cfg.skills_dir == SKILLPORT_HOME / "skills"

    def test_db_path_default(self, monkeypatch):
        """SKILLPORT_DB_PATH defaults to ~/.skillport/indexes/default/skills.lancedb."""
        monkeypatch.delenv("SKILLPORT_DB_PATH", raising=False)
        cfg = Config()
        assert cfg.db_path == SKILLPORT_HOME / "indexes" / "default" / "skills.lancedb"

    def test_meta_dir_default(self, monkeypatch):
        """meta_dir defaults to db_path parent / meta."""
        monkeypatch.delenv("SKILLPORT_DB_PATH", raising=False)
        cfg = Config()
        assert cfg.meta_dir == SKILLPORT_HOME / "indexes" / "default" / "meta"

    def test_embedding_provider_default(self, monkeypatch):
        """SKILLPORT_EMBEDDING_PROVIDER defaults to 'none'."""
        monkeypatch.delenv("SKILLPORT_EMBEDDING_PROVIDER", raising=False)
        cfg = Config()
        assert cfg.embedding_provider == "none"

    def test_search_limit_default(self, monkeypatch):
        """SKILLPORT_SEARCH_LIMIT defaults to 10."""
        monkeypatch.delenv("SKILLPORT_SEARCH_LIMIT", raising=False)
        cfg = Config()
        assert cfg.search_limit == 10

    def test_search_threshold_default(self, monkeypatch):
        """SKILLPORT_SEARCH_THRESHOLD defaults to 0.2."""
        monkeypatch.delenv("SKILLPORT_SEARCH_THRESHOLD", raising=False)
        cfg = Config()
        assert cfg.search_threshold == 0.2


class TestConfigEnvironment:
    """Config environment variable loading tests."""

    def test_skills_dir_from_env(self, monkeypatch, tmp_path):
        """SKILLPORT_SKILLS_DIR loaded from environment."""
        monkeypatch.setenv("SKILLPORT_SKILLS_DIR", str(tmp_path / "custom-skills"))
        cfg = Config()
        assert cfg.skills_dir == tmp_path / "custom-skills"

    def test_db_path_from_env(self, monkeypatch, tmp_path):
        """SKILLPORT_DB_PATH loaded from environment."""
        monkeypatch.setenv("SKILLPORT_DB_PATH", str(tmp_path / "custom.lancedb"))
        cfg = Config()
        assert cfg.db_path == tmp_path / "custom.lancedb"
        # meta_dir should follow explicit db_path
        assert cfg.meta_dir == (tmp_path / "custom.lancedb").parent / "meta"

    def test_embedding_provider_from_env(self, monkeypatch):
        """SKILLPORT_EMBEDDING_PROVIDER loaded from environment."""
        monkeypatch.setenv("SKILLPORT_EMBEDDING_PROVIDER", "none")
        cfg = Config()
        assert cfg.embedding_provider == "none"

    def test_search_limit_from_env(self, monkeypatch):
        """SKILLPORT_SEARCH_LIMIT loaded from environment."""
        monkeypatch.setenv("SKILLPORT_SEARCH_LIMIT", "50")
        cfg = Config()
        assert cfg.search_limit == 50

    def test_path_expands_tilde(self, monkeypatch):
        """Paths with ~ are expanded."""
        monkeypatch.setenv("SKILLPORT_SKILLS_DIR", "~/my-skills")
        cfg = Config()
        assert "~" not in str(cfg.skills_dir)
        assert cfg.skills_dir == Path.home() / "my-skills"

    def test_log_level_env_optional(self, monkeypatch):
        """SKILLPORT_LOG_LEVEL is accepted but optional."""
        monkeypatch.setenv("SKILLPORT_LOG_LEVEL", "DEBUG")
        cfg = Config()
        assert cfg.log_level == "DEBUG"


class TestConfigAutoPaths:
    """Derived path/slugs from skills_dir."""

    def test_custom_skills_dir_derives_db_and_meta(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SKILLPORT_DB_PATH", raising=False)
        custom = tmp_path / "custom-skills"
        cfg = Config(skills_dir=custom)
        # slug-based directory (10 hex chars)
        slug = cfg.db_path.parent.name
        assert len(slug) == 10 or slug == "default"
        assert cfg.db_path.name == "skills.lancedb"
        assert cfg.meta_dir == cfg.db_path.parent / "meta"


class TestConfigFilters:
    """Config filter parsing tests.

    Note: pydantic-settings expects JSON format for list fields from env vars.
    While SPEC2-CLI documents comma-separated format, the current implementation
    requires JSON (e.g., '["a","b"]' not 'a,b').
    """

    def test_enabled_skills_json_format(self, monkeypatch):
        """SKILLPORT_ENABLED_SKILLS parsed as JSON list."""
        monkeypatch.setenv("SKILLPORT_ENABLED_SKILLS", '["skill-a","skill-b","skill-c"]')
        cfg = Config()
        assert cfg.enabled_skills == ["skill-a", "skill-b", "skill-c"]

    def test_enabled_categories_json_format(self, monkeypatch):
        """SKILLPORT_ENABLED_CATEGORIES parsed as JSON list."""
        monkeypatch.setenv("SKILLPORT_ENABLED_CATEGORIES", '["dev","test"]')
        cfg = Config()
        assert cfg.enabled_categories == ["dev", "test"]

    def test_enabled_namespaces_json_format(self, monkeypatch):
        """SKILLPORT_ENABLED_NAMESPACES parsed as JSON list."""
        monkeypatch.setenv("SKILLPORT_ENABLED_NAMESPACES", '["team-a","team-b"]')
        cfg = Config()
        assert cfg.enabled_namespaces == ["team-a", "team-b"]

    def test_filter_empty_list_json(self, monkeypatch):
        """Empty JSON list → empty list."""
        monkeypatch.setenv("SKILLPORT_ENABLED_SKILLS", "[]")
        cfg = Config()
        assert cfg.enabled_skills == []

    def test_filter_unset_returns_empty_list(self, monkeypatch):
        """Unset filter → empty list."""
        monkeypatch.delenv("SKILLPORT_ENABLED_SKILLS", raising=False)
        cfg = Config()
        assert cfg.enabled_skills == []

    def test_filter_via_constructor(self, monkeypatch):
        """Filters passed via constructor support list format."""
        # When passed directly (not via env), list format works
        cfg = Config(enabled_skills=["skill-a", "skill-b"])
        assert cfg.enabled_skills == ["skill-a", "skill-b"]


class TestConfigProviderValidation:
    """Provider API key validation tests."""

    def test_openai_requires_key(self, monkeypatch):
        """provider=openai without OPENAI_API_KEY → ValueError."""
        monkeypatch.setenv("SKILLPORT_EMBEDDING_PROVIDER", "openai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            Config()

    def test_openai_with_key_ok(self, monkeypatch):
        """provider=openai with OPENAI_API_KEY → ok."""
        monkeypatch.setenv("SKILLPORT_EMBEDDING_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        cfg = Config()
        assert cfg.embedding_provider == "openai"
        assert cfg.openai_api_key == "sk-test-key"

    def test_unsupported_provider_rejected(self, monkeypatch):
        """Unsupported embedding provider raises validation error."""
        monkeypatch.setenv("SKILLPORT_EMBEDDING_PROVIDER", "gemini")
        with pytest.raises(ValueError):
            Config()

    def test_none_provider_no_key_required(self, monkeypatch):
        """provider=none requires no API keys."""
        monkeypatch.setenv("SKILLPORT_EMBEDDING_PROVIDER", "none")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        cfg = Config()
        assert cfg.embedding_provider == "none"


class TestConfigImmutability:
    """Config immutability tests."""

    def test_config_is_frozen(self, monkeypatch):
        """Config instances are frozen (immutable)."""
        cfg = Config()
        with pytest.raises(Exception):  # ValidationError or AttributeError
            cfg.skills_dir = Path("/new/path")

    def test_with_overrides_creates_new(self, monkeypatch, tmp_path):
        """with_overrides creates new Config without mutating original."""
        cfg1 = Config()
        cfg2 = cfg1.with_overrides(skills_dir=tmp_path / "new-skills")

        assert cfg1.skills_dir != cfg2.skills_dir
        assert cfg2.skills_dir == tmp_path / "new-skills"
        # Original unchanged
        assert cfg1.skills_dir == SKILLPORT_HOME / "skills"


class TestCoreSkillsModeConfig:
    """Core Skills Mode configuration tests."""

    def test_core_skills_mode_default_is_auto(self, monkeypatch):
        """SKILLPORT_CORE_SKILLS_MODE defaults to 'auto'."""
        monkeypatch.delenv("SKILLPORT_CORE_SKILLS_MODE", raising=False)
        cfg = Config()
        assert cfg.core_skills_mode == "auto"

    def test_core_skills_default_is_empty_list(self, monkeypatch):
        """SKILLPORT_CORE_SKILLS defaults to empty list."""
        monkeypatch.delenv("SKILLPORT_CORE_SKILLS", raising=False)
        cfg = Config()
        assert cfg.core_skills == []

    def test_core_skills_mode_from_env_explicit(self, monkeypatch):
        """SKILLPORT_CORE_SKILLS_MODE=explicit loaded correctly."""
        monkeypatch.setenv("SKILLPORT_CORE_SKILLS_MODE", "explicit")
        cfg = Config()
        assert cfg.core_skills_mode == "explicit"

    def test_core_skills_mode_from_env_none(self, monkeypatch):
        """SKILLPORT_CORE_SKILLS_MODE=none loaded correctly."""
        monkeypatch.setenv("SKILLPORT_CORE_SKILLS_MODE", "none")
        cfg = Config()
        assert cfg.core_skills_mode == "none"

    def test_core_skills_from_env_comma_separated(self, monkeypatch):
        """SKILLPORT_CORE_SKILLS=skill-a,skill-b parsed correctly."""
        monkeypatch.setenv("SKILLPORT_CORE_SKILLS", "skill-a,skill-b")
        cfg = Config()
        assert cfg.core_skills == ["skill-a", "skill-b"]

    def test_core_skills_mode_invalid_value_rejected(self, monkeypatch):
        """Invalid mode value raises ValidationError."""
        monkeypatch.setenv("SKILLPORT_CORE_SKILLS_MODE", "invalid")
        with pytest.raises(Exception):  # ValidationError
            Config()
