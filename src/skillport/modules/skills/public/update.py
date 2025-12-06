"""Update skills from their original sources."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skillport.modules.skills.internal import (
    compute_content_hash,
    compute_content_hash_with_reason,
    detect_skills,
    fetch_github_source_with_info,
    get_all_origins,
    get_origin,
    get_remote_tree_hash,
    parse_github_url,
    rename_single_skill_dir,
    update_origin,
)
from skillport.shared.config import Config

from .types import Origin, UpdateResult, UpdateResultItem


def detect_local_modification(skill_id: str, *, config: Config) -> bool:
    """Check if a skill has local modifications.

    Compares the current SKILL.md content hash against the stored hash.
    Returns False if origin info is missing or doesn't have content_hash.
    """
    origin = get_origin(skill_id, config=config)
    if not origin:
        return False  # No origin = not tracked

    stored_hash = origin.get("content_hash")
    if not stored_hash:
        return False  # Old format = can't detect, assume no changes

    skill_path = config.skills_dir / skill_id
    current_hash = compute_content_hash(skill_path)

    return stored_hash != current_hash


# --- common helpers ---------------------------------------------------------

def _installed_hash(skill_id: str, *, config: Config) -> tuple[str, str | None]:
    """Hash installed skill; returns (hash, reason)."""
    return compute_content_hash_with_reason(config.skills_dir / skill_id)


def _resolve_origin_path(origin: Origin, parsed_path_fallback: str, skill_id: str) -> str:
    """Pick the narrowest path for hashing/copying."""
    return origin.get("path") or parsed_path_fallback or skill_id.split("/")[-1]


def _local_source_hash(
    origin: Origin, skill_id: str, *, config: Config
) -> tuple[str, str | None]:
    """Compute source hash for local origin; returns (hash, reason)."""
    source_base = Path(origin.get("source", ""))
    if not source_base.exists():
        return "", f"Source path not found: {source_base}"
    if not source_base.is_dir():
        return "", f"Source is not a directory: {source_base}"

    origin_path = _resolve_origin_path(origin, "", skill_id)
    if origin_path:
        candidate = source_base / origin_path
        if (candidate / "SKILL.md").exists():
            source_path = candidate
        else:
            source_path = _resolve_local_skill_path(source_base, skill_id)
    else:
        source_path = _resolve_local_skill_path(source_base, skill_id)

    if source_path is None:
        return "", f"Could not find skill in source: {source_base}"

    return compute_content_hash_with_reason(source_path)


def _github_source_hash(
    origin: Origin, skill_id: str, *, config: Config
) -> tuple[str, str | None]:
    """Compute source hash for GitHub origin via tree API; returns (hash, reason)."""
    source_url = origin.get("source", "")
    if not source_url:
        return "", "Missing source URL"

    parsed = parse_github_url(source_url, resolve_default_branch=True)
    path = _resolve_origin_path(origin, parsed.normalized_path, skill_id)
    token = os.getenv("GITHUB_TOKEN")

    # 1st try: as-is
    remote_hash = get_remote_tree_hash(parsed, token, path)

    # If the recorded path points to a parent dir (e.g., "skills"),
    # try narrowing to "<path>/<skill_name>" and persist when found.
    if not remote_hash or path == parsed.normalized_path:
        skill_tail = skill_id.split("/")[-1]
        candidate = "/".join(p for p in [parsed.normalized_path, skill_tail] if p)
        if candidate != path:
            alt_hash = get_remote_tree_hash(parsed, token, candidate)
            if alt_hash:
                remote_hash = alt_hash
                try:
                    update_origin(skill_id, {"path": candidate}, config=config)
                except Exception:
                    pass

    if not remote_hash:
        return "", "Could not fetch remote tree (treated as unknown)"
    return remote_hash, None


def _source_hash(
    origin: Origin, skill_id: str, *, config: Config
) -> tuple[str, str | None]:
    """Compute source-side hash; returns (hash, reason).

    Dispatches to _local_source_hash or _github_source_hash based on origin kind.
    """
    kind = origin.get("kind", "")

    if kind == "local":
        return _local_source_hash(origin, skill_id, config=config)

    if kind == "github":
        return _github_source_hash(origin, skill_id, config=config)

    return "", f"Unknown origin kind: {kind}"


def check_update_available(skill_id: str, *, config: Config) -> dict[str, Any]:
    """Check if an update is available for a skill.

    Returns a dict with:
    - available: bool - whether an update is available
    - reason: str - explanation
    - origin: dict | None - the origin info
    - new_commit: str - the new commit SHA (if available)
    """
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

    # Unified source / installed hash comparison
    source_hash, source_reason = _source_hash(origin, skill_id, config=config)
    if source_reason:
        return {
            "available": False,
            "reason": source_reason,
            "origin": origin,
            "new_commit": "",
        }

    installed_hash, installed_reason = _installed_hash(skill_id, config=config)
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
        "reason": "Remote content differs"
        if kind == "github"
        else "Local source changed",
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
    """Update a single skill from its original source.

    Args:
        skill_id: The skill ID to update
        config: Config instance
        force: If True, overwrite local modifications
        dry_run: If True, don't actually update, just check

    Returns:
        UpdateResult with success status and details
    """
    # Check if skill exists
    skill_path = config.skills_dir / skill_id
    if not skill_path.exists():
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message=f"Skill '{skill_id}' not found",
        )

    # Get origin info
    origin = get_origin(skill_id, config=config)
    if not origin:
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message=f"Skill '{skill_id}' has no origin info (cannot update)",
        )

    kind = origin.get("kind", "")

    # Handle different origin types
    # Local modification check is now done inside each handler
    # because we need to compare with source to determine if it's truly modified
    if kind == "builtin":
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message="Built-in skill cannot be updated",
        )

    if kind == "local":
        return _update_from_local(
            skill_id, origin, config=config, force=force, dry_run=dry_run
        )

    if kind == "github":
        return _update_from_github(
            skill_id, origin, config=config, force=force, dry_run=dry_run
        )

    return UpdateResult(
        success=False,
        skill_id=skill_id,
        message=f"Unknown origin kind: {kind}",
    )


def _resolve_local_skill_path(source: Path, skill_id: str) -> Path | None:
    """Resolve the actual skill directory within a source.

    The source can be:
    - A container directory with skills inside (e.g., /path/to/source with source/my-skill/)
    - A single skill directory (e.g., /path/to/my-skill with my-skill/SKILL.md)
    """
    # Extract skill name (last part of skill_id for namespaced skills)
    skill_name = skill_id.split("/")[-1]

    # Check various possible locations
    candidates = [
        source / skill_id,  # Full path (e.g., ns/my-skill)
        source / skill_name,  # Just the name (e.g., my-skill)
        source,  # Direct skill directory
    ]

    for candidate in candidates:
        if (candidate / "SKILL.md").exists():
            return candidate

    return None


def _update_from_local(
    skill_id: str,
    origin: Origin,
    *,
    config: Config,
    force: bool,
    dry_run: bool,
) -> UpdateResult:
    """Update a skill from a local source."""
    source_base = Path(origin.get("source", ""))

    if not source_base.exists():
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message=f"Source path not found: {source_base}",
        )

    if not source_base.is_dir():
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message=f"Source is not a directory: {source_base}",
        )

    # Resolve actual skill path within source (prefer origin.path)
    origin_path = origin.get("path", "")
    if origin_path:
        candidate = source_base / origin_path
        source_path = candidate if (candidate / "SKILL.md").exists() else None
    else:
        source_path = _resolve_local_skill_path(source_base, skill_id)
    if source_path is None:
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message=f"Could not find skill in source: {source_base}",
        )

    if not origin.get("path"):
        try:
            rel = source_path.relative_to(source_base)
            update_origin(skill_id, {"path": str(rel)}, config=config)
        except Exception:
            pass

    # Compute hashes for comparison
    source_hash, source_reason = compute_content_hash_with_reason(source_path)
    if source_reason:
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message=f"Source not readable: {source_reason}",
        )

    current_hash, current_reason = compute_content_hash_with_reason(
        config.skills_dir / skill_id
    )
    if current_reason:
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message=f"Installed skill unreadable: {current_reason}",
        )

    stored_hash = origin.get("content_hash", "")

    # If current matches source, already up to date (even if locally modified to match source)
    if source_hash == current_hash:
        # Sync stored hash if outdated (e.g., old format -> new git blob format)
        if stored_hash != current_hash:
            update_origin(
                skill_id,
                {"content_hash": current_hash},
                config=config,
            )
        return UpdateResult(
            success=True,
            skill_id=skill_id,
            message="Already up to date",
            skipped=[skill_id],
        )

    # Check for local modifications (current differs from what was installed)
    has_local_mods = stored_hash and stored_hash != current_hash

    if has_local_mods and not force:
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message="Local modifications detected. Use --force to overwrite",
            local_modified=True,
        )

    if dry_run:
        return UpdateResult(
            success=True,
            skill_id=skill_id,
            message=f"Would update from {source_path}",
            updated=[skill_id],
        )

    # Perform update: remove old, copy new
    try:
        dest_path = config.skills_dir / skill_id
        shutil.rmtree(dest_path)
        shutil.copytree(source_path, dest_path)

        # Update origin with new content_hash
        new_hash, _ = compute_content_hash_with_reason(dest_path)
        update_origin(
            skill_id,
            {
                "content_hash": new_hash,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            config=config,
        )

        return UpdateResult(
            success=True,
            skill_id=skill_id,
            message="Updated from local source",
            updated=[skill_id],
        )
    except Exception as e:
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message=f"Failed to update: {e}",
        )


def _update_from_github(
    skill_id: str,
    origin: Origin,
    *,
    config: Config,
    force: bool,
    dry_run: bool,
) -> UpdateResult:
    """Update a skill from GitHub.

    Optimized to check for updates via tree API before downloading tarball.
    Only downloads when an actual update is needed.
    """
    source_url = origin.get("source", "")
    old_commit = origin.get("commit_sha", "")[:7] or "unknown"
    stored_hash = origin.get("content_hash", "")

    if not source_url:
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message="Missing GitHub source URL",
        )

    # --- Phase 1: Check if update is needed (no download) ---

    # Get installed hash
    current_hash, current_reason = compute_content_hash_with_reason(
        config.skills_dir / skill_id
    )
    if current_reason:
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message=f"Installed skill unreadable: {current_reason}",
        )

    # Get remote hash via tree API (no tarball download)
    remote_hash, remote_reason = _source_hash(origin, skill_id, config=config)
    if remote_reason:
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message=f"Cannot check remote: {remote_reason}",
        )

    # Helper to sync stored hash if outdated
    def _sync_stored_hash_if_needed() -> None:
        if stored_hash != current_hash:
            update_origin(
                skill_id,
                {"content_hash": current_hash},
                config=config,
            )

    # If hashes match, no update needed
    if remote_hash == current_hash:
        _sync_stored_hash_if_needed()
        return UpdateResult(
            success=True,
            skill_id=skill_id,
            message="Already up to date",
            skipped=[skill_id],
        )

    # Check for local modifications before downloading
    has_local_mods = stored_hash and stored_hash != current_hash
    if has_local_mods and not force:
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message="Local modifications detected. Use --force to overwrite",
            local_modified=True,
        )

    # For dry-run, we can return here without downloading
    if dry_run:
        return UpdateResult(
            success=True,
            skill_id=skill_id,
            message=f"Would update ({old_commit} -> latest)",
            updated=[skill_id],
            details=[
                UpdateResultItem(
                    skill_id=skill_id,
                    success=True,
                    message="Would update",
                    from_commit=old_commit,
                    to_commit="latest",
                )
            ],
        )

    # --- Phase 2: Download and apply update ---

    temp_dir: Path | None = None
    try:
        fetch_result = fetch_github_source_with_info(source_url)
        temp_dir = fetch_result.extracted_path
        new_commit = fetch_result.commit_sha[:7] if fetch_result.commit_sha else ""

        # Compute relative path for extraction
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

        # Perform update: remove old, copy new
        dest_path = config.skills_dir / skill_id
        shutil.rmtree(dest_path)

        if relative_path:
            candidate = temp_dir / relative_path
            if candidate.exists():
                shutil.copytree(candidate, dest_path)
            else:
                shutil.copytree(temp_dir, dest_path)
        else:
            skills = detect_skills(temp_dir)
            if skills:
                source_skill_path = temp_dir
                if len(skills) == 1:
                    source_skill_path = rename_single_skill_dir(temp_dir, skills[0].name)
                    temp_dir = source_skill_path
                shutil.copytree(source_skill_path, dest_path)
            else:
                shutil.copytree(temp_dir, dest_path)

        # Update origin with new content_hash and commit_sha
        new_hash, _ = compute_content_hash_with_reason(dest_path)
        history_entry = {
            "from_commit": old_commit,
            "to_commit": new_commit or "latest",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        update_origin(
            skill_id,
            {
                "content_hash": new_hash,
                "commit_sha": fetch_result.commit_sha,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "local_modified": False,
            },
            config=config,
            add_history_entry=history_entry,
        )

        return UpdateResult(
            success=True,
            skill_id=skill_id,
            message=f"Updated ({old_commit} -> {new_commit or 'latest'})",
            updated=[skill_id],
            details=[
                UpdateResultItem(
                    skill_id=skill_id,
                    success=True,
                    message="Updated",
                    from_commit=old_commit,
                    to_commit=new_commit or "latest",
                )
            ],
        )

    except Exception as e:
        return UpdateResult(
            success=False,
            skill_id=skill_id,
            message=f"Failed to fetch from GitHub: {e}",
        )
    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def update_all_skills(
    *,
    config: Config,
    force: bool = False,
    dry_run: bool = False,
    skill_ids: list[str] | None = None,
) -> UpdateResult:
    """Update all updatable skills (optionally limited to skill_ids).

    Returns a combined UpdateResult with all results.
    """
    origins = get_all_origins(config=config)

    if skill_ids is not None:
        origins = {k: v for k, v in origins.items() if k in skill_ids}

    if not origins:
        return UpdateResult(
            success=True,
            skill_id="",
            message="No skills to update",
        )

    updated: list[str] = []
    skipped: list[str] = []
    details: list[UpdateResultItem] = []
    errors: list[str] = []

    for skill_id, origin in origins.items():
        kind = origin.get("kind", "")

        # Skip non-updatable origins
        if kind == "builtin":
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
                UpdateResultItem(
                    skill_id=skill_id,
                    success=False,
                    message=result.message,
                    from_commit="",
                    to_commit="",
                )
            )

    # Build summary message
    parts = []
    if updated:
        parts.append(f"Updated {len(updated)} skill(s)")
    if skipped:
        parts.append(f"Skipped {len(skipped)} (up to date)")
    if errors:
        parts.append(f"{len(errors)} error(s)")

    message = ", ".join(parts) if parts else "No skills to update"

    return UpdateResult(
        success=len(errors) == 0,
        skill_id=",".join(updated) if updated else "",
        message=message,
        updated=updated,
        skipped=skipped,
        details=details,
        errors=errors,
    )
