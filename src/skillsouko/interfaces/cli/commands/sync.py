"""Sync installed skills to AGENTS.md for non-MCP agents.

Implements SPEC3 Section 3: sync コマンド.
Generates a skills block that can be embedded in AGENTS.md files.
"""

import re
from pathlib import Path
from typing import Optional

import typer

from skillsouko.modules.skills import list_skills, SkillSummary
from skillsouko.shared.config import Config
from ..theme import console

MARKER_START = "<!-- SKILLSOUKO_START -->"
MARKER_END = "<!-- SKILLSOUKO_END -->"


def _truncate_description(desc: str, max_len: int = 50) -> str:
    """Truncate description to max length with ellipsis."""
    # Clean up newlines and extra spaces
    desc = " ".join(desc.split())
    if len(desc) <= max_len:
        return desc
    return desc[: max_len - 3] + "..."


CLI_INSTRUCTIONS = """
## SkillSouko Skills

Skills are reusable expert knowledge that help you complete tasks effectively.
Each skill contains step-by-step instructions, templates, and scripts.

### Workflow

1. **Find a skill** - Check the table below for a skill matching your task
2. **Get instructions** - Run `skillsouko show <skill-id>` to load full instructions
3. **Follow the instructions** - Execute the steps using your available tools

### Tips

- Skills may include scripts - execute them via the skill's path, don't read them into context
- If instructions reference `{path}`, replace it with the skill's directory path
- When uncertain, check the skill's description to confirm it matches your task
""".strip()

MCP_INSTRUCTIONS = """
## SkillSouko Skills

Skills are reusable expert knowledge that help you complete tasks effectively.
Each skill contains step-by-step instructions, templates, and scripts.

### Workflow

1. **Search** - Call `search_skills(query)` to find skills matching your task
2. **Load** - Call `load_skill(skill_id)` to get full instructions and `path`
3. **Execute** - Follow the instructions using your available tools

### Tools

- `search_skills(query)` - Find skills by task description. Use `""` to list all.
- `load_skill(id)` - Get full instructions and the skill's filesystem path.
- `read_skill_file(id, file)` - Read templates or config files inside a skill.

### Tips

- Execute scripts via path, don't read them into context: `python {path}/scripts/run.py`
- Replace `{path}` in instructions with the actual path from `load_skill`
- If search returns too many results, use more specific terms
""".strip()


def generate_skills_block(
    skills: list[SkillSummary],
    format: str = "xml",
    mode: str = "cli",
) -> str:
    """Generate skills block for AGENTS.md.

    Args:
        skills: List of skills to include.
        format: Output format ("xml" or "markdown").
        mode: Target mode ("cli" or "mcp").

    Returns:
        Formatted skills block with markers.
    """
    lines = [MARKER_START]

    if format == "xml":
        lines.append("<available_skills>")
        lines.append("")

    # Instructions first (most important for agents)
    instructions = MCP_INSTRUCTIONS if mode == "mcp" else CLI_INSTRUCTIONS
    lines.append(instructions)
    lines.append("")

    # Skills table
    lines.append("### Available Skills")
    lines.append("")
    lines.append("| ID | Description | Category |")
    lines.append("|----|-------------|----------|")

    for skill in skills:
        skill_id = skill.id
        # Clean description (normalize whitespace, escape pipes)
        desc = " ".join(skill.description.split())
        desc = desc.replace("|", "\\|")
        cat = skill.category or "-"
        lines.append(f"| {skill_id} | {desc} | {cat} |")

    if format == "xml":
        lines.append("")
        lines.append("</available_skills>")

    lines.append(MARKER_END)
    return "\n".join(lines)


def update_agents_md(
    path: Path,
    block: str,
    append: bool = True,
) -> bool:
    """Update AGENTS.md with skills block.

    Args:
        path: Path to AGENTS.md file.
        block: Skills block to insert.
        append: If True, append to existing content; if False, replace entirely.

    Returns:
        True if file was updated successfully.
    """
    if not path.exists():
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(block + "\n", encoding="utf-8")
        return True

    content = path.read_text(encoding="utf-8")

    # Check for existing block
    if MARKER_START in content and MARKER_END in content:
        # Replace existing block
        pattern = rf"{re.escape(MARKER_START)}.*?{re.escape(MARKER_END)}"
        new_content = re.sub(pattern, block, content, flags=re.DOTALL)
        path.write_text(new_content, encoding="utf-8")
        return True
    elif append:
        # Append to end
        path.write_text(content.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
        return True
    else:
        # Replace entire file
        path.write_text(block + "\n", encoding="utf-8")
        return True


def sync(
    output: Path = typer.Option(
        Path("./AGENTS.md"),
        "--output",
        "-o",
        help="Output file path",
    ),
    append: bool = typer.Option(
        True,
        "--append/--replace",
        help="Append to existing file or replace entirely",
    ),
    skills_filter: Optional[str] = typer.Option(
        None,
        "--skills",
        help="Comma-separated skill IDs to include",
    ),
    category_filter: Optional[str] = typer.Option(
        None,
        "--category",
        help="Comma-separated categories to include",
    ),
    format: str = typer.Option(
        "xml",
        "--format",
        help="Output format: xml or markdown",
    ),
    mode: str = typer.Option(
        "cli",
        "--mode",
        "-m",
        help="Target agent type: cli (skillsouko show) or mcp (MCP tools)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite without confirmation",
    ),
):
    """Sync installed skills to AGENTS.md."""
    # Validate format
    if format not in ("xml", "markdown"):
        console.print(f"[error]Invalid format: {format}. Use 'xml' or 'markdown'.[/error]")
        raise typer.Exit(1)

    # Validate mode
    if mode not in ("cli", "mcp"):
        console.print(f"[error]Invalid mode: {mode}. Use 'cli' or 'mcp'.[/error]")
        raise typer.Exit(1)

    config = Config()

    # Get all skills
    result = list_skills(config=config, limit=1000)
    skills = list(result.skills)

    # Apply skill ID filter
    if skills_filter:
        ids = {s.strip() for s in skills_filter.split(",") if s.strip()}
        skills = [s for s in skills if s.id in ids]

    # Apply category filter
    if category_filter:
        cats = {c.strip().lower() for c in category_filter.split(",") if c.strip()}
        skills = [s for s in skills if s.category.lower() in cats]

    if not skills:
        console.print("[warning]No skills found matching filters[/warning]")
        raise typer.Exit(1)

    # Generate block
    block = generate_skills_block(skills, format=format, mode=mode)

    # Confirm if file exists and not force
    if output.exists() and not force:
        action = "Update" if MARKER_START in output.read_text(encoding="utf-8") else "Append to"
        if not typer.confirm(f"{action} {output}?"):
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    # Update file
    update_agents_md(output, block, append=append)

    console.print(f"[success]Synced {len(skills)} skill(s) to {output}[/success]")
