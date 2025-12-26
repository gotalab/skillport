from __future__ import annotations

import json

from skillport.modules.indexing.public.query import get_by_id as idx_get_by_id
from skillport.shared.config import Config
from skillport.shared.exceptions import AmbiguousSkillError, SkillNotFoundError
from skillport.shared.filters import is_skill_enabled, normalize_token

from .types import SkillDetail


def load_skill(skill_id: str, *, config: Config) -> SkillDetail:
    """Load full skill details."""
    try:
        record = idx_get_by_id(skill_id, config=config)
    except ValueError as exc:
        raise AmbiguousSkillError(skill_id, []) from exc

    if not record:
        raise SkillNotFoundError(skill_id)

    identifier = record.get("id", skill_id)
    if not is_skill_enabled(identifier, record.get("category"), config=config):
        raise SkillNotFoundError(identifier)

    metadata_raw = record.get("metadata", "{}")
    try:
        metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else dict(metadata_raw)
    except Exception:
        metadata = {}

    return SkillDetail(
        id=identifier,
        name=record.get("name", identifier),
        description=record.get("description", ""),
        category=normalize_token(record.get("category", "")),
        tags=[normalize_token(t) for t in record.get("tags", [])] if record.get("tags") else [],
        instructions=record.get("instructions", ""),
        path=record.get("path", ""),
        metadata=metadata,
    )
