"""Add skills command."""

import shutil
from pathlib import Path

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from skillport.modules.skills.internal import (
    detect_skills,
    extract_zip,
    fetch_github_source_with_info,
    get_default_branch,
    is_github_shorthand,
    parse_github_shorthand,
    parse_github_url,
)
from skillport.modules.skills.public.add import add_skill

from ..context import get_config
from ..theme import (
    console,
    is_interactive,
    print_error,
    print_success,
    print_warning,
    stderr_console,
)


def _is_github_shorthand_source(source: str) -> bool:
    """Check if source is GitHub shorthand (owner/repo) and not a local path."""
    if not is_github_shorthand(source):
        return False
    # Local path takes priority over GitHub shorthand
    candidate = Path(source).expanduser().resolve()
    return not candidate.exists()


def _is_external_source(source: str) -> bool:
    """Check if source is a path, URL, or GitHub shorthand (not builtin)."""
    if source.startswith((".", "/", "~", "https://")):
        return True
    # Also consider .zip files as external sources
    if source.lower().endswith(".zip"):
        return True
    # GitHub shorthand (owner/repo) is external
    if _is_github_shorthand_source(source):
        return True
    return False


def _get_source_name(source: str) -> str:
    """Extract name from source path or URL."""
    if source.startswith("https://"):
        parsed = parse_github_url(source)
        return Path(parsed.normalized_path or parsed.repo).name
    # GitHub shorthand: owner/repo
    shorthand = parse_github_shorthand(source)
    if shorthand:
        return shorthand[1]  # repo name
    return Path(source.rstrip("/")).name


def _get_default_namespace(source: str) -> str:
    """Get default namespace for source (repo name for GitHub)."""
    if source.startswith("https://"):
        parsed = parse_github_url(source)
        return parsed.repo
    # GitHub shorthand: owner/repo
    shorthand = parse_github_shorthand(source)
    if shorthand:
        return shorthand[1]  # repo name
    return Path(source.rstrip("/")).name


class UserSkipped(Exception):
    """Raised when user chooses to skip."""

    pass


def _prompt_namespace_selection(
    skill_names: list[str],
    source: str,
    *,
    yes: bool,
    keep_structure: bool | None,
    namespace: str | None,
) -> tuple[bool | None, str | None]:
    """Prompt user for namespace selection if needed.

    Args:
        skill_names: List of detected skill names
        source: Original source string
        yes: Skip interactive prompts
        keep_structure: Current keep_structure setting
        namespace: Current namespace setting

    Returns:
        (keep_structure, namespace)

    Raises:
        UserSkipped: If user chooses to skip
    """
    # Already configured - no prompt needed
    if keep_structure is not None or namespace is not None:
        return keep_structure, namespace

    is_single = len(skill_names) == 1

    # Non-interactive mode: use sensible defaults
    if yes or not is_interactive():
        if is_single:
            return False, namespace
        else:
            return True, namespace or _get_default_namespace(source)

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
        raise UserSkipped()
    if choice == "1":
        return False, namespace
    if choice == "2":
        ns = Prompt.ask("Namespace", default=_get_default_namespace(source))
        return True, ns

    return keep_structure, namespace


def _display_add_result(result: "AddResult", json_output: bool) -> int:  # noqa: F821
    """Display add result and return exit code."""
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
        return 1 if (not result.added and result.skipped) else 0

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
        return 0
    elif result.added and result.skipped:
        print_warning(
            f"Added {len(result.added)}, skipped {len(result.skipped)} ({result.message})"
        )
        return 0
    elif result.skipped:
        print_error(result.message or f"All {len(result.skipped)} skill(s) skipped")
        return 1
    else:
        print_error(result.message)
        return 1


def _add_from_github_paths(
    source: str,
    paths: list[str],
    *,
    config: "Config",  # noqa: F821
    force: bool,
    yes: bool,
    keep_structure: bool | None,
    namespace: str | None,
) -> "AddResult":  # noqa: F821
    """Add skills from GitHub shorthand with multiple paths.

    Downloads the repository once and adds skills from each specified path.

    Raises:
        UserSkipped: If user chooses to skip
    """
    from skillport.modules.skills.public.types import AddResult, AddResultItem

    parsed = parse_github_shorthand(source)
    if not parsed:
        return AddResult(
            success=False,
            skill_id="",
            message=f"Invalid GitHub shorthand: {source}",
        )

    owner, repo = parsed
    base_url = f"https://github.com/{owner}/{repo}"

    temp_dir: Path | None = None
    try:
        # Phase 1: Fetch tarball
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=stderr_console,
            transient=True,
        ) as progress:
            progress.add_task(f"Fetching {base_url}...", total=None)
            fetch_result = fetch_github_source_with_info(base_url)
            temp_dir = fetch_result.extracted_path
            commit_sha = fetch_result.commit_sha

        default_branch = get_default_branch(owner, repo)

        # Phase 2: Collect paths and detect skills
        path_infos: list[tuple[str, str, Path]] = []
        all_skill_names: list[str] = []
        invalid_paths: list[tuple[str, str]] = []

        for path in paths:
            path = path.strip("/")
            path_url = f"https://github.com/{owner}/{repo}/tree/{default_branch}/{path}"
            path_dir = temp_dir / path

            if not path_dir.exists():
                invalid_paths.append((path, f"Path not found in repository: {path}"))
                continue

            path_infos.append((path, path_url, path_dir))
            skills = detect_skills(path_dir)
            all_skill_names.extend([s.name for s in skills])

        # Phase 3: Interactive prompt (raises UserSkipped if user skips)
        if path_infos and all_skill_names:
            keep_structure, namespace = _prompt_namespace_selection(
                all_skill_names,
                source,
                yes=yes,
                keep_structure=keep_structure,
                namespace=namespace,
            )

        # Phase 4: Add skills
        all_added: list[str] = []
        all_skipped: list[str] = []
        all_details: list[AddResultItem] = []
        messages: list[str] = []

        for path, msg in invalid_paths:
            all_skipped.append(path)
            all_details.append(AddResultItem(skill_id=path, success=False, message=msg))

        for _path, path_url, path_dir in path_infos:
            result = add_skill(
                path_url,
                config=config,
                force=force,
                keep_structure=keep_structure,
                namespace=namespace,
                pre_fetched_dir=path_dir,
                pre_fetched_commit_sha=commit_sha,
            )
            all_added.extend(result.added)
            all_skipped.extend(result.skipped)
            all_details.extend(result.details)
            if result.message and result.message not in messages:
                messages.append(result.message)

        return AddResult(
            success=len(all_added) > 0,
            skill_id=all_added[0] if all_added else "",
            message="; ".join(messages) if messages else "",
            added=all_added,
            skipped=all_skipped,
            details=all_details,
        )

    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


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
        help="Built-in name, local path, GitHub URL, or owner/repo",
        show_default=False,
    ),
    paths: list[str] = typer.Argument(
        None,
        help="Paths within the repository (GitHub shorthand only)",
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
    """Add skills from various sources.

    Examples:
        skillport add owner/repo                  # Add from repo root
        skillport add owner/repo skills           # Add from skills/ directory
        skillport add owner/repo skills examples  # Add from multiple paths
        skillport add https://github.com/o/r      # Full URL (existing)
    """
    temp_dir: Path | None = None
    commit_sha: str = ""
    paths = paths or []
    config = get_config(ctx)

    try:
        # Route 1: GitHub shorthand with paths (multi-path, single download)
        if _is_github_shorthand_source(source) and paths:
            result = _add_from_github_paths(
                source,
                paths,
                config=config,
                force=force,
                yes=yes,
                keep_structure=keep_structure,
                namespace=namespace,
            )
        else:
            # Route 2: Standard flow (URL, local, builtin, shorthand without paths)
            if _is_external_source(source) and keep_structure is None and namespace is None:
                skill_names, _source_name, temp_dir, commit_sha = _detect_skills_from_source(source)
                keep_structure, namespace = _prompt_namespace_selection(
                    skill_names,
                    source,
                    yes=yes,
                    keep_structure=keep_structure,
                    namespace=namespace,
                )

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

        # Shared: Display result
        exit_code = _display_add_result(result, json_output)
        if exit_code != 0:
            raise typer.Exit(code=exit_code)

    except UserSkipped:
        print_warning("Skipped")
        raise typer.Exit(code=0)

    finally:
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
