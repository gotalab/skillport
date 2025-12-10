from __future__ import annotations

import shutil
from pathlib import Path

from skillport.modules.skills.internal import (
    add_builtin as _add_builtin,
)
from skillport.modules.skills.internal import (
    add_local as _add_local,
)
from skillport.modules.skills.internal import (
    compute_content_hash,
    detect_skills,
    extract_zip,
    fetch_github_source_with_info,
    parse_github_url,
    record_origin,
    rename_single_skill_dir,
    resolve_source,
)
from skillport.shared.config import Config
from skillport.shared.types import SourceType

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
    pre_fetched_commit_sha: str = "",
) -> AddResult:
    """Add a skill from builtin/local/github source."""
    try:
        source_type, resolved = resolve_source(source)
    except Exception as exc:
        return AddResult(success=False, skill_id="", message=str(exc))

    temp_dir: Path | None = None
    cleanup_temp_dir = False
    origin_payload: dict | None = None
    commit_sha: str = ""
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
                commit_sha = pre_fetched_commit_sha
                cleanup_temp_dir = True
            else:
                fetch_result = fetch_github_source_with_info(resolved)
                temp_dir = fetch_result.extracted_path
                commit_sha = fetch_result.commit_sha
                cleanup_temp_dir = True
            source_path = Path(temp_dir)
            source_label = Path(parsed.normalized_path or parsed.repo).name
            origin_payload = {
                "source": resolved,
                "kind": "github",
                "ref": parsed.ref,
                # パスが空の場合でも単一スキルなら skill 名を path に保存して判定対象を限定する
                "path": parsed.normalized_path or "",
                "commit_sha": commit_sha,
            }
        elif source_type == SourceType.ZIP:
            zip_path = Path(resolved)
            extract_result = extract_zip(zip_path)
            temp_dir = extract_result.extracted_path
            cleanup_temp_dir = True
            source_path = temp_dir
            source_label = zip_path.stem  # "my-skill.zip" -> "my-skill"
            origin_payload = {
                "source": resolved,
                "kind": "zip",
                "path": "",
                "source_mtime": zip_path.stat().st_mtime_ns,
            }
        else:
            source_path = Path(resolved)
            source_label = source_path.name
            origin_payload = {"source": str(source_path), "kind": "local", "path": ""}

        skills = detect_skills(source_path)

        if source_type == SourceType.ZIP:
            if not skills:
                return AddResult(
                    success=False, skill_id="", message=f"No skills found in {source_path}"
                )
            if len(skills) != 1:
                return AddResult(
                    success=False,
                    skill_id="",
                    message=(
                        f"Zip must contain exactly one skill (found {len(skills)}). "
                        "Split the archive into separate zip files."
                    ),
                )

        # When fetching from GitHub or extracting a zip, the temporary extraction
        # directory is a random mkdtemp path. For single-skill repos/zips, the
        # SKILL.md frontmatter name is expected to match the directory name,
        # so we rename the temp dir to the skill name to satisfy validation
        # before adding it to the local catalog.
        if source_type in (SourceType.GITHUB, SourceType.ZIP) and len(skills) == 1:
            single = skills[0]
            source_path = rename_single_skill_dir(source_path, single.name)
            temp_dir = source_path
            skills = detect_skills(source_path)
            # 単一スキルの場合は origin.path をスキル名で確定させる
            if origin_payload is not None:
                origin_payload["path"] = origin_payload.get("path") or single.name
        # LOCAL の場合、ディレクトリ内の zip ファイルがあるかチェック
        has_zip_files = (
            source_type == SourceType.LOCAL
            and not (source_path / "SKILL.md").exists()
            and any(f.is_file() and f.suffix.lower() == ".zip" for f in source_path.iterdir())
        )

        if not skills and not has_zip_files:
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
            # 単一スキル: path をスキル名で固定
            if origin_payload is not None and not origin_payload.get("path"):
                origin_payload["path"] = skills[0].name
        else:
            if effective_keep_structure is None:
                effective_keep_structure = True
            if effective_keep_structure and namespace_override is None:
                namespace_override = source_label

        # ディレクトリスキルを追加（skills が空でない場合のみ）
        details: list[AddResultItem] = []
        added_ids: list[str] = []
        skipped_ids: list[str] = []
        messages_added: list[str] = []
        messages_skipped: list[str] = []

        if skills:
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

        # LOCAL の場合、ディレクトリ内の zip ファイルも処理
        # (ルートが単一スキルでない場合のみ)
        zip_added_ids: set[str] = set()  # zip で追加された skill_id を追跡
        if source_type == SourceType.LOCAL and not (source_path / "SKILL.md").exists():
            zip_files = sorted(
                f for f in source_path.iterdir() if f.is_file() and f.suffix.lower() == ".zip"
            )
            for zip_file in zip_files:
                # ユーザーが明示的に指定した namespace のみを適用
                # (ディレクトリ名由来の namespace_override ではなく元の namespace を使う)
                zip_result = add_skill(
                    str(zip_file),
                    config=config,
                    force=force,
                    namespace=namespace,  # ユーザー指定の namespace
                    keep_structure=namespace is not None,  # namespace があれば適用
                )
                # 結果をマージ
                if zip_result.details:
                    details.extend(zip_result.details)
                added_ids.extend(zip_result.added)
                zip_added_ids.update(zip_result.added)  # zip で追加された ID を記録
                skipped_ids.extend(zip_result.skipped)
                if zip_result.added:
                    messages_added.extend(
                        d.message for d in (zip_result.details or []) if d.success and d.message
                    )
                if zip_result.skipped or (not zip_result.success and not zip_result.added):
                    if zip_result.message:
                        messages_skipped.append(zip_result.message)

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
            # Build per-skill origin payload with path filled
            # (zip で追加されたスキルは再帰呼び出しで origin 記録済みなのでスキップ)
            for sid in added_ids:
                if sid in zip_added_ids:
                    continue
                try:
                    # Compute content_hash from the installed skill location
                    skill_path = config.skills_dir / sid
                    content_hash = compute_content_hash(skill_path)

                    # Determine path for this skill relative to source_path
                    rel_path = ""
                    if source_path.exists():
                        try:
                            rel_path = str(
                                (source_path / sid.split("/")[-1]).relative_to(source_path)
                            )
                        except Exception:
                            rel_path = sid.split("/")[-1]

                    # Enrich payload with content_hash for v2 origin tracking
                    enriched_payload = dict(origin_payload)
                    # For GitHub sources, origin.path は「リポジトリ基準のサブパス」を持つ必要がある。
                    # 複数スキル追加時もスキル単位のサブディレクトリを正しく記録する。
                    if origin_payload.get("kind") == "github":
                        prefix = origin_payload.get("path", "").rstrip("/")
                        if (
                            prefix
                            and rel_path
                            and rel_path != prefix
                            and not prefix.endswith(f"/{rel_path}")
                        ):
                            enriched_payload["path"] = f"{prefix}/{rel_path}"
                        elif prefix:
                            enriched_payload["path"] = prefix
                        else:
                            enriched_payload["path"] = rel_path
                    else:
                        enriched_payload["path"] = rel_path
                    enriched_payload["content_hash"] = content_hash

                    record_origin(sid, enriched_payload, config=config)
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
