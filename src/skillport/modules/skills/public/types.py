from typing import Any, Literal

from pydantic import Field

from skillport.shared.types import FrozenModel, ValidationIssue


class SkillSummary(FrozenModel):
    """検索結果・一覧用のスキル情報"""

    id: str = Field(
        ...,
        description="Unique skill identifier (e.g., 'hello-world' or 'group/skill')",
    )
    name: str = Field(..., description="Skill display name")
    description: str = Field(..., description="Brief skill description")
    category: str = Field(default="", description="Skill category (normalized)")
    score: float = Field(
        default=0.0, ge=0.0, description="Search relevance score (raw)"
    )


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
    skipped: list[str] = Field(default_factory=list, description="Skipped skill IDs (already exist)")
    details: list[AddResultItem] = Field(
        default_factory=list,
        description="Per-skill results for bulk adds",
    )


class RemoveResult(FrozenModel):
    """remove_skill の戻り値"""

    success: bool
    skill_id: str
    message: str


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
    "SkillSummary",
    "SkillDetail",
    "FileContent",
    "SearchResult",
    "AddResult",
    "AddResultItem",
    "RemoveResult",
    "ListResult",
    "ValidationIssue",
    "ValidationResult",
]
