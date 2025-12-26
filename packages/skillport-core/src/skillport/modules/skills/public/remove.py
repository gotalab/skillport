from skillport.modules.skills.internal import (
    remove_origin_record,
)
from skillport.modules.skills.internal import (
    remove_skill as _remove_skill_internal,
)
from skillport.shared.config import Config

from .types import RemoveResult


def remove_skill(skill_id: str, *, config: Config) -> RemoveResult:
    result = _remove_skill_internal(skill_id, config=config)
    if result.success:
        try:
            remove_origin_record(skill_id, config=config)
        except Exception:
            # non-fatal
            pass
    return result
