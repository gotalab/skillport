"""Add skills command."""

import shutil
from pathlib import Path

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from skillport.modules.indexing import build_index
from skillport.modules.skills import add_skill
from skillport.modules.skills.internal import (
    detect_skills,
    extract_zip,
    fetch_github_source_with_info,
    parse_github_url,
)

from ..context import get_config
from ..theme import (
    console,
    is_interactive,
    print_error,
    print_success,
    print_warning,
    stderr_console,
)


def _is_external_source(source: str) -> bool:
    """Check if source is a path or URL (not builtin)."""
    if source.startswith((".", "/", "~", "https://")):
        return True
    # Also consider .zip files as external sources
    if source.lower().endswith(".zip"):
        return True
    return False


def _get_source_name(source: str) -> str:
    """Extract name from source path or URL."""
    if source.startswith("https://"):
        parsed = parse_github_url(source)
        return Path(parsed.normalized_path or parsed.repo).name
    return Path(source.rstrip("/")).name


def _get_default_namespace(source: str) -> str:
    """Get default namespace for source (repo name for GitHub)."""
    if source.startswith("https://"):
        parsed = parse_github_url(source)
        return parsed.repo
    return Path(source.rstrip("/")).name


def _detect_skills_from_source(source: str) -> tuple[list[str], str, Path | None, str]:
    """Detect skills from source. Returns (skill_names, source_name, temp_dir, commit_sha)."""
    source_name = _get_source_name(source)
    temp_dir: Path | None = None
    commit_sha: str = ""

    if source.startswith("https://"):
        try:
            # Progress spinner on stderr to keep stdout clean
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=stderr_console,
                transient=True,
            ) as progress:
                progress.add_task(f"Fetching {source}...", total=None)
                fetch_result = fetch_github_source_with_info(source)
                temp_dir = fetch_result.extracted_path
                commit_sha = fetch_result.commit_sha

            skills = detect_skills(Path(temp_dir))
            skill_names = [s.name for s in skills] if skills else [source_name]
            return skill_names, source_name, temp_dir, commit_sha
        except Exception as e:
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            print_warning(f"Could not fetch source: {e}")
            return [source_name], source_name, None, ""

    source_path = Path(source).expanduser().resolve()

    # Handle zip files
    if source_path.exists() and source_path.is_file() and source_path.suffix.lower() == ".zip":
        try:
            extract_result = extract_zip(source_path)
            temp_dir = extract_result.extracted_path
            skills = detect_skills(temp_dir)
            skill_names = [s.name for s in skills] if skills else [source_name]
            return skill_names, source_name, temp_dir, ""
        except Exception as e:
            print_warning(f"Could not extract zip: {e}")
            return [source_name], source_name, None, ""

    if source_path.exists() and source_path.is_dir():
        try:
            skills = detect_skills(source_path)
            skill_names = [s.name for s in skills] if skills else [source_name]
            return skill_names, source_name, None, ""
        except Exception:
            return [source_name], source_name, None, ""

    return [source_name], source_name, None, ""


def add(
    ctx: typer.Context,
    source: str = typer.Argument(
        ...,
        help="Built-in name, local path, or GitHub URL",
        show_default=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing skills",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip interactive prompts (for CI/automation)",
    ),
    keep_structure: bool | None = typer.Option(
        None,
        "--keep-structure/--no-keep-structure",
        help="Preserve directory structure as namespace",
    ),
    namespace: str | None = typer.Option(
        None,
        "--namespace",
        "-n",
        help="Custom namespace for the skill(s)",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="Rename skill (single skill only)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON (for scripting/AI agents)",
    ),
):
    """Add skills from various sources."""
    temp_dir: Path | None = None
    commit_sha: str = ""

    try:
        # Interactive namespace selection for external sources
        if _is_external_source(source) and keep_structure is None and namespace is None:
            skill_names, source_name, temp_dir, commit_sha = _detect_skills_from_source(source)
            is_single = len(skill_names) == 1

            # Non-interactive mode: use sensible defaults
            if yes or not is_interactive():
                if is_single:
                    keep_structure = False
                else:
                    keep_structure = True
                    namespace = namespace or _get_default_namespace(source)
            else:
                # Interactive mode
                skill_display = (
                    skill_names[0]
                    if is_single
                    else ", ".join(skill_names[:3]) + ("..." if len(skill_names) > 3 else "")
                )

                console.print(f"\n[bold]Found {len(skill_names)} skill(s):[/bold] {skill_display}")
                console.print("[bold]Where to add?[/bold]")
                if is_single:
                    console.print(f"  [info][1][/info] Flat       → skills/{skill_names[0]}/")
                    console.print(
                        f"  [info][2][/info] Namespace  → skills/[dim]<ns>[/dim]/{skill_names[0]}/ "
                        "[warning](Claude Code incompatible)[/warning]"
                    )
                else:
                    console.print(
                        f"  [info][1][/info] Flat       → skills/{skill_names[0]}/, skills/{skill_names[1]}/, ..."
                    )
                    console.print(
                        f"  [info][2][/info] Namespace  → skills/[dim]<ns>[/dim]/{skill_names[0]}/, ... "
                        "[warning](Claude Code incompatible)[/warning]"
                    )
                console.print("  [info][3][/info] Skip")
                choice = Prompt.ask("Choice", choices=["1", "2", "3"], default="1")

                if choice == "3":
                    print_warning("Skipped")
                    raise typer.Exit(code=0)
                if choice == "1":
                    keep_structure = False
                if choice == "2":
                    keep_structure = True
                    namespace = Prompt.ask("Namespace", default=_get_default_namespace(source))

        config = get_config(ctx)
        result = add_skill(
            source,
            config=config,
            force=force,
            keep_structure=keep_structure,
            namespace=namespace,
            name=name,
            pre_fetched_dir=temp_dir,
            pre_fetched_commit_sha=commit_sha,
        )

        # Auto-reindex if skills were added
        if result.added:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=stderr_console,
                transient=True,
            ) as progress:
                progress.add_task("Updating index...", total=None)
                build_index(config=config, force=False)

        # JSON output for programmatic use
        if json_output:
            console.print_json(
                data={
                    "added": result.added,
                    "skipped": result.skipped,
                    "message": result.message,
                    "details": [d.model_dump() for d in getattr(result, "details", [])],
                }
            )
            if not result.added and result.skipped:
                raise typer.Exit(code=1)
            return

        # Human-readable output
        if result.added:
            for skill_id in result.added:
                console.print(f"[success]  ✓ Added '{skill_id}'[/success]")
        if result.skipped:
            for skill_id in result.skipped:
                detail_reason = next(
                    (
                        d.message
                        for d in getattr(result, "details", [])
                        if d.skill_id == skill_id and d.message
                    ),
                    None,
                )
                skip_reason = detail_reason or result.message or "skipped"
                console.print(f"[warning]  ⊘ Skipped '{skill_id}' ({skip_reason})[/warning]")

        # Summary
        if result.added and not result.skipped:
            print_success(f"Added {len(result.added)} skill(s)")
        elif result.added and result.skipped:
            print_warning(
                f"Added {len(result.added)}, skipped {len(result.skipped)} ({result.message})"
            )
        elif result.skipped:
            print_error(
                result.message or f"All {len(result.skipped)} skill(s) skipped",
            )
            raise typer.Exit(code=1)
        else:
            print_error(result.message)
            raise typer.Exit(code=1)
    finally:
        # Cleanup temp dir from pre-scan
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
