"""Skill validation rules."""

from __future__ import annotations

import unicodedata
from pathlib import Path

from skillport.shared.types import ValidationIssue
from skillport.shared.utils import parse_frontmatter

SKILL_LINE_THRESHOLD = 500
NAME_MAX_LENGTH = 64
DESCRIPTION_MAX_LENGTH = 1024
COMPATIBILITY_MAX_LENGTH = 500


def _is_valid_name_char(char: str) -> bool:
    """Check if a character is valid for skill names (lowercase letter, digit, or hyphen)."""
    if char == "-":
        return True
    category = unicodedata.category(char)
    # Ll = lowercase letter, Nd = decimal digit
    return category in ("Ll", "Nd")


def _validate_name_chars(name: str) -> bool:
    """Validate that all characters in name are lowercase letters, digits, or hyphens."""
    normalized = unicodedata.normalize("NFKC", name)
    return all(_is_valid_name_char(c) for c in normalized)


# Allowed top-level frontmatter properties
ALLOWED_FRONTMATTER_KEYS: set[str] = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}


def validate_skill_record(
    skill: dict,
    *,
    strict: bool = False,
    meta: dict | None = None,
) -> list[ValidationIssue]:
    """Validate a skill dict; returns issue list.

    Args:
        skill: Skill data dict (name, description, lines, path).
        strict: If True, return only fatal issues. Used by add command.
        meta: Raw frontmatter dict from parse_frontmatter(). If provided,
              enables key existence checks (A1/A2). Used by add command.

    Returns:
        List of validation issues.
    """
    issues: list[ValidationIssue] = []
    name = skill.get("name", "")
    description = skill.get("description", "")
    lines = skill.get("lines", 0)
    path = skill.get("path", "")
    dir_name = Path(path).name if path else ""

    # A1/A2: Key existence checks (only when meta is provided)
    if meta is not None:
        if "name" not in meta:
            issues.append(
                ValidationIssue(
                    severity="fatal",
                    message="frontmatter: 'name' key is missing",
                    field="name",
                )
            )
        if "description" not in meta:
            issues.append(
                ValidationIssue(
                    severity="fatal",
                    message="frontmatter: 'description' key is missing",
                    field="description",
                )
            )

    # Required fields (value checks)
    if not name:
        issues.append(
            ValidationIssue(severity="fatal", message="frontmatter.name: missing", field="name")
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
        if not _validate_name_chars(name):
            issues.append(
                ValidationIssue(
                    severity="fatal",
                    message="frontmatter.name: invalid chars (use lowercase letters, digits, hyphens)",
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

    if description:
        if len(description) > DESCRIPTION_MAX_LENGTH:
            issues.append(
                ValidationIssue(
                    severity="fatal",
                    message=f"frontmatter.description: {len(description)} chars (max {DESCRIPTION_MAX_LENGTH})",
                    field="description",
                )
            )

    # Check for unexpected frontmatter keys and compatibility (requires reading SKILL.md)
    if path:
        skill_md = Path(path) / "SKILL.md"
        if skill_md.exists():
            try:
                parsed_meta, _ = parse_frontmatter(skill_md)
                if isinstance(parsed_meta, dict):
                    # Unexpected keys → fatal (per Agent Skills spec)
                    unexpected_keys = set(parsed_meta.keys()) - ALLOWED_FRONTMATTER_KEYS
                    if unexpected_keys:
                        issues.append(
                            ValidationIssue(
                                severity="fatal",
                                message=f"frontmatter: unexpected field(s): {', '.join(sorted(unexpected_keys))}",
                                field="frontmatter",
                            )
                        )
                    # Compatibility validation (optional, max 500 chars, string type)
                    compatibility = parsed_meta.get("compatibility")
                    if compatibility is not None:
                        if not isinstance(compatibility, str):
                            issues.append(
                                ValidationIssue(
                                    severity="fatal",
                                    message="frontmatter.compatibility: must be a string",
                                    field="compatibility",
                                )
                            )
                        elif len(compatibility) > COMPATIBILITY_MAX_LENGTH:
                            issues.append(
                                ValidationIssue(
                                    severity="fatal",
                                    message=f"frontmatter.compatibility: {len(compatibility)} chars (max {COMPATIBILITY_MAX_LENGTH})",
                                    field="compatibility",
                                )
                            )
            except Exception:
                pass  # Skip if file cannot be parsed

    # strict mode: return only fatal issues
    if strict:
        return [i for i in issues if i.severity == "fatal"]
    return issues
