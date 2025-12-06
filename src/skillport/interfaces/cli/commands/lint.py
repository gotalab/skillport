"""Lint skill definitions command."""

import typer
from rich.panel import Panel

from skillport.modules.indexing import list_all
from skillport.modules.skills.public.validation import validate_skill

from ..context import get_config
from ..theme import console, print_success, print_warning


def lint(
    ctx: typer.Context,
    skill_id: str | None = typer.Argument(
        None,
        help="Skill ID to validate (validates all if not specified)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON (for scripting/AI agents)",
    ),
):
    """Validate skill definitions."""
    config = get_config(ctx)
    skills = list_all(limit=1000, config=config)

    if skill_id:
        skills = [s for s in skills if s.get("id") == skill_id or s.get("name") == skill_id]

    if not skills:
        if json_output:
            console.print_json(
                data={
                    "valid": False,
                    "message": "No skills found",
                    "skills": [],
                }
            )
        else:
            print_warning("No skills found to validate.")
        raise typer.Exit(code=1)

    # Collect all issues
    all_results: list[dict] = []
    total_fatal = 0
    total_warning = 0

    for skill in skills:
        result = validate_skill(skill)
        skill_result = {
            "id": skill.get("id", skill.get("name")),
            "valid": result.valid,
            "issues": [
                {"severity": i.severity, "field": i.field, "message": i.message}
                for i in result.issues
            ],
        }
        all_results.append(skill_result)

        for issue in result.issues:
            if issue.severity == "fatal":
                total_fatal += 1
            else:
                total_warning += 1

    # JSON output
    if json_output:
        console.print_json(
            data={
                "valid": total_fatal == 0,
                "skills": all_results,
                "summary": {
                    "total_skills": len(skills),
                    "fatal_issues": total_fatal,
                    "warning_issues": total_warning,
                },
            }
        )
        if total_fatal > 0:
            raise typer.Exit(code=1)
        return

    # Human-readable output
    if total_fatal == 0 and total_warning == 0:
        print_success("✓ All skills pass validation")
        return

    # Show issues grouped by skill
    for skill_result in all_results:
        if not skill_result["issues"]:
            continue

        console.print(f"\n[bold]{skill_result['id']}[/bold]")
        for issue in skill_result["issues"]:
            if issue["severity"] == "fatal":
                console.print(f"  [error]✗ (fatal)[/error] {issue['message']}")
            else:
                console.print(f"  [warning]⚠ (warning)[/warning] {issue['message']}")

    # Summary panel
    console.print()
    summary_style = "red" if total_fatal > 0 else "yellow"
    summary_parts = []
    if total_fatal > 0:
        summary_parts.append(f"[error]{total_fatal} fatal[/error]")
    if total_warning > 0:
        summary_parts.append(f"[warning]{total_warning} warning[/warning]")

    console.print(
        Panel(
            f"Checked {len(skills)} skill(s): {', '.join(summary_parts)}",
            border_style=summary_style,
        )
    )

    if total_fatal > 0:
        raise typer.Exit(code=1)
