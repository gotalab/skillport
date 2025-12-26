from __future__ import annotations

from skillport.modules.indexing.public.query import list_all as idx_list_all
from skillport.modules.indexing.public.query import search as idx_search
from skillport.shared.config import MAX_SKILLS, Config
from skillport.shared.filters import is_skill_enabled, normalize_token

from .types import SearchResult, SkillSummary


def search_skills(query: str, *, limit: int = 10, config: Config) -> SearchResult:
    """Search for skills via indexing module with filters applied."""
    effective_limit = limit or config.search_limit
    normalized_query = query or ""
    is_list_all = not normalized_query.strip() or normalized_query.strip() == "*"

    # Fetch up to MAX_SKILLS to count total filtered results
    raw_results: list[dict]
    if is_list_all:
        raw_results = idx_list_all(limit=MAX_SKILLS, config=config)
    else:
        raw_results = idx_search(normalized_query, limit=MAX_SKILLS, config=config)

    # Filter and collect all matching skills
    all_matching: list[SkillSummary] = []
    for row in raw_results:
        skill_id = row.get("id") or row.get("name")
        category = row.get("category", "")
        if not skill_id:
            continue
        if not is_skill_enabled(skill_id, category, config=config):
            continue
        score = float(row.get("_score", 0.0))
        all_matching.append(
            SkillSummary(
                id=skill_id,
                name=row.get("name", skill_id),
                description=row.get("description", ""),
                category=normalize_token(category),
                score=score,
            )
        )

    # Return limited results but total count of all matching
    return SearchResult(
        skills=all_matching[:effective_limit],
        total=len(all_matching),
        query=query,
    )
