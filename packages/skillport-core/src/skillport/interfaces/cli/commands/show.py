"""Show skill details command."""

import typer
from rich.markdown import Markdown
from rich.panel import Panel

from skillport.shared.exceptions import SkillNotFoundError

from ..catalog import load_skill_fs
from ..context import get_config
from ..theme import console, print_error


def show(
    ctx: typer.Context,
    skill_id: str = typer.Argument(
        ...,
        help="Skill ID (e.g., hello-world or namespace/skill)",
        show_default=False,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON (for scripting/AI agents)",
    ),
):
    """Show skill details and instructions."""
    config = get_config(ctx)

    try:
        detail = load_skill_fs(skill_id, config=config)
    except SkillNotFoundError:
        print_error(
            f"Skill '{skill_id}' not found",
            code="SKILL_NOT_FOUND",
            suggestion="Run 'skillport list' to see available skills",
            json_output=json_output,
        )
        raise typer.Exit(code=1)

    if json_output:
        console.print_json(data=detail.model_dump())
        return

    # Header panel with metadata
    header = f"[bold]{detail.name}[/bold]\n\n{detail.description}"
    if detail.category:
        header += f"\n\n[dim]Category:[/dim] [magenta]{detail.category}[/magenta]"
    header += f"\n[dim]Path:[/dim] {detail.path}"

    console.print(
        Panel(
            header,
            title=f"[skill.id]{detail.id}[/skill.id]",
            border_style="info",
        )
    )

    # Instructions as markdown
    console.print()
    console.print("[bold]Instructions[/bold]")
    console.print("─" * 40)
    console.print(Markdown(detail.instructions))
