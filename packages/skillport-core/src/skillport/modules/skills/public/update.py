"""Update skills from their original sources.

This module uses function-based dispatch to handle different update sources
(local, GitHub, zip) with shared helper functions for common operations.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skillport.modules.skills.internal import (
    compute_content_hash,
    compute_content_hash_with_reason,
    detect_skills,
    extract_zip,
    fetch_github_source_with_info,
    get_all_origins,
    get_origin,
    get_remote_tree_hash,
    parse_github_url,
    rename_single_skill_dir,
    update_origin,
)
from skillport.shared.auth import resolve_github_token
from skillport.shared.config import Config

from .types import Origin, UpdateResult, UpdateResultItem

# =============================================================================
# Public API
# =============================================================================


def detect_local_modification(skill_id: str, *, config: Config) -> bool:
    """Check if a skill has local modifications.

    Compares the current SKILL.md content hash against the stored hash.
    Returns False if origin info is missing or doesn't have content_hash.
    """
    origin = get_origin(skill_id, config=config)
    if not origin:
        return False

    stored_hash = origin.get("content_hash")
    if not stored_hash:
        return False

    skill_path = config.skills_dir / skill_id
    current_hash = compute_content_hash(skill_path)

    return stored_hash != current_hash


def check_update_available(skill_id: str, *, config: Config) -> dict[str, Any]:
    """Check if an update is available for a skill."""
    origin = get_origin(skill_id, config=config)

    if not origin:
        return {
            "available": False,
            "reason": "No origin info (cannot update)",
            "origin": None,
            "new_commit": "",
        }

    kind = origin.get("kind", "")

    if kind == "builtin":
        return {
            "available": False,
            "reason": "Built-in skill cannot be updated",
            "origin": origin,
            "new_commit": "",
        }

    source_hash, source_reason = _compute_source_hash(origin, skill_id, config=config)
    if source_reason:
        return {"available": False, "reason": source_reason, "origin": origin, "new_commit": ""}

    installed_hash, installed_reason = compute_content_hash_with_reason(
        config.skills_dir / skill_id
    )
    if installed_reason:
        return {
            "available": False,
            "reason": f"Installed skill unreadable: {installed_reason}",
            "origin": origin,
            "new_commit": "",
        }

    if source_hash == installed_hash:
        return {
            "available": False,
            "reason": "Already at latest content",
            "origin": origin,
            "new_commit": "",
        }

    return {
        "available": True,
        "reason": "Remote content differs" if kind == "github" else "Local source changed",
        "origin": origin,
        "new_commit": source_hash.split(":", 1)[-1][:7]
        if source_hash.startswith("sha256:")
        else source_hash[:7],
    }


def update_skill(
    skill_id: str,
    *,
    config: Config,
    force: bool = False,
    dry_run: bool = False,
) -> UpdateResult:
    """Update a single skill from its original source."""
    skill_path = config.skills_dir / skill_id
    if not skill_path.exists():
        return UpdateResult(
            success=False, skill_id=skill_id, message=f"Skill '{skill_id}' not found"
        )

    origin = get_origin(skill_id, config=config)
    if not origin:
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message=f"Skill '{skill_id}' has no origin info (cannot update)",
        )

    kind = origin.get("kind", "")

    if kind == "builtin":
        return UpdateResult(
            success=False, skill_id=skill_id, message="Built-in skill cannot be updated"
        )

    ctx = UpdateContext(
        skill_id=skill_id, origin=origin, config=config, force=force, dry_run=dry_run
    )

    handler = _UPDATE_HANDLERS.get(kind)
    if handler is None:
        return UpdateResult(
            success=False, skill_id=skill_id, message=f"Unknown origin kind: {kind}"
        )

    return handler(ctx)


def update_all_skills(
    *,
    config: Config,
    force: bool = False,
    dry_run: bool = False,
    skill_ids: list[str] | None = None,
) -> UpdateResult:
    """Update all updatable skills (optionally limited to skill_ids)."""
    origins = get_all_origins(config=config)

    if skill_ids is not None:
        origins = {k: v for k, v in origins.items() if k in skill_ids}

    if not origins:
        return UpdateResult(success=True, skill_id="", message="No skills to update")

    updated: list[str] = []
    skipped: list[str] = []
    details: list[UpdateResultItem] = []
    errors: list[str] = []

    for skill_id, origin in origins.items():
        if origin.get("kind") == "builtin":
            continue

        result = update_skill(skill_id, config=config, force=force, dry_run=dry_run)

        if result.updated:
            updated.extend(result.updated)
        if result.skipped:
            skipped.extend(result.skipped)
        if result.details:
            details.extend(result.details)
        if not result.success and not result.skipped:
            errors.append(f"{skill_id}: {result.message}")
            details.append(
                UpdateResultItem(skill_id=skill_id, success=False, message=result.message)
            )

    parts = []
    if updated:
        parts.append(f"Updated {len(updated)} skill(s)")
    if skipped:
        parts.append(f"Skipped {len(skipped)} (up to date)")
    if errors:
        parts.append(f"{len(errors)} error(s)")

    return UpdateResult(
        success=len(errors) == 0,
        skill_id=",".join(updated) if updated else "",
        message=", ".join(parts) if parts else "No skills to update",
        updated=updated,
        skipped=skipped,
        details=details,
        errors=errors,
    )


# =============================================================================
# Update Context
# =============================================================================


@dataclass
class UpdateContext:
    """Context for update operations."""

    skill_id: str
    origin: Origin
    config: Config
    force: bool
    dry_run: bool

    @property
    def stored_hash(self) -> str:
        return self.origin.get("content_hash", "")

    @property
    def dest_path(self) -> Path:
        return self.config.skills_dir / self.skill_id


# =============================================================================
# Common Helpers
# =============================================================================


def _error(ctx: UpdateContext, message: str) -> UpdateResult:
    """Create an error result."""
    return UpdateResult(success=False, skill_id=ctx.skill_id, message=message)


def _already_up_to_date(ctx: UpdateContext) -> UpdateResult:
    """Create an 'already up to date' result."""
    return UpdateResult(
        success=True, skill_id=ctx.skill_id, message="Already up to date", skipped=[ctx.skill_id]
    )


def _local_modification_error(ctx: UpdateContext) -> UpdateResult:
    """Create a local modification error result."""
    return UpdateResult(
        success=False,
        skill_id=ctx.skill_id,
        message="Local modifications detected. Use --force to overwrite",
        local_modified=True,
    )


def _sync_stored_hash_if_needed(ctx: UpdateContext, current_hash: str) -> None:
    """Sync stored hash if outdated."""
    if ctx.stored_hash != current_hash:
        update_origin(ctx.skill_id, {"content_hash": current_hash}, config=ctx.config)


def _has_local_modifications(ctx: UpdateContext, current_hash: str) -> bool:
    """Check if local modifications exist."""
    return bool(ctx.stored_hash and ctx.stored_hash != current_hash)


def _check_update_needed(
    ctx: UpdateContext, source_hash: str, current_hash: str
) -> UpdateResult | None:
    """Check if update is needed.

    Returns None if update should proceed, otherwise returns early-exit result.
    """
    if source_hash == current_hash:
        _sync_stored_hash_if_needed(ctx, current_hash)
        return _already_up_to_date(ctx)

    if _has_local_modifications(ctx, current_hash) and not ctx.force:
        return _local_modification_error(ctx)

    return None


def _copy_and_update_origin(
    ctx: UpdateContext,
    source_path: Path,
    success_message: str,
    extra_fields: dict[str, Any] | None = None,
    history_entry: dict[str, Any] | None = None,
    details: list[UpdateResultItem] | None = None,
) -> UpdateResult:
    """Common update: rmtree + copytree + update_origin."""
    try:
        shutil.rmtree(ctx.dest_path)
        shutil.copytree(source_path, ctx.dest_path)

        new_hash, _ = compute_content_hash_with_reason(ctx.dest_path)
        origin_updates: dict[str, Any] = {
            "content_hash": new_hash,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "local_modified": False,
        }
        if extra_fields:
            origin_updates.update(extra_fields)

        update_origin(
            ctx.skill_id, origin_updates, config=ctx.config, add_history_entry=history_entry
        )

        return UpdateResult(
            success=True,
            skill_id=ctx.skill_id,
            message=success_message,
            updated=[ctx.skill_id],
            details=details or [],
        )
    except Exception as e:
        return _error(ctx, f"Failed to update: {e}")


# =============================================================================
# Update Handlers (one per origin kind)
# =============================================================================


def _update_local(ctx: UpdateContext) -> UpdateResult:
    """Update from local source directory."""
    source_base = Path(ctx.origin.get("source", ""))

    # Validate source
    if not source_base.exists():
        return _error(ctx, f"Source path not found: {source_base}")
    if not source_base.is_dir():
        return _error(ctx, f"Source is not a directory: {source_base}")

    # Resolve skill path within source
    origin_path = ctx.origin.get("path", "")
    if origin_path:
        candidate = source_base / origin_path
        source_path = candidate if (candidate / "SKILL.md").exists() else None
    else:
        source_path = _resolve_local_skill_path(source_base, ctx.skill_id)

    if source_path is None:
        return _error(ctx, f"Could not find skill in source: {source_base}")

    # Update origin.path if not set
    if not origin_path:
        try:
            rel = source_path.relative_to(source_base)
            update_origin(ctx.skill_id, {"path": rel.as_posix()}, config=ctx.config)
        except Exception:
            pass

    # Compute hashes
    source_hash, reason = compute_content_hash_with_reason(source_path)
    if reason:
        return _error(ctx, f"Source not readable: {reason}")

    current_hash, reason = compute_content_hash_with_reason(ctx.dest_path)
    if reason:
        return _error(ctx, f"Installed skill unreadable: {reason}")

    # Check if update needed
    if result := _check_update_needed(ctx, source_hash, current_hash):
        return result

    # Dry run
    if ctx.dry_run:
        return UpdateResult(
            success=True,
            skill_id=ctx.skill_id,
            message=f"Would update from {source_path}",
            updated=[ctx.skill_id],
        )

    # Apply update
    return _copy_and_update_origin(ctx, source_path, "Updated from local source")


def _update_github(ctx: UpdateContext) -> UpdateResult:
    """Update from GitHub repository."""
    source_url = ctx.origin.get("source", "")
    if not source_url:
        return _error(ctx, "Missing GitHub source URL")

    old_commit = ctx.origin.get("commit_sha", "")[:7] or "unknown"

    # Compute installed hash
    current_hash, reason = compute_content_hash_with_reason(ctx.dest_path)
    if reason:
        return _error(ctx, f"Installed skill unreadable: {reason}")

    # Get remote hash via tree API (no download yet)
    remote_hash, reason = _github_source_hash(ctx.origin, ctx.skill_id, config=ctx.config)
    if reason:
        return _error(ctx, f"Cannot check remote: {reason}")

    # Check if update needed
    if result := _check_update_needed(ctx, remote_hash, current_hash):
        return result

    # Dry run
    if ctx.dry_run:
        return UpdateResult(
            success=True,
            skill_id=ctx.skill_id,
            message=f"Would update ({old_commit} -> latest)",
            updated=[ctx.skill_id],
            details=[
                UpdateResultItem(
                    skill_id=ctx.skill_id,
                    success=True,
                    message="Would update",
                    from_commit=old_commit,
                    to_commit="latest",
                )
            ],
        )

    # Download and apply update
    temp_dir: Path | None = None
    try:
        fetch_result = fetch_github_source_with_info(source_url)
        temp_dir = fetch_result.extracted_path
        new_commit = fetch_result.commit_sha[:7] if fetch_result.commit_sha else ""

        source_path = _resolve_github_source_path(temp_dir, ctx.origin, source_url)

        history_entry = {
            "from_commit": old_commit,
            "to_commit": new_commit or "latest",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        return _copy_and_update_origin(
            ctx,
            source_path,
            f"Updated ({old_commit} -> {new_commit or 'latest'})",
            extra_fields={"commit_sha": fetch_result.commit_sha},
            history_entry=history_entry,
            details=[
                UpdateResultItem(
                    skill_id=ctx.skill_id,
                    success=True,
                    message="Updated",
                    from_commit=old_commit,
                    to_commit=new_commit or "latest",
                )
            ],
        )

    except Exception as e:
        return _error(ctx, f"Failed to fetch from GitHub: {e}")
    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def _update_zip(ctx: UpdateContext) -> UpdateResult:
    """Update from zip file source."""
    source_zip = Path(ctx.origin.get("source", ""))

    # Validate source
    if not source_zip.exists():
        return _error(ctx, f"Zip file not found: {source_zip}")
    if not source_zip.is_file():
        return _error(ctx, f"Source is not a file: {source_zip}")

    current_mtime = source_zip.stat().st_mtime_ns

    # Compute installed hash
    current_hash, reason = compute_content_hash_with_reason(ctx.dest_path)
    if reason:
        return _error(ctx, f"Installed skill unreadable: {reason}")

    # Fast path: mtime unchanged
    stored_mtime = ctx.origin.get("source_mtime")
    if stored_mtime == current_mtime and ctx.stored_hash:
        if ctx.stored_hash == current_hash:
            return _already_up_to_date(ctx)
        if not ctx.force:
            return _local_modification_error(ctx)

    # Extract and compute source hash
    temp_dir: Path | None = None
    try:
        extract_result = extract_zip(source_zip)
        temp_dir = extract_result.extracted_path

        skills = detect_skills(temp_dir)
        if not skills:
            return _error(ctx, "No skills found in zip source")
        if len(skills) != 1:
            return _error(ctx, f"Zip must contain exactly one skill (found {len(skills)})")

        skill_source_path = _resolve_zip_skill_path(temp_dir, ctx.origin, skills)

        source_hash, reason = compute_content_hash_with_reason(skill_source_path)
        if reason:
            return _error(ctx, f"Source not readable: {reason}")

        # Check if update needed
        if result := _check_update_needed(ctx, source_hash, current_hash):
            # Update mtime for fast path next time
            if result.skipped:
                update_origin(
                    ctx.skill_id,
                    {"source_mtime": current_mtime, "content_hash": current_hash},
                    config=ctx.config,
                )
            return result

        # Dry run
        if ctx.dry_run:
            return UpdateResult(
                success=True,
                skill_id=ctx.skill_id,
                message=f"Would update from {source_zip.name}",
                updated=[ctx.skill_id],
            )

        # Apply update
        return _copy_and_update_origin(
            ctx,
            skill_source_path,
            "Updated from zip source",
            extra_fields={"source_mtime": current_mtime},
        )

    except Exception as e:
        return _error(ctx, f"Failed to extract zip: {e}")
    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


# Handler dispatch table
_UPDATE_HANDLERS: dict[str, Callable[[UpdateContext], UpdateResult]] = {
    "local": _update_local,
    "github": _update_github,
    "zip": _update_zip,
}


# =============================================================================
# Path Resolution Helpers
# =============================================================================


def _resolve_local_skill_path(source: Path, skill_id: str) -> Path | None:
    """Resolve skill directory within a local source."""
    skill_name = skill_id.split("/")[-1]

    for candidate in [source / skill_id, source / skill_name, source]:
        if (candidate / "SKILL.md").exists():
            return candidate

    return None


def _resolve_github_source_path(temp_dir: Path, origin: Origin, source_url: str) -> Path:
    """Resolve skill directory within extracted GitHub tarball."""
    parsed = parse_github_url(source_url, resolve_default_branch=True)
    url_prefix = parsed.normalized_path
    origin_path = origin.get("path") or ""

    # Strip URL prefix from origin.path if present
    if url_prefix and origin_path.startswith(url_prefix + "/"):
        relative_path = origin_path[len(url_prefix) + 1 :]
    elif url_prefix and origin_path == url_prefix:
        relative_path = ""
    else:
        relative_path = origin_path

    if relative_path:
        candidate = temp_dir / relative_path
        if candidate.exists():
            return candidate
        return temp_dir

    skills = detect_skills(temp_dir)
    if skills and len(skills) == 1:
        return rename_single_skill_dir(temp_dir, skills[0].name)

    return temp_dir


def _resolve_zip_skill_path(temp_dir: Path, origin: Origin, skills: list) -> Path:
    """Resolve skill directory within extracted zip."""
    origin_path = origin.get("path", "")
    if origin_path:
        candidate = temp_dir / origin_path
        if (candidate / "SKILL.md").exists():
            return candidate
    return skills[0].source_path


# =============================================================================
# Source Hash Computation (for check_update_available)
# =============================================================================


def _compute_source_hash(
    origin: Origin, skill_id: str, *, config: Config
) -> tuple[str, str | None]:
    """Compute source-side hash. Returns (hash, error_reason)."""
    kind = origin.get("kind", "")

    if kind == "local":
        return _local_source_hash(origin, skill_id, config=config)
    if kind == "github":
        return _github_source_hash(origin, skill_id, config=config)
    if kind == "zip":
        return _zip_source_hash(origin, skill_id, config=config)

    return "", f"Unknown origin kind: {kind}"


def _local_source_hash(origin: Origin, skill_id: str, *, config: Config) -> tuple[str, str | None]:
    """Compute source hash for local origin."""
    source_base = Path(origin.get("source", ""))
    if not source_base.exists():
        return "", f"Source path not found: {source_base}"
    if not source_base.is_dir():
        return "", f"Source is not a directory: {source_base}"

    origin_path = origin.get("path") or ""
    if origin_path:
        candidate = source_base / origin_path
        source_path = (
            candidate
            if (candidate / "SKILL.md").exists()
            else _resolve_local_skill_path(source_base, skill_id)
        )
    else:
        source_path = _resolve_local_skill_path(source_base, skill_id)

    if source_path is None:
        return "", f"Could not find skill in source: {source_base}"

    return compute_content_hash_with_reason(source_path)


def _github_source_hash(origin: Origin, skill_id: str, *, config: Config) -> tuple[str, str | None]:
    """Compute source hash for GitHub origin via tree API."""
    source_url = origin.get("source", "")
    if not source_url:
        return "", "Missing source URL"

    auth = resolve_github_token()
    parsed = parse_github_url(source_url, resolve_default_branch=True, auth=auth)
    path = origin.get("path") or parsed.normalized_path or skill_id.split("/")[-1]

    remote_hash = get_remote_tree_hash(parsed, auth.token, path)

    # Try narrowing path if initial attempt failed
    if not remote_hash or path == parsed.normalized_path:
        skill_tail = skill_id.split("/")[-1]
        candidate = "/".join(p for p in [parsed.normalized_path, skill_tail] if p)
        if candidate != path:
            alt_hash = get_remote_tree_hash(parsed, auth.token, candidate)
            if alt_hash:
                remote_hash = alt_hash
                try:
                    update_origin(skill_id, {"path": candidate}, config=config)
                except Exception:
                    pass

    if not remote_hash:
        return "", "Could not fetch remote tree (treated as unknown)"
    return remote_hash, None


def _zip_source_hash(origin: Origin, skill_id: str, *, config: Config) -> tuple[str, str | None]:
    """Compute source hash for zip origin."""
    source_path = Path(origin.get("source", ""))
    if not source_path.exists():
        return "", f"Zip file not found: {source_path}"
    if not source_path.is_file():
        return "", f"Source is not a file: {source_path}"

    # Fast path: mtime unchanged
    current_mtime = source_path.stat().st_mtime_ns
    stored_mtime = origin.get("source_mtime")
    stored_hash = origin.get("content_hash", "")

    if stored_mtime == current_mtime and stored_hash:
        return stored_hash, None

    # Need to extract
    temp_dir: Path | None = None
    try:
        extract_result = extract_zip(source_path)
        temp_dir = extract_result.extracted_path

        skills = detect_skills(temp_dir)
        if not skills:
            return "", "No skills found in zip source"
        if len(skills) != 1:
            return "", f"Zip must contain exactly one skill (found {len(skills)})"

        skill_path = _resolve_zip_skill_path(temp_dir, origin, skills)
        return compute_content_hash_with_reason(skill_path)

    except Exception as e:
        return "", f"Failed to extract zip: {e}"
    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
