import sys
import os
from fastmcp import FastMCP
from .db import SkillDB
from .tools.discovery import DiscoveryTools
from .tools.loading import LoadingTools
from .tools.execution import ExecutionTools

def _parse_flags():
    argv = sys.argv[1:]
    force_reindex = "--reindex" in argv
    skip_auto = ("--skip-auto-reindex" in argv) or (os.getenv("SKILLHUB_SKIP_AUTO_REINDEX") == "1")
    # strip known flags so FastMCP doesn't see them
    sys.argv = [sys.argv[0]] + [a for a in argv if a not in {"--reindex", "--skip-auto-reindex"}]
    return force_reindex, skip_auto

def create_server() -> FastMCP:
    force_reindex, skip_auto_reindex = _parse_flags()

    # Instantiate DB explicitly so lifecycle is tied to the server instance.
    db = SkillDB()

    # Decide on index refresh
    reindex_decision = db.should_reindex(force=force_reindex, skip_auto=skip_auto_reindex)
    if reindex_decision["need"]:
        print(f"[INFO] Reindexing skills (reason={reindex_decision['reason']})", file=sys.stderr)
        try:
            db.initialize_index()
            db.persist_state(reindex_decision["state"])
        except Exception as e:
            print(f"Warning: Failed to initialize index: {e}", file=sys.stderr)
    else:
        print(f"[INFO] Skipping reindex (reason={reindex_decision['reason']})", file=sys.stderr)

    # Generate Instructions (concise, English, agent-skills aware)
    core_skills = db.get_core_skills()
    instructions = (
        "SkillHub MCP is an MCP server that exposes reusable Agent Skills.\n"
        "- What is a Skill: a folder with SKILL.md (name, description) plus step-by-step instructions and optional assets/scripts.\n"
        "- Why it matters: staged/just-in-time context loading keeps prompts small, improves grounding, and stays portable across MCP-capable tools.\n"
        "- How to use: `search_skills` to find skills, `load_skill` to read instructions, `read_file` to inspect files, `execute_skill_command` to run allowed commands.\n"
    )
    if core_skills:
        instructions += "Core skills preloaded:\n"
        for skill in core_skills:
            instructions += f"- {skill['name']}: {skill['description']}\n"
    else:
        instructions += "Use `search_skills` to discover available skills.\n"

    # Debug: Print instructions to stderr to verify
    print(f"[DEBUG] Generated Instructions:\n{instructions}", file=sys.stderr)

    # Create MCP Server
    mcp = FastMCP("skillhub-mcp", version="0.0.0", instructions=instructions)

    # Register Tools (methods preserve __name__/__doc__)
    discovery_tools = DiscoveryTools(db)
    loading_tools = LoadingTools(db)
    execution_tools = ExecutionTools(db)

    mcp.tool()(discovery_tools.search_skills)
    mcp.tool()(loading_tools.load_skill)
    mcp.tool()(execution_tools.read_file)
    mcp.tool()(execution_tools.execute_skill_command)
    
    return mcp

def main():
    mcp = create_server()
    mcp.run()

if __name__ == "__main__":
    main()
