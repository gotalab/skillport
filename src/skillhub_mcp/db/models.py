from typing import List, Optional

from lancedb.pydantic import LanceModel


class SkillRecord(LanceModel):
    name: str
    description: str
    category: str = ""
    tags: List[str] = []
    always_apply: bool = False
    instructions: str
    path: str
    metadata: str  # JSON string
    # Using List[float] allows flexibility for different embedding models (OpenAI: 1536, Gemini: 768, etc.)
    # without strict schema validation failures on dimension mismatch during development/model switching.
    vector: Optional[List[float]] = None

