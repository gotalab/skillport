from typing import Any, Literal, TypedDict

from pydantic import Field

from skillport.shared.types import FrozenModel, ValidationIssue


class OriginKind(TypedDict, total=False):
    """Base origin fields common to all origin kinds."""

    source: str  # Source URL or path
    kind: Literal["builtin", "local", "github"]
    added_at: str  # ISO8601 timestamp
    updated_at: str  # ISO8601 timestamp
    skills_dir: str  # Directory where skill is installed


class OriginLocal(OriginKind):
    """Origin info for locally sourced skills."""

    path: str  # Relative path within source


class OriginGitHub(OriginKind):
    """Origin info for GitHub sourced skills."""

    ref: str  # Git ref (branch/tag)
    path: str  # Path within repo (e.g., "skills/my-skill")
    commit_sha: str  # Short commit SHA (7 chars)
    content_hash: str  # Content hash for change detection
    local_modified: bool  # Whether local modifications detected
    update_history: list[dict[str, str]]  # Update history entries


# Union type for any origin
Origin = OriginKind | OriginLocal | OriginGitHub


class SkillSummary(FrozenModel):
    """検索結果・一覧用のスキル情報"""

    id: str = Field(
        ...,
        description="Unique skill identifier (e.g., 'hello-world' or 'group/skill')",
    )
    name: str = Field(..., description="Skill display name")
    description: str = Field(..., description="Brief skill description")
    category: str = Field(default="", description="Skill category (normalized)")
    score: float = Field(default=0.0, ge=0.0, description="Search relevance score (raw)")


class SkillDetail(FrozenModel):
    """load_skill の戻り値 - スキル詳細情報"""

    id: str
    name: str
    description: str
    category: str
    tags: list[str] = Field(default_factory=list)
    instructions: str = Field(..., description="SKILL.md body content")
    path: str = Field(..., description="Absolute filesystem path")
    metadata: dict[str, Any] = Field(default_factory=dict)


class FileContent(FrozenModel):
    """read_skill_file の戻り値"""

    content: str = Field(
        ...,
        description="File content (UTF-8 text or base64-encoded binary)",
    )
    path: str = Field(..., description="Resolved absolute path")
    size: int = Field(..., ge=0, description="Content size in bytes")
    encoding: Literal["utf-8", "base64"] = Field(
        default="utf-8",
        description="Content encoding: 'utf-8' for text, 'base64' for binary",
    )
    mime_type: str = Field(
        default="text/plain",
        description="MIME type (e.g., 'image/png', 'application/pdf')",
    )


class SearchResult(FrozenModel):
    """search_skills の戻り値"""

    skills: list[SkillSummary] = Field(default_factory=list)
    total: int = Field(..., ge=0, description="Total matching skills")
    query: str = Field(..., description="Original search query")


class AddResultItem(FrozenModel):
    """Individual skill add result."""

    skill_id: str
    success: bool
    message: str


class AddResult(FrozenModel):
    """add_skill の戻り値"""

    success: bool
    skill_id: str = Field(..., description="Added skill ID (empty if failed)")
    message: str = Field(..., description="Human-readable result message")
    added: list[str] = Field(default_factory=list, description="Successfully added skill IDs")
    skipped: list[str] = Field(
        default_factory=list, description="Skipped skill IDs (already exist)"
    )
    details: list[AddResultItem] = Field(
        default_factory=list,
        description="Per-skill results for bulk adds",
    )


class RemoveResult(FrozenModel):
    """remove_skill の戻り値"""

    success: bool
    skill_id: str
    message: str


class UpdateResultItem(FrozenModel):
    """Individual skill update result."""

    skill_id: str
    success: bool
    message: str
    from_commit: str = ""
    to_commit: str = ""


class UpdateResult(FrozenModel):
    """update_skill の戻り値"""

    success: bool
    skill_id: str = Field(..., description="Updated skill ID (empty if failed)")
    message: str = Field(..., description="Human-readable result message")
    updated: list[str] = Field(default_factory=list, description="Successfully updated skill IDs")
    skipped: list[str] = Field(
        default_factory=list, description="Skipped skill IDs (no updates/errors)"
    )
    details: list[UpdateResultItem] = Field(
        default_factory=list,
        description="Per-skill results for bulk updates",
    )
    local_modified: bool = Field(
        default=False, description="Whether local modifications were detected"
    )
    errors: list[str] = Field(
        default_factory=list, description="Errors encountered during update (if any)"
    )


class ListResult(FrozenModel):
    """list_skills の戻り値"""

    skills: list[SkillSummary] = Field(default_factory=list)
    total: int = Field(..., ge=0)


# Re-export ValidationIssue from shared for public API
# (defined in shared/types.py to avoid internal -> public dependency)


class ValidationResult(FrozenModel):
    """validate_skill の戻り値"""

    valid: bool = Field(..., description="True if no fatal issues")
    issues: list[ValidationIssue] = Field(default_factory=list)
    skill_id: str


__all__ = [
    # Origin types
    "Origin",
    "OriginKind",
    "OriginLocal",
    "OriginGitHub",
    # Skill types
    "SkillSummary",
    "SkillDetail",
    "FileContent",
    "SearchResult",
    "AddResult",
    "AddResultItem",
    "RemoveResult",
    "UpdateResult",
    "UpdateResultItem",
    "ListResult",
    "ValidationIssue",
    "ValidationResult",
]
