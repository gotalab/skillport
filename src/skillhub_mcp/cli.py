"""CLI-only modes for SkillHub (--lint, --list, add).

This module handles CLI flags and standalone commands that don't start the server.
"""

import os
import sys
from typing import Dict, List, Any

from .db import SkillDB
from .validation import (
    TROPHY_ART,
    validate_skill,
)
from .config import settings

# CLI flags
KNOWN_FLAGS = {"--reindex", "--skip-auto-reindex", "--lint", "--list"}
# Subcommands (positional, like 'add')
KNOWN_COMMANDS = {"add"}


def parse_flags() -> Dict[str, Any]:
    """Parse CLI flags and return a dict of flag states."""
    argv = sys.argv[1:]

    # Check for --lint [skill-name]
    lint_mode = "--lint" in argv
    lint_skill = None
    if lint_mode:
        lint_idx = argv.index("--lint")
        # Check if there's a skill name after --lint
        if lint_idx + 1 < len(argv) and not argv[lint_idx + 1].startswith("--"):
            lint_skill = argv[lint_idx + 1]
            argv = argv[:lint_idx] + argv[lint_idx + 2:]  # Remove --lint and skill name
        else:
            argv = argv[:lint_idx] + argv[lint_idx + 1:]  # Remove just --lint

    list_mode = "--list" in argv

    flags = {
        "force_reindex": "--reindex" in argv,
        "skip_auto": ("--skip-auto-reindex" in argv) or (os.getenv("SKILLHUB_SKIP_AUTO_REINDEX") == "1"),
        "lint": lint_mode,
        "lint_skill": lint_skill,
        "list": list_mode,
    }
    # strip known flags so FastMCP doesn't see them
    sys.argv = [sys.argv[0]] + [a for a in argv if a not in KNOWN_FLAGS]
    return flags


def _ensure_index(db: SkillDB) -> None:
    """Ensure index is up to date before CLI operations."""
    reindex_decision = db.should_reindex(force=False, skip_auto=False)
    if reindex_decision["need"]:
        db.initialize_index()
        db.persist_state(reindex_decision["state"])


def run_lint(db: SkillDB, skill_name: str | None = None) -> int:
    """Run detailed lint validation. Returns exit code (0=pass, 1=fail)."""
    all_skills = db.list_all_skills(limit=1000)
    if not all_skills:
        print("No skills found.")
        return 1

    # Filter to specific skill if requested
    if skill_name:
        all_skills = [s for s in all_skills if s.get("name") == skill_name]
        if not all_skills:
            print(f"Skill '{skill_name}' not found.")
            return 1

    print(f"{'─' * 50}")
    print(f" Validating {len(all_skills)} skill(s)")
    print(f"{'─' * 50}")

    # Collect only skills with issues
    skills_with_issues: List[tuple] = []
    for skill in all_skills:
        issues = validate_skill(skill)
        if issues:
            skills_with_issues.append((skill, issues))

    # Sort by number of issues (most problematic first)
    skills_with_issues.sort(key=lambda x: len(x[1]), reverse=True)

    ok_count = len(all_skills) - len(skills_with_issues)

    if not skills_with_issues:
        # All pass - trophy!
        print(TROPHY_ART)
        print(f"  ✓ All {len(all_skills)} skill(s) pass validation!")
        print(f"{'─' * 50}\n")
        return 0

    # Show issues only
    print(f"\n⚠ {len(skills_with_issues)} skill(s) with issues:\n")

    for skill, issues in skills_with_issues:
        name = skill.get("name", "unknown")
        print(f"  {name}")
        for issue in issues:
            print(f"    · {issue}")
        print()

    print(f"{'─' * 50}")
    print(f"  {len(skills_with_issues)} with issues / {ok_count} OK")
    print(f"{'─' * 50}\n")
    return 1


def run_list(db: SkillDB) -> int:
    """List all skills without starting the server. Returns exit code."""
    all_skills = db.list_all_skills(limit=1000)
    if not all_skills:
        print("No skills found.")
        return 1

    # Sort by name
    all_skills.sort(key=lambda s: s.get("name", ""))

    print(f"{'─' * 60}")
    print(f" {len(all_skills)} skill(s)")
    print(f"{'─' * 60}\n")

    for skill in all_skills:
        name = skill.get("name", "unknown")
        description = skill.get("description", "")
        always_apply = skill.get("always_apply", False)
        # Truncate description for display
        desc_display = description[:40] + "..." if len(description) > 40 else description
        marker = "★" if always_apply else " "
        print(f"  {marker} {name:<24} {desc_display}")

    print(f"\n{'─' * 60}\n")
    return 0


def handle_cli_mode() -> bool:
    """Handle CLI-only modes (--lint, --list, add).

    Returns True if a CLI mode was handled (and program should exit),
    False if normal server startup should proceed.
    """
    argv = sys.argv[1:]

    # add subcommand
    if argv and argv[0] == "add":
        skill_name = argv[1] if len(argv) > 1 else None
        exit_code = run_add(skill_name)
        sys.exit(exit_code)

    # --lint mode
    if "--lint" in argv:
        flags = parse_flags()
        db = SkillDB()
        _ensure_index(db)
        exit_code = run_lint(db, flags.get("lint_skill"))
        sys.exit(exit_code)

    # --list mode
    if "--list" in argv:
        parse_flags()  # consume flags
        db = SkillDB()
        _ensure_index(db)
        exit_code = run_list(db)
        sys.exit(exit_code)

    return False


# =============================================================================
# add command
# =============================================================================

# Built-in skill templates
BUILTIN_SKILLS = {
    "hello-world": """\
---
name: hello-world
description: A simple hello world skill for testing SkillHub.
metadata:
  skillhub:
    category: examples
    tags: [hello, test, demo]
---
# Hello World Skill

This is a sample skill to verify your SkillHub installation is working.

## Usage

When the user asks to test SkillHub or says "hello", respond with a friendly greeting
and confirm that the skill system is operational.

## Example Response

"Hello! The hello-world skill is working correctly."
""",
    "template": """\
---
name: my-custom-skill
description: Replace this with a description of what your skill does.
metadata:
  skillhub:
    category: custom
    tags: [template, starter]
---
# My Custom Skill

Replace this content with instructions for the AI agent.

## When to Use

Describe the situations when this skill should be activated.

## Instructions

1. Step one...
2. Step two...
3. Step three...

## Examples

Provide example inputs and expected outputs.
""",
}


def run_add(skill_name: str | None) -> int:
    """Add a built-in skill to the skills directory.

    Args:
        skill_name: Name of the built-in skill to add (hello-world, template).

    Returns:
        Exit code (0=success, 1=failure).
    """
    skills_dir = settings.get_effective_skills_dir()

    # Show usage if no skill name provided
    if not skill_name:
        print(f"{'─' * 60}")
        print(" SkillHub Add")
        print(f"{'─' * 60}\n")
        print("  Usage: skillhub add <skill-name>\n")
        print("  Available skills:")
        for name in BUILTIN_SKILLS:
            print(f"    - {name}")
        print("\n  Example:")
        print("    skillhub add hello-world")
        print("    skillhub add template")
        print(f"\n{'─' * 60}\n")
        return 1

    # Check if skill exists
    if skill_name not in BUILTIN_SKILLS:
        print(f"Unknown skill: {skill_name}")
        print(f"Available skills: {', '.join(BUILTIN_SKILLS.keys())}")
        return 1

    # Create skills directory if needed
    if not skills_dir.exists():
        try:
            skills_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created: {skills_dir}")
        except OSError as e:
            print(f"Failed to create directory: {e}")
            return 1

    # Determine target directory name
    target_dir_name = f"_{skill_name}" if skill_name == "template" else skill_name
    target_dir = skills_dir / target_dir_name
    target_file = target_dir / "SKILL.md"

    # Check if already exists
    if target_file.exists():
        print(f"Skill already exists: {target_dir}")
        return 1

    # Create skill
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text(BUILTIN_SKILLS[skill_name])
        print(f"Added: {target_dir}")
        print("\nVerify with: skillhub --list")
        return 0
    except OSError as e:
        print(f"Failed to create skill: {e}")
        return 1
