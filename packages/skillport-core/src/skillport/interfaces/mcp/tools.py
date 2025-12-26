from typing import Any

from fastmcp import FastMCP

from skillport.modules.skills import load_skill, read_skill_file, search_skills
from skillport.shared.config import Config


def register_tools(mcp: FastMCP, config: Config, *, is_remote: bool = False) -> list[str]:
    """Register MCP tools based on transport mode.

    Args:
        mcp: FastMCP server instance.
        config: Application configuration.
        is_remote: True for HTTP transport (Remote mode), False for stdio (Local mode).
            Remote mode enables read_skill_file tool for agents without file access.

    Returns:
        List of registered tool names.
    """
    registered: list[str] = []

    @mcp.tool(name="search_skills")
    def search_skills_tool(query: str) -> dict[str, Any]:
        """Find skills relevant to a task description.

        Use this to discover skills. If you already have a skill_id, skip to load_skill.
        If too many results, refine your query with more specific terms instead of loading more.

        Args:
            query: Natural-language task (e.g., "extract PDF text"). Use "" or "*" to list all.

        Returns:
            skills: Top matches as {id, description, score}. Higher score = better match.
            total: Total matching skills. If high, use a more specific query.
        """
        result = search_skills(query, limit=config.search_limit, config=config)
        skills_list = []
        for s in result.skills:
            item: dict[str, Any] = {
                "id": s.id,
                "description": s.description,
                "score": s.score,
            }
            # Only include name if it differs from id
            if s.name != s.id:
                item["name"] = s.name
            skills_list.append(item)
        return {"skills": skills_list, "total": result.total}

    registered.append("search_skills")

    @mcp.tool(name="load_skill")
    def load_skill_tool(skill_id: str) -> dict[str, Any]:
        """Load a skill's instructions and absolute filesystem path.

        Call this after selecting an id from search_skills. The returned `path` is
        required for executing scripts (e.g., `python {path}/script.py`).

        Args:
            skill_id: Skill identifier (e.g., "hello-world" or "namespace/skill").

        Returns:
            id, name, description, instructions, path (absolute directory).
        """
        detail = load_skill(skill_id, config=config)
        return {
            "id": detail.id,
            "name": detail.name,
            "description": detail.description,
            "instructions": detail.instructions,
            "path": detail.path,
        }

    registered.append("load_skill")

    # Remote mode only: read_skill_file (for agents without direct file access)
    if is_remote:

        @mcp.tool(name="read_skill_file")
        def read_skill_file_tool(skill_id: str, file_path: str) -> dict[str, Any]:
            """Read a file inside a skill directory.

            Handles both text and binary files:
            - Text: encoding="utf-8", content is plain text
            - Binary: encoding="base64", content is base64-encoded

            The mime_type field indicates the file type (e.g., "image/png", "application/pdf").

            Args:
                skill_id: Skill identifier from load_skill.
                file_path: Relative path (e.g., "templates/config.yaml").

            Returns:
                content: File content (text or base64)
                path: Absolute path
                size: Size in bytes
                encoding: "utf-8" or "base64"
                mime_type: MIME type of the file
            """
            result = read_skill_file(skill_id, file_path, config=config)
            return {
                "content": result.content,
                "path": result.path,
                "size": result.size,
                "encoding": result.encoding,
                "mime_type": result.mime_type,
            }

        registered.append("read_skill_file")

    return registered


__all__ = ["register_tools"]
