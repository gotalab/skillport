"""Shared configuration for SkillPod.

The Config class is immutable, validated via pydantic-settings, and designed
to be passed explicitly (no global singleton). Environment variables are
prefixed with SKILLPOD_ (e.g., SKILLPOD_SKILLS_DIR).
"""

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SKILLPOD_HOME = Path("~/.skillpod").expanduser()


class Config(BaseSettings):
    """Application configuration with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="SKILLPOD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # Paths
    skills_dir: Path = Field(
        default=SKILLPOD_HOME / "skills",
        description="Directory containing skill definitions",
    )
    db_path: Path = Field(
        default=SKILLPOD_HOME / "indexes" / "default" / "skills.lancedb",
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

    # Filters
    enabled_skills: list[str] = Field(
        default_factory=list, description="Whitelist of skill IDs"
    )
    enabled_categories: list[str] = Field(
        default_factory=list, description="Whitelist of categories"
    )
    enabled_namespaces: list[str] = Field(
        default_factory=list, description="Whitelist of namespaces"
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

    @field_validator("skills_dir", "db_path", mode="before")
    @classmethod
    def expand_path(cls, value: str | Path) -> Path:
        return Path(value).expanduser().resolve()

    @field_validator(
        "enabled_skills", "enabled_categories", "enabled_namespaces", mode="before"
    )
    @classmethod
    def parse_comma_list(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return list(value)

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


__all__ = ["Config", "SKILLPOD_HOME"]
