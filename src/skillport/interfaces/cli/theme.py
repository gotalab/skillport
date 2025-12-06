"""CLI theme and shared utilities for consistent UI/UX.

This module provides:
- Consistent color scheme for human-readable output
- Structured error output for AI agents
- Console utilities for stderr/stdout separation
"""

import os
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme

# Version from package metadata (pyproject.toml)
try:
    VERSION = version("skillport")
except PackageNotFoundError:
    VERSION = "0.0.0"  # Fallback for development


def print_banner(subtitle: str = ""):
    """Print a compact SkillPort banner with optional subtitle."""
    from rich.align import Align
    from rich.panel import Panel
    from rich.text import Text

    # Build content
    content = Text(justify="center")

    # Logo line
    content.append("⚓ ", style="blue bold")
    content.append("Skill", style="bold white")
    content.append("Port", style="bold blue")
    content.append(f"  v{VERSION}\n", style="dim")

    # Tagline (from README)
    content.append("🚢 All Your Agent Skills in One Place", style="dim italic")

    # Subtitle if provided
    if subtitle:
        content.append("\n\n")
        content.append("🚀 ", style="yellow")
        content.append(subtitle, style="white")

    panel = Panel(
        Align.center(content),
        border_style="blue",
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


# Color scheme
THEME = Theme(
    {
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "cyan",
        "dim": "dim",
        "skill.id": "cyan bold",
        "skill.name": "bold",
        "skill.category": "magenta",
        "score.high": "green",  # >= 0.7
        "score.mid": "yellow",  # >= 0.4
        "score.low": "dim",  # < 0.4
    }
)


# Consoles: stdout for data, stderr for progress/logs
console = Console(theme=THEME)
stderr_console = Console(stderr=True, theme=THEME)


def is_interactive() -> bool:
    """Check if running in interactive mode."""
    if os.environ.get("SKILLPORT_NO_INTERACTIVE"):
        return False
    if os.environ.get("CI"):
        return False
    return console.is_terminal


def score_style(score: float) -> str:
    """Get style for score value."""
    if score >= 0.7:
        return "score.high"
    if score >= 0.4:
        return "score.mid"
    return "score.low"


def format_score(score: float) -> str:
    """Format score with color."""
    style = score_style(score)
    return f"[{style}]{score:.2f}[/{style}]"


def print_error(
    message: str, code: str | None = None, suggestion: str | None = None, json_output: bool = False
):
    """Print error message consistently.

    For humans: Colored error with optional suggestion
    For JSON: Structured error object
    """
    if json_output:
        error_data: dict[str, Any] = {
            "error": True,
            "message": message,
        }
        if code:
            error_data["code"] = code
        if suggestion:
            error_data["suggestion"] = suggestion
        console.print_json(data=error_data)
    else:
        console.print(f"[error]Error:[/error] {message}")
        if suggestion:
            console.print(f"[dim]Hint: {suggestion}[/dim]")


def print_success(message: str):
    """Print success message."""
    console.print(f"[success]{message}[/success]")


def print_warning(message: str):
    """Print warning message."""
    console.print(f"[warning]{message}[/warning]")


def empty_skills_panel() -> Panel:
    """Panel shown when no skills are installed."""
    return Panel(
        "[warning]No skills installed yet.[/warning]\n\n"
        "Get started:\n"
        "  [info]skillport add hello-world[/info]  Add sample skill\n"
        "  [info]skillport add template[/info]     Create your own skill\n\n"
        "[dim]Learn more: skillport --help[/dim]",
        title="Skills (0)",
        border_style="dim",
    )


def no_results_panel(query: str) -> Panel:
    """Panel shown when search returns no results."""
    return Panel(
        f"[warning]No skills match '{query}'[/warning]\n\n"
        "Suggestions:\n"
        "  [dim]-[/dim] Try a different query\n"
        "  [dim]-[/dim] Use broader terms\n"
        "  [dim]-[/dim] Run [info]skillport list[/info] to see all skills",
        title="Search Results (0)",
        border_style="dim",
    )


def create_skills_table(title: str, show_score: bool = False, show_category: bool = True) -> Table:
    """Create a consistently styled skills table."""
    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("ID", style="skill.id", no_wrap=True)
    if show_category:
        table.add_column("Category", style="skill.category")
    table.add_column("Description", overflow="ellipsis", max_width=50)
    if show_score:
        table.add_column("Score", justify="right", width=6)
    return table
