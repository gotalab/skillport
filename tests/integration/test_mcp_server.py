"""Integration tests for MCP Server using FastMCP Client.

Tests both Local (stdio) and Remote (HTTP) modes using in-memory transport.
Note: These are integration tests, not E2E tests, as they bypass the network layer.
"""

import base64
from pathlib import Path

import pytest
from fastmcp.client import Client

from skillsouko.interfaces.mcp.server import create_mcp_server
from skillsouko.modules.indexing import build_index
from skillsouko.shared.config import Config


def _create_test_skill(skills_dir: Path, skill_id: str, content: str = "Test content") -> None:
    """Create a minimal test skill."""
    skill_dir = skills_dir / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"""---
name: {skill_id}
description: Test skill {skill_id}
metadata:
  skillsouko:
    category: test
    tags: [test]
---
# {skill_id}

{content}
""",
        encoding="utf-8",
    )


def _create_test_config(tmp_path: Path) -> Config:
    """Create a test config with temporary directories."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True)
    return Config(
        skills_dir=skills_dir,
        db_path=tmp_path / "db.lancedb",
        embedding_provider="none",
    )


@pytest.fixture
def test_config(tmp_path: Path) -> Config:
    """Create test config with a sample skill."""
    config = _create_test_config(tmp_path)
    _create_test_skill(config.skills_dir, "test-skill", "Hello from test skill")
    build_index(config=config, force=True)
    return config


@pytest.fixture
async def local_client(test_config: Config):
    """FastMCP Client for Local mode (stdio)."""
    mcp = create_mcp_server(config=test_config, is_remote=False)
    async with Client(transport=mcp) as client:
        yield client


@pytest.fixture
async def remote_client(test_config: Config):
    """FastMCP Client for Remote mode (HTTP)."""
    mcp = create_mcp_server(config=test_config, is_remote=True)
    async with Client(transport=mcp) as client:
        yield client


class TestLocalMode:
    """Tests for Local mode (stdio transport)."""

    async def test_list_tools_returns_two_tools(self, local_client: Client):
        """Local mode should have exactly 2 tools."""
        tools = await local_client.list_tools()
        tool_names = [t.name for t in tools]
        assert sorted(tool_names) == ["load_skill", "search_skills"]
        assert "read_skill_file" not in tool_names

    async def test_search_skills_returns_results(self, local_client: Client):
        """search_skills should find indexed skills."""
        result = await local_client.call_tool("search_skills", {"query": "test"})
        assert result.data is not None
        assert "skills" in result.data
        assert len(result.data["skills"]) > 0

    async def test_search_skills_empty_query_lists_all(self, local_client: Client):
        """Empty query should list all skills."""
        result = await local_client.call_tool("search_skills", {"query": ""})
        assert result.data is not None
        assert "skills" in result.data
        assert result.data["total"] >= 1

    async def test_load_skill_returns_details(self, local_client: Client):
        """load_skill should return skill details with path."""
        result = await local_client.call_tool("load_skill", {"skill_id": "test-skill"})
        assert result.data is not None
        assert result.data["id"] == "test-skill"
        assert "instructions" in result.data
        assert "path" in result.data
        assert Path(result.data["path"]).exists()


class TestRemoteMode:
    """Tests for Remote mode (HTTP transport)."""

    async def test_list_tools_returns_three_tools(self, remote_client: Client):
        """Remote mode should have 3 tools including read_skill_file."""
        tools = await remote_client.list_tools()
        tool_names = [t.name for t in tools]
        assert sorted(tool_names) == ["load_skill", "read_skill_file", "search_skills"]

    async def test_search_skills_works(self, remote_client: Client):
        """search_skills should work in Remote mode."""
        result = await remote_client.call_tool("search_skills", {"query": "test"})
        assert result.data is not None
        assert "skills" in result.data

    async def test_load_skill_works(self, remote_client: Client):
        """load_skill should work in Remote mode."""
        result = await remote_client.call_tool("load_skill", {"skill_id": "test-skill"})
        assert result.data is not None
        assert result.data["id"] == "test-skill"

    async def test_read_skill_file_text(self, remote_client: Client, test_config: Config):
        """read_skill_file should return UTF-8 text content."""
        # Create a text file in the skill directory
        skill_dir = test_config.skills_dir / "test-skill"
        (skill_dir / "readme.txt").write_text("Hello, World!", encoding="utf-8")

        result = await remote_client.call_tool(
            "read_skill_file",
            {"skill_id": "test-skill", "file_path": "readme.txt"},
        )
        assert result.data is not None
        assert result.data["content"] == "Hello, World!"
        assert result.data["encoding"] == "utf-8"
        assert "text" in result.data["mime_type"]

    async def test_read_skill_file_binary(self, remote_client: Client, test_config: Config):
        """read_skill_file should return base64-encoded binary content."""
        # Create a binary file in the skill directory
        skill_dir = test_config.skills_dir / "test-skill"
        binary_data = bytes([0x89, 0x50, 0x4E, 0x47])  # PNG header
        (skill_dir / "image.png").write_bytes(binary_data)

        result = await remote_client.call_tool(
            "read_skill_file",
            {"skill_id": "test-skill", "file_path": "image.png"},
        )
        assert result.data is not None
        assert result.data["encoding"] == "base64"
        assert result.data["mime_type"] == "image/png"
        decoded = base64.b64decode(result.data["content"])
        assert decoded == binary_data

    async def test_read_skill_file_path_traversal_blocked(self, remote_client: Client):
        """read_skill_file should block path traversal attempts."""
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="Path traversal"):
            await remote_client.call_tool(
                "read_skill_file",
                {"skill_id": "test-skill", "file_path": "../escape.txt"},
            )


class TestInstructions:
    """Tests for dynamic instructions generation."""

    async def test_local_mode_instructions_mention_read_tool(self, local_client: Client):
        """Local mode instructions should mention using native Read tool."""
        # Get server info which includes instructions
        # Note: FastMCP Client may not expose instructions directly,
        # so we test via the server creation
        from skillsouko.interfaces.mcp.instructions import build_xml_instructions
        from skillsouko.shared.config import Config

        config = Config(core_skills_mode="none")
        instructions = build_xml_instructions(config, ["search_skills", "load_skill"])
        assert "Read tool" in instructions or "Read" in instructions
        # Should NOT have read_skill_file in tools section
        assert "read_skill_file" not in instructions.split("## Tips")[0]

    async def test_remote_mode_instructions_mention_read_skill_file(self, remote_client: Client):
        """Remote mode instructions should mention read_skill_file."""
        from skillsouko.interfaces.mcp.instructions import build_xml_instructions
        from skillsouko.shared.config import Config

        config = Config(core_skills_mode="none")
        instructions = build_xml_instructions(
            config, ["search_skills", "load_skill", "read_skill_file"]
        )
        assert "read_skill_file" in instructions
        assert "base64" in instructions or "encoding" in instructions
