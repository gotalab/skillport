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
    if name == "add_skill":
        from .add import add_skill as value
    elif name == "list_skills":
        from .list import list_skills as value
    elif name == "load_skill":
        from .load import load_skill as value
    elif name == "read_skill_file":
        from .read import read_skill_file as value
    elif name == "remove_skill":
        from .remove import remove_skill as value
    elif name == "search_skills":
        from .search import search_skills as value
    elif name == "validate_skill":
        from .validation import validate_skill as value
    elif name in {"update_skill", "update_all_skills", "detect_local_modification", "check_update_available"}:
        from .update import (
            check_update_available,
            detect_local_modification,
            update_all_skills,
            update_skill,
        )

        value = {
            "update_skill": update_skill,
            "update_all_skills": update_all_skills,
            "detect_local_modification": detect_local_modification,
            "check_update_available": check_update_available,
        }[name]
    else:
        from .types import (
            AddResult,
            FileContent,
            ListResult,
            RemoveResult,
            SearchResult,
            SkillDetail,
            SkillSummary,
            UpdateResult,
            UpdateResultItem,
            ValidationIssue,
            ValidationResult,
        )

        value = {
            "SkillSummary": SkillSummary,
            "SkillDetail": SkillDetail,
            "FileContent": FileContent,
            "SearchResult": SearchResult,
            "AddResult": AddResult,
            "RemoveResult": RemoveResult,
            "UpdateResult": UpdateResult,
            "UpdateResultItem": UpdateResultItem,
            "ListResult": ListResult,
            "ValidationIssue": ValidationIssue,
            "ValidationResult": ValidationResult,
        }.get(name)

    if value is None:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    return value
