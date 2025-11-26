"""CLI-only modes for SkillHub (lint, list, add, remove).

This module handles CLI flags and standalone commands that don't start the server.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

from .db import SkillDB
from .validation import (
    TROPHY_ART,
    validate_skill,
)
from .config import settings
from .skill_manager import (
    SourceType,
    SkillInfo,
    AddResult,
    resolve_source,
    detect_skills,
    add_builtin,
    add_local,
    remove_skill,
    fetch_github_source,
    parse_github_url,
)

# CLI flags (server options only)
KNOWN_FLAGS = {"--reindex", "--skip-auto-reindex"}


def parse_flags() -> Dict[str, Any]:
    """Parse CLI flags and return a dict of flag states."""
    argv = sys.argv[1:]

    flags = {
        "force_reindex": "--reindex" in argv,
        "skip_auto": ("--skip-auto-reindex" in argv) or (os.getenv("SKILLHUB_SKIP_AUTO_REINDEX") == "1"),
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
        all_skills = [
            s
            for s in all_skills
            if s.get("name") == skill_name or s.get("id") == skill_name
        ]
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


def run_list(db: SkillDB, skills: List[Dict[str, Any]] | None = None) -> int:
    """List all skills without starting the server. Returns exit code."""
    all_skills = skills if skills is not None else db.list_all_skills(limit=1000)
    if not all_skills:
        print("No skills found.")
        return 1

    # Sort by id for stability
    all_skills.sort(key=lambda s: s.get("id", ""))

    # Group by namespace (prefix before /)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    flat: List[Dict[str, Any]] = []

    for skill in all_skills:
        skill_id = skill.get("id", "")
        if "/" in skill_id:
            ns = skill_id.rsplit("/", 1)[0]
            grouped.setdefault(ns, []).append(skill)
        else:
            flat.append(skill)

    print(f"{'─' * 50}")
    print(f" {len(all_skills)} skill(s)")
    print(f"{'─' * 50}\n")

    # Print flat skills first
    for skill in flat:
        skill_id = skill.get("id", "")
        category = skill.get("category", "") or ""
        cat_display = f"[{category}]" if category else ""
        print(f"  {skill_id:<30} {cat_display}")

    # Print grouped skills with tree structure
    namespaces = sorted(grouped.keys())
    for ns in namespaces:
        print(f"  {ns}/")
        ns_skills = grouped[ns]
        for i, skill in enumerate(ns_skills):
            skill_id = skill.get("id", "")
            name = skill_id.rsplit("/", 1)[-1]  # leaf name
            category = skill.get("category", "") or ""
            cat_display = f"[{category}]" if category else ""
            is_last = i == len(ns_skills) - 1
            branch = "└─" if is_last else "├─"
            print(f"    {branch} {name:<26} {cat_display}")

    print(f"\n{'─' * 50}")
    return 0


def handle_cli_mode() -> bool:
    """Handle CLI-only modes (lint, list, add, remove).

    Returns True if a CLI mode was handled (and program should exit),
    False if normal server startup should proceed.
    """
    argv = sys.argv[1:]

    if argv:
        if argv[0] == "add":
            exit_code = run_add_cli(argv[1:])
            sys.exit(exit_code)
        if argv[0] == "remove":
            exit_code = run_remove_cli(argv[1:])
            sys.exit(exit_code)
        if argv[0] == "list":
            exit_code = run_list_cli(argv[1:])
            sys.exit(exit_code)
        if argv[0] == "lint":
            exit_code = run_lint_cli(argv[1:])
            sys.exit(exit_code)

    return False


# =============================================================================
# add / remove / list commands
# =============================================================================
def _settings_with_dir(dir_arg: str | None):
    if dir_arg is None:
        return settings
    return settings.model_copy(update={"skills_dir": Path(dir_arg).expanduser().resolve()})


def _print_add_results(results: List[AddResult]) -> bool:
    ok = True
    for res in results:
        mark = "✓" if res.success else "⚠"
        print(f"{mark} {res.message}")
        ok = ok and res.success
    return ok


def _prompt_structure_choice(skills: List[SkillInfo], source_name: str):
    """Multiple skills detected -> ask structure.

    Returns:
      False -> flat
      True -> keep_structure with source_name
      ("custom", namespace) -> keep_structure with custom namespace
      None -> cancel
    """
    print(f"\nFound {len(skills)} skills:")
    for s in skills:
        print(f"  - {s.name}")

    print("\nHow to add?")
    print(f"  [1] Flat    → skills/{skills[0].name}/, ...")
    print(f"  [2] Grouped → skills/{source_name}/{skills[0].name}/, ...")
    print(f"  [3] Custom Group → skills/<namespace>/{skills[0].name}/, ...")
    print("  [0] Cancel")

    while True:
        choice = input("\nChoice [1]: ").strip() or "1"
        if choice == "0":
            return None      # Cancel
        if choice == "1":
            return False     # flat
        if choice == "2":
            return True      # keep_structure
        if choice == "3":
            ns = input("Enter namespace (no slashes, e.g., my-collection): ").strip()
            if not ns or "/" in ns or ".." in ns:
                print("Invalid namespace. Use a single segment without '/'.")
                continue
            return ("custom", ns)
        print("Invalid choice. Enter 0, 1, 2, or 3.")


def run_add_cli(argv: List[str]) -> int:
    """Add skills from built-ins or local paths."""
    parser = argparse.ArgumentParser(prog="skillhub add", add_help=True)
    parser.add_argument("source", help="Built-in skill name, local path, or GitHub URL")
    parser.add_argument("--dir", dest="target_dir", help="Install destination (default: SKILLS_DIR)")
    parser.add_argument("--force", action="store_true", help="Overwrite without confirmation")
    parser.add_argument("--name", dest="name_override", help="Override skill name (single skill only)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--flat", dest="keep_structure", action="store_false", help="Flatten when multiple skills")
    group.add_argument(
        "--keep-structure",
        dest="keep_structure",
        action="store_true",
        help="Preserve directory structure when multiple skills",
    )
    parser.add_argument("--namespace", dest="namespace_override", help="Custom namespace when keeping structure")
    parser.set_defaults(keep_structure=None)

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code

    try:
        source_type, resolved = resolve_source(args.source)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    target_dir = Path(args.target_dir).expanduser().resolve() if args.target_dir else settings.get_effective_skills_dir()

    temp_dir_to_cleanup = None
    origin_payload = None

    if source_type == SourceType.GITHUB:
        try:
            parsed_url = parse_github_url(resolved)
            temp_dir = fetch_github_source(resolved)
        except Exception as e:
            print(f"Error: {e}")
            return 1
        source_path = Path(temp_dir)
        source_label = Path(parsed_url.normalized_path).name or parsed_url.repo
        temp_dir_to_cleanup = source_path
        origin_payload = {
            "source": resolved,
            "kind": "github",
            "ref": parsed_url.ref,
            "path": parsed_url.normalized_path,
        }
    else:
        source_path = Path(resolved)
        source_label = source_path.name
        origin_payload = {
            "source": str(source_path),
            "kind": "local",
        }

    if source_type == SourceType.BUILTIN:
        try:
            force_flag = args.force
            dest = target_dir / resolved
            if dest.exists() and not force_flag:
                answer = input(f"Skill '{resolved}' already exists. Overwrite? [y/N] ").strip().lower()
                if answer not in {"y", "yes"}:
                    print("Aborted.")
                    return 1
                force_flag = True
            result = add_builtin(resolved, target_dir, force_flag)
            print(result.message)
            if result.success:
                from .skill_manager import record_origin

                record_origin(result.skill_id, {"source": "builtin", "kind": "builtin"})
            return 0 if result.success else 1
        except Exception as e:
            print(f"Error: {e}")
            return 1

    try:
        skills = detect_skills(source_path)
    except Exception as e:
        print(f"Error: {e}")
        return 1

    if not skills:
        print(f"Error: No skills found in {source_path}")
        return 1

    keep_structure = args.keep_structure
    namespace_override = args.namespace_override
    name_override = args.name_override
    if len(skills) == 1:
        keep_structure = False if keep_structure is None else keep_structure
    else:
        if keep_structure is None:
            choice = _prompt_structure_choice(skills, source_label if isinstance(source_label, str) else source_path.name)
            if choice is None:
                print("Cancelled.")
                return 1
            if choice is True or choice is False:
                keep_structure = choice
            elif isinstance(choice, tuple) and choice[0] == "custom":
                keep_structure = True
                namespace_override = choice[1]
    if name_override and len(skills) != 1:
        print("--name can only be used when a single skill is detected.")
        return 1
    if name_override and ("/" in name_override or ".." in name_override):
        print("Invalid --name value. Use a single segment without '/'.")
        return 1

    # Prompt before destructive overwrite if needed
    conflicts: List[str] = []
    for skill in skills:
        namespace = namespace_override or source_label
        skill_id = skill.name if not keep_structure else f"{namespace}/{skill.name}"
        if (target_dir / skill_id).exists():
            conflicts.append(skill_id)

    force_flag = args.force
    if conflicts and not force_flag:
        listed = ", ".join(conflicts)
        answer = input(f"Skill(s) {listed} already exist. Overwrite? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Aborted.")
            return 1
        force_flag = True

    try:
        results = add_local(
            source_path,
            skills,
            target_dir=target_dir,
            keep_structure=bool(keep_structure),
            force=force_flag,
            namespace_override=namespace_override,
            rename_single_to=name_override,
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1

    ok = _print_add_results(results)

    if ok and origin_payload:
        from .skill_manager import record_origin

        for res in results:
            if res.success:
                record_origin(res.skill_id, origin_payload)

    if temp_dir_to_cleanup:
        import shutil

        try:
            shutil.rmtree(temp_dir_to_cleanup, ignore_errors=True)
        except Exception:
            pass

    return 0 if ok else 1


def run_remove_cli(argv: List[str]) -> int:
    """Remove a skill by id."""
    parser = argparse.ArgumentParser(prog="skillhub remove", add_help=True)
    parser.add_argument("skill_id", help="Skill id (e.g., hello-world or group/skill)")
    parser.add_argument("--dir", dest="target_dir", help="Skills directory (default: SKILLS_DIR)")
    parser.add_argument("--force", action="store_true", help="Delete without confirmation")

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code

    target_dir = Path(args.target_dir).expanduser().resolve() if args.target_dir else settings.get_effective_skills_dir()

    if not target_dir.exists():
        print(f"Skills directory not found: {target_dir}")
        return 1

    if not args.force:
        confirm = input(f"Remove '{args.skill_id}'? [y/N] ").strip().lower()
        if confirm not in {"y", "yes"}:
            print("Aborted.")
            return 1

    try:
        result = remove_skill(args.skill_id, target_dir)
    except Exception as e:
        print(f"Error: {e}")
        return 1

    print(result.message)
    if result.success:
        from .skill_manager import remove_origin

        remove_origin(args.skill_id)
    return 0 if result.success else 1


def run_list_cli(argv: List[str]) -> int:
    """List installed skills (optionally as JSON)."""
    parser = argparse.ArgumentParser(prog="skillhub list", add_help=True)
    parser.add_argument("--dir", dest="target_dir", help="Skills directory (default: SKILLS_DIR)")
    parser.add_argument("--category", dest="category", help="Filter by category")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Output JSON")
    parser.add_argument("--id-prefix", dest="id_prefix", help="Filter by skill id prefix (e.g., group/)")
    parser.add_argument("--name", dest="name_filter", help="Filter by exact skill name")

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code

    cfg = _settings_with_dir(args.target_dir)
    db = SkillDB(settings_override=cfg)
    _ensure_index(db)
    skills = db.list_all_skills(limit=1000)

    if args.category:
        cat_norm = " ".join(args.category.strip().split()).lower()
        skills = [s for s in skills if (s.get("category") or "").lower() == cat_norm]
    if args.id_prefix:
        prefix = args.id_prefix
        skills = [s for s in skills if str(s.get("id", "")).startswith(prefix)]
    if args.name_filter:
        skills = [s for s in skills if s.get("name") == args.name_filter]

    if args.as_json:
        import json

        print(json.dumps(skills, ensure_ascii=False, indent=2))
        return 0 if skills else 1

    return run_list(db, skills=skills)


def run_lint_cli(argv: List[str]) -> int:
    """Validate skills (lint check)."""
    parser = argparse.ArgumentParser(prog="skillhub lint", add_help=True)
    parser.add_argument("skill_id", nargs="?", help="Skill id to lint (e.g., hello-world or group/skill). Lints all if omitted")
    parser.add_argument("--dir", dest="target_dir", help="Skills directory (default: SKILLS_DIR)")

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code

    cfg = _settings_with_dir(args.target_dir)
    db = SkillDB(settings_override=cfg)
    _ensure_index(db)
    return run_lint(db, args.skill_id)
