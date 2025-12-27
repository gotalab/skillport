"""Filesystem-based skill catalog for CLI SkillOps."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from skillport.modules.skills.public.types import ListResult, SkillDetail, SkillSummary
from skillport.shared.config import Config
from skillport.shared.exceptions import SkillNotFoundError
from skillport.shared.filters import is_skill_enabled, normalize_token
from skillport.shared.utils import parse_frontmatter, resolve_inside

SCAN_EXCLUDE_NAMES = {"__pycache__", "node_modules"}
MAX_DEPTH = 2


def _iter_skill_dirs(skills_dir: Path) -> Iterable[tuple[str, Path]]:
    if not skills_dir.exists():
        return

    seen: set[str] = set()
    for skill_md in skills_dir.rglob("SKILL.md"):
        skill_dir = skill_md.parent
        rel_parts = skill_dir.relative_to(skills_dir).parts

        if any(part.startswith(".") or part in SCAN_EXCLUDE_NAMES for part in rel_parts):
            continue
        if len(rel_parts) == 0 or len(rel_parts) > MAX_DEPTH:
            continue

        skill_id = "/".join(rel_parts)
        if skill_id in seen:
            continue
        seen.add(skill_id)
        yield skill_id, skill_dir


def iter_skill_dirs(skills_dir: Path) -> Iterable[tuple[str, Path]]:
    """Yield skill IDs and directories discovered on disk (no filtering)."""
    yield from _iter_skill_dirs(skills_dir)


def iter_skill_dirs_filtered(*, config: Config) -> Iterable[tuple[str, Path]]:
    """Yield skill IDs and directories, applying the same filters as list_skills_fs."""
    collected: list[tuple[str, Path]] = []
    for skill_id, skill_dir in _iter_skill_dirs(config.skills_dir):
        meta, _body = parse_frontmatter(skill_dir / "SKILL.md")
        if not isinstance(meta, dict):
            meta = {}
        _name, _description, category_norm, _tags_norm, _ = _extract_skill_meta(
            meta, skill_dir.name
        )

        if not is_skill_enabled(skill_id, category_norm, config=config):
            continue
        collected.append((skill_id, skill_dir))

    for skill_id, skill_dir in sorted(collected, key=lambda item: item[0]):
        yield skill_id, skill_dir


def _extract_skill_meta(meta: dict, fallback_name: str) -> tuple[str, str, str, list[str], dict]:
    metadata_block = meta.get("metadata", {})
    if not isinstance(metadata_block, dict):
        metadata_block = {}

    skillport_meta = metadata_block.get("skillport", {})
    if not isinstance(skillport_meta, dict):
        skillport_meta = {}

    name = meta.get("name") or fallback_name
    description = meta.get("description") or ""
    category = skillport_meta.get("category", "")
    tags = skillport_meta.get("tags", [])

    category_norm = normalize_token(category) if category else ""
    tags_norm: list[str] = []
    if isinstance(tags, list):
        tags_norm = [normalize_token(t) for t in tags]
    elif isinstance(tags, str):
        tags_norm = [normalize_token(tags)]

    return name, description, category_norm, tags_norm, meta


def list_skills_fs(*, config: Config, limit: int | None = None) -> ListResult:
    """List skills from filesystem (no index dependency)."""
    effective_limit = limit or config.search_limit
    skills: list[SkillSummary] = []

    collected: list[SkillSummary] = []
    for skill_id, skill_dir in iter_skill_dirs_filtered(config=config):
        meta, _body = parse_frontmatter(skill_dir / "SKILL.md")
        if not isinstance(meta, dict):
            meta = {}
        name, description, category_norm, _tags_norm, _ = _extract_skill_meta(meta, skill_dir.name)

        collected.append(
            SkillSummary(
                id=skill_id,
                name=name,
                description=description,
                category=category_norm,
                score=0.0,
            )
        )

    for summary in sorted(collected, key=lambda s: s.id):
        skills.append(summary)
        if len(skills) >= effective_limit:
            break

    return ListResult(skills=skills, total=len(skills))


def load_skill_fs(skill_id: str, *, config: Config) -> SkillDetail:
    """Load a skill from filesystem by ID (no index dependency)."""
    if len(Path(skill_id).parts) > MAX_DEPTH:
        raise SkillNotFoundError(skill_id)
    skill_dir = resolve_inside(config.skills_dir, skill_id)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise SkillNotFoundError(skill_id)

    meta, body = parse_frontmatter(skill_md)
    if not isinstance(meta, dict):
        meta = {}

    name, description, category_norm, tags_norm, metadata = _extract_skill_meta(
        meta, skill_dir.name
    )

    if not is_skill_enabled(skill_id, category_norm, config=config):
        raise SkillNotFoundError(skill_id)

    return SkillDetail(
        id=skill_id,
        name=name,
        description=description,
        category=category_norm,
        tags=tags_norm,
        instructions=body,
        path=str(skill_dir.resolve()),
        metadata=metadata,
    )


__all__ = [
    "iter_skill_dirs",
    "iter_skill_dirs_filtered",
    "list_skills_fs",
    "load_skill_fs",
]
