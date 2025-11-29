import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure environment for the server
server_env = os.environ.copy()
server_env["SKILLSOUKO_SKILLS_DIR"] = os.path.abspath(".agent/skills")
server_env["SKILLSOUKO_EMBEDDING_PROVIDER"] = "none"
server_env["SKILLSOUKO_LOG_LEVEL"] = "ERROR"  # Reduce noise

# Define server parameters (stdio = Local mode)
# For Remote mode, use: skillsouko serve --http
server_params = StdioServerParameters(
    command="uv",
    args=["run", "skillsouko"],
    env=server_env
)

async def run_test():
    print("Starting SkillSouko MCP Client Verification (stdio/Local mode)...")
    print("Note: For HTTP/Remote mode, run: skillsouko serve --http")
    print()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Initialize
            await session.initialize()
            print("✅ MCP Initialized")

            # 2. List Tools
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"✅ Found Tools: {tool_names}")

            # In Local mode (stdio), only core tools are available
            # read_skill_file is only available in Remote mode (HTTP)
            expected_tools = ["search_skills", "load_skill"]
            missing = [t for t in expected_tools if t not in tool_names]
            if missing:
                print(f"❌ Missing core tools: {missing}")
                return

            # Verify we're in Local mode (no read_skill_file)
            if "read_skill_file" in tool_names:
                print("⚠️  Unexpected: read_skill_file available in stdio mode")
            else:
                print("✅ Mode: Local (stdio) - read_skill_file not available as expected")

            # 3. Test search_skills
            print("\n--- Testing search_skills ---")
            search_result = await session.call_tool("search_skills", arguments={"query": "hello"})
            # fastmcp returns list of content blocks.
            # The tool returns a dict, but via MCP protocol it comes wrapped in content.
            # Let's inspect the text content.
            print(f"Search Result: {search_result.content[0].text}")

            # 4. Test load_skill
            print("\n--- Testing load_skill ---")
            try:
                load_result = await session.call_tool("load_skill", arguments={"skill_id": "hello-world"})
                print(f"Load Result: {load_result.content[0].text[:50]}...") # Show first 50 chars
            except Exception as e:
                print(f"❌ load_skill failed: {e}")

            # 5. read_skill_file - only available in HTTP mode
            print("\n--- read_skill_file ---")
            print("ℹ️  Not available in Local mode (use --http for Remote mode)")

            # 6. Test run_skill_command - SKIPPED (disabled by default in Phase 5)
            # Agents should execute scripts directly using the path from load_skill
            print("\n--- Skipping run_skill_command (disabled by default) ---")

            print("\n✅ Verification Complete!")

if __name__ == "__main__":
    asyncio.run(run_test())
