"""XML-structured instructions for MCP server.

Implements SPEC3 Section 2: XML 構造化インストラクション.
Implements SPEC4: Dynamic instructions based on registered tools.
Compatible with Claude Code's <skills_system> format and other MCP clients.
"""

from skillport.modules.indexing import get_core_skills
from skillport.shared.config import Config


def _escape_xml(text: str) -> str:
    """Escape special characters for XML content."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_xml_instructions(config: Config, registered_tools: list[str] | None = None) -> str:
    """Build XML-structured instructions for MCP server.

    Dynamically generates instructions based on registered tools.
    This ensures instructions always match the actual available tools.

    Args:
        config: Application configuration.
        registered_tools: List of registered tool names. If None, defaults to
            ["search_skills", "load_skill"] (Local Mode behavior).

    Returns:
        XML-formatted instructions string with <skills_system> root element.
    """
    if registered_tools is None:
        registered_tools = ["search_skills", "load_skill"]

    has_file_read = "read_skill_file" in registered_tools

    lines = ["<skills_system>", "", "<usage>"]
    lines.append("SkillPort provides Agent Skills that load on demand.")
    lines.append("")

    # Workflow - conditional based on registered tools
    lines.append("## Workflow")
    lines.append("1. `search_skills(query)` — Find skills by task description")
    lines.append("2. `load_skill(id)` — Get instructions and `path`")
    if has_file_read:
        lines.append("3. `read_skill_file(id, file)` — Fetch templates/assets")
    else:
        lines.append("3. Use your Read tool with `{path}/file` for templates/assets")
    lines.append("")

    # Tools - generated from registered_tools
    lines.append("## Tools")
    lines.append('- `search_skills(query)` — Find skills. Use "" to list all.')
    lines.append("- `load_skill(id)` — Get instructions and path.")
    if has_file_read:
        lines.append("- `read_skill_file(id, file)` — Read files (text or base64).")
    lines.append("")

    # Tips - conditional
    lines.append("## Tips")
    if has_file_read:
        lines.append('- Text: encoding="utf-8", Binary: encoding="base64"')
        lines.append('- mime_type indicates file type (e.g., "image/png")')
    else:
        lines.append("- Use your native Read for full capabilities (images, PDFs)")
        lines.append("- Replace `{path}` with actual path from load_skill")
    lines.append("- Execute scripts via path, don't read them into context")

    lines.append("</usage>")

    # Core Skills section (only if core skills exist)
    core = get_core_skills(config=config)
    if core:
        lines.append("")
        lines.append("<core_skills>")
        for skill in core:
            sid = skill.get("id") or skill.get("name")
            desc = skill.get("description", "")
            path = skill.get("path", "")
            lines.append("<skill>")
            lines.append(f"  <name>{_escape_xml(str(sid))}</name>")
            lines.append(f"  <description>{_escape_xml(str(desc))}</description>")
            if path:
                location = f"{path}/SKILL.md"
                lines.append(f"  <location>{_escape_xml(location)}</location>")
            lines.append("</skill>")
        lines.append("</core_skills>")

    lines.append("")
    lines.append("</skills_system>")

    return "\n".join(lines)


__all__ = ["build_xml_instructions"]
