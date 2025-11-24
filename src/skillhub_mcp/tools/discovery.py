from typing import Dict, Any
from ..config import settings
from ..db import SkillDB
from ..utils import is_skill_enabled

class DiscoveryTools:
    """Tool implementations related to discovery/search."""

    def __init__(self, db: SkillDB):
        self.db = db

    def search_skills(self, query: str) -> Dict[str, Any]:
        """
        Search for relevant skills using natural language query.
        """
        # 1. Search in DB (Hybrid or FTS)
        limit = settings.search_limit
        candidates = self.db.search(query, limit=limit)
        
        # 2. Filter by enabled settings
        results = []
        for cand in candidates:
            # cand is a dict-like object from LanceDB
            name = cand["name"]
            category = cand.get("category")
            
            if is_skill_enabled(name, category):
                score = float(cand.get("_score", 0.0))
                results.append(
                    {
                        "name": name,
                        "description": cand["description"],
                        "score": max(0.0, score),  # presentable score (non-negative)
                    }
                )
                
            if len(results) >= limit:
                break
                
        return {"skills": results}
