"""SkillPort package entry (lazy import)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from skillport.shared import exceptions
from skillport.shared.config import Config

if TYPE_CHECKING:
    from skillport.modules import (
        AddResult,
        FileContent,
        IndexBuildResult,
        ListResult,
        ReindexDecision,
        RemoveResult,
        SearchResult,
        SkillDetail,
        SkillSummary,
        ValidationIssue,
        ValidationResult,
        add_skill,
        build_index,
        get_by_id,
        index_search,
        list_all,
        list_skills,
        load_skill,
        read_skill_file,
        remove_skill,
        search_skills,
        should_reindex,
        validate_skill,
    )

__all__ = [
    "Config",
    "exceptions",
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

_MODULE_EXPORTS = set(__all__) - {"Config", "exceptions"}


def __getattr__(name: str):
    if name in _MODULE_EXPORTS:
        from skillport import modules as _modules

        return getattr(_modules, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
