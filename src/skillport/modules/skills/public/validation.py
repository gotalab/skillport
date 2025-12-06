from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from skillport.modules.skills.internal import validate_skill_record

from .types import SkillSummary, ValidationResult


def _build_validation_dict(skill: SkillSummary | Mapping[str, Any]) -> dict[str, Any]:
    """Build a dict for validation, preserving path/lines for full validation."""
    if isinstance(skill, SkillSummary):
        return skill.model_dump()
    if not isinstance(skill, Mapping):
        raise TypeError(f"Unsupported skill type for validation: {type(skill)}")
    return {
        "id": skill.get("id") or skill.get("name"),
        "name": skill.get("name") or skill.get("id") or "",
        "description": skill.get("description") or "",
        "category": (skill.get("category") or "").strip().lower(),
        "score": skill.get("score", 0.0) or 0.0,
        "path": skill.get("path") or "",
        "lines": skill.get("lines") or 0,
    }


def validate_skill(
    skill: SkillSummary | Mapping[str, Any],
    *,
    strict: bool = False,
) -> ValidationResult:
    """Validate a skill summary (SkillSummary or dict from index).

    Args:
        skill: Skill summary or dict to validate.
        strict: If True, only fatal issues are returned.

    Returns:
        ValidationResult with valid flag, issues, and skill_id.
    """
    data = _build_validation_dict(skill)
    issues = validate_skill_record(data, strict=strict)
    valid = all(issue.severity != "fatal" for issue in issues)
    skill_id = data.get("id") or data.get("name") or ""
    return ValidationResult(valid=valid, issues=issues, skill_id=skill_id)
