import typer
from rich.console import Console

from skillpod.modules.indexing import list_all
from skillpod.modules.skills.public.validation import validate_skill
from skillpod.shared.config import Config

console = Console()


def lint(skill_id: str | None = typer.Argument(None, help="Optional skill id to lint")):
    config = Config()
    skills = list_all(limit=1000, config=config)
    if skill_id:
        skills = [
            s for s in skills if s.get("id") == skill_id or s.get("name") == skill_id
        ]
    if not skills:
        console.print("[yellow]No skills found.[/yellow]")
        raise typer.Exit(code=1)

    issues_total = 0
    fatal_count = 0
    for skill in skills:
        result = validate_skill(skill)
        if not result.issues:
            continue
        issues_total += len(result.issues)
        fatal_count += sum(1 for i in result.issues if i.severity == "fatal")
        console.print(f"[red]{skill.get('id', skill.get('name'))}[/red]")
        for issue in result.issues:
            console.print(f"  - ({issue.severity}) {issue.message}")

    if issues_total == 0:
        console.print("[green]✓ All skills pass validation[/green]")
    else:
        console.print(f"[yellow]{issues_total} issue(s) found[/yellow]")
        if fatal_count > 0:
            raise typer.Exit(code=1)
