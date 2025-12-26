"""Remove skill command."""

import typer

from skillport.modules.skills.public.remove import remove_skill

from ..context import get_config
from ..theme import console, is_interactive, print_error, print_success


def remove(
    ctx: typer.Context,
    skill_id: str = typer.Argument(
        ...,
        help="Skill ID to remove (e.g., hello-world or namespace/skill)",
        show_default=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt (alias for --force)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON (for scripting/AI agents)",
    ),
):
    """Remove an installed skill."""
    # --yes is alias for --force
    skip_confirm = force or yes

    if not skip_confirm and is_interactive():
        confirm = typer.confirm(f"Remove '{skill_id}'?", default=False)
        if not confirm:
            if json_output:
                console.print_json(
                    data={
                        "success": False,
                        "message": "Cancelled by user",
                    }
                )
            else:
                console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(code=1)

    config = get_config(ctx)
    result = remove_skill(skill_id, config=config)

    if json_output:
        console.print_json(
            data={
                "success": result.success,
                "message": result.message,
            }
        )
        if not result.success:
            raise typer.Exit(code=1)
        return

    if result.success:
        print_success(result.message)
    else:
        print_error(
            result.message,
            code="SKILL_NOT_FOUND" if "not found" in result.message.lower() else "REMOVE_FAILED",
            suggestion="Run 'skillport list' to see available skills",
        )
        raise typer.Exit(code=1)
