"""Skill validation rules."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from skillport.shared.types import ValidationIssue
from skillport.shared.utils import parse_frontmatter

SKILL_LINE_THRESHOLD = 500
NAME_MAX_LENGTH = 64
DESCRIPTION_MAX_LENGTH = 1024
COMPATIBILITY_MAX_LENGTH = 500

# Reserved words that cannot appear in skill names
RESERVED_WORDS: frozenset[str] = frozenset({"anthropic", "claude"})

# Pattern to detect XML-like tags (e.g., <tag>, </tag>, <tag attr="x"/>)
# Tags must start with a letter or "/" (for closing tags)
_XML_TAG_PATTERN = re.compile(r"</?[a-zA-Z][^>]*>")


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


def _contains_reserved_word(name: str) -> str | None:
    """Return the first reserved word found in name, or None."""
    name_lower = name.lower()
    for word in RESERVED_WORDS:
        if word in name_lower:
            return word
    return None


def _contains_xml_tags(text: str) -> bool:
    """Check if text contains XML-like tags."""
    return bool(_XML_TAG_PATTERN.search(text))


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

    # Type and required field checks
    name_is_str = isinstance(name, str)
    desc_is_str = isinstance(description, str)

    # name: must be non-empty string
    if not name_is_str:
        issues.append(
            ValidationIssue(
                severity="fatal",
                message=f"frontmatter.name: must be a string (got {type(name).__name__})",
                field="name",
            )
        )
    elif not name:
        issues.append(
            ValidationIssue(severity="fatal", message="frontmatter.name: missing", field="name")
        )

    # description: must be non-empty string
    if not desc_is_str:
        issues.append(
            ValidationIssue(
                severity="fatal",
                message=f"frontmatter.description: must be a string (got {type(description).__name__})",
                field="description",
            )
        )
    elif not description:
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

    if name and name_is_str:
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
        reserved = _contains_reserved_word(name)
        if reserved:
            issues.append(
                ValidationIssue(
                    severity="fatal",
                    message=f"frontmatter.name: cannot contain reserved word '{reserved}'",
                    field="name",
                )
            )
        if _contains_xml_tags(name):
            issues.append(
                ValidationIssue(
                    severity="fatal",
                    message="frontmatter.name: cannot contain XML tags",
                    field="name",
                )
            )

    if description and desc_is_str:
        if len(description) > DESCRIPTION_MAX_LENGTH:
            issues.append(
                ValidationIssue(
                    severity="fatal",
                    message=f"frontmatter.description: {len(description)} chars (max {DESCRIPTION_MAX_LENGTH})",
                    field="description",
                )
            )
        if _contains_xml_tags(description):
            issues.append(
                ValidationIssue(
                    severity="fatal",
                    message="frontmatter.description: cannot contain XML tags",
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
