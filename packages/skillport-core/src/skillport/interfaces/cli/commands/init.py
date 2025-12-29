"""Initialize SkillPort for a project.

Implements SPEC2-CLI Section 3.1: init コマンド.
Creates .skillportrc, skills directory, and updates instruction files.
"""

from pathlib import Path

import typer

from ..catalog import list_skills_fs
from ..context import get_config
from ..theme import console, print_banner
from .doc import generate_skills_block, update_agents_md

# Default choices for interactive mode
# (display_name, actual_path) - None means "use display as path"
DEFAULT_SKILLS_DIRS = [
    ("~/.skillport/skills (default)", "~/.skillport/skills"),
    (".claude/skills (Claude Code)", ".claude/skills"),
    ("~/.codex/skills (Codex)", "~/.codex/skills"),
    (".skills", None),
]

DEFAULT_INSTRUCTIONS = [
    ("AGENTS.md", "Codex, Cursor, Windsurf"),
    ("GEMINI.md", "Gemini CLI, Antigravity"),
    (None, "None (skip)"),  # Special: None means skip instruction file creation
]


def _prompt_skills_dir() -> Path:
    """Interactively prompt for skills directory."""
    console.print("\n[bold]? Where are your skills located?[/bold]")
    for i, (display, _) in enumerate(DEFAULT_SKILLS_DIRS, 1):
        console.print(f"  [{i}] {display}")
    console.print(f"  [{len(DEFAULT_SKILLS_DIRS) + 1}] Custom path...")

    while True:
        choice = typer.prompt("Choice", default="1")
        try:
            idx = int(choice)
            if 1 <= idx <= len(DEFAULT_SKILLS_DIRS):
                display, actual = DEFAULT_SKILLS_DIRS[idx - 1]
                return Path(actual if actual else display)
            elif idx == len(DEFAULT_SKILLS_DIRS) + 1:
                custom = typer.prompt("Enter path")
                return Path(custom)
        except ValueError:
            pass
        console.print("[error]Invalid choice[/error]")


def _prompt_instructions() -> list[str]:
    """Interactively prompt for instruction files (multi-select)."""
    console.print("\n[bold]? Which instruction files to update? (comma-separated)[/bold]")
    for i, (name, desc) in enumerate(DEFAULT_INSTRUCTIONS, 1):
        if name is None:
            # "None (skip)" option
            console.print(f"  [{i}] {desc}")
        else:
            console.print(f"  [{i}] {name} ({desc})")
    console.print(f"  [{len(DEFAULT_INSTRUCTIONS) + 1}] Custom...")

    selection = typer.prompt("Choice (e.g., 1,2)", default="1")
    choices = [c.strip() for c in selection.split(",")]

    result = []
    for choice in choices:
        try:
            idx = int(choice)
            if 1 <= idx <= len(DEFAULT_INSTRUCTIONS):
                name, _ = DEFAULT_INSTRUCTIONS[idx - 1]
                if name is None:
                    # "None (skip)" selected - return empty list immediately
                    return []
                result.append(name)
            elif idx == len(DEFAULT_INSTRUCTIONS) + 1:
                custom = typer.prompt("Enter file path")
                result.append(custom)
        except ValueError:
            # Treat as direct path
            if choice:
                result.append(choice)

    return result if result else ["AGENTS.md"]


def _create_skillportrc(
    path: Path,
    skills_dir: Path,
    instructions: list[str],
) -> None:
    """Create .skillportrc file."""
    # Convert skills_dir to string with forward slashes (cross-platform)
    try:
        rel = skills_dir.relative_to(Path.home())
        skills_dir_str = "~/" + rel.as_posix()
    except ValueError:
        # Outside home directory, use absolute path with forward slashes
        skills_dir_str = skills_dir.as_posix()

    with open(path, "w", encoding="utf-8") as f:
        f.write("# SkillPort Configuration\n")
        f.write("# See: https://github.com/gotalab/skillport\n\n")
        f.write(f"skills_dir: {skills_dir_str}\n")
        if instructions:
            f.write("instructions:\n")
            for instr in instructions:
                f.write(f"  - {instr}\n")


def init(
    ctx: typer.Context,
    skills_dir: Path | None = typer.Option(
        None,
        "--skills-dir",
        "-d",
        help="Skills directory path",
    ),
    instructions: list[str] | None = typer.Option(
        None,
        "--instructions",
        "-i",
        help="Instruction files to update (can be specified multiple times)",
    ),
    no_instructions: bool = typer.Option(
        False,
        "--no-instructions",
        "--skip-instructions",
        help="Skip updating instruction files",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip prompts and use defaults",
    ),
):
    """Initialize SkillPort for a project.

    Creates .skillportrc, skills directory, and updates instruction files.
    After init, start your coding agent to use skills immediately.
    """
    # Show banner
    print_banner("Initialize your project for Agent Skills")

    cwd = Path.cwd()

    # Check if already initialized
    rc_path = cwd / ".skillportrc"
    if rc_path.exists():
        if not typer.confirm(".skillportrc already exists. Overwrite?"):
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    # Determine skills_dir
    if skills_dir is None:
        if yes:
            # Use first option's actual path (or display if actual is None)
            display, actual = DEFAULT_SKILLS_DIRS[0]
            skills_dir = Path(actual if actual else display)
        else:
            skills_dir = _prompt_skills_dir()

    # Expand and resolve path
    skills_path = skills_dir.expanduser()
    if not skills_path.is_absolute():
        skills_path = (cwd / skills_path).resolve()

    # Determine instruction files
    if no_instructions:
        if instructions:
            raise typer.BadParameter(
                "Cannot combine --no-instructions/--skip-instructions with --instructions/-i"
            )
        instructions = []
    elif instructions is None or len(instructions) == 0:
        if yes:
            instructions = ["AGENTS.md"]
        else:
            instructions = _prompt_instructions()

    # 1. Create .skillportrc
    _create_skillportrc(rc_path, skills_dir, instructions)
    console.print("[success]✓ Created .skillportrc[/success]")

    # 2. Create skills directory if needed
    if not skills_path.exists():
        skills_path.mkdir(parents=True, exist_ok=True)
        console.print(f"[success]✓ Created {skills_dir}/[/success]")
    else:
        console.print(f"[dim]✓ {skills_dir}/ already exists[/dim]")

    # 3. Scan skills
    base_config = get_config(ctx)
    config = base_config.with_overrides(skills_dir=skills_path)
    result = list_skills_fs(config=config, limit=1000)
    skill_count = result.total
    console.print(f"[success]✓ Found {skill_count} skill(s)[/success]")

    # 4. Update instruction files
    if not instructions:
        console.print("[dim]⊘ Skipped instruction files (none selected)[/dim]")
    elif skill_count > 0:
        skills = list(result.skills)
        block = generate_skills_block(skills, format="xml", mode="cli")

        for instr_file in instructions:
            instr_path = cwd / instr_file
            update_agents_md(instr_path, block, append=True)
            console.print(f"[success]✓ Updated {instr_file}[/success]")
    else:
        for instr_file in instructions:
            console.print(f"[dim]⊘ Skipped {instr_file} (no skills)[/dim]")

    console.print()
    console.print("[bold green]✨ Ready![/bold green] Start your coding agent to use skills.")
    console.print("[dim]   Run 'skillport add hello-world' to add your first skill[/dim]")
    if skill_count > 5 and instructions:
        console.print(
            "[dim]   Tip: Edit instruction files to remove skills not relevant to this project[/dim]"
        )
