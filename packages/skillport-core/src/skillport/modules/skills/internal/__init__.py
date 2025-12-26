"""Internal implementations for the skills module."""

from .github import (
    GitHubFetchResult,
    ParsedGitHubURL,
    fetch_github_source,
    fetch_github_source_with_info,
    get_default_branch,
    get_latest_commit_sha,
    get_remote_tree_hash,
    parse_github_url,
    rename_single_skill_dir,
)
from .manager import (
    GITHUB_SHORTHAND_RE,
    SkillInfo,
    add_builtin,
    add_local,
    detect_skills,
    is_github_shorthand,
    parse_github_shorthand,
    remove_skill,
    resolve_source,
)
from .origin import (
    compute_content_hash,
    compute_content_hash_with_reason,
    get_all_origins,
    get_origin,
    migrate_origin_v2,
    prune_orphan_origins,
    record_origin,
    update_origin,
)
from .origin import (
    remove_origin as remove_origin_record,
)
from .tracking import (
    get_missing_skill_ids,
    get_tracked_skill_ids,
    get_untracked_skill_ids,
    scan_installed_skill_ids,
)
from .validation import validate_skill_record
from .zip_handler import (
    ZipExtractResult,
    extract_zip,
)

__all__ = [
    "resolve_source",
    "detect_skills",
    "add_builtin",
    "add_local",
    "remove_skill",
    "SkillInfo",
    "validate_skill_record",
    "parse_github_url",
    "fetch_github_source",
    "fetch_github_source_with_info",
    "get_default_branch",
    "get_latest_commit_sha",
    "get_remote_tree_hash",
    "rename_single_skill_dir",
    "ParsedGitHubURL",
    "GitHubFetchResult",
    "GITHUB_SHORTHAND_RE",
    "is_github_shorthand",
    "parse_github_shorthand",
    "record_origin",
    "remove_origin_record",
    "get_origin",
    "get_all_origins",
    "compute_content_hash",
    "compute_content_hash_with_reason",
    "update_origin",
    "migrate_origin_v2",
    "prune_orphan_origins",
    "scan_installed_skill_ids",
    "get_tracked_skill_ids",
    "get_untracked_skill_ids",
    "get_missing_skill_ids",
    "ZipExtractResult",
    "extract_zip",
]
