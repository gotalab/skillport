"""Typer-based CLI entry point.

SkillPort CLI provides commands to manage AI agent skills:
- show: Display skill details
- add: Install skills from various sources
- list: Show installed skills
- remove: Uninstall skills
- update: Update skills from original sources
- validate: Validate skill definitions against Agent Skills spec
- doc: Generate skill documentation for AGENTS.md
"""

import os
from pathlib import Path

import typer

from skillport.shared.config import Config

from .commands.add import add
from .commands.doc import doc
from .commands.init import init
from .commands.list import list_cmd
from .commands.meta import meta_app
from .commands.remove import remove
from .commands.show import show
from .commands.update import update
from .commands.validate import lint_deprecated, validate
from .config import load_project_config
from .theme import VERSION, console


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"skillport [info]{VERSION}[/info]")
        raise typer.Exit()


app = typer.Typer(
    name="skillport",
    help="[bold]⚓ SkillPort[/bold] - SkillOps CLI for Agent Skills\n\n"
    "A CLI for managing and documenting skills on disk.\n\n"
    "[dim]Docs: https://github.com/gotalab/skillport[/dim]",
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=True,
    pretty_exceptions_show_locals=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    skills_dir: Path | None = typer.Option(
        None,
        "--skills-dir",
        help="Override skills directory (CLI > env > default)",
    ),
):
    """SkillPort - All Your Agent Skills in One Place."""
    # Resolve project config (env → .skillportrc → pyproject → default)
    project_config = load_project_config()

    # Build base config and apply CLI overrides (CLI > env/.skillportrc > default)
    overrides = {}
    if skills_dir:
        overrides["skills_dir"] = skills_dir.expanduser().resolve()
    # Only inject project-config skills_dir when env/CLI haven't set it
    if not os.getenv("SKILLPORT_SKILLS_DIR") and not skills_dir:
        overrides.setdefault("skills_dir", project_config.skills_dir)

    config = Config(**overrides) if overrides else Config()
    ctx.obj = config


# Register commands with enhanced help
app.command(
    "init",
    help="Initialize SkillPort for a project.\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport init\n\n"
    "  skillport init --yes\n\n"
    "  skillport init -d .skills\n\n"
    "  skillport init -d ~/.codex/skills\n\n"
    "  skillport init -d .claude/skills -i CLAUDE.md\n\n"
    "  skillport init --no-instructions",
)(init)

app.command(
    "show",
    help="Show skill details and instructions.\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport show hello-world\n\n"
    "  skillport show team/code-review\n\n"
    "  skillport show pdf --json",
)(show)

app.command(
    "add",
    help="Add skills from various sources.\n\n"
    "[bold]Sources:[/bold]\n\n"
    "  [dim]Built-in:[/dim]  hello-world, template\n\n"
    "  [dim]Local:[/dim]     ./my-skill/, ./collection/\n\n"
    "  [dim]GitHub:[/dim]    https://github.com/user/repo\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport add hello-world\n\n"
    "  skillport add ./my-skills/ --namespace team\n\n"
    "  skillport add https://github.com/user/repo --yes",
)(add)

app.command(
    "list",
    help="List installed skills.\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport list\n\n"
    "  skillport list --limit 20\n\n"
    "  skillport list --json",
)(list_cmd)

app.command(
    "remove",
    help="Remove an installed skill.\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport remove hello-world\n\n"
    "  skillport remove team/skill --force",
)(remove)

app.command(
    "update",
    help="Update skills from their original sources.\n\n"
    "By default shows available updates. Use --all to update all,\n"
    "or specify a skill ID to update one.\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport update\n\n"
    "  skillport update my-skill\n\n"
    "  skillport update --all\n\n"
    "  skillport update my-skill --force\n\n"
    "  skillport update --all --dry-run",
)(update)

app.command(
    "validate",
    help="Validate skill definitions against Agent Skills specification.\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport validate\n\n"
    "  skillport validate hello-world\n\n"
    "  skillport validate ./my-skill\n\n"
    "  skillport validate ./skills/",
)(validate)

# Deprecated alias for 'validate'
app.command(
    "lint",
    help="[dim][Deprecated] Use 'validate' instead.[/dim]",
    hidden=True,
)(lint_deprecated)

app.command(
    "doc",
    help="Generate skill documentation for AGENTS.md.\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport doc\n\n"
    "  skillport doc --all\n\n"
    "  skillport doc -o .claude/AGENTS.md\n\n"
    "  skillport doc --category development,testing",
)(doc)

app.add_typer(
    meta_app,
    name="meta",
    help="Manage skill frontmatter metadata.\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport meta show my-skill\n\n"
    "  skillport meta set my-skill author gota\n\n"
    "  skillport meta bump my-skill version --patch\n\n"
    "  skillport meta unset my-skill author",
)


def run():
    """Entry point for CLI."""
    app()
