"""Modules layer entry point (lazy import)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .indexing import (
        IndexBuildResult,
        ReindexDecision,
        build_index,
        get_by_id,
        list_all,
        should_reindex,
    )
    from .indexing import search as index_search
    from .skills import (
        AddResult,
        FileContent,
        ListResult,
        RemoveResult,
        SearchResult,
        SkillDetail,
        SkillSummary,
        ValidationIssue,
        ValidationResult,
        add_skill,
        list_skills,
        load_skill,
        read_skill_file,
        remove_skill,
        search_skills,
        validate_skill,
    )

_SKILLS_EXPORTS = {
    "search_skills",
    "load_skill",
    "add_skill",
    "remove_skill",
    "list_skills",
    "read_skill_file",
    "validate_skill",
    "SkillSummary",
    "SkillDetail",
    "FileContent",
    "SearchResult",
    "AddResult",
    "RemoveResult",
    "ListResult",
    "ValidationIssue",
    "ValidationResult",
}

_INDEX_EXPORTS = {
    "build_index",
    "should_reindex",
    "index_search",
    "get_by_id",
    "list_all",
    "IndexBuildResult",
    "ReindexDecision",
}

__all__ = [
    "search_skills",
    "load_skill",
    "add_skill",
    "remove_skill",
    "list_skills",
    "read_skill_file",
    "validate_skill",
    "SkillSummary",
    "SkillDetail",
    "FileContent",
    "SearchResult",
    "AddResult",
    "RemoveResult",
    "ListResult",
    "ValidationIssue",
    "ValidationResult",
    "build_index",
    "should_reindex",
    "index_search",
    "get_by_id",
    "list_all",
    "IndexBuildResult",
    "ReindexDecision",
]


def __getattr__(name: str):
    if name in _SKILLS_EXPORTS:
        from . import skills as _skills

        return getattr(_skills, name)
    if name in _INDEX_EXPORTS:
        from . import indexing as _indexing

        if name == "index_search":
            return _indexing.search
        return getattr(_indexing, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
