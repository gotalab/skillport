"""DB package facade.

Provides the SkillDB class and helper re-exports. The DB is now created
explicitly by the server and injected into tool modules; no module-level
connection is opened on import.
"""

from ..config import settings  # re-export for legacy patches
from .search import SkillDB, lancedb
from .embeddings import get_embedding

__all__ = ["SkillDB", "get_embedding", "lancedb", "settings"]
