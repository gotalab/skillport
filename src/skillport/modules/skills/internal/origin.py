import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skillport.shared.config import Config

# Maximum number of entries in update_history
MAX_UPDATE_HISTORY = 10

# Hash calculation safeguards (configurable via env in the future)
MAX_HASH_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_HASH_FILES = 5000


def _path_for_config(config: Config) -> Path:
    return (config.meta_dir / "origins.json").expanduser().resolve()


def _load(config: Config) -> dict[str, Any]:
    path = _path_for_config(config)
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        print(f"[WARN] Failed to load origins.json: {exc}", file=sys.stderr)
    return {}


def _save(config: Config, data: dict[str, Any]) -> None:
    path = _path_for_config(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_origin(skill_id: str, payload: dict[str, Any], *, config: Config) -> None:
    data = _load(config)
    enriched = dict(payload)
    now_iso = datetime.now(timezone.utc).isoformat()
    enriched.setdefault("added_at", now_iso)
    enriched.setdefault("updated_at", enriched.get("added_at", now_iso))
    enriched.setdefault("skills_dir", str(config.skills_dir))
    data[skill_id] = enriched
    _save(config, data)


def remove_origin(skill_id: str, *, config: Config) -> None:
    data = _load(config)
    if skill_id in data:
        del data[skill_id]
        _save(config, data)


def prune_orphan_origins(*, config: Config) -> list[str]:
    """Remove origin entries whose skill directory no longer exists.

    Returns:
        List of skill_ids removed.
    """
    data = _load(config)
    if not data:
        return []

    removed: list[str] = []
    for skill_id, origin in list(data.items()):
        # Only touch entries that belong to the same skills_dir to avoid
        # accidentally pruning other catalogs.
        origin_skills_dir = origin.get("skills_dir")
        if origin_skills_dir and Path(origin_skills_dir).resolve() != config.skills_dir:
            continue

        skill_path = config.skills_dir / skill_id
        if not skill_path.exists():
            removed.append(skill_id)
            data.pop(skill_id, None)

    if removed:
        _save(config, data)

    return removed


def get_origin(skill_id: str, *, config: Config) -> dict[str, Any] | None:
    """Get origin info for a skill.

    Returns the origin dict if found, otherwise None.
    The origin is automatically migrated to v2 format.
    """
    data = _load(config)
    origin = data.get(skill_id)
    if origin is None:
        return None

    migrated = migrate_origin_v2(dict(origin))
    if migrated != origin:
        data[skill_id] = migrated
        _save(config, data)
    return migrated


def get_all_origins(*, config: Config) -> dict[str, dict[str, Any]]:
    """Get all origins, migrated to v2 format."""
    data = _load(config)
    migrated: dict[str, dict[str, Any]] = {}
    changed = False

    for skill_id, origin in data.items():
        new_origin = migrate_origin_v2(dict(origin))
        migrated[skill_id] = new_origin
        if new_origin != origin:
            changed = True

    if changed:
        _save(config, migrated)

    return migrated


def migrate_origin_v2(origin: dict[str, Any]) -> dict[str, Any]:
    """Migrate origin entry to v2 format in-place and return it.

    v2 fields:
    - updated_at: ISO8601 timestamp of last update
    - commit_sha: GitHub commit SHA (for github kind)
    - content_hash: SHA256 hash of SKILL.md content
    - local_modified: Whether local changes exist
    - update_history: List of update events (max 10)
    """
    # Ensure v2 fields are present with safe defaults
    origin.setdefault("content_hash", "")  # Will be computed on next update
    origin.setdefault("commit_sha", "")  # Will be fetched on next update
    origin.setdefault("local_modified", False)
    origin.setdefault("update_history", [])
    origin.setdefault("updated_at", origin.get("added_at", ""))

    # Trim history to the allowed window
    if len(origin["update_history"]) > MAX_UPDATE_HISTORY:
        origin["update_history"] = origin["update_history"][:MAX_UPDATE_HISTORY]

    return origin


def compute_content_hash(skill_path: Path) -> str:
    """Backward-compatible wrapper returning only the hash."""
    hash_value, _reason = compute_content_hash_with_reason(skill_path)
    return hash_value


def compute_content_hash_with_reason(skill_path: Path) -> tuple[str, str | None]:
    """Compute directory content hash with safeguards.

    Hash = sha256( join(relpath + NUL + file_sha1 + NUL) for files sorted by relpath )
    file_sha1 is sha1 over file bytes (matches Git blob hash).

    Returns:
        (hash, skipped_reason)
        - hash: "sha256:..." when successful, "" on failure/skip
        - skipped_reason: None if computed, else a human-readable reason
    """
    if not skill_path.exists() or not skill_path.is_dir():
        return "", "missing"

    files: list[Path] = []
    total_bytes = 0
    # Sort by posix-style relative path to match GitHub tree API ordering on all OSes
    # (Windows backslashes would otherwise produce different hashes)
    for p in sorted(skill_path.rglob("*"), key=lambda p: p.relative_to(skill_path).as_posix()):
        if not p.is_file():
            continue
        rel = p.relative_to(skill_path)
        parts = rel.parts
        if any(part.startswith(".") for part in parts):
            continue
        if any(part in ("__pycache__", ".git") for part in parts):
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        total_bytes += st.st_size
        files.append(p)
        if len(files) > MAX_HASH_FILES:
            return "", "too_many_files"
        if total_bytes > MAX_HASH_BYTES:
            return "", "too_large"

    hasher = hashlib.sha256()
    if not files:
        return "", "empty"

    for p in files:
        rel = p.relative_to(skill_path)
        try:
            data = p.read_bytes()
        except OSError:
            return "", "unreadable"
        # Use Git blob format: sha1("blob " + length + "\0" + contents)
        # This matches the SHA returned by GitHub's tree API
        blob_header = f"blob {len(data)}\x00".encode()
        blob_sha = hashlib.sha1(blob_header + data).hexdigest()
        hasher.update(rel.as_posix().encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(blob_sha.encode("utf-8"))
        hasher.update(b"\x00")

    return f"sha256:{hasher.hexdigest()}", None


def update_origin(
    skill_id: str,
    updates: dict[str, Any],
    *,
    config: Config,
    add_history_entry: dict[str, Any] | None = None,
) -> None:
    """Update origin fields for a skill.

    Args:
        skill_id: The skill ID
        updates: Dict of fields to update (merged into existing origin)
        config: Config instance
        add_history_entry: Optional history entry to prepend to update_history

    Note:
        - Existing fields not in updates are preserved
        - update_history is rotated to keep max 10 entries
    """
    data = _load(config)

    if skill_id not in data:
        # Create new entry with updates
        origin = dict(updates)
        origin.setdefault("added_at", datetime.now(timezone.utc).isoformat())
        origin.setdefault("skills_dir", str(config.skills_dir))
    else:
        # Merge updates into existing origin (migrated to v2)
        origin = migrate_origin_v2(dict(data[skill_id]))
        origin.update(updates)

    # Handle update_history rotation
    if add_history_entry:
        history = origin.get("update_history", [])
        # Prepend new entry and limit to MAX_UPDATE_HISTORY
        history = [add_history_entry] + history[: MAX_UPDATE_HISTORY - 1]
        origin["update_history"] = history

    data[skill_id] = origin
    _save(config, data)
