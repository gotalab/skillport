from typing import Any

from pydantic import Field

from skillport.shared.types import FrozenModel


class IndexBuildResult(FrozenModel):
    success: bool
    skill_count: int = Field(..., ge=0, description="Number of skills indexed")
    message: str


class ReindexDecision(FrozenModel):
    need: bool = Field(..., description="Whether reindex is needed")
    reason: str = Field(..., description="Reason for the decision")
    state: dict[str, Any] = Field(
        default_factory=dict, description="Current index state for persistence"
    )
