"""Skill validation rules."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set

from skillport.shared.types import ValidationIssue
from skillport.shared.utils import parse_frontmatter

SKILL_LINE_THRESHOLD = 500
NAME_MAX_LENGTH = 64
NAME_PATTERN = re.compile(r"^[a-z0-9-]+$")
NAME_RESERVED_WORDS = {"anthropic-helper", "claude-tools"}
DESCRIPTION_MAX_LENGTH = 1024
XML_TAG_PATTERN = re.compile(r"<[^>]+>")

# Allowed top-level frontmatter properties
ALLOWED_FRONTMATTER_KEYS: Set[str] = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
}


def validate_skill_record(skill: Dict) -> List[ValidationIssue]:
    """Validate a skill dict; returns issue list."""
    issues: List[ValidationIssue] = []
    name = skill.get("name", "")
    description = skill.get("description", "")
    lines = skill.get("lines", 0)
    path = skill.get("path", "")
    dir_name = path.rsplit("/", 1)[-1] if path else ""

    # Required fields
    if not name:
        issues.append(
            ValidationIssue(
                severity="fatal", message="frontmatter.name: missing", field="name"
            )
        )
    if not description:
        issues.append(
            ValidationIssue(
                severity="fatal",
                message="frontmatter.description: missing",
                field="description",
            )
        )

    # Name vs directory
    if name and dir_name and name != dir_name:
        issues.append(
            ValidationIssue(
                severity="fatal",
                message=f"frontmatter.name '{name}' doesn't match directory '{dir_name}'",
                field="name",
            )
        )

    if lines and lines > SKILL_LINE_THRESHOLD:
        issues.append(
            ValidationIssue(
                severity="warning",
                message=f"SKILL.md: {lines} lines (recommended ≤{SKILL_LINE_THRESHOLD})",
                field="lines",
            )
        )

    if name:
        if len(name) > NAME_MAX_LENGTH:
            issues.append(
                ValidationIssue(
                    severity="fatal",
                    message=f"frontmatter.name: {len(name)} chars (max {NAME_MAX_LENGTH})",
                    field="name",
                )
            )
        if not NAME_PATTERN.match(name):
            issues.append(
                ValidationIssue(
                    severity="fatal",
                    message="frontmatter.name: invalid chars (use a-z, 0-9, -)",
                    field="name",
                )
            )
        if name.startswith("-") or name.endswith("-"):
            issues.append(
                ValidationIssue(
                    severity="fatal",
                    message="frontmatter.name: cannot start or end with hyphen",
                    field="name",
                )
            )
        if "--" in name:
            issues.append(
                ValidationIssue(
                    severity="fatal",
                    message="frontmatter.name: cannot contain consecutive hyphens",
                    field="name",
                )
            )
        for reserved in NAME_RESERVED_WORDS:
            if reserved in name.lower():
                issues.append(
                    ValidationIssue(
                        severity="fatal",
                        message=f"frontmatter.name: contains reserved word '{reserved}'",
                        field="name",
                    )
                )
                break

    if description:
        if len(description) > DESCRIPTION_MAX_LENGTH:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message=f"frontmatter.description: {len(description)} chars (max {DESCRIPTION_MAX_LENGTH})",
                    field="description",
                )
            )
        if XML_TAG_PATTERN.search(description):
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message="frontmatter.description: contains <xml> tags",
                    field="description",
                )
            )

    # Check for unexpected frontmatter keys (requires reading SKILL.md)
    if path:
        skill_md = Path(path) / "SKILL.md"
        if skill_md.exists():
            try:
                meta, _ = parse_frontmatter(skill_md)
                if isinstance(meta, dict):
                    unexpected_keys = set(meta.keys()) - ALLOWED_FRONTMATTER_KEYS
                    if unexpected_keys:
                        issues.append(
                            ValidationIssue(
                                severity="warning",
                                message=f"frontmatter: unexpected key(s): {', '.join(sorted(unexpected_keys))}",
                                field="frontmatter",
                            )
                        )
            except Exception:
                pass  # Skip if file cannot be parsed

    return issues
