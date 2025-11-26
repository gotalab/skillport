import hashlib
import os
from typing import List, Optional, Any
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


def _parse_comma_list(v: Any) -> List[str]:
    """Parse comma-separated string or list into List[str]."""
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        return [item.strip() for item in v.split(",") if item.strip()]
    return []

# Default base directory: ~/.skillhub/
# This follows the common CLI tool convention (~/.npm, ~/.cargo, ~/.docker, etc.)
# and is easy for users to find and manage their skills.
SKILLHUB_HOME = Path("~/.skillhub").expanduser()


class Settings(BaseSettings):
    # Paths - all under ~/.skillhub/ by default
    # ~/.skillhub/skills/  - user's skill files
    # ~/.skillhub/indexes/ - database/index files (auto-generated per skills_dir)
    skills_dir: Path = Field(default=SKILLHUB_HOME / "skills")
    db_path: Path = Field(default=SKILLHUB_HOME / "indexes" / "default" / "skills.lancedb")

    # Embedding / AI
    embedding_provider: str = Field(default="none")  # openai, gemini, none
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None)
    embedding_model: Optional[str] = Field(default="text-embedding-3-small")  # Default for openai
    # Google Gemini (google-genai). Accepts GEMINI_API_KEY or fallback GOOGLE_API_KEY.
    gemini_api_key: Optional[str] = Field(default=None)
    gemini_embedding_model: Optional[str] = Field(default="gemini-embedding-001")  # multilingual per docs

    # Search / Execution Limits
    search_limit: int = Field(default=10)
    search_threshold: float = Field(default=0.2)
    allowed_commands: List[str] = Field(default=["python3", "python", "uv", "node", "bash", "sh", "cat", "ls", "grep"])
    exec_timeout_seconds: int = Field(default=60)
    exec_max_output_bytes: int = Field(default=65536)
    max_file_bytes: int = Field(default=65536)
    log_level: str = Field(default="INFO")

    # Filter Settings (comma-separated strings)
    skillhub_enabled_skills: str = Field(default="")
    skillhub_enabled_categories: str = Field(default="")
    skillhub_enabled_namespaces: str = Field(default="")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get_enabled_skills(self) -> List[str]:
        return _parse_comma_list(self.skillhub_enabled_skills)

    def get_enabled_categories(self) -> List[str]:
        return _parse_comma_list(self.skillhub_enabled_categories)

    def get_enabled_namespaces(self) -> List[str]:
        return _parse_comma_list(self.skillhub_enabled_namespaces)

    def model_post_init(self, __context: Any):
        """
        Keep rules simple:
        - Only the selected provider's key/model are required.
        - Extra provider fields are ignored (no error).
        - Missing required key/model -> raise early to fail fast.
        """
        # Alias for Gemini
        if not self.gemini_api_key:
            google_key = os.getenv("GOOGLE_API_KEY")
            if google_key:
                object.__setattr__(self, "gemini_api_key", google_key)

        provider = self.embedding_provider

        def require(field_name: str, value: Any, provider_label: str):
            if not value:
                raise ValueError(f"{field_name.upper()} is required when embedding_provider='{provider_label}'")

        if provider == "openai":
            require("openai_api_key", self.openai_api_key, provider)
            require("embedding_model", self.embedding_model, provider)
        elif provider == "gemini":
            require("gemini_api_key", self.gemini_api_key, provider)
            require("gemini_embedding_model", self.gemini_embedding_model, provider)
        elif provider == "none":
            # Nothing required
            pass
        else:
            raise ValueError(f"Unsupported embedding_provider: {provider}")

    def get_effective_skills_dir(self) -> Path:
        return self.skills_dir.expanduser().resolve()

    def get_effective_db_path(self) -> Path:
        # If DB_PATH is explicitly set, use it
        if os.getenv("DB_PATH"):
            return self.db_path.expanduser().resolve()

        skills_dir = self.get_effective_skills_dir()
        default_skills_dir = (SKILLHUB_HOME / "skills").resolve()

        # Default skills dir -> default index path
        if skills_dir == default_skills_dir:
            return (SKILLHUB_HOME / "indexes" / "default" / "skills.lancedb").resolve()

        # Custom skills dir -> hash-based index path
        dir_hash = hashlib.sha256(str(skills_dir).encode()).hexdigest()[:12]
        return (SKILLHUB_HOME / "indexes" / dir_hash / "skills.lancedb").resolve()

settings = Settings()
