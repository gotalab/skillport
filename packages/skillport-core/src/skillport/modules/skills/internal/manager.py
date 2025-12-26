from __future__ import annotations

import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from skillport.modules.skills.public.types import AddResult, RemoveResult
from skillport.shared.config import Config
from skillport.shared.types import SourceType
from skillport.shared.utils import parse_frontmatter, resolve_inside

from .validation import validate_skill_record

# GitHub shorthand pattern: owner/repo (no slashes in owner or repo)
GITHUB_SHORTHAND_RE = re.compile(r"^(?P<owner>[a-zA-Z0-9_-]+)/(?P<repo>[a-zA-Z0-9_.-]+)$")

# Built-in skills
BUILTIN_SKILLS = {
    "hello-world": """\
---
name: hello-world
description: A simple hello world skill for testing SkillPort.
metadata:
  skillport:
    category: examples
    tags: [hello, test, demo]
---
# Hello World Skill

This is a sample skill to verify your SkillPort installation is working.

## Usage

When the user asks to test SkillPort or says "hello", respond with a friendly greeting
and confirm that the skill system is operational.

## Example Response

"Hello! The hello-world skill is working correctly."
""",
    "template": """\
---
name: template
description: Replace this with a description of what your skill does.
metadata:
  skillport:
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

EXCLUDE_NAMES = {".git", ".env", ".DS_Store", "__pycache__", "node_modules"}


@dataclass
class SkillInfo:
    name: str
    source_path: Path


def is_github_shorthand(source: str) -> bool:
    """Check if source matches GitHub shorthand format (owner/repo)."""
    return bool(GITHUB_SHORTHAND_RE.match(source))


def parse_github_shorthand(source: str) -> tuple[str, str] | None:
    """Parse GitHub shorthand format. Returns (owner, repo) or None."""
    match = GITHUB_SHORTHAND_RE.match(source)
    if match:
        return match.group("owner"), match.group("repo")
    return None


def resolve_source(source: str) -> tuple[SourceType, str]:
    """Determine source type and resolved value."""
    if not source:
        raise ValueError("Source is required")
    if source in BUILTIN_SKILLS:
        return SourceType.BUILTIN, source
    if source.startswith("https://github.com/"):
        return SourceType.GITHUB, source

    # Check local path first (priority over GitHub shorthand)
    candidate = Path(source).expanduser().resolve()
    if candidate.exists():
        if candidate.is_dir():
            return SourceType.LOCAL, str(candidate)
        if candidate.is_file() and candidate.suffix.lower() == ".zip":
            return SourceType.ZIP, str(candidate)
        raise ValueError(f"Source is not a directory or zip file: {candidate}")

    # GitHub shorthand: owner/repo (only if not a local path)
    parsed = parse_github_shorthand(source)
    if parsed:
        owner, repo = parsed
        return SourceType.GITHUB, f"https://github.com/{owner}/{repo}"

    raise ValueError(f"Source not found: {source}")


def _load_skill_info(skill_dir: Path) -> SkillInfo:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found in {skill_dir}")
    meta, _ = parse_frontmatter(skill_md)
    if not isinstance(meta, dict):
        raise ValueError(f"Invalid SKILL.md in {skill_dir}: frontmatter must be a mapping")
    name = meta.get("name") or ""
    return SkillInfo(name=name, source_path=skill_dir)


def detect_skills(path: Path) -> list[SkillInfo]:
    """Detect skills under the given path (root or one-level children)."""
    if not path.exists():
        raise FileNotFoundError(f"Source not found: {path}")
    if not path.is_dir():
        raise ValueError(f"Source must be a directory: {path}")

    skills: list[SkillInfo] = []
    root_skill = path / "SKILL.md"
    if root_skill.exists():
        skills.append(_load_skill_info(path))
        return skills

    for child in sorted(path.iterdir()):
        if child.is_dir() and (child / "SKILL.md").exists():
            skills.append(_load_skill_info(child))
    return skills


def _ensure_frontmatter_name(raw_content: str, target_name: str) -> str:
    """Rewrite frontmatter.name to match target directory for lint compliance."""
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


def _fail_on_symlinks(path: Path) -> None:
    for root, dirs, files in os.walk(path):
        for entry in dirs + files:
            candidate = Path(root) / entry
            if candidate.is_symlink():
                raise ValueError(f"Symlinks are not allowed in skills: {candidate}")


def _copy_skill_dir(source: Path, dest: Path) -> None:
    _fail_on_symlinks(source)

    def _ignore(_src, names):
        return {n for n in names if n in EXCLUDE_NAMES or n.startswith(".")}

    shutil.copytree(source, dest, dirs_exist_ok=False, ignore=_ignore)


def _validate_skill_file(skill_dir: Path) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found: {skill_dir}")
    meta, body = parse_frontmatter(skill_md)
    if not isinstance(meta, dict):
        raise ValueError(f"Invalid SKILL.md in {skill_dir}: frontmatter must be a mapping")

    name = meta.get("name")
    description = meta.get("description", "")

    # Spec: frontmatter.name/description are必須
    if not name or not str(name).strip():
        raise ValueError(f"Invalid SKILL.md in {skill_dir}: frontmatter.name is required")
    if not description or not str(description).strip():
        raise ValueError(f"Invalid SKILL.md in {skill_dir}: frontmatter.description is required")

    name = str(name).strip()
    description = str(description)
    lines = body.count("\n") + (1 if body and not body.endswith("\n") else 0)

    # Spec: frontmatter.name/description are必須
    if "name" not in meta or not str(meta.get("name", "")).strip():
        raise ValueError(f"Invalid SKILL.md in {skill_dir}: frontmatter.name is required")
    if "description" not in meta or not str(meta.get("description", "")).strip():
        raise ValueError(f"Invalid SKILL.md in {skill_dir}: frontmatter.description is required")

    issues = validate_skill_record(
        {
            "name": name,
            "description": description,
            "lines": lines,
            "path": str(skill_dir),
        },
        strict=True,
        meta=meta,
    )
    # strict=True returns only fatal issues
    if issues:
        raise ValueError("; ".join([i.message for i in issues]))
    # Warnings printed but non-fatal
    for issue in issues:
        if issue.severity != "fatal":
            print(f"[WARN] {skill_dir}: {issue.message}", file=sys.stderr)

    if name != skill_dir.name:
        raise ValueError(
            f"Invalid SKILL.md in {skill_dir}: name '{name}' must match directory '{skill_dir.name}'"
        )


def add_builtin(name: str, *, config: Config, force: bool) -> AddResult:
    if name not in BUILTIN_SKILLS:
        raise ValueError(f"Unknown built-in skill: {name}")

    dest_root = config.skills_dir
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / name
    if dest.exists():
        if not force:
            return AddResult(
                success=False,
                skill_id=name,
                message=f"Skill '{name}' exists. Use --force to overwrite.",
                skipped=[name],
            )
        shutil.rmtree(dest)

    dest.mkdir(parents=True, exist_ok=True)
    content = _ensure_frontmatter_name(BUILTIN_SKILLS[name], name)
    (dest / "SKILL.md").write_text(content, encoding="utf-8")
    return AddResult(
        success=True,
        skill_id=name,
        message=f"Added '{name}' to {dest_root}",
        added=[name],
    )


def add_local(
    source_path: Path,
    skills: list[SkillInfo],
    *,
    config: Config,
    keep_structure: bool,
    force: bool,
    namespace_override: str | None = None,
    rename_single_to: str | None = None,
) -> list[AddResult]:
    target_root = config.skills_dir
    target_root.mkdir(parents=True, exist_ok=True)

    results: list[AddResult] = []
    namespace = namespace_override or source_path.name
    seen_ids: set[str] = set()

    for skill in skills:
        try:
            _validate_skill_file(skill.source_path)
        except Exception as exc:
            results.append(
                AddResult(
                    success=False,
                    skill_id=skill.name,
                    message=str(exc),
                )
            )
            continue

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
                results.append(
                    AddResult(
                        success=False,
                        skill_id=skill_id,
                        message=f"Skill '{skill_id}' exists.",
                    )
                )
                continue
            shutil.rmtree(dest)

        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            _copy_skill_dir(skill.source_path, dest)
            if rename_single_to and len(skills) == 1:
                skill_md_path = dest / "SKILL.md"
                raw = skill_md_path.read_text(encoding="utf-8")
                skill_md_path.write_text(
                    _ensure_frontmatter_name(raw, skill_name), encoding="utf-8"
                )
            results.append(
                AddResult(success=True, skill_id=skill_id, message=f"Added '{skill_id}'")
            )
        except Exception as exc:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            results.append(
                AddResult(
                    success=False,
                    skill_id=skill_id,
                    message=f"Failed to add '{skill_id}': {exc}",
                )
            )

    return results


def remove_skill(skill_id: str, *, config: Config) -> RemoveResult:
    dest = config.skills_dir / skill_id
    resolve_inside(config.skills_dir, skill_id)  # traversal guard
    if not dest.exists():
        return RemoveResult(
            success=False, skill_id=skill_id, message=f"Skill not found: {skill_id}"
        )
    if not dest.is_dir():
        return RemoveResult(success=False, skill_id=skill_id, message=f"Not a directory: {dest}")
    shutil.rmtree(dest)
    return RemoveResult(success=True, skill_id=skill_id, message=f"Removed '{skill_id}'")
