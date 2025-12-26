"""Skills module public API (lazy import)."""

from __future__ import annotations

_EXPORTS = {
    "search_skills",
    "load_skill",
    "add_skill",
    "remove_skill",
    "list_skills",
    "read_skill_file",
    "validate_skill",
    "update_skill",
    "update_all_skills",
    "detect_local_modification",
    "check_update_available",
    "SkillSummary",
    "SkillDetail",
    "FileContent",
    "SearchResult",
    "AddResult",
    "RemoveResult",
    "UpdateResult",
    "UpdateResultItem",
    "ListResult",
    "ValidationIssue",
    "ValidationResult",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str):
    if name in _EXPORTS:
        from . import public as _public

        return getattr(_public, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
