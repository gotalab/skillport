import os
import yaml
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from .config import settings


def _norm_token(value: str) -> str:
    """Trim + compress whitespace + lowercase for stable comparisons."""
    return " ".join(str(value).strip().split()).lower()

def validate_path(skill_name: str, file_path: str, settings_obj=None) -> Path:
    """
    Resolves and validates that file_path is within the skill directory.
    Raises ValueError or PermissionError if invalid.
    """
    cfg = settings_obj or settings

    skills_root = cfg.get_effective_skills_dir()
    skill_dir = skills_root / skill_name
    
    # Resolve relative to skill_dir
    # Note: file_path comes from user, e.g. "templates/invoice.txt"
    # We must prevent /... or ../..
    
    try:
        # Join and resolve
        target_path = (skill_dir / file_path).resolve()
    except Exception as e:
        raise ValueError(f"Invalid path: {e}")

    # Security check: target must stay inside the specific skill directory
    try:
        # Python 3.9+: safe relative check
        if not target_path.is_relative_to(skill_dir):
            raise PermissionError(f"Path traversal detected: {file_path} is outside skill '{skill_name}' directory")
    except AttributeError:
        # Fallback for older Python: use commonpath
        common = os.path.commonpath([skill_dir, target_path])
        if common != str(skill_dir):
            raise PermissionError(f"Path traversal detected: {file_path} is outside skill '{skill_name}' directory")
    
    if not target_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return target_path

def parse_frontmatter(file_path: Path) -> Tuple[Dict[str, Any], str]:
    """
    Parses a Markdown file with YAML frontmatter.
    Returns (metadata_dict, content_string).
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if content.startswith("---"):
        try:
            parts = content.split("---", 2)
            if len(parts) >= 3:
                # parts[0] is empty, parts[1] is yaml, parts[2] is content
                metadata = yaml.safe_load(parts[1])
                body = parts[2].lstrip() # remove leading newline
                if metadata is None:
                    metadata = {}
                return metadata, body
        except yaml.YAMLError:
            pass # Fallback if yaml parsing fails
    
    # No frontmatter or parse error
    return {}, content

def is_skill_enabled(skill_name: str, category: Optional[str] = None, settings_obj=None) -> bool:
    """
    Checks if a skill is enabled based on server configuration.
    """
    cfg = settings_obj or settings

    # Normalize inputs and configured filters for parity between DB prefilter and runtime checks
    skill_norm = _norm_token(skill_name)
    enabled_skills = [_norm_token(s) for s in cfg.skillhub_enabled_skills]
    enabled_categories = [_norm_token(c) for c in cfg.skillhub_enabled_categories]
    category_norm = _norm_token(category) if category is not None else None

    # 1. If enabled_skills is set, only those are enabled.
    if enabled_skills:
        return skill_norm in enabled_skills

    # 2. If enabled_categories is set, only skills in those categories are enabled.
    if enabled_categories:
        if category_norm and category_norm in enabled_categories:
            return True
        return False

    # 3. If both empty, all enabled.
    return True

def is_command_allowed(command: str, settings_obj=None) -> bool:
    """
    Checks if command is in the allowed list.
    """
    cfg = settings_obj or settings
    cmd_name = Path(command).name
    return cmd_name in cfg.allowed_commands
