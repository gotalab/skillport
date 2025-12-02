from typing import List, Optional

from lancedb.pydantic import LanceModel
from pydantic import Field


class SkillRecord(LanceModel):
    id: str
    name: str
    description: str
    category: str = ""
    tags: List[str] = Field(default_factory=list)
    always_apply: bool = False
    instructions: str
    path: str
    lines: int = 0
    metadata: str
    vector: Optional[List[float]] = None
