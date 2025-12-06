"""Start MCP server command."""

import typer

from skillport.interfaces.mcp.server import run_server

from ..context import get_config
from ..theme import VERSION, stderr_console


def serve(
    ctx: typer.Context,
    http: bool = typer.Option(
        False,
        "--http",
        help="Run as HTTP server (enables read_skill_file tool)",
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="HTTP server host (only with --http)",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        help="HTTP server port (only with --http)",
    ),
    reindex: bool = typer.Option(
        False,
        "--reindex",
        help="Force reindex before starting server",
    ),
    skip_auto_reindex: bool = typer.Option(
        False,
        "--skip-auto-reindex",
        help="Skip automatic reindex check",
    ),
):
    """Start the MCP server for AI agent integration.

    By default, runs in stdio mode (Local) for direct agent integration.
    Use --http to run as HTTP server (Remote) for network access.
    """
    config = get_config(ctx)
    transport = "http" if http else "stdio"

    # Log startup info to stderr (stdout is reserved for MCP JSON-RPC)
    stderr_console.print(f"[dim]SkillPort MCP Server v{VERSION}[/dim]", highlight=False)
    stderr_console.print(f"[dim]Skills: {config.skills_dir}[/dim]", highlight=False)
    stderr_console.print(f"[dim]Index:  {config.db_path}[/dim]", highlight=False)
    stderr_console.print(f"[dim]Provider: {config.embedding_provider}[/dim]", highlight=False)
    stderr_console.print(f"[dim]Transport: {transport}[/dim]", highlight=False)

    if http:
        stderr_console.print(f"[dim]Endpoint: http://{host}:{port}/mcp[/dim]", highlight=False)

    if reindex:
        stderr_console.print("[dim]Mode: Force reindex[/dim]", highlight=False)
    elif skip_auto_reindex:
        stderr_console.print("[dim]Mode: Skip auto-reindex[/dim]", highlight=False)

    stderr_console.print("[dim]─" * 40 + "[/dim]", highlight=False)

    run_server(
        config=config,
        transport=transport,
        host=host,
        port=port,
        force_reindex=reindex,
        skip_auto_reindex=skip_auto_reindex,
    )
