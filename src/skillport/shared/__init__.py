"""Shared infrastructure for SkillPort."""

from .auth import TokenResult, is_gh_cli_available, resolve_github_token
from .config import SKILLPORT_HOME, Config
from .exceptions import (
    AmbiguousSkillError,
    IndexingError,
    SkillNotFoundError,
    SkillPortError,
    SourceError,
    ValidationError,
)
from .filters import is_skill_enabled, normalize_token
from .types import (
    FrozenModel,
    Namespace,
    Severity,
    SkillId,
    SkillName,
    SourceType,
    ValidationIssue,
)
from .utils import parse_frontmatter, resolve_inside

__all__ = [
    # Auth
    "TokenResult",
    "is_gh_cli_available",
    "resolve_github_token",
    # Config
    "Config",
    "SKILLPORT_HOME",
    # Exceptions
    "SkillPortError",
    "SkillNotFoundError",
    "AmbiguousSkillError",
    "ValidationError",
    "IndexingError",
    "SourceError",
    # Types
    "FrozenModel",
    "Severity",
    "SourceType",
    "ValidationIssue",
    "SkillId",
    "SkillName",
    "Namespace",
    # Utils
    "normalize_token",
    "parse_frontmatter",
    "is_skill_enabled",
    "resolve_inside",
]
