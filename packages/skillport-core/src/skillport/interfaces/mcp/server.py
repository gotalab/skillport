import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Literal

from fastmcp import FastMCP

from skillport.interfaces.mcp.instructions import build_xml_instructions
from skillport.interfaces.mcp.tools import register_tools
from skillport.modules.indexing import build_index, should_reindex
from skillport.shared.config import Config

BANNER = r"""
░██████╗██╗░░██╗██╗██╗░░░░░██╗░░░░░██████╗░░█████╗░██████╗░████████╗
██╔════╝██║░██╔╝██║██║░░░░░██║░░░░░██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝
╚█████╗░█████═╝░██║██║░░░░░██║░░░░░██████╔╝██║░░██║██████╔╝░░░██║░░░
░╚═══██╗██╔═██╗░██║██║░░░░░██║░░░░░██╔═══╝░██║░░██║██╔══██╗░░░██║░░░
██████╔╝██║░╚██╗██║███████╗███████╗██║░░░░░╚█████╔╝██║░░██║░░░██║░░░
╚═════╝░╚═╝░░╚═╝╚═╝╚══════╝╚══════╝╚═╝░░░░░░╚════╝░╚═╝░░╚═╝░░░╚═╝░░░
"""


def _resolve_version() -> str:
    for dist in ("skillport-mcp", "skillport"):
        try:
            return version(dist)
        except PackageNotFoundError:
            continue
    return "0.0.0"


__version__ = _resolve_version()


def _get_registered_tools_list(is_remote: bool) -> list[str]:
    """Determine which tools will be registered based on transport mode.

    Args:
        is_remote: True for HTTP transport (Remote), False for stdio (Local).

    Returns:
        List of tool names that will be registered.
    """
    tools = ["search_skills", "load_skill"]
    if is_remote:
        tools.append("read_skill_file")
    return tools


def create_mcp_server(*, config: Config, is_remote: bool = False) -> FastMCP:
    """Create a configured FastMCP server instance.

    This factory function creates the server without starting it, enabling:
    - Unit/integration testing with fastmcp.Client(transport=mcp)
    - Reuse by run_server() for actual execution

    Args:
        config: Application configuration.
        is_remote: True for Remote mode (HTTP), False for Local mode (stdio).

    Returns:
        Configured FastMCP instance with tools registered.
    """
    registered_tools = _get_registered_tools_list(is_remote)
    instructions = build_xml_instructions(config, registered_tools)

    mcp = FastMCP("skillport", version=__version__, instructions=instructions)
    register_tools(mcp, config, is_remote=is_remote)

    return mcp


def run_server(
    *,
    config: Config,
    transport: Literal["stdio", "http"] = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
    force_reindex: bool = False,
    skip_auto_reindex: bool = False,
):
    """Run the MCP server.

    Args:
        config: Application configuration.
        transport: Transport protocol ("stdio" for local, "http" for remote).
        host: HTTP server host (only used with transport="http").
        port: HTTP server port (only used with transport="http").
        force_reindex: Force reindex before starting.
        skip_auto_reindex: Skip automatic reindex check.
    """
    print(BANNER, file=sys.stderr)

    decision = should_reindex(config=config)
    if force_reindex:
        print("[INFO] Reindexing (force)", file=sys.stderr)
        build_index(config=config, force=True)
    elif not skip_auto_reindex and decision.need:
        print(f"[INFO] Reindexing (reason={decision.reason})", file=sys.stderr)
        build_index(config=config, force=False)
    else:
        print(f"[INFO] Skipping reindex (reason={decision.reason})", file=sys.stderr)

    # Transport determines mode: HTTP = Remote, stdio = Local
    is_remote = transport == "http"
    mode = "Remote" if is_remote else "Local"

    print(f"[INFO] Mode: {mode} (transport: {transport})", file=sys.stderr)
    print(f"[INFO] Tools: {', '.join(_get_registered_tools_list(is_remote))}", file=sys.stderr)

    mcp = create_mcp_server(config=config, is_remote=is_remote)

    if transport == "http":
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    run_server(config=Config(), transport="stdio")
