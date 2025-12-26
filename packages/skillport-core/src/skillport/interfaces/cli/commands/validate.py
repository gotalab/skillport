"""Validate skill definitions command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel

from skillport.modules.skills.internal.validation import validate_skill_record
from skillport.shared.utils import parse_frontmatter, resolve_inside

from ..context import get_config
from ..theme import console, print_error, print_success, print_warning

# Directories to exclude from scanning (matching tracking.py)
SCAN_EXCLUDE_NAMES = {"__pycache__", "node_modules"}


def _scan_skills_from_path(target_path: Path) -> list[dict]:
    """Scan skills from a path (single skill dir or parent dir with multiple skills).

    Uses rglob to recursively find all SKILL.md files, matching the behavior
    of the indexing logic in tracking.py.
    """
    skills = []

    if not target_path.exists():
        raise typer.BadParameter(f"Path does not exist: {target_path}")

    # Check if target is a single skill directory (has SKILL.md)
    skill_md = target_path / "SKILL.md"
    if skill_md.exists():
        skills.append(_load_skill_from_path(target_path))
    else:
        # Recursively scan for all SKILL.md files (matching tracking.py behavior)
        for skill_md_path in sorted(target_path.rglob("SKILL.md")):
            skill_dir = skill_md_path.parent
            rel_parts = skill_dir.relative_to(target_path).parts

            # Skip hidden directories and excluded directories
            if any(part.startswith(".") or part in SCAN_EXCLUDE_NAMES for part in rel_parts):
                continue

            skills.append(_load_skill_from_path(skill_dir))

    return skills


def _load_skill_from_path(skill_dir: Path) -> dict:
    """Load skill data from a directory path."""
    skill_md = skill_dir / "SKILL.md"
    meta, body = parse_frontmatter(skill_md)

    # Count lines
    lines = len(skill_md.read_text(encoding="utf-8").splitlines())

    return {
        "id": meta.get("name", skill_dir.name),
        "name": meta.get("name", ""),
        "description": meta.get("description", ""),
        "path": str(skill_dir.resolve()),
        "lines": lines,
        "_meta": meta,  # Keep raw meta for key existence checks
    }


def _is_path_target(target: str) -> bool:
    """Check if target looks like a path rather than a skill_id."""
    # Explicit path prefixes
    if target.startswith(("./", "../", "/", "~")):
        return True
    # Contains path separator
    if "/" in target or "\\" in target:
        path = Path(target).expanduser()
        return path.exists()
    # Check if it's an existing path (e.g., ".agent" or "skills")
    path = Path(target).expanduser()
    return path.exists() and path.is_dir()


def validate(
    ctx: typer.Context,
    target: str | None = typer.Argument(
        None,
        help="Skill ID, path to skill directory, or path to skills parent directory",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON (for scripting/AI agents)",
    ),
):
    """Validate skill definitions against Agent Skills specification.

    Validates frontmatter schema, required fields, and field constraints.
    """
    config = get_config(ctx)
    skills: list[dict] = []

    if target is None:
        # No target: validate all skills from filesystem
        skills = _scan_skills_from_path(config.skills_dir)
    elif _is_path_target(target):
        # Path target: scan from filesystem
        target_path = Path(target).expanduser().resolve()
        try:
            skills = _scan_skills_from_path(target_path)
        except typer.BadParameter as e:
            if json_output:
                console.print_json(data={"valid": False, "message": str(e), "skills": []})
            else:
                print_error(str(e))
            raise typer.Exit(code=1)
    else:
        # Skill ID: resolve within skills_dir
        try:
            skill_dir = resolve_inside(config.skills_dir, target)
        except PermissionError:
            skill_dir = None

        if skill_dir and (skill_dir / "SKILL.md").exists():
            skills = [_load_skill_from_path(skill_dir)]
        else:
            skills = []

    if not skills:
        msg = "No skills found" + (f" matching '{target}'" if target else "")
        if json_output:
            console.print_json(data={"valid": False, "message": msg, "skills": []})
        else:
            print_warning(f"{msg} to validate.")
        raise typer.Exit(code=1)

    # Collect all issues
    all_results: list[dict] = []
    total_fatal = 0
    total_warning = 0

    for skill in skills:
        # Pass meta for key existence checks if available (path-based loading)
        meta = skill.pop("_meta", None)
        issues = validate_skill_record(skill, meta=meta)
        skill_result = {
            "id": skill.get("id", skill.get("name")),
            "valid": all(issue.severity != "fatal" for issue in issues),
            "issues": [
                {"severity": i.severity, "field": i.field, "message": i.message} for i in issues
            ],
        }
        all_results.append(skill_result)

        for issue in issues:
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
        print_success(f"✓ All {len(skills)} skill(s) pass validation")
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


def lint_deprecated(
    ctx: typer.Context,
    target: str | None = typer.Argument(None),
    json_output: bool = typer.Option(False, "--json"),
):
    """[Deprecated] Use 'validate' instead."""
    print_warning("'lint' is deprecated. Use 'validate' instead.")
    # Directly call validate with same context
    validate(ctx=ctx, target=target, json_output=json_output)
