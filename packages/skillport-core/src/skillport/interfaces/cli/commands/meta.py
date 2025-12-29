"""Manage SKILL.md frontmatter metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import typer
import yaml

from skillport.shared.config import Config
from skillport.shared.exceptions import SkillNotFoundError
from skillport.shared.utils import parse_frontmatter, resolve_inside

from ..catalog import iter_skill_dirs
from ..context import get_config
from ..theme import console, print_error


@dataclass
class Target:
    skill_id: str
    path: Path


@dataclass
class MetaResult:
    skill_id: str
    path: str
    status: str
    action: str
    key: str
    old_value: Any
    new_value: Any
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "path": self.path,
            "status": self.status,
            "action": self.action,
            "key": self.key,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
        }


def _normalize_key(key: str) -> str:
    if key.startswith("metadata."):
        return key
    return f"metadata.{key}"


def _parse_args_key(
    args: list[str],
    *,
    all_skills: bool,
    json_output: bool,
    expect_value: bool,
) -> tuple[list[str], str, str | None]:
    if all_skills:
        expected = 2 if expect_value else 1
        if len(args) != expected:
            message = "Expected <key> and <value> when using --all"
            if not expect_value:
                message = "Expected <key> when using --all"
            _abort(message, json_output=json_output)
        if expect_value:
            return [], args[0], args[1]
        return [], args[0], None

    if expect_value:
        if len(args) < 3:
            _abort("Expected [SKILL_ID ...] <key> <value>", json_output=json_output)
        return args[:-2], args[-2], args[-1]

    if len(args) < 2:
        _abort("Expected [SKILL_ID ...] <key>", json_output=json_output)
    return args[:-1], args[-1], None


def _parse_args_show(args: list[str] | None, *, all_skills: bool, json_output: bool) -> list[str]:
    args = args or []
    if all_skills:
        if args:
            _abort("Do not pass skill IDs with --all", json_output=json_output)
        return []
    if not args:
        _abort("Expected one or more SKILL_ID values, or use --all", json_output=json_output)
    return args


def _abort(message: str, *, json_output: bool) -> None:
    print_error(message, code="INVALID_ARGS", json_output=json_output)
    raise typer.Exit(code=1)


def _resolve_targets(
    config: Config,
    *,
    skill_ids: list[str],
    all_skills: bool,
) -> tuple[list[Target], list[tuple[str, str]]]:
    targets: list[Target] = []
    errors: list[tuple[str, str]] = []

    if all_skills:
        for skill_id, skill_dir in iter_skill_dirs(config.skills_dir):
            targets.append(Target(skill_id=skill_id, path=skill_dir / "SKILL.md"))
        return targets, errors

    for skill_id in skill_ids:
        if not skill_id.strip():
            continue
        try:
            skill_dir = resolve_inside(config.skills_dir, skill_id)
        except PermissionError as exc:
            errors.append((skill_id, str(exc)))
            continue
        targets.append(Target(skill_id=skill_id, path=skill_dir / "SKILL.md"))
    return targets, errors


def _load_frontmatter(skill_md: Path) -> tuple[dict[str, Any], str]:
    if not skill_md.exists():
        raise SkillNotFoundError(str(skill_md))
    meta, body = parse_frontmatter(skill_md)
    if not isinstance(meta, dict):
        meta = {}
    return meta, body


class _FrontmatterStr(str):
    pass


class _FrontmatterDumper(yaml.SafeDumper):
    pass


def _represent_frontmatter_str(dumper: yaml.Dumper, data: _FrontmatterStr) -> yaml.ScalarNode:
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')


_FrontmatterDumper.add_representer(_FrontmatterStr, _represent_frontmatter_str)


def _should_quote_string(value: str) -> bool:
    if "\n" in value or "\r" in value:
        return True
    if value == "" or value.strip() != value:
        return True
    try:
        loaded = yaml.safe_load(value)
    except yaml.YAMLError:
        return True
    return not isinstance(loaded, str) or loaded != value


def _prepare_frontmatter_for_dump(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _prepare_frontmatter_for_dump(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_prepare_frontmatter_for_dump(v) for v in value]
    if isinstance(value, tuple):
        return [_prepare_frontmatter_for_dump(v) for v in value]
    if isinstance(value, str) and _should_quote_string(value):
        return _FrontmatterStr(value)
    return value


def _write_frontmatter(skill_md: Path, meta: dict[str, Any], body: str) -> None:
    prepared = _prepare_frontmatter_for_dump(meta)
    meta_text = yaml.dump(
        prepared,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1_000_000,
        Dumper=_FrontmatterDumper,
    ).strip()
    cleaned_body = body.lstrip("\n")
    content = f"---\n{meta_text}\n---\n{cleaned_body}"
    skill_md.write_text(content, encoding="utf-8")


def _resolve_metadata_path(
    meta: dict[str, Any], normalized_key: str
) -> tuple[dict[str, Any], str]:
    parts = normalized_key.split(".")
    if parts[0] != "metadata" or len(parts) < 2:
        raise ValueError("key must target metadata.*")

    metadata = meta.get("metadata")
    if metadata is None:
        metadata = {}
        meta["metadata"] = metadata
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter.metadata must be a mapping")

    current: dict[str, Any] = metadata
    for part in parts[1:-1]:
        if not part:
            raise ValueError("key contains empty path segment")
        if part not in current:
            current[part] = {}
        elif not isinstance(current[part], dict):
            raise ValueError(f"metadata.{part} must be a mapping")
        current = current[part]

    leaf = parts[-1]
    if not leaf:
        raise ValueError("key contains empty path segment")
    return current, leaf


def _get_metadata_value(meta: dict[str, Any], normalized_key: str) -> tuple[bool, Any]:
    parts = normalized_key.split(".")
    if parts[0] != "metadata" or len(parts) < 2:
        raise ValueError("key must target metadata.*")

    metadata = meta.get("metadata")
    if metadata is None:
        return False, None
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter.metadata must be a mapping")

    current: dict[str, Any] = metadata
    for part in parts[1:-1]:
        if not part:
            raise ValueError("key contains empty path segment")
        if part not in current:
            return False, None
        if not isinstance(current[part], dict):
            raise ValueError(f"metadata.{part} must be a mapping")
        current = current[part]

    leaf = parts[-1]
    if not leaf:
        raise ValueError("key contains empty path segment")
    if leaf not in current:
        return False, None
    return True, current[leaf]


def _set_metadata_value(meta: dict[str, Any], normalized_key: str, value: str) -> Any:
    parent, leaf = _resolve_metadata_path(meta, normalized_key)
    old_value = parent.get(leaf)
    parent[leaf] = value
    return old_value


def _delete_metadata_value(meta: dict[str, Any], normalized_key: str) -> tuple[bool, Any]:
    parent, leaf = _resolve_metadata_path(meta, normalized_key)
    if leaf not in parent:
        return False, None
    old_value = parent.pop(leaf)
    return True, old_value


def _bump_semver(value: str, *, part: str) -> str:
    prefix = ""
    raw = value
    if raw.startswith("v"):
        prefix = "v"
        raw = raw[1:]

    parts = raw.split(".")
    if len(parts) not in (2, 3) or any(not p.isdigit() for p in parts):
        raise ValueError("value is not a SemVer-like string")

    nums = [int(p) for p in parts]
    if part == "major":
        if len(nums) == 2:
            nums = [nums[0] + 1, 0]
        else:
            nums = [nums[0] + 1, 0, 0]
    elif part == "minor":
        if len(nums) == 2:
            nums = [nums[0], nums[1] + 1]
        else:
            nums = [nums[0], nums[1] + 1, 0]
    elif part == "patch":
        if len(nums) == 2:
            nums = [nums[0], nums[1], 1]
        else:
            nums = [nums[0], nums[1], nums[2] + 1]
    else:
        raise ValueError("unknown bump type")

    return prefix + ".".join(str(n) for n in nums)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, set):
        return [_json_safe(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _emit_mutation_results(
    *,
    results: list[MetaResult],
    action: str,
    key: str,
    dry_run: bool,
    json_output: bool,
    summary: dict[str, int],
) -> None:
    if json_output:
        console.print_json(
            data=_json_safe(
                {
                    "command": f"meta {action}",
                    "key": key,
                    "dry_run": dry_run,
                    "summary": summary,
                    "results": [result.to_dict() for result in results],
                }
            )
        )
        return

    for result in results:
        skill_id = result.skill_id
        status = result.status
        if status in {"updated", "would_update"}:
            is_dry = status == "would_update"
            if action == "set":
                prefix = "would set" if is_dry else "set"
                console.print(
                    f"{skill_id}: {prefix} {key}: "
                    f"\"{result.old_value}\" -> \"{result.new_value}\""
                )
            elif action == "bump":
                prefix = "would bump" if is_dry else "bumped"
                console.print(
                    f"{skill_id}: {prefix} {key}: "
                    f"\"{result.old_value}\" -> \"{result.new_value}\""
                )
            elif action == "unset":
                prefix = "would unset" if is_dry else "unset"
                console.print(f"{skill_id}: {prefix} {key}")
        elif status == "skipped":
            console.print(f"{skill_id}: skipped ({result.reason})")
        else:
            console.print(f"{skill_id}: error ({result.reason})")


def _build_summary(
    *, total: int, updated: int, skipped: int, errors: int
) -> dict[str, int]:
    return {
        "total": total,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


def _emit_show_results(
    *, results: list[dict[str, Any]], json_output: bool, errors: int
) -> None:
    if json_output:
        console.print_json(
            data=_json_safe(
                {
                    "command": "meta show",
                    "summary": {"total": len(results), "errors": errors},
                    "results": results,
                }
            )
        )
        return

    for result in results:
        skill_id = result["skill_id"]
        if "error" in result:
            console.print(f"{skill_id}: error ({result['error']})")
            continue
        console.print(f"[skill.id]{skill_id}[/skill.id]")
        payload = {"metadata": result["metadata"]}
        yaml_text = yaml.safe_dump(
            payload,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            width=1_000_000,
        ).rstrip()
        console.print(yaml_text)
        console.print()


meta_app = typer.Typer(
    name="meta",
    help="Manage SKILL.md frontmatter metadata.",
    no_args_is_help=True,
)


@meta_app.command("set")
def meta_set(
    ctx: typer.Context,
    args: list[str] = typer.Argument(
        ...,
        help="Targets followed by <key> <value> (e.g., skill-a skill-b author gota)",
    ),
    all_skills: bool = typer.Option(False, "--all", help="Target all skills"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without writing files"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Set a metadata key to a string value."""
    if all_skills and args and len(args) > 2:
        _abort("Do not pass skill IDs with --all", json_output=json_output)

    skill_ids, key, value = _parse_args_key(
        args, all_skills=all_skills, json_output=json_output, expect_value=True
    )
    assert value is not None
    normalized_key = _normalize_key(key)

    results: list[MetaResult] = []
    updated = skipped = errors = 0
    action = "set"

    targets, target_errors = _resolve_targets(
        get_config(ctx), skill_ids=skill_ids, all_skills=all_skills
    )
    for skill_id, reason in target_errors:
        errors += 1
        results.append(
            MetaResult(
                skill_id=skill_id,
                path="",
                status="error",
                action=action,
                key=normalized_key,
                old_value=None,
                new_value=value,
                reason=reason,
            )
        )

    for target in targets:
        try:
            meta, body = _load_frontmatter(target.path)
            old_value = _set_metadata_value(meta, normalized_key, value)
            status = "would_update" if dry_run else "updated"
            if not dry_run:
                _write_frontmatter(target.path, meta, body)
            updated += 1
            results.append(
                MetaResult(
                    skill_id=target.skill_id,
                    path=str(target.path.parent.resolve()),
                    status=status,
                    action=action,
                    key=normalized_key,
                    old_value=old_value,
                    new_value=value,
                    reason="",
                )
            )
        except (SkillNotFoundError, PermissionError, ValueError) as exc:
            errors += 1
            results.append(
                MetaResult(
                    skill_id=target.skill_id,
                    path="",
                    status="error",
                    action=action,
                    key=normalized_key,
                    old_value=None,
                    new_value=value,
                    reason=str(exc),
                )
            )

    _emit_mutation_results(
        results=results,
        action=action,
        key=normalized_key,
        dry_run=dry_run,
        json_output=json_output,
        summary=_build_summary(
            total=len(results),
            updated=updated,
            skipped=skipped,
            errors=errors,
        ),
    )

    if errors > 0 or len(results) == 0:
        raise typer.Exit(code=1)


@meta_app.command("bump")
def meta_bump(
    ctx: typer.Context,
    args: list[str] = typer.Argument(
        ...,
        help="Targets followed by <key> (e.g., skill-a skill-b version --patch)",
    ),
    major: bool = typer.Option(False, "--major", help="Bump major version"),
    minor: bool = typer.Option(False, "--minor", help="Bump minor version"),
    patch: bool = typer.Option(False, "--patch", help="Bump patch version"),
    all_skills: bool = typer.Option(False, "--all", help="Target all skills"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without writing files"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Bump a SemVer-like metadata value."""
    if sum([major, minor, patch]) != 1:
        _abort("Select exactly one of --major/--minor/--patch", json_output=json_output)
    if all_skills and args and len(args) > 1:
        _abort("Do not pass skill IDs with --all", json_output=json_output)

    skill_ids, key, _value = _parse_args_key(
        args, all_skills=all_skills, json_output=json_output, expect_value=False
    )
    normalized_key = _normalize_key(key)

    bump_part = "major" if major else "minor" if minor else "patch"
    results: list[MetaResult] = []
    updated = skipped = errors = 0
    action = "bump"

    targets, target_errors = _resolve_targets(
        get_config(ctx), skill_ids=skill_ids, all_skills=all_skills
    )
    for skill_id, reason in target_errors:
        errors += 1
        results.append(
            MetaResult(
                skill_id=skill_id,
                path="",
                status="error",
                action=action,
                key=normalized_key,
                old_value=None,
                new_value=None,
                reason=reason,
            )
        )

    for target in targets:
        try:
            meta, body = _load_frontmatter(target.path)
            found, current_value = _get_metadata_value(meta, normalized_key)
            if not found or not isinstance(current_value, str):
                skipped += 1
                results.append(
                    MetaResult(
                        skill_id=target.skill_id,
                        path=str(target.path.parent.resolve()),
                        status="skipped",
                        action=action,
                        key=normalized_key,
                        old_value=current_value if found else None,
                        new_value=None,
                        reason="missing or non-string value",
                    )
                )
                continue

            new_value = _bump_semver(current_value, part=bump_part)
            status = "would_update" if dry_run else "updated"
            _set_metadata_value(meta, normalized_key, new_value)
            if not dry_run:
                _write_frontmatter(target.path, meta, body)
            updated += 1
            results.append(
                MetaResult(
                    skill_id=target.skill_id,
                    path=str(target.path.parent.resolve()),
                    status=status,
                    action=action,
                    key=normalized_key,
                    old_value=current_value,
                    new_value=new_value,
                    reason="",
                )
            )
        except (SkillNotFoundError, PermissionError, ValueError) as exc:
            errors += 1
            results.append(
                MetaResult(
                    skill_id=target.skill_id,
                    path="",
                    status="error",
                    action=action,
                    key=normalized_key,
                    old_value=None,
                    new_value=None,
                    reason=str(exc),
                )
            )

    _emit_mutation_results(
        results=results,
        action=action,
        key=normalized_key,
        dry_run=dry_run,
        json_output=json_output,
        summary=_build_summary(
            total=len(results),
            updated=updated,
            skipped=skipped,
            errors=errors,
        ),
    )

    if errors > 0 or len(results) == 0:
        raise typer.Exit(code=1)


@meta_app.command("unset")
def meta_unset(
    ctx: typer.Context,
    args: list[str] = typer.Argument(
        ...,
        help="Targets followed by <key> (e.g., skill-a skill-b author)",
    ),
    all_skills: bool = typer.Option(False, "--all", help="Target all skills"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without writing files"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Remove a metadata key."""
    if all_skills and args and len(args) > 1:
        _abort("Do not pass skill IDs with --all", json_output=json_output)

    skill_ids, key, _value = _parse_args_key(
        args, all_skills=all_skills, json_output=json_output, expect_value=False
    )
    normalized_key = _normalize_key(key)

    results: list[MetaResult] = []
    updated = skipped = errors = 0
    action = "unset"

    targets, target_errors = _resolve_targets(
        get_config(ctx), skill_ids=skill_ids, all_skills=all_skills
    )
    for skill_id, reason in target_errors:
        errors += 1
        results.append(
            MetaResult(
                skill_id=skill_id,
                path="",
                status="error",
                action=action,
                key=normalized_key,
                old_value=None,
                new_value=None,
                reason=reason,
            )
        )

    for target in targets:
        try:
            meta, body = _load_frontmatter(target.path)
            found, old_value = _delete_metadata_value(meta, normalized_key)
            if not found:
                skipped += 1
                results.append(
                    MetaResult(
                        skill_id=target.skill_id,
                        path=str(target.path.parent.resolve()),
                        status="skipped",
                        action=action,
                        key=normalized_key,
                        old_value=None,
                        new_value=None,
                        reason="key not found",
                    )
                )
                continue
            status = "would_update" if dry_run else "updated"
            if not dry_run:
                _write_frontmatter(target.path, meta, body)
            updated += 1
            results.append(
                MetaResult(
                    skill_id=target.skill_id,
                    path=str(target.path.parent.resolve()),
                    status=status,
                    action=action,
                    key=normalized_key,
                    old_value=old_value,
                    new_value=None,
                    reason="",
                )
            )
        except (SkillNotFoundError, PermissionError, ValueError) as exc:
            errors += 1
            results.append(
                MetaResult(
                    skill_id=target.skill_id,
                    path="",
                    status="error",
                    action=action,
                    key=normalized_key,
                    old_value=None,
                    new_value=None,
                    reason=str(exc),
                )
            )

    _emit_mutation_results(
        results=results,
        action=action,
        key=normalized_key,
        dry_run=dry_run,
        json_output=json_output,
        summary=_build_summary(
            total=len(results),
            updated=updated,
            skipped=skipped,
            errors=errors,
        ),
    )

    if errors > 0 or len(results) == 0:
        raise typer.Exit(code=1)


@meta_app.command("show")
def meta_show(
    ctx: typer.Context,
    args: list[str] | None = typer.Argument(
        None,
        help="Skill IDs (e.g., skill-a skill-b) or use --all",
    ),
    all_skills: bool = typer.Option(False, "--all", help="Target all skills"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show metadata for skill(s)."""
    skill_ids = _parse_args_show(args, all_skills=all_skills, json_output=json_output)

    results: list[dict[str, Any]] = []
    errors = 0
    targets, target_errors = _resolve_targets(
        get_config(ctx), skill_ids=skill_ids, all_skills=all_skills
    )
    for skill_id, reason in target_errors:
        errors += 1
        results.append(
            {
                "skill_id": skill_id,
                "path": "",
                "metadata": {},
                "error": reason,
            }
        )

    for target in targets:
        try:
            meta, _body = _load_frontmatter(target.path)
            metadata = meta.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            results.append(
                {
                    "skill_id": target.skill_id,
                    "path": str(target.path.parent.resolve()),
                    "metadata": metadata,
                }
            )
        except (SkillNotFoundError, PermissionError, ValueError) as exc:
            errors += 1
            results.append(
                {
                    "skill_id": target.skill_id,
                    "path": "",
                    "metadata": {},
                    "error": str(exc),
                }
            )

    _emit_show_results(results=results, json_output=json_output, errors=errors)

    if errors > 0 or len(results) == 0:
        raise typer.Exit(code=1)
