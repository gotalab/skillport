"""Shared configuration for SkillPort.

The Config class is immutable, validated via pydantic-settings, and designed
to be passed explicitly (no global singleton). Environment variables are
prefixed with SKILLPORT_ (e.g., SKILLPORT_SKILLS_DIR).
"""

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import EnvSettingsSource


def _parse_comma_or_json(value: str) -> list[str]:
    """Parse as JSON array or comma-separated string."""
    if not value:
        return []
    # Try JSON first (e.g., '["a","b"]')
    if value.startswith("["):
        try:
            result = json.loads(value)
            if isinstance(result, list):
                return [str(x).strip() for x in result if str(x).strip()]
        except json.JSONDecodeError:
            pass
    # Fallback to comma-separated
    return [item.strip() for item in value.split(",") if item.strip()]


class CommaListEnvSettingsSource(EnvSettingsSource):
    """Custom env source that handles comma-separated lists for list[str] fields."""

    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        # For list[str] fields, parse comma-separated or JSON
        if value is not None and isinstance(value, str):
            origin = getattr(field.annotation, "__origin__", None)
            if origin is list:
                return _parse_comma_or_json(value)
        return super().prepare_field_value(field_name, field, value, value_is_complex)


def _expanduser_cross_platform(value: str | Path) -> Path:
    """Expand "~", "~/" and "~\\" in a cross-platform way.

    Windows' `os.path.expanduser()` historically handles "~\\" reliably but may not
    always expand "~/" (POSIX-style) depending on the Python/OS combination. We
    accept both since `.skillportrc` and docs often use "~/".
    """
    raw = str(value).strip()
    if raw == "~":
        return Path.home()
    if raw.startswith("~/") or raw.startswith("~\\"):
        rest = raw[2:]
        if not rest:
            return Path.home()
        parts = PurePosixPath(rest.replace("\\", "/")).parts
        return Path.home().joinpath(*parts)
    return Path(raw).expanduser()


SKILLPORT_HOME = Path.home() / ".skillport"

# Upper bound for skill enumeration (total count, not returned results)
MAX_SKILLS = 10000
DEFAULT_DB_SUBDIR = Path("indexes") / "default"


class Config(BaseSettings):
    """Application configuration with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="SKILLPORT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # Paths
    skills_dir: Path = Field(
        default=SKILLPORT_HOME / "skills",
        description="Directory containing skill definitions",
    )
    db_path: Path | None = Field(
        default=None,
        description="LanceDB database path (auto-derived from skills_dir if not set)",
    )
    meta_dir: Path | None = Field(
        default=None,
        description="Directory for SkillPort metadata (origins, etc., auto-derived)",
    )

    # Embeddings
    embedding_provider: Literal["none", "openai"] = Field(
        default="none",
        description="Embedding provider for vector search",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key",
        validation_alias="OPENAI_API_KEY",
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="OPENAI_EMBEDDING_MODEL",
    )
    # Search
    search_limit: int = Field(default=10, ge=1, le=100, description="Default search result limit")
    search_threshold: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Minimum relevance score"
    )

    # Filters (comma-separated strings from env, e.g., "cat1,cat2")
    enabled_skills: list[str] = Field(default_factory=list, description="Whitelist of skill IDs")
    enabled_categories: list[str] = Field(
        default_factory=list, description="Whitelist of categories"
    )
    enabled_namespaces: list[str] = Field(
        default_factory=list, description="Whitelist of namespaces"
    )

    # Core Skills mode control
    core_skills_mode: Literal["auto", "explicit", "none"] = Field(
        default="auto",
        description="Core skills behavior: auto (use alwaysApply), explicit (use CORE_SKILLS env), none (disable)",
    )
    core_skills: list[str] = Field(
        default_factory=list,
        description="Explicit list of core skill IDs (used when mode=explicit)",
    )

    # Optional execution-related settings (kept for backwards compatibility)
    allowed_commands: list[str] = Field(
        default_factory=lambda: [
            "python3",
            "python",
            "uv",
            "node",
            "bash",
            "sh",
            "cat",
            "ls",
            "grep",
        ],
        description="Allowlist for executable commands",
    )
    exec_timeout_seconds: int = Field(default=60, description="Command timeout seconds")
    exec_max_output_bytes: int = Field(default=65536, description="Max captured output in bytes")
    max_file_bytes: int = Field(default=65536, description="Max file size to read")
    log_level: str | None = Field(
        default=None, description="Optional log level (e.g., DEBUG/INFO/WARN/ERROR)"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Use custom env source that handles comma-separated lists."""
        return (
            init_settings,
            CommaListEnvSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    @field_validator("skills_dir", "db_path", "meta_dir", mode="before")
    @classmethod
    def expand_path(cls, value: str | Path):
        if value is None:
            return None
        return _expanduser_cross_platform(value).resolve()

    @staticmethod
    def _slug_for_skills_dir(skills_dir: Path) -> str:
        default_path = SKILLPORT_HOME / "skills"
        if skills_dir == default_path:
            return "default"
        digest = hashlib.sha1(str(skills_dir).encode("utf-8")).hexdigest()
        return digest[:10]

    @model_validator(mode="after")
    def validate_provider_keys(self):
        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when embedding_provider='openai'")
        return self

    def model_post_init(self, __context: Any) -> None:
        # Derive db_path/meta_dir when not specified
        slug = self._slug_for_skills_dir(self.skills_dir)

        db_path = self.db_path
        if db_path is None:
            db_path = (
                SKILLPORT_HOME
                / "indexes"
                / (DEFAULT_DB_SUBDIR.name if slug == "default" else slug)
                / "skills.lancedb"
            )

        meta_dir = self.meta_dir
        if meta_dir is None:
            meta_dir = Path(db_path).parent / "meta"

        object.__setattr__(self, "db_path", _expanduser_cross_platform(db_path).resolve())
        object.__setattr__(self, "meta_dir", _expanduser_cross_platform(meta_dir).resolve())

    def with_overrides(self, **kwargs) -> "Config":
        """Create new Config with overrides (immutable pattern)."""
        data = self.model_dump()

        # If skills_dir changes and db_path is not explicitly provided, allow db/meta to be re-derived
        if "skills_dir" in kwargs and "db_path" not in kwargs:
            data.pop("db_path", None)
            data.pop("meta_dir", None)

        # If db_path changes and meta_dir is not explicitly provided, allow meta_dir to be re-derived
        if "db_path" in kwargs and "meta_dir" not in kwargs:
            data.pop("meta_dir", None)

        data.update(kwargs)
        return Config(**data)


__all__ = ["Config", "SKILLPORT_HOME", "MAX_SKILLS"]
