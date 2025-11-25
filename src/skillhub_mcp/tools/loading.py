from typing import Dict, Any
from ..db import SkillDB
from ..utils import is_skill_enabled


class LoadingTools:
    """Tool implementations for loading skills."""

    def __init__(self, db: SkillDB):
        self.db = db
        self.settings = getattr(db, "settings", None)

    def load_skill(self, skill_name: str) -> Dict[str, Any]:
        """Load a skill's full instructions and directory path.

        Args:
            skill_name: Skill name from search_skills or server instructions.

        Returns:
            name: Skill identifier
            instructions: Step-by-step guidance to follow
            path: Skill directory. Execute scripts in your terminal: `python {path}/script.py`
        """
        # 1. Check if exists in DB
        record = self.db.get_skill(skill_name)
        if not record:
            raise ValueError(f"Skill not found: {skill_name}")

        # 2. Check if enabled
        if not is_skill_enabled(skill_name, record.get("category"), settings_obj=self.settings):
            raise ValueError(f"Skill is disabled: {skill_name}")

        # 3. Return instructions with path
        return {
            "name": skill_name,
            "instructions": record["instructions"],
            "path": record.get("path", ""),
        }
