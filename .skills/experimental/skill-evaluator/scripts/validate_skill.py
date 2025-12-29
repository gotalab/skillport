#!/usr/bin/env python3
"""
Skill Validator

Performs automated validation checks on skills against Anthropic's best practices.
Checks structure, naming, description, and file organization.

Usage:
    python validate_skill.py <path/to/skill>
    python validate_skill.py <path/to/skill> --verbose
    python validate_skill.py <path/to/skill> --json

Exit codes:
    0 - All checks passed
    1 - Validation errors found
    2 - Invalid arguments or skill not found
"""

import argparse
import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    check: str
    passed: bool
    message: str
    severity: str = "error"  # error, warning, info


@dataclass
class ValidationReport:
    """Complete validation report for a skill."""
    skill_path: str
    skill_name: Optional[str] = None
    passed: bool = False
    results: list = field(default_factory=list)
    errors: int = 0
    warnings: int = 0

    def add_result(self, result: ValidationResult):
        self.results.append(result)
        if not result.passed:
            if result.severity == "error":
                self.errors += 1
            elif result.severity == "warning":
                self.warnings += 1

    def to_dict(self) -> dict:
        return {
            "skill_path": self.skill_path,
            "skill_name": self.skill_name,
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "results": [
                {
                    "check": r.check,
                    "passed": r.passed,
                    "message": r.message,
                    "severity": r.severity,
                }
                for r in self.results
            ],
        }


RESERVED_WORDS = {"anthropic", "claude"}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
XML_TAG_PATTERN = re.compile(r"<[^>]+>")


def parse_frontmatter(content: str) -> tuple[Optional[dict], str]:
    """Parse YAML frontmatter from SKILL.md content."""
    if not content.startswith("---"):
        return None, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content

    try:
        # Simple YAML parsing for frontmatter (name and description only)
        frontmatter = {}
        for line in parts[1].strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key in ("name", "description"):
                    frontmatter[key] = value
        return frontmatter, parts[2]
    except Exception:
        return None, content


def count_lines(content: str) -> int:
    """Count non-empty lines in content."""
    return len([line for line in content.split("\n") if line.strip()])


def find_file_references(content: str) -> list[str]:
    """Find all file references in markdown content."""
    # Match markdown links: [text](path) and bare paths
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    references = []
    for match in link_pattern.finditer(content):
        path = match.group(2)
        if not path.startswith("http") and not path.startswith("#"):
            references.append(path)
    return references


def check_reference_depth(skill_path: Path, references: list[str]) -> list[str]:
    """Check if any references are more than one level deep."""
    deeply_nested = []
    for ref in references:
        ref_path = skill_path / ref
        if ref_path.exists() and ref_path.is_file():
            try:
                ref_content = ref_path.read_text()
                sub_refs = find_file_references(ref_content)
                for sub_ref in sub_refs:
                    # Check if sub-reference points to another file in skill
                    sub_path = ref_path.parent / sub_ref
                    if sub_path.exists() and sub_path.is_file():
                        deeply_nested.append(f"{ref} -> {sub_ref}")
            except Exception:
                pass
    return deeply_nested


def validate_skill(skill_path: Path, verbose: bool = False) -> ValidationReport:
    """Validate a skill against best practices."""
    report = ValidationReport(skill_path=str(skill_path))

    # Check 1: Skill directory exists
    if not skill_path.exists():
        report.add_result(
            ValidationResult(
                check="skill_exists",
                passed=False,
                message=f"Skill directory not found: {skill_path}",
            )
        )
        return report

    if not skill_path.is_dir():
        report.add_result(
            ValidationResult(
                check="skill_is_directory",
                passed=False,
                message=f"Path is not a directory: {skill_path}",
            )
        )
        return report

    report.add_result(
        ValidationResult(
            check="skill_exists",
            passed=True,
            message="Skill directory exists",
            severity="info",
        )
    )

    # Check 2: SKILL.md exists
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        report.add_result(
            ValidationResult(
                check="skill_md_exists",
                passed=False,
                message="SKILL.md not found in skill directory",
            )
        )
        return report

    report.add_result(
        ValidationResult(
            check="skill_md_exists",
            passed=True,
            message="SKILL.md exists",
            severity="info",
        )
    )

    # Read SKILL.md content
    try:
        content = skill_md.read_text()
    except Exception as e:
        report.add_result(
            ValidationResult(
                check="skill_md_readable",
                passed=False,
                message=f"Could not read SKILL.md: {e}",
            )
        )
        return report

    # Check 3: Parse frontmatter
    frontmatter, body = parse_frontmatter(content)
    if frontmatter is None:
        report.add_result(
            ValidationResult(
                check="frontmatter_exists",
                passed=False,
                message="YAML frontmatter not found (must start with ---)",
            )
        )
    else:
        report.add_result(
            ValidationResult(
                check="frontmatter_exists",
                passed=True,
                message="YAML frontmatter found",
                severity="info",
            )
        )

        # Check 4: Name field
        name = frontmatter.get("name")
        if not name:
            report.add_result(
                ValidationResult(
                    check="name_present",
                    passed=False,
                    message="'name' field missing in frontmatter",
                )
            )
        else:
            report.skill_name = name
            report.add_result(
                ValidationResult(
                    check="name_present",
                    passed=True,
                    message=f"Name: {name}",
                    severity="info",
                )
            )

            # Check 4a: Name length
            if len(name) > 64:
                report.add_result(
                    ValidationResult(
                        check="name_length",
                        passed=False,
                        message=f"Name exceeds 64 characters ({len(name)} chars)",
                    )
                )
            else:
                report.add_result(
                    ValidationResult(
                        check="name_length",
                        passed=True,
                        message=f"Name length OK ({len(name)}/64 chars)",
                        severity="info",
                    )
                )

            # Check 4b: Name format
            if not NAME_PATTERN.match(name):
                report.add_result(
                    ValidationResult(
                        check="name_format",
                        passed=False,
                        message="Name must be lowercase letters, numbers, and hyphens only",
                    )
                )
            else:
                report.add_result(
                    ValidationResult(
                        check="name_format",
                        passed=True,
                        message="Name format OK",
                        severity="info",
                    )
                )

            # Check 4c: Reserved words
            name_lower = name.lower()
            for reserved in RESERVED_WORDS:
                if reserved in name_lower:
                    report.add_result(
                        ValidationResult(
                            check="name_reserved",
                            passed=False,
                            message=f"Name contains reserved word: '{reserved}'",
                        )
                    )
                    break
            else:
                report.add_result(
                    ValidationResult(
                        check="name_reserved",
                        passed=True,
                        message="No reserved words in name",
                        severity="info",
                    )
                )

            # Check 4d: XML tags in name
            if XML_TAG_PATTERN.search(name):
                report.add_result(
                    ValidationResult(
                        check="name_xml",
                        passed=False,
                        message="Name contains XML-like patterns",
                    )
                )

            # Check 4e: Gerund form (warning, not error)
            if not name.endswith("ing") and "-ing-" not in name:
                report.add_result(
                    ValidationResult(
                        check="name_gerund",
                        passed=False,
                        message="Name not in gerund form (verb + -ing recommended)",
                        severity="warning",
                    )
                )

        # Check 5: Description field
        description = frontmatter.get("description")
        if not description:
            report.add_result(
                ValidationResult(
                    check="description_present",
                    passed=False,
                    message="'description' field missing in frontmatter",
                )
            )
        else:
            report.add_result(
                ValidationResult(
                    check="description_present",
                    passed=True,
                    message="Description present",
                    severity="info",
                )
            )

            # Check 5a: Description length
            if len(description) > 1024:
                report.add_result(
                    ValidationResult(
                        check="description_length",
                        passed=False,
                        message=f"Description exceeds 1024 characters ({len(description)} chars)",
                    )
                )
            else:
                report.add_result(
                    ValidationResult(
                        check="description_length",
                        passed=True,
                        message=f"Description length OK ({len(description)}/1024 chars)",
                        severity="info",
                    )
                )

            # Check 5b: XML tags in description
            if XML_TAG_PATTERN.search(description):
                report.add_result(
                    ValidationResult(
                        check="description_xml",
                        passed=False,
                        message="Description contains XML-like patterns",
                    )
                )

            # Check 5c: Activation triggers (warning)
            trigger_keywords = ["use when", "use for", "use if", "use to", "trigger"]
            has_trigger = any(kw in description.lower() for kw in trigger_keywords)
            if not has_trigger:
                report.add_result(
                    ValidationResult(
                        check="description_triggers",
                        passed=False,
                        message="Description may be missing activation triggers (e.g., 'Use when...')",
                        severity="warning",
                    )
                )

    # Check 6: Body line count
    body_lines = count_lines(body)
    if body_lines > 500:
        report.add_result(
            ValidationResult(
                check="body_length",
                passed=False,
                message=f"SKILL.md body exceeds 500 lines ({body_lines} lines)",
            )
        )
    else:
        report.add_result(
            ValidationResult(
                check="body_length",
                passed=True,
                message=f"Body length OK ({body_lines}/500 lines)",
                severity="info",
            )
        )

    # Check 7: File references
    references = find_file_references(body)
    if references:
        # Check for Windows-style paths
        windows_paths = [r for r in references if "\\" in r]
        if windows_paths:
            report.add_result(
                ValidationResult(
                    check="path_style",
                    passed=False,
                    message=f"Windows-style paths found: {windows_paths}",
                )
            )
        else:
            report.add_result(
                ValidationResult(
                    check="path_style",
                    passed=True,
                    message="All paths use forward slashes",
                    severity="info",
                )
            )

        # Check for deeply nested references
        deeply_nested = check_reference_depth(skill_path, references)
        if deeply_nested:
            report.add_result(
                ValidationResult(
                    check="reference_depth",
                    passed=False,
                    message=f"Deeply nested references found: {deeply_nested}",
                    severity="warning",
                )
            )
        else:
            report.add_result(
                ValidationResult(
                    check="reference_depth",
                    passed=True,
                    message="All references are one-level deep",
                    severity="info",
                )
            )

    # Check 8: Look for extraneous files
    extraneous_files = ["README.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md", "QUICK_REFERENCE.md"]
    found_extraneous = []
    for ef in extraneous_files:
        if (skill_path / ef).exists():
            found_extraneous.append(ef)
    if found_extraneous:
        report.add_result(
            ValidationResult(
                check="extraneous_files",
                passed=False,
                message=f"Extraneous documentation files found: {found_extraneous}",
                severity="warning",
            )
        )

    # Final pass/fail determination
    report.passed = report.errors == 0

    return report


def print_report(report: ValidationReport, verbose: bool = False):
    """Print validation report to stderr."""
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"Skill Validation Report", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)
    print(f"Path: {report.skill_path}", file=sys.stderr)
    if report.skill_name:
        print(f"Name: {report.skill_name}", file=sys.stderr)
    print(f"{'=' * 60}\n", file=sys.stderr)

    # Group results by status
    errors = [r for r in report.results if not r.passed and r.severity == "error"]
    warnings = [r for r in report.results if not r.passed and r.severity == "warning"]
    passed = [r for r in report.results if r.passed]

    if errors:
        print("ERRORS:", file=sys.stderr)
        for r in errors:
            print(f"  [x] {r.check}: {r.message}", file=sys.stderr)
        print(file=sys.stderr)

    if warnings:
        print("WARNINGS:", file=sys.stderr)
        for r in warnings:
            print(f"  [!] {r.check}: {r.message}", file=sys.stderr)
        print(file=sys.stderr)

    if verbose and passed:
        print("PASSED:", file=sys.stderr)
        for r in passed:
            print(f"  [✓] {r.check}: {r.message}", file=sys.stderr)
        print(file=sys.stderr)

    # Summary
    print(f"{'=' * 60}", file=sys.stderr)
    status = "PASSED" if report.passed else "FAILED"
    print(f"Result: {status} ({report.errors} errors, {report.warnings} warnings)", file=sys.stderr)
    print(f"{'=' * 60}\n", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Validate a skill against Anthropic's best practices"
    )
    parser.add_argument("skill_path", help="Path to the skill directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show all checks")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    skill_path = Path(args.skill_path).resolve()
    report = validate_skill(skill_path, verbose=args.verbose)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report, verbose=args.verbose)

    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
