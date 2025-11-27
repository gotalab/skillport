import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt

from skillpod.modules.skills import add_skill
from skillpod.modules.skills.internal import detect_skills, fetch_github_source, parse_github_url
from skillpod.shared.config import Config

console = Console()


def _is_external_source(source: str) -> bool:
    """Check if source is a path or URL (not builtin)."""
    return source.startswith((".", "/", "~", "https://"))


def _get_source_name(source: str) -> str:
    """Extract name from source path or URL."""
    if source.startswith("https://"):
        parsed = parse_github_url(source)
        return Path(parsed.normalized_path or parsed.repo).name
    return Path(source.rstrip("/")).name


def _detect_skills_from_source(source: str) -> tuple[list[str], str, Path | None]:
    """Detect skills from source. Returns (skill_names, source_name, temp_dir)."""
    source_name = _get_source_name(source)
    temp_dir: Path | None = None

    if source.startswith("https://"):
        try:
            console.print(f"[dim]Fetching {source}...[/dim]")
            temp_dir = fetch_github_source(source)
            skills = detect_skills(Path(temp_dir))
            skill_names = [s.name for s in skills] if skills else [source_name]
            return skill_names, source_name, temp_dir
        except Exception as e:
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            console.print(f"[yellow]Warning: Could not fetch source: {e}[/yellow]")
            return [source_name], source_name, None

    source_path = Path(source).expanduser().resolve()
    if source_path.exists() and source_path.is_dir():
        try:
            skills = detect_skills(source_path)
            skill_names = [s.name for s in skills] if skills else [source_name]
            return skill_names, source_name, None
        except Exception:
            return [source_name], source_name, None

    return [source_name], source_name, None


def add(
    source: str = typer.Argument(..., help="Built-in name, local path, or GitHub URL"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing"),
    keep_structure: bool | None = typer.Option(
        None,
        "--keep-structure/--no-keep-structure",
        help="Preserve directory structure (default: auto - false for single, true for multiple)",
    ),
    namespace: str | None = typer.Option(
        None, "--namespace", "-n", help="Namespace for the skill(s)"
    ),
    name: str | None = typer.Option(
        None, "--name", help="Rename single skill to this name"
    ),
):
    temp_dir: Path | None = None

    try:
        # Interactive namespace selection for external sources
        if _is_external_source(source) and keep_structure is None and namespace is None:
            skill_names, source_name, temp_dir = _detect_skills_from_source(source)

            is_single = len(skill_names) == 1
            skill_display = skill_names[0] if is_single else ", ".join(skill_names[:3]) + ("..." if len(skill_names) > 3 else "")

            console.print(f"\n[bold]Found {len(skill_names)} skill(s):[/bold] {skill_display}")
            console.print("[bold]Where to add?[/bold]")
            if is_single:
                console.print(f"  [cyan][1][/cyan] Flat       → skills/{skill_names[0]}/")
                console.print(f"  [cyan][2][/cyan] Namespace  → skills/[dim]<ns>[/dim]/{skill_names[0]}/")
            else:
                console.print(f"  [cyan][1][/cyan] Flat       → skills/{skill_names[0]}/, skills/{skill_names[1]}/, ...")
                console.print(f"  [cyan][2][/cyan] Namespace  → skills/[dim]<ns>[/dim]/{skill_names[0]}/, ...")
            console.print("  [cyan][3][/cyan] Skip")
            choice = Prompt.ask("Choice", choices=["1", "2", "3"], default="1")

            if choice == "3":
                console.print("[yellow]Skipped[/yellow]")
                raise typer.Exit(code=0)
            if choice == "1":
                keep_structure = False
            if choice == "2":
                keep_structure = True
                namespace = Prompt.ask("Namespace", default=source_name)

        config = Config()
        result = add_skill(
            source,
            config=config,
            force=force,
            keep_structure=keep_structure,
            namespace=namespace,
            name=name,
        )

        # Display results clearly
        if result.added:
            for skill_id in result.added:
                console.print(f"[green]  ✓ Added '{skill_id}'[/green]")
        if result.skipped:
            for skill_id in result.skipped:
                console.print(f"[yellow]  ⊘ Skipped '{skill_id}' (exists)[/yellow]")

        # Summary
        if result.added and not result.skipped:
            console.print(f"[green]Added {len(result.added)} skill(s)[/green]")
        elif result.added and result.skipped:
            console.print(f"[yellow]Added {len(result.added)}, skipped {len(result.skipped)} (use --force to overwrite)[/yellow]")
        elif result.skipped:
            console.print(f"[red]All {len(result.skipped)} skill(s) already exist (use --force to overwrite)[/red]")
            raise typer.Exit(code=1)
        else:
            console.print(f"[red]✗ {result.message}[/red]")
            raise typer.Exit(code=1)
    finally:
        # Cleanup temp dir from pre-scan (add_skill will do its own fetch)
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
