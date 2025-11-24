from typing import Dict, Any
from ..db import SkillDB
from ..utils import is_skill_enabled

class LoadingTools:
    """Tool implementations for loading skills."""

    def __init__(self, db: SkillDB):
        self.db = db

    def load_skill(self, skill_name: str) -> Dict[str, Any]:
        """
        Load instructions for a specific skill.
        """
        # 1. Check if exists in DB
        record = self.db.get_skill(skill_name)
        if not record:
            raise ValueError(f"Skill not found: {skill_name}")
        
        # 2. Check if enabled
        if not is_skill_enabled(skill_name, record.get("category")):
            raise ValueError(f"Skill is disabled: {skill_name}")
        
        # 3. Return instructions
        return {
            "name": skill_name,
            "instructions": record["instructions"]
        }
