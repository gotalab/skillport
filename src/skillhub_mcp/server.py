import sys
import os
from typing import Dict, List, Any
from fastmcp import FastMCP
from .db import SkillDB
from .tools.discovery import DiscoveryTools
from .tools.loading import LoadingTools
from .tools.execution import ExecutionTools

# CLI flags (Phase 5: simplified - removed --setup-list, --setup-auto)
KNOWN_FLAGS = {"--reindex", "--skip-auto-reindex"}


def _parse_flags() -> Dict[str, bool]:
    """Parse CLI flags and return a dict of flag states."""
    argv = sys.argv[1:]
    flags = {
        "force_reindex": "--reindex" in argv,
        "skip_auto": ("--skip-auto-reindex" in argv) or (os.getenv("SKILLHUB_SKIP_AUTO_REINDEX") == "1"),
    }
    # strip known flags so FastMCP doesn't see them
    sys.argv = [sys.argv[0]] + [a for a in argv if a not in KNOWN_FLAGS]
    return flags


def _report_skill_status(db: SkillDB) -> None:
    """Report the status of all skills at startup (simplified for Phase 5).

    Phase 5: Removed ready/not-ready checks. Simply lists indexed skills.
    """
    try:
        all_skills = db.list_all_skills(limit=1000)
        if not all_skills:
            print("[INFO] No skills found.", file=sys.stderr)
            return

        skill_count = len(all_skills)
        print(f"[INFO] {skill_count} skill(s) indexed:", file=sys.stderr)
        for skill in all_skills[:10]:  # Show first 10
            name = skill.get("name", "unknown")
            print(f"  - {name}", file=sys.stderr)
        if skill_count > 10:
            print(f"  ... and {skill_count - 10} more", file=sys.stderr)

    except Exception as e:
        print(f"[WARN] Failed to report skill status: {e}", file=sys.stderr)


def create_server() -> FastMCP:
    flags = _parse_flags()

    # Instantiate DB explicitly so lifecycle is tied to the server instance.
    db = SkillDB()

    # Decide on index refresh
    reindex_decision = db.should_reindex(force=flags["force_reindex"], skip_auto=flags["skip_auto"])
    if reindex_decision["need"]:
        print(f"[INFO] Reindexing skills (reason={reindex_decision['reason']})", file=sys.stderr)
        try:
            db.initialize_index()
            db.persist_state(reindex_decision["state"])
        except Exception as e:
            print(f"Warning: Failed to initialize index: {e}", file=sys.stderr)
    else:
        print(f"[INFO] Skipping reindex (reason={reindex_decision['reason']})", file=sys.stderr)

    # Report skill status at startup
    _report_skill_status(db)

    # Generate Instructions for AI agents
    core_skills = db.get_core_skills()

    instructions = """SkillHub provides reusable Agent Skills that load progressively to save context.

Workflow: search_skills → load_skill → execute in your terminal

When instructions say "run script.py", use the path from load_skill: `python {path}/script.py`
"""
    if core_skills:
        instructions += "\nPre-loaded skills (always available):\n"
        for skill in core_skills:
            instructions += f"- {skill['name']}: {skill['description']}\n"

    print(f"[DEBUG] Server Instructions:\n{instructions}", file=sys.stderr)

    # Create MCP Server
    mcp = FastMCP("skillhub-mcp", version="0.0.0", instructions=instructions)

    # Register Tools (methods preserve __name__/__doc__)
    discovery_tools = DiscoveryTools(db)
    loading_tools = LoadingTools(db)
    execution_tools = ExecutionTools(db)

    mcp.tool()(discovery_tools.search_skills)
    mcp.tool()(loading_tools.load_skill)
    mcp.tool()(execution_tools.read_skill_file)
    # This tool is not recommended for coding agents as it requires a terminal.
    # mcp.tool()(execution_tools.run_skill_command)
    
    return mcp

def main():
    mcp = create_server()
    mcp.run()

if __name__ == "__main__":
    main()
