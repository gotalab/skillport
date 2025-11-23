import os
from typing import List, Optional, Any
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Paths
    skills_dir: Path = Field(default=Path("./.agent/skills").expanduser())
    db_path: Path = Field(default=Path("./.skillhub/skills.lancedb").expanduser())

    # Embedding / AI
    embedding_provider: str = Field(default="none")  # openai, gemini, none
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None)
    embedding_model: Optional[str] = Field(default="text-embedding-3-small") # Default for openai/ollama-compatible
    # Google Gemini (google-genai). Accepts GEMINI_API_KEY or fallback GOOGLE_API_KEY.
    gemini_api_key: Optional[str] = Field(default=None)
    gemini_embedding_model: Optional[str] = Field(default="gemini-embedding-001")  # multilingual per docs

    # Search / Execution Limits
    search_limit: int = Field(default=10)
    search_threshold: float = Field(default=0.1)
    allowed_commands: List[str] = Field(default=["python3", "python", "uv", "node", "cat", "ls", "grep"])
    exec_timeout_seconds: int = Field(default=60)
    exec_max_output_bytes: int = Field(default=65536)
    max_file_bytes: int = Field(default=65536)
    log_level: str = Field(default="INFO")

    # Filter Settings
    skillhub_enabled_skills: List[str] = Field(default=[])
    skillhub_enabled_categories: List[str] = Field(default=[])

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
        return self.db_path.expanduser().resolve()

settings = Settings()
