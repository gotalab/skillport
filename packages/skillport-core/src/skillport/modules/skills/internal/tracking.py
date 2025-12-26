"""Tracking utilities for skill lifecycle management.

This module provides functions to compute the relationship between:
- Installed skills (present in skills_dir)
- Tracked skills (recorded in origins.json)
- Untracked skills (installed but not tracked)
- Missing skills (tracked but not installed)
"""

from __future__ import annotations

from pathlib import Path

from skillport.shared.config import Config

from .origin import get_all_origins

# Directories to exclude from scanning (in addition to hidden directories)
SCAN_EXCLUDE_NAMES = {"__pycache__", "node_modules"}


def _scan_installed_skill_ids(skills_dir: Path) -> set[str]:
    """Scan skills_dir and return installed skill IDs (FS-based, index-independent).

    Skill ID is the relative path from skills_dir (e.g., "my-skill", "ns/my-skill").
    Hidden directories (.git, .venv, etc.) and heavy directories (node_modules, etc.)
    are skipped.
    """
    if not skills_dir.exists():
        return set()

    result: set[str] = set()
    for skill_md in skills_dir.rglob("SKILL.md"):
        skill_dir = skill_md.parent
        rel_parts = skill_dir.relative_to(skills_dir).parts

        # Skip hidden directories and excluded directories
        if any(part.startswith(".") or part in SCAN_EXCLUDE_NAMES for part in rel_parts):
            continue

        # Normalize path separator to "/" for cross-platform consistency
        skill_id = "/".join(rel_parts)
        result.add(skill_id)

    return result


def scan_installed_skill_ids(*, config: Config) -> set[str]:
    """Scan installed skill IDs from the configured skills directory.

    Returns:
        Set of skill IDs (relative paths from skills_dir).
    """
    return _scan_installed_skill_ids(config.skills_dir)


def get_tracked_skill_ids(*, config: Config) -> set[str]:
    """Get skill IDs that are tracked in origins.json for the current skills_dir.

    Only returns entries where origin["skills_dir"] matches config.skills_dir,
    or entries without "skills_dir" field (legacy format, assumed to belong to
    current skills_dir).

    Returns:
        Set of tracked skill IDs.
    """
    origins = get_all_origins(config=config)
    tracked: set[str] = set()

    for skill_id, origin in origins.items():
        origin_skills_dir = origin.get("skills_dir")
        # Legacy entries without skills_dir are assumed to belong to current skills_dir
        if origin_skills_dir is None:
            tracked.add(skill_id)
            continue
        # Only include entries that match the current skills_dir
        if Path(origin_skills_dir).resolve() == config.skills_dir:
            tracked.add(skill_id)

    return tracked


def get_untracked_skill_ids(*, config: Config) -> list[str]:
    """Get skill IDs that are installed but not tracked in origins.json.

    Returns:
        Sorted list of untracked skill IDs.
    """
    installed = scan_installed_skill_ids(config=config)
    tracked = get_tracked_skill_ids(config=config)
    return sorted(installed - tracked)


def get_missing_skill_ids(*, config: Config) -> set[str]:
    """Get skill IDs that are tracked in origins.json but not installed.

    Useful for detecting orphan origin entries or skills that were manually deleted.

    Returns:
        Set of missing skill IDs.
    """
    installed = scan_installed_skill_ids(config=config)
    tracked = get_tracked_skill_ids(config=config)
    return tracked - installed
