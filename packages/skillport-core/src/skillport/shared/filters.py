"""Filter utilities for skill enablement checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config


def normalize_token(value: str) -> str:
    """Trim + compress whitespace + lowercase."""
    return " ".join(str(value).strip().split()).lower()


def is_skill_enabled(skill_id: str, category: str | None, *, config: Config) -> bool:
    """Check filters against config (skills, namespaces, categories).

    Args:
        skill_id: The skill identifier to check
        category: The skill's category (may be None)
        config: Configuration with enabled_* filter lists

    Returns:
        True if the skill passes all filters, False otherwise
    """
    skill_norm = normalize_token(skill_id)
    leaf_norm = normalize_token(skill_id.split("/")[-1])
    enabled_skills = [normalize_token(s) for s in config.enabled_skills]
    enabled_categories = [normalize_token(c) for c in config.enabled_categories]
    enabled_namespaces = [normalize_token(ns).rstrip("/") for ns in config.enabled_namespaces]
    category_norm = normalize_token(category) if category is not None else None

    if enabled_skills:
        return skill_norm in enabled_skills or leaf_norm in enabled_skills

    if enabled_namespaces:
        for ns in enabled_namespaces:
            if skill_norm.startswith(ns):
                return True
        return False

    if enabled_categories:
        if category_norm and category_norm in enabled_categories:
            return True
        return False

    return True


__all__ = ["is_skill_enabled", "normalize_token"]
