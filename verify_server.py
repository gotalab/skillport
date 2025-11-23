import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure environment for the server
server_env = os.environ.copy()
server_env["SKILLS_DIR"] = os.path.abspath(".agent/skills")
server_env["EMBEDDING_PROVIDER"] = "none"
server_env["LOG_LEVEL"] = "ERROR" # Reduce noise

# Define server parameters
server_params = StdioServerParameters(
    command="uv",
    args=["run", "skillhub-mcp"],
    env=server_env
)

async def run_test():
    print("Starting SkillHub MCP Client Verification...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Initialize
            await session.initialize()
            print("✅ MCP Initialized")

            # 2. List Tools
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"✅ Found Tools: {tool_names}")
            
            expected_tools = ["search_skills", "load_skill", "read_file", "execute_skill_command"]
            if not all(t in tool_names for t in expected_tools):
                print(f"❌ Missing tools! Expected {expected_tools}")
                return

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
                load_result = await session.call_tool("load_skill", arguments={"skill_name": "hello-world"})
                print(f"Load Result: {load_result.content[0].text[:50]}...") # Show first 50 chars
            except Exception as e:
                print(f"❌ load_skill failed: {e}")

            # 5. Test read_file
            print("\n--- Testing read_file ---")
            try:
                read_result = await session.call_tool("read_file", arguments={"skill_name": "hello-world", "file_path": "hello.py"})
                print(f"Read Result: {read_result.content[0].text}")
            except Exception as e:
                print(f"❌ read_file failed: {e}")

            # 6. Test execute_skill_command (python hello.py)
            print("\n--- Testing execute_skill_command ---")
            try:
                exec_result = await session.call_tool("execute_skill_command", arguments={
                    "skill_name": "hello-world", 
                    "command": "python", 
                    "args": ["hello.py"]
                })
                print(f"Exec Result: {exec_result.content[0].text}")
            except Exception as e:
                print(f"❌ execute_skill_command failed: {e}")

            print("\n✅ Verification Complete!")

if __name__ == "__main__":
    asyncio.run(run_test())
