"""XML-structured instructions for MCP server.

Implements SPEC3 Section 2: XML 構造化インストラクション.
Compatible with Claude Code's <skills_system> format and other MCP clients.
"""

from skillsouko.modules.indexing import get_core_skills
from skillsouko.shared.config import Config

USAGE_TEMPLATE = """
SkillSouko provides Agent Skills that load on demand.

## Workflow
1. `search_skills(query)` — Find skills by task description
2. `load_skill(id)` — Get instructions and `path` (skill directory)
3. Follow the instructions using your tools

## Tools
- `search_skills(query)` — Find skills. Use "" to list all.
- `load_skill(id)` — Get instructions and path.
- `read_skill_file(id, file)` — Read files inside a skill (returns `encoding`: "utf-8" or "base64").

## Tips
- Execute scripts via path, don't read them into context: `python {path}/scripts/run.py`
- Replace `{path}` in instructions with the actual path from load_skill
""".strip()


def _escape_xml(text: str) -> str:
    """Escape special characters for XML content."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_xml_instructions(config: Config) -> str:
    """Build XML-structured instructions for MCP server.

    Args:
        config: Application configuration.

    Returns:
        XML-formatted instructions string with <skills_system> root element.
    """
    lines = ["<skills_system>", "", "<usage>"]
    lines.append(USAGE_TEMPLATE)
    lines.append("</usage>")

    # Core Skills section (only if core skills exist)
    core = get_core_skills(config=config)
    if core:
        lines.append("")
        lines.append("<core_skills>")
        for skill in core:
            sid = skill.get("id") or skill.get("name")
            desc = skill.get("description", "")
            lines.append("<skill>")
            lines.append(f"  <name>{_escape_xml(str(sid))}</name>")
            lines.append(f"  <description>{_escape_xml(str(desc))}</description>")
            lines.append("</skill>")
        lines.append("</core_skills>")

    lines.append("")
    lines.append("</skills_system>")

    return "\n".join(lines)


__all__ = ["build_xml_instructions"]
