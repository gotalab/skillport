"""Generate skill documentation for AGENTS.md.

Implements SPEC2-CLI Section 3.2: doc コマンド.
Generates a skills block that can be embedded in AGENTS.md files.
"""

import re
from pathlib import Path

import typer

from skillport.modules.skills.public.types import SkillSummary
from skillport.shared.config import Config

from ..catalog import list_skills_fs
from ..config import load_project_config
from ..theme import console

MARKER_START = "<!-- SKILLPORT_START -->"
MARKER_END = "<!-- SKILLPORT_END -->"


def _truncate_description(desc: str, max_len: int = 50) -> str:
    """Truncate description to max length with ellipsis."""
    # Clean up newlines and extra spaces
    desc = " ".join(desc.split())
    if len(desc) <= max_len:
        return desc
    return desc[: max_len - 3] + "..."


CLI_INSTRUCTIONS = """
## SkillPort Skills

Skills are reusable expert knowledge that help you complete tasks effectively.
Each skill contains step-by-step instructions, templates, and scripts.

### Workflow

1. **Find a skill** - Check the list below for a skill matching your task
2. **Get instructions** - Run `skillport show <skill-id>` to load full instructions
3. **Follow the instructions** - Execute the steps using your available tools

### Tips

- Skills may include scripts - execute them via the skill's path, don't read them into context
- If instructions reference `{path}`, replace it with the skill's directory path
- When uncertain, check the skill's description to confirm it matches your task
""".strip()

MCP_INSTRUCTIONS = """
## SkillPort Skills

Skills are reusable expert knowledge that help you complete tasks effectively.
Each skill contains step-by-step instructions, templates, and scripts.

### Workflow

1. **Search** - Call `search_skills(query)` to find skills matching your task
2. **Load** - Call `load_skill(skill_id)` to get full instructions and `path`
3. **Execute** - Follow the instructions using your available tools

### Tools

- `search_skills(query)` - Find skills by task description. Use `""` to list all.
- `load_skill(id)` - Get full instructions and the skill's filesystem path.

### Tips

- Use your native Read tool with `{path}/file` for templates/assets
- Execute scripts via path, don't read them into context: `python {path}/scripts/run.py`
- Replace `{path}` in instructions with the actual path from `load_skill`
- If search returns too many results, use more specific terms
""".strip()


def _escape_xml(text: str) -> str:
    """Escape special characters for XML content."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_skills_block(
    skills: list[SkillSummary],
    format: str = "xml",
    mode: str = "cli",
    config: Config | None = None,
    skills_only: bool = False,
) -> str:
    """Generate skills block for AGENTS.md.

    Args:
        skills: List of skills to include.
        format: Output format ("xml" or "markdown").
        mode: Target mode ("cli" or "mcp").
        config: Config for resolving skill paths.
        skills_only: If True, output only the skills list without instructions.

    Returns:
        Formatted skills block with markers.
    """
    lines = []

    if not skills_only:
        lines.append(MARKER_START)
        # Instructions first (most important for agents)
        instructions = MCP_INSTRUCTIONS if mode == "mcp" else CLI_INSTRUCTIONS
        lines.append(instructions)
        lines.append("")

    if format == "xml":
        # Proper XML format per skill-client-integration spec
        lines.append("<available_skills>")
        for skill in skills:
            skill_id = skill.id
            desc = " ".join(skill.description.split())
            lines.append("<skill>")
            lines.append(f"  <name>{_escape_xml(skill_id)}</name>")
            lines.append(f"  <description>{_escape_xml(desc)}</description>")
            # Add location for filesystem-based clients
            if config and config.skills_dir:
                skill_path = config.skills_dir / skill_id / "SKILL.md"
                if skill_path.exists():
                    lines.append(f"  <location>{_escape_xml(str(skill_path))}</location>")
            lines.append("</skill>")
        lines.append("</available_skills>")
    else:
        # Markdown format (legacy)
        for skill in skills:
            skill_id = skill.id
            desc = " ".join(skill.description.split())
            lines.append(f"- `{skill_id}`: {desc}")

    if not skills_only:
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


def doc(
    ctx: typer.Context,
    output: Path = typer.Option(
        Path("./AGENTS.md"),
        "--output",
        "-o",
        help="Output file path",
    ),
    doc_all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Update all instruction files from .skillportrc",
    ),
    append: bool = typer.Option(
        True,
        "--append/--replace",
        help="Append to existing file or replace entirely",
    ),
    skills_filter: str | None = typer.Option(
        None,
        "--skills",
        help="Comma-separated skill IDs to include",
    ),
    category_filter: str | None = typer.Option(
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
        help="Target agent type: cli (skillport show) or mcp (MCP tools)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite without confirmation",
    ),
    skills_only: bool = typer.Option(
        False,
        "--skills-only",
        help="Output only <available_skills> block (no instructions/markers)",
    ),
):
    """Generate skill documentation for AGENTS.md."""
    # Validate format
    if format not in ("xml", "markdown"):
        console.print(f"[error]Invalid format: {format}. Use 'xml' or 'markdown'.[/error]")
        raise typer.Exit(1)

    # Validate mode
    if mode not in ("cli", "mcp"):
        console.print(f"[error]Invalid mode: {mode}. Use 'cli' or 'mcp'.[/error]")
        raise typer.Exit(1)

    # Load project config for instruction targets; prefer CLI/global config for skills_dir
    project_config = load_project_config()

    obj = getattr(ctx, "obj", None)
    if isinstance(obj, Config):
        config = obj
    else:
        config = Config(skills_dir=project_config.skills_dir)

    # Get all skills
    result = list_skills_fs(config=config, limit=1000)
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
    block = generate_skills_block(
        skills, format=format, mode=mode, config=config, skills_only=skills_only
    )

    # Determine output files
    if doc_all:
        # Use instruction files from project config
        if not project_config.instructions:
            console.print(
                "[warning]No instruction files in .skillportrc. Using default AGENTS.md[/warning]"
            )
            output_files = [Path("./AGENTS.md")]
        else:
            output_files = [Path(f) for f in project_config.instructions]
    else:
        output_files = [output]

    # Update each file
    for out_path in output_files:
        # Confirm if file exists and not force
        if out_path.exists() and not force:
            if skills_only:
                action = "Append to" if append else "Overwrite"
            else:
                try:
                    content = out_path.read_text(encoding="utf-8")
                    action = "Update" if MARKER_START in content else "Append to"
                except Exception:
                    action = "Create"
            if not typer.confirm(f"{action} {out_path}?"):
                console.print(f"[dim]Skipped {out_path}[/dim]")
                continue

        # Update file
        if skills_only:
            # Direct write for skills-only mode (no marker handling)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if append and out_path.exists():
                existing = out_path.read_text(encoding="utf-8")
                out_path.write_text(existing.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
            else:
                out_path.write_text(block + "\n", encoding="utf-8")
        else:
            update_agents_md(out_path, block, append=append)
        console.print(f"[success]Generated {len(skills)} skill(s) to {out_path}[/success]")
