import os
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

import yaml

from ..config import settings
from ..utils import parse_frontmatter
from ..validation import validate_skill
from .types import SourceType, SkillInfo, AddResult


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
name: template
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

# Exclude dot-directories/files that should never be copied
EXCLUDE_NAMES = {".git", ".env", ".DS_Store", "__pycache__"}


def resolve_source(source: str) -> Tuple[SourceType, str]:
    """Determine the source type and return a resolved identifier/path."""
    if not source:
        raise ValueError("Source is required")

    if source in BUILTIN_SKILLS:
        return SourceType.BUILTIN, source

    if source.startswith("https://github.com/"):
        return SourceType.GITHUB, source

    candidate = Path(source).expanduser().resolve()
    if candidate.exists():
        if candidate.is_dir():
            return SourceType.LOCAL, str(candidate)
        raise ValueError(f"Source is not a directory: {candidate}")

    raise ValueError(f"Source not found: {source}")


def _load_skill_info(skill_dir: Path) -> SkillInfo:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found in {skill_dir}")
    meta, _ = parse_frontmatter(skill_md)
    if not isinstance(meta, dict):
        raise ValueError(f"Invalid SKILL.md in {skill_dir}: frontmatter must be a mapping")
    name = meta.get("name") or skill_dir.name
    return SkillInfo(name=name, source_path=skill_dir)


def detect_skills(path: Path) -> List[SkillInfo]:
    """Detect skills under the given path (root or one-level children)."""
    if not path.exists():
        raise FileNotFoundError(f"Source not found: {path}")
    if not path.is_dir():
        raise ValueError(f"Source must be a directory: {path}")

    skills: List[SkillInfo] = []

    root_skill = path / "SKILL.md"
    if root_skill.exists():
        skills.append(_load_skill_info(path))
        return skills

    # Search one level deep
    for child in sorted(path.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if skill_md.exists():
            skills.append(_load_skill_info(child))

    return skills


def _ensure_frontmatter_name(raw_content: str, target_name: str) -> str:
    """Rewrite frontmatter.name to match the target directory for lint compliance."""
    if not raw_content.startswith("---"):
        return raw_content
    try:
        parts = raw_content.split("---", 2)
        if len(parts) < 3:
            return raw_content
        meta = yaml.safe_load(parts[1]) or {}
        if not isinstance(meta, dict):
            return raw_content
        meta["name"] = target_name
        new_meta = yaml.safe_dump(meta, sort_keys=False).strip()
        body = parts[2].lstrip("\n")
        return f"---\n{new_meta}\n---\n{body}"
    except Exception:
        return raw_content


def _validate_skill_file(skill_dir: Path) -> None:
    """Validate SKILL.md structure before copying.

    Fatal conditions raise, non-fatal emit warnings (stderr) but allow add.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found: {skill_dir}")
    meta, body = parse_frontmatter(skill_md)
    if not isinstance(meta, dict):
        raise ValueError(f"Invalid SKILL.md in {skill_dir}: frontmatter must be a mapping")

    name = meta.get("name") or skill_dir.name
    description = meta.get("description", "")
    lines = body.count("\n") + (1 if body and not body.endswith("\n") else 0)

    issues = validate_skill({"name": name, "description": description, "lines": lines, "path": str(skill_dir)})

    fatal_markers = ("missing", "doesn't match directory", "invalid chars", "reserved word")
    fatal_issues = [i for i in issues if any(marker in i for marker in fatal_markers)]
    if fatal_issues:
        raise ValueError(f"Invalid SKILL.md in {skill_dir}: " + "; ".join(fatal_issues))

    warn_issues = [i for i in issues if i not in fatal_issues]
    for issue in warn_issues:
        print(f"[WARN] {skill_dir}: {issue}", file=sys.stderr)

    # Ensure name matches terminal directory as per spec (redundant but fatal)
    if name != skill_dir.name:
        raise ValueError(f"Invalid SKILL.md in {skill_dir}: name '{name}' must match directory '{skill_dir.name}'")


def _fail_on_symlinks(path: Path) -> None:
    """Reject any symlinks inside the source to avoid copying unintended files."""
    for root, dirs, files in os.walk(path):
        for entry in dirs + files:
            candidate = Path(root) / entry
            if candidate.is_symlink():
                raise ValueError(f"Symlinks are not allowed in skills: {candidate}")


def _copy_skill_dir(source: Path, dest: Path) -> None:
    """Copy a skill directory excluding hidden/system files."""
    _fail_on_symlinks(source)

    def _ignore(_src, names):
        ignored = {n for n in names if n in EXCLUDE_NAMES or n.startswith(".")}
        return ignored

    shutil.copytree(source, dest, dirs_exist_ok=False, ignore=_ignore)


def add_builtin(name: str, target_dir: Path, force: bool) -> AddResult:
    """Add a built-in skill into target_dir."""
    if name not in BUILTIN_SKILLS:
        raise ValueError(f"Unknown built-in skill: {name}")

    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / name
    if dest.exists():
        if not force:
            return AddResult(False, name, f"Skill '{name}' exists. Use --force to overwrite.")
        shutil.rmtree(dest)

    dest.mkdir(parents=True, exist_ok=True)
    content = _ensure_frontmatter_name(BUILTIN_SKILLS[name], name)
    (dest / "SKILL.md").write_text(content, encoding="utf-8")
    return AddResult(True, name, f"Added '{name}' to {target_dir}")


def add_local(
    source_path: Path,
    skills: List[SkillInfo],
    target_dir: Path | None = None,
    keep_structure: bool = False,
    force: bool = False,
    namespace_override: str | None = None,
    rename_single_to: str | None = None,
) -> List[AddResult]:
    """Copy skills from a local directory into the skills dir."""
    target_root = target_dir or settings.get_effective_skills_dir()
    target_root.mkdir(parents=True, exist_ok=True)

    # Validate all skills first to avoid partial copies
    for skill in skills:
        _validate_skill_file(skill.source_path)

    results: List[AddResult] = []
    namespace = namespace_override or source_path.name

    # detect duplicate IDs within the batch
    seen_ids = set()

    for skill in skills:
        skill_name = skill.name
        if rename_single_to and len(skills) == 1:
            skill_name = rename_single_to
        skill_id = skill_name if not keep_structure else f"{namespace}/{skill_name}"
        if skill_id in seen_ids:
            raise ValueError(f"Duplicate skill id detected: {skill_id}")
        seen_ids.add(skill_id)

        dest = target_root / skill_id
        if dest.exists():
            if not force:
                results.append(AddResult(False, skill_id, f"Skill '{skill_id}' exists. Use --force to overwrite."))
                continue
            shutil.rmtree(dest)

        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            _copy_skill_dir(skill.source_path, dest)
            # Ensure frontmatter name matches target when renamed
            if rename_single_to and len(skills) == 1:
                skill_md_path = dest / "SKILL.md"
                raw = skill_md_path.read_text(encoding="utf-8")
                skill_md_path.write_text(_ensure_frontmatter_name(raw, skill_name), encoding="utf-8")
            results.append(AddResult(True, skill_id, f"Added '{skill_id}'"))
        except Exception as e:
            # Rollback: remove partially copied directory on failure
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            results.append(AddResult(False, skill_id, f"Failed to add '{skill_id}': {e}"))

    return results
