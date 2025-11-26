"""SkillHub MCP Server.

This module handles server creation and the main entry point.
CLI modes (--lint, --list) are handled by cli.py.
Validation logic is in validation.py.
"""

import sys
from fastmcp import FastMCP
from .db import SkillDB
from .cli import parse_flags, handle_cli_mode
from .validation import SKILLHUB_BANNER, report_skill_status
from .tools.discovery import DiscoveryTools
from .tools.loading import LoadingTools
from .tools.execution import ExecutionTools


def create_server() -> FastMCP:
    """Create and configure the MCP server."""
    flags = parse_flags()

    # Show banner at startup
    print(SKILLHUB_BANNER, file=sys.stderr)

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
    report_skill_status(db)

    # Generate Instructions for AI agents
    core_skills = db.get_core_skills()

    instructions = """SkillHub provides reusable Agent Skills that load progressively to save context.

Workflow: search_skills → load_skill (by skill_id) → execute in your terminal

When instructions say "run script.py", use the path from load_skill: `python {path}/script.py`
"""
    if core_skills:
        instructions += "\nPre-loaded skills (always available):\n"
        for skill in core_skills:
            skill_id = skill.get("id", skill.get("name"))
            instructions += f"- {skill_id}: {skill['description']}\n"

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
    """Main entry point for SkillHub MCP."""
    # Handle CLI-only modes (--lint, --list)
    handle_cli_mode()

    # Normal server startup
    mcp = create_server()
    mcp.run()


if __name__ == "__main__":
    main()
