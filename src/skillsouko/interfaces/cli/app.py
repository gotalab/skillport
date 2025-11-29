"""Typer-based CLI entry point.

SkillSouko CLI provides commands to manage AI agent skills:
- search: Find skills by query
- show: Display skill details
- add: Install skills from various sources
- list: Show installed skills
- remove: Uninstall skills
- lint: Validate skill definitions
- serve: Start MCP server
- sync: Sync skills to AGENTS.md for non-MCP agents
"""

from typing import Optional

import typer

from .commands.search import search
from .commands.show import show
from .commands.add import add
from .commands.remove import remove
from .commands.list import list_cmd
from .commands.lint import lint
from .commands.serve import serve
from .commands.sync import sync
from .theme import VERSION, console


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"skillsouko [info]{VERSION}[/info]")
        raise typer.Exit()


app = typer.Typer(
    name="skillsouko",
    help="[bold]SkillSouko[/bold] - Manage AI agent skills\n\n"
         "A CLI and MCP server for organizing, searching, and serving skills to AI agents.",
    rich_markup_mode="rich",
    no_args_is_help=False,
    add_completion=True,
    pretty_exceptions_show_locals=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """SkillSouko - Manage AI agent skills."""
    # If no command given, run serve (legacy behavior)
    if ctx.invoked_subcommand is None:
        serve()


# Register commands with enhanced help
app.command(
    "search",
    help="Search for skills matching a query.\n\n"
         "[bold]Examples:[/bold]\n\n"
         "  skillsouko search 'PDF extraction'\n\n"
         "  skillsouko search code --limit 5\n\n"
         "  skillsouko search test --json",
)(search)

app.command(
    "show",
    help="Show skill details and instructions.\n\n"
         "[bold]Examples:[/bold]\n\n"
         "  skillsouko show hello-world\n\n"
         "  skillsouko show team/code-review\n\n"
         "  skillsouko show pdf --json",
)(show)

app.command(
    "add",
    help="Add skills from various sources.\n\n"
         "[bold]Sources:[/bold]\n\n"
         "  [dim]Built-in:[/dim]  hello-world, template\n\n"
         "  [dim]Local:[/dim]     ./my-skill/, ./collection/\n\n"
         "  [dim]GitHub:[/dim]    https://github.com/user/repo\n\n"
         "[bold]Examples:[/bold]\n\n"
         "  skillsouko add hello-world\n\n"
         "  skillsouko add ./my-skills/ --namespace team\n\n"
         "  skillsouko add https://github.com/user/repo --yes",
)(add)

app.command(
    "list",
    help="List installed skills.\n\n"
         "[bold]Examples:[/bold]\n\n"
         "  skillsouko list\n\n"
         "  skillsouko list --limit 20\n\n"
         "  skillsouko list --json",
)(list_cmd)

app.command(
    "remove",
    help="Remove an installed skill.\n\n"
         "[bold]Examples:[/bold]\n\n"
         "  skillsouko remove hello-world\n\n"
         "  skillsouko remove team/skill --force",
)(remove)

app.command(
    "lint",
    help="Validate skill definitions.\n\n"
         "[bold]Examples:[/bold]\n\n"
         "  skillsouko lint\n\n"
         "  skillsouko lint hello-world",
)(lint)

app.command(
    "serve",
    help="Start the MCP server.\n\n"
         "[bold]Examples:[/bold]\n\n"
         "  skillsouko serve\n\n"
         "  skillsouko serve --reindex",
)(serve)

app.command(
    "sync",
    help="Sync skills to AGENTS.md for non-MCP agents.\n\n"
         "[bold]Examples:[/bold]\n\n"
         "  skillsouko sync\n\n"
         "  skillsouko sync -o .claude/AGENTS.md\n\n"
         "  skillsouko sync --category development,testing\n\n"
         "  skillsouko sync --format markdown",
)(sync)


def run():
    """Entry point for CLI."""
    app()
