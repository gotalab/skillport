"""Shared configuration for SkillSouko.

The Config class is immutable, validated via pydantic-settings, and designed
to be passed explicitly (no global singleton). Environment variables are
prefixed with SKILLSOUKO_ (e.g., SKILLSOUKO_SKILLS_DIR).
"""

import json
from pathlib import Path
from typing import Any, Literal, Tuple, Type

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource
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


SKILLSOUKO_HOME = Path("~/.skillsouko").expanduser()

# Upper bound for skill enumeration (total count, not returned results)
MAX_SKILLS = 10000


class Config(BaseSettings):
    """Application configuration with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="SKILLSOUKO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # Paths
    skills_dir: Path = Field(
        default=SKILLSOUKO_HOME / "skills",
        description="Directory containing skill definitions",
    )
    db_path: Path = Field(
        default=SKILLSOUKO_HOME / "indexes" / "default" / "skills.lancedb",
        description="LanceDB database path",
    )

    # Embeddings
    embedding_provider: Literal["none", "openai", "gemini"] = Field(
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
    gemini_api_key: str | None = Field(
        default=None,
        description="Gemini API key",
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    gemini_embedding_model: str = Field(
        default="gemini-embedding-001",
        validation_alias="GEMINI_EMBEDDING_MODEL",
    )

    # Search
    search_limit: int = Field(
        default=10, ge=1, le=100, description="Default search result limit"
    )
    search_threshold: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Minimum relevance score"
    )

    # Filters (comma-separated strings from env, e.g., "cat1,cat2")
    enabled_skills: list[str] = Field(
        default_factory=list, description="Whitelist of skill IDs"
    )
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
    exec_max_output_bytes: int = Field(
        default=65536, description="Max captured output in bytes"
    )
    max_file_bytes: int = Field(default=65536, description="Max file size to read")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """Use custom env source that handles comma-separated lists."""
        return (
            init_settings,
            CommaListEnvSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    @field_validator("skills_dir", "db_path", mode="before")
    @classmethod
    def expand_path(cls, value: str | Path) -> Path:
        return Path(value).expanduser().resolve()

    @model_validator(mode="after")
    def validate_provider_keys(self):
        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when embedding_provider='openai'"
            )
        if self.embedding_provider == "gemini" and not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) is required when embedding_provider='gemini'"
            )
        return self

    def with_overrides(self, **kwargs) -> "Config":
        """Create new Config with overrides (immutable pattern)."""
        return self.model_copy(update=kwargs)


__all__ = ["Config", "SKILLSOUKO_HOME", "MAX_SKILLS"]
