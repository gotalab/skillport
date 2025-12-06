from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from skillport.modules.indexing.public.query import get_by_id as idx_get_by_id
from skillport.shared.config import Config
from skillport.shared.exceptions import SkillNotFoundError
from skillport.shared.filters import is_skill_enabled
from skillport.shared.utils import resolve_inside

from .types import FileContent

# Extensions that should be treated as text even if mimetypes doesn't recognize them
TEXT_EXTENSIONS = {
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".xml",
    ".txt",
    ".csv",
    ".toml",
    ".ini",
    ".cfg",
    ".sh",
    ".py",
    ".js",
    ".ts",
    ".html",
    ".css",
}


def read_skill_file(skill_id: str, file_path: str, *, config: Config) -> FileContent:
    """Read a file inside a skill directory.

    Handles both text and binary files:
    - Text files: Returns content as UTF-8 string with encoding="utf-8"
    - Binary files: Returns content as base64-encoded string with encoding="base64"

    Args:
        skill_id: Skill identifier from load_skill.
        file_path: Relative path within the skill directory.
        config: Application configuration.

    Returns:
        FileContent with content, path, size, encoding, and mime_type.

    Raises:
        SkillNotFoundError: If skill doesn't exist or is disabled.
        FileNotFoundError: If file doesn't exist within skill directory.
        ValueError: If file exceeds max_file_bytes limit.
    """
    record = idx_get_by_id(skill_id, config=config)
    if not record:
        raise SkillNotFoundError(skill_id)

    identifier = record.get("id", skill_id)
    if not is_skill_enabled(identifier, record.get("category"), config=config):
        raise SkillNotFoundError(identifier)

    skill_dir = Path(record.get("path", "")).resolve()
    target = resolve_inside(skill_dir, file_path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    size = target.stat().st_size
    if size > config.max_file_bytes:
        raise ValueError(f"File too large: {size} bytes (max: {config.max_file_bytes})")

    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(str(target))
    mime_type = mime_type or "application/octet-stream"

    # Try to read as text first if it looks like a text file
    if mime_type.startswith("text/") or target.suffix.lower() in TEXT_EXTENSIONS:
        try:
            content = target.read_text(encoding="utf-8")
            return FileContent(
                content=content,
                path=str(target),
                size=size,
                encoding="utf-8",
                mime_type=mime_type,
            )
        except UnicodeDecodeError:
            pass  # Fall through to binary handling

    # Binary file: encode as base64
    content = base64.b64encode(target.read_bytes()).decode("ascii")
    return FileContent(
        content=content,
        path=str(target),
        size=size,
        encoding="base64",
        mime_type=mime_type,
    )
