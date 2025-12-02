import asyncio
import os
import tempfile
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure environment for the server
server_env = os.environ.copy()
server_env["SKILLPORT_SKILLS_DIR"] = os.path.abspath(".agent/skills")
server_env["SKILLPORT_EMBEDDING_PROVIDER"] = "none"
server_env["SKILLPORT_LOG_LEVEL"] = "ERROR"  # Reduce noise

async def run_test():
    # Use temp dirs for DB/meta to avoid polluting ~/.skillport
    with tempfile.TemporaryDirectory() as tmpdir:
        server_env["SKILLPORT_DB_PATH"] = os.path.join(tmpdir, "skills.lancedb")

        # Define server parameters (stdio = Local mode)
        # For Remote mode, use: skillport serve --http
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "skillport"],
            env=server_env
        )

        print("Starting SkillPort MCP Client Verification (stdio/Local mode)...")
        print("Note: For HTTP/Remote mode, run: skillport serve --http")
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
                print("\n--- Skipping run_skill_command (disabled by default) ---")

                print("\n✅ Verification Complete!")

if __name__ == "__main__":
    asyncio.run(run_test())
