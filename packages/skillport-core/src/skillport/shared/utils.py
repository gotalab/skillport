"""Pure utility helpers shared across modules."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# Re-export normalize_token from filters for backwards compatibility
from .filters import normalize_token


def parse_frontmatter(file_path: Path) -> tuple[dict[str, Any], str]:
    """Parse a Markdown file with YAML frontmatter.

    Returns (metadata, body). If frontmatter is absent or invalid, metadata is {}.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    text = file_path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
                if not isinstance(meta, dict):
                    meta = {}
            except yaml.YAMLError:
                meta = {}
            body = parts[2].lstrip("\n")
            return meta, body
    return {}, text


def resolve_inside(base: Path, relative_path: str) -> Path:
    """Resolve relative_path within base; prevent traversal."""
    target = (base / relative_path).resolve()
    try:
        if not target.is_relative_to(base.resolve()):
            raise PermissionError(f"Path traversal detected: {relative_path}")
    except AttributeError:
        base_resolved = str(base.resolve())
        try:
            common = os.path.commonpath([base_resolved, str(target)])
        except ValueError:
            raise PermissionError(f"Path traversal detected: {relative_path}") from None

        if os.path.normcase(common) != os.path.normcase(base_resolved):
            raise PermissionError(f"Path traversal detected: {relative_path}")
    return target


__all__ = ["normalize_token", "parse_frontmatter", "resolve_inside"]
