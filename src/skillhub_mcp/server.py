import sys
from fastmcp import FastMCP
from .db import db
from .tools import discovery, loading, execution

def create_server() -> FastMCP:
    # Initialize DB Index
    try:
        db.initialize_index()
    except Exception as e:
        print(f"Warning: Failed to initialize index: {e}", file=sys.stderr)

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

    # Register Tools
    mcp.tool()(discovery.search_skills)
    mcp.tool()(loading.load_skill)
    mcp.tool()(execution.read_file)
    mcp.tool()(execution.execute_skill_command)
    
    return mcp

def main():
    mcp = create_server()
    mcp.run()

if __name__ == "__main__":
    main()
