from __future__ import annotations

import shutil
from pathlib import Path

from skillport.shared.config import Config
from skillport.shared.types import SourceType
from skillport.modules.skills.internal import (
    resolve_source,
    detect_skills,
    add_builtin as _add_builtin,
    add_local as _add_local,
    parse_github_url,
    fetch_github_source,
    record_origin,
)
from .types import AddResult, AddResultItem


def add_skill(
    source: str,
    *,
    config: Config,
    force: bool = False,
    keep_structure: bool | None = None,
    namespace: str | None = None,
    name: str | None = None,
    pre_fetched_dir: Path | None = None,
) -> AddResult:
    """Add a skill from builtin/local/github source."""
    try:
        source_type, resolved = resolve_source(source)
    except Exception as exc:
        return AddResult(success=False, skill_id="", message=str(exc))

    temp_dir: Path | None = None
    cleanup_temp_dir = False
    origin_payload: dict | None = None
    source_path: Path
    source_label: str

    try:
        if source_type == SourceType.BUILTIN:
            result = _add_builtin(resolved, config=config, force=force)
            if result.success:
                try:
                    record_origin(
                        resolved,
                        {"source": resolved, "kind": "builtin"},
                        config=config,
                    )
                except Exception:
                    pass
            return result

        if source_type == SourceType.GITHUB:
            parsed = parse_github_url(resolved)
            if pre_fetched_dir:
                temp_dir = Path(pre_fetched_dir)
            else:
                temp_dir = fetch_github_source(resolved)
                cleanup_temp_dir = True
            source_path = Path(temp_dir)
            source_label = Path(parsed.normalized_path or parsed.repo).name
            origin_payload = {
                "source": resolved,
                "kind": "github",
                "ref": parsed.ref,
                "path": parsed.normalized_path,
            }
        else:
            source_path = Path(resolved)
            source_label = source_path.name
            origin_payload = {"source": str(source_path), "kind": "local"}

        skills = detect_skills(source_path)

        # When fetching from GitHub, the temporary extraction directory is a
        # random mkdtemp path (skillport-gh-*). For single-skill repos, the
        # SKILL.md frontmatter name is expected to match the directory name,
        # so we rename the temp dir to the skill name to satisfy validation
        # before adding it to the local catalog.
        if source_type == SourceType.GITHUB and len(skills) == 1:
            single = skills[0]
            if single.name != source_path.name:
                renamed = source_path.parent / single.name
                if renamed.exists():
                    shutil.rmtree(renamed)
                source_path.rename(renamed)
                source_path = renamed
                temp_dir = renamed
                skills = detect_skills(source_path)
        if not skills:
            return AddResult(
                success=False, skill_id="", message=f"No skills found in {source_path}"
            )

        effective_keep_structure = keep_structure
        namespace_override = namespace
        name_override = name
        if len(skills) == 1:
            effective_keep_structure = (
                False if effective_keep_structure is None else effective_keep_structure
            )
        else:
            if effective_keep_structure is None:
                effective_keep_structure = True
            if effective_keep_structure and namespace_override is None:
                namespace_override = source_label

        results = _add_local(
            source_path=source_path,
            skills=skills,
            config=config,
            keep_structure=bool(effective_keep_structure),
            force=force,
            namespace_override=namespace_override,
            rename_single_to=name_override,
        )

        details = [
            AddResultItem(skill_id=r.skill_id, success=r.success, message=r.message)
            for r in results
        ]

        added_ids = [r.skill_id for r in results if r.success]
        skipped_ids = [r.skill_id for r in results if not r.success]
        messages_added = [r.message for r in results if r.success and r.message]
        messages_skipped = [r.message for r in results if not r.success and r.message]

        def _summarize_skipped(reasons: list[str]) -> str:
            """Return a concise summary for skipped skills."""
            if not reasons:
                return "No skills added"

            exists = [r for r in reasons if "exists" in r]
            invalid = [r for r in reasons if "Invalid SKILL.md" in r]
            others = [r for r in reasons if r not in exists and r not in invalid]

            parts: list[str] = []
            if exists:
                parts.append(f"{len(exists)} already exist")
            if invalid:
                parts.append(f"{len(invalid)} invalid SKILL.md")
            if others:
                # Show first other reason and count remainder
                first_other = others[0]
                extra = len(others) - 1
                parts.append(first_other if extra == 0 else f"{first_other} (+{extra} more)")

            return "; ".join(parts) if parts else "No skills added"

        success_all = len(skipped_ids) == 0
        if messages_skipped:
            message = _summarize_skipped(messages_skipped)
        elif messages_added:
            # Deduplicate added messages but keep order
            seen = set()
            uniq_added = []
            for msg in messages_added:
                if msg not in seen:
                    uniq_added.append(msg)
                    seen.add(msg)
            message = "; ".join(uniq_added)
        else:
            message = "No skills added"

        overall_id = added_ids[0] if len(added_ids) == 1 else ",".join(added_ids)

        if added_ids and origin_payload:
            for sid in added_ids:
                try:
                    record_origin(sid, origin_payload, config=config)
                except Exception:
                    pass

        return AddResult(
            success=success_all,
            skill_id=overall_id,
            message=message,
            added=added_ids,
            skipped=skipped_ids,
            details=details,
        )
    finally:
        if cleanup_temp_dir and temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
