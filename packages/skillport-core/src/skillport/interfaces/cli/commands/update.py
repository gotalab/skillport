"""Update skills command."""

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from skillport.modules.skills.internal import get_all_origins, get_untracked_skill_ids
from skillport.modules.skills.public.update import (
    check_update_available,
    detect_local_modification,
    update_all_skills,
    update_skill,
)

from ..context import get_config
from ..theme import console, print_error, print_success, print_warning, stderr_console


def update(
    ctx: typer.Context,
    skill_id: str = typer.Argument(
        None,
        help="Skill ID to update (omit for --all or --check)",
        show_default=False,
    ),
    all_skills: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Update all updatable skills",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite local modifications",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be updated without making changes",
    ),
    check: bool = typer.Option(
        False,
        "--check",
        "-c",
        help="Check for available updates without updating",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON (for scripting/AI agents)",
    ),
):
    """Update skills from their original sources.

    By default (no arguments), shows available updates like --check.
    Use --all to update all skills, or specify a skill ID to update one.
    """
    config = get_config(ctx)

    # Detect "default invocation" (no flags/ID) to apply spec default behavior
    default_invocation = skill_id is None and not all_skills and not check

    # Default behavior: check mode
    if default_invocation:
        check = True

    # Check mode: show available updates
    if check:
        result = _show_available_updates(
            config,
            json_output,
            interactive=default_invocation and not json_output,
        )

        # In the default (flagなし) case, offer to run --all when updates exist
        if (
            default_invocation
            and not json_output
            and result["updates_available"]
            and console.is_interactive
        ):
            if typer.confirm("\nUpdate all listed skills now?", default=False):
                candidate_ids = [item["skill_id"] for item in result["updates_available"]]
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=stderr_console,
                    transient=True,
                ) as progress:
                    if not dry_run:
                        progress.add_task("Updating selected skills...", total=None)
                    bulk_result = update_all_skills(
                        config=config,
                        force=force,
                        dry_run=dry_run,
                        skill_ids=candidate_ids,
                    )

                _render_update_all_result(
                    bulk_result,
                    config=config,
                    dry_run=dry_run,
                )
            else:
                console.print("[dim]No changes made.[/dim]")
        return

    # Update single skill
    if skill_id and not all_skills:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=stderr_console,
            transient=True,
        ) as progress:
            if not dry_run:
                progress.add_task(f"Updating {skill_id}...", total=None)

            result = update_skill(
                skill_id,
                config=config,
                force=force,
                dry_run=dry_run,
            )

        # JSON output
        if json_output:
            console.print_json(
                data={
                    "updated": result.updated,
                    "skipped": result.skipped,
                    "errors": result.errors,
                    "message": result.message,
                    "local_modified": result.local_modified,
                    "details": [d.model_dump() for d in result.details],
                }
            )
            if not result.success:
                raise typer.Exit(code=1)
            return

        # Human-readable output
        if result.local_modified and not force:
            print_warning(f"Local modifications detected in '{skill_id}'")
            console.print("  Use [bold]--force[/bold] to overwrite local changes")
            raise typer.Exit(code=1)

        if result.updated:
            for detail in result.details:
                if detail.from_commit and detail.to_commit:
                    console.print(
                        f"[success]  + Updated '{skill_id}' ({detail.from_commit} -> {detail.to_commit})[/success]"
                    )
                else:
                    console.print(f"[success]  + Updated '{skill_id}'[/success]")
            print_success(result.message)

        elif result.skipped:
            console.print(f"[dim]  - '{skill_id}' is already up to date[/dim]")
        else:
            print_error(result.message)
            raise typer.Exit(code=1)

        return

    # Update all skills
    if all_skills:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=stderr_console,
            transient=True,
        ) as progress:
            if not dry_run:
                progress.add_task("Updating all skills...", total=None)

            result = update_all_skills(
                config=config,
                force=force,
                dry_run=dry_run,
            )

        # JSON output
        if json_output:
            console.print_json(
                data={
                    "updated": result.updated,
                    "skipped": result.skipped,
                    "errors": result.errors,
                    "message": result.message,
                    "details": [d.model_dump() for d in result.details],
                }
            )
            if not result.success:
                raise typer.Exit(code=1)
            return

        _render_update_all_result(result, config=config, dry_run=dry_run)
        return

    # No skill specified and not --all
    print_error("Specify a skill ID or use --all to update all skills")
    raise typer.Exit(code=1)


def _show_available_updates(config, json_output: bool, interactive: bool = False):
    """Show available updates without making changes."""
    origins = get_all_origins(config=config)

    updates_available = []
    up_to_date = []
    not_updatable = []

    for skill_id, origin in origins.items():
        kind = origin.get("kind", "")

        if kind == "builtin":
            not_updatable.append({"skill_id": skill_id, "reason": "Built-in skill"})
            continue

        has_local_mods = detect_local_modification(skill_id, config=config)
        result = check_update_available(skill_id, config=config)

        if result.get("available"):
            updates_available.append(
                {
                    "skill_id": skill_id,
                    "kind": kind,
                    "local_modified": has_local_mods,
                    "new_commit": result.get("new_commit", ""),
                }
            )
            continue

        reason = result.get("reason", "Already up to date")
        # classify non-updatable reasons
        if any(
            term in reason.lower()
            for term in [
                "not found",
                "missing",
                "unreadable",
                "unknown origin",
                "not checkable",
                "too_many_files",
                "too_large",
            ]
        ):
            not_updatable.append({"skill_id": skill_id, "reason": reason})
        else:
            up_to_date.append({"skill_id": skill_id, "kind": kind, "reason": reason})

    # Get untracked skills (installed but not in origins.json)
    untracked = get_untracked_skill_ids(config=config)

    # JSON output
    data = {
        "updates_available": updates_available,
        "up_to_date": up_to_date,
        "not_updatable": not_updatable,
        "untracked": untracked,
    }

    if json_output:
        console.print_json(data=data)
        return data

    # Human-readable output
    has_any_content = updates_available or up_to_date or not_updatable or untracked

    if not has_any_content:
        console.print("\n[dim]All skills are up to date.[/dim]")
        return data

    if updates_available:
        console.print("\n[bold]Updates available:[/bold]")
        for item in updates_available:
            mod_marker = " [warning](local changes)[/warning]" if item.get("local_modified") else ""
            commit = ""
            if item.get("new_commit"):
                commit = f" @ {item['new_commit']}"
            console.print(
                f"  [skill.id]{item['skill_id']}[/skill.id] ({item['kind']}{commit}){mod_marker}"
            )

        console.print(
            "\n[dim]Run 'skillport update --all' to update all, or 'skillport update <skill-id>' for one.[/dim]"
        )

    # Secondary information: counts only (less prominent)
    if up_to_date:
        console.print(f"\n[dim]Up to date: {len(up_to_date)} skill(s)[/dim]")

    if not_updatable:
        console.print(f"[dim]Not updatable: {len(not_updatable)} skill(s)[/dim]")

    if untracked:
        console.print(f"[dim]Untracked: {len(untracked)} skill(s)[/dim]")
        console.print("[dim]  → Use 'skillport add <source>' to track[/dim]")

    return data


def _render_update_all_result(result, *, config, dry_run: bool):
    """Render human-readable output for bulk update results."""
    if result.updated:
        for detail in result.details:
            if detail.from_commit and detail.to_commit:
                console.print(
                    f"[success]  + Updated '{detail.skill_id}' ({detail.from_commit} -> {detail.to_commit})[/success]"
                )
            else:
                console.print(f"[success]  + Updated '{detail.skill_id}'[/success]")

    if result.skipped:
        console.print(f"[dim]  - {len(result.skipped)} skill(s) already up to date[/dim]")

    if result.errors:
        print_error("Errors encountered during update:")
        for err in result.errors:
            console.print(f"  - {err}")

    if result.updated:
        print_success(result.message)
    elif result.skipped:
        console.print("[dim]All skills are up to date[/dim]")
    else:
        if result.success:
            console.print("[dim]No skills to update[/dim]")
        else:
            print_error(result.message)

    if not result.success:
        raise typer.Exit(code=1)
