"""Query-facing public APIs."""

from skillport.shared.config import Config

from ..internal.lancedb import IndexStore


def search(query: str, *, limit: int, config: Config) -> list[dict]:
    store = IndexStore(config)
    return store.search(query, limit=limit)


def get_by_id(skill_id: str, *, config: Config) -> dict | None:
    store = IndexStore(config)
    return store.get_by_id(skill_id)


def list_all(*, limit: int, config: Config) -> list[dict]:
    store = IndexStore(config)
    return store.list_all(limit=limit)


def get_core_skills(*, config: Config) -> list[dict]:
    """Get core skills based on core_skills_mode setting.

    Modes:
    - auto: Returns skills with alwaysApply=true (default, backward compatible)
    - explicit: Returns only skills specified in config.core_skills
    - none: Returns empty list (disables core skills)
    """
    if config.core_skills_mode == "none":
        return []

    if config.core_skills_mode == "explicit":
        if not config.core_skills:
            return []
        store = IndexStore(config)
        results = []
        for skill_id in config.core_skills:
            skill = store.get_by_id(skill_id)
            if skill:
                results.append(skill)
        return results

    # mode == "auto" (default)
    store = IndexStore(config)
    return store.get_core_skills()
