"""Shared types for SkillPort."""

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    """Base model with immutability and strict fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceType(str, Enum):
    BUILTIN = "builtin"
    LOCAL = "local"
    GITHUB = "github"
    ZIP = "zip"


class Severity(str, Enum):
    FATAL = "fatal"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(FrozenModel):
    """Validation issue detected in a skill."""

    severity: Literal["fatal", "warning", "info"] = Field(..., description="Issue severity level")
    message: str = Field(..., description="Human-readable issue description")
    field: str | None = Field(default=None, description="Related field name if applicable")


SkillId = Annotated[
    str,
    Field(
        min_length=1,
        max_length=256,
        pattern=r"^[a-zA-Z0-9_-]+(/[a-zA-Z0-9_-]+)?$",
        description="Skill identifier: 'name' or 'namespace/name'",
    ),
]

SkillName = Annotated[
    str,
    Field(
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Skill name (directory name)",
    ),
]

Namespace = Annotated[
    str,
    Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Skill namespace (group name)",
    ),
]

__all__ = [
    "FrozenModel",
    "SourceType",
    "Severity",
    "ValidationIssue",
    "SkillId",
    "SkillName",
    "Namespace",
]
