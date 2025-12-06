"""Typer-based CLI entry point.

SkillPort CLI provides commands to manage AI agent skills:
- search: Find skills by query
- show: Display skill details
- add: Install skills from various sources
- list: Show installed skills
- remove: Uninstall skills
- update: Update skills from original sources
- lint: Validate skill definitions
- serve: Start MCP server
- doc: Generate skill documentation for AGENTS.md
"""

import os
from pathlib import Path

import typer

from skillport.shared.config import Config

from .auto_index import should_auto_reindex
from .commands.add import add
from .commands.doc import doc
from .commands.init import init
from .commands.lint import lint
from .commands.list import list_cmd
from .commands.remove import remove
from .commands.search import search
from .commands.serve import serve
from .commands.show import show
from .commands.update import update
from .config import load_project_config
from .theme import VERSION, console


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"skillport [info]{VERSION}[/info]")
        raise typer.Exit()


app = typer.Typer(
    name="skillport",
    help="[bold]⚓ SkillPort[/bold] - All Your Agent Skills in One Place\n\n"
    "A CLI and MCP server for managing, searching, and serving skills to AI agents.\n\n"
    "[dim]Docs: https://github.com/gotalab/skillport[/dim]",
    rich_markup_mode="rich",
    no_args_is_help=False,
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
    db_path: Path | None = typer.Option(
        None,
        "--db-path",
        help="Override LanceDB path (CLI > env > default)",
    ),
    auto_reindex: bool | None = typer.Option(
        None,
        "--auto-reindex/--no-auto-reindex",
        help="Automatically rebuild index if stale (default: enabled; respects SKILLPORT_AUTO_REINDEX)",
    ),
):
    """SkillPort - All Your Agent Skills in One Place."""
    # Resolve project config (env → .skillportrc → pyproject → default)
    project_config = load_project_config()

    # Build base config and apply CLI overrides (CLI > env/.skillportrc > default)
    overrides = {}
    if skills_dir:
        overrides["skills_dir"] = skills_dir.expanduser().resolve()
    if db_path:
        overrides["db_path"] = db_path.expanduser().resolve()

    # Only inject project-config skills_dir when env/CLI haven't set it
    if not os.getenv("SKILLPORT_SKILLS_DIR") and not skills_dir:
        overrides.setdefault("skills_dir", project_config.skills_dir)

    config = Config(**overrides) if overrides else Config()
    # propagate auto_reindex preference to child commands
    ctx.meta["auto_reindex"] = auto_reindex if auto_reindex is not None else None
    ctx.meta["auto_reindex_default"] = should_auto_reindex(ctx)
    ctx.obj = config

    # If no command given, run serve (legacy behavior) with injected config
    if ctx.invoked_subcommand is None:
        ctx.invoke(serve)


# Register commands with enhanced help
app.command(
    "init",
    help="Initialize SkillPort for a project.\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport init\n\n"
    "  skillport init --yes\n\n"
    "  skillport init -d .agent/skills -i AGENTS.md",
)(init)

app.command(
    "search",
    help="Search for skills matching a query.\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport search 'PDF extraction'\n\n"
    "  skillport search code --limit 5\n\n"
    "  skillport search test --json",
)(search)

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
    "lint",
    help="Validate skill definitions.\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport lint\n\n"
    "  skillport lint hello-world",
)(lint)

app.command(
    "serve",
    help="Start the MCP server.\n\n"
    "By default, runs in stdio mode (Local) for direct agent integration.\n"
    "Use --http for HTTP server (Remote) mode.\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport serve\n\n"
    "  skillport serve --reindex\n\n"
    "  skillport serve --http --port 8080",
)(serve)

app.command(
    "doc",
    help="Generate skill documentation for AGENTS.md.\n\n"
    "[bold]Examples:[/bold]\n\n"
    "  skillport doc\n\n"
    "  skillport doc --all\n\n"
    "  skillport doc -o .claude/AGENTS.md\n\n"
    "  skillport doc --category development,testing",
)(doc)


def run():
    """Entry point for CLI."""
    app()
