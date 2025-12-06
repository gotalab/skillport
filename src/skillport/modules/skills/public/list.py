from __future__ import annotations

from skillport.modules.indexing.public.query import list_all as idx_list_all
from skillport.shared.config import Config
from skillport.shared.filters import is_skill_enabled, normalize_token

from .types import ListResult, SkillSummary


def list_skills(*, config: Config, limit: int | None = None) -> ListResult:
    effective_limit = limit or config.search_limit
    rows = idx_list_all(limit=effective_limit * 2, config=config)

    skills: list[SkillSummary] = []
    for row in rows:
        skill_id = row.get("id") or row.get("name")
        category = row.get("category", "")
        if not skill_id:
            continue
        if not is_skill_enabled(skill_id, category, config=config):
            continue
        skills.append(
            SkillSummary(
                id=skill_id,
                name=row.get("name", skill_id),
                description=row.get("description", ""),
                category=normalize_token(category),
                score=float(row.get("_score", 0.0)) if row.get("_score") is not None else 0.0,
            )
        )
        if len(skills) >= effective_limit:
            break

    return ListResult(skills=skills, total=len(skills))
