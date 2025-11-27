"""Transitional entry point dispatching to CLI or MCP server."""

import sys

from skillpod.interfaces.cli.app import app
from skillpod.interfaces.mcp.server import run_server
from skillpod.shared.config import Config


def main():
    args = sys.argv[1:]
    # Legacy: no args → run MCP server (backward compat)
    # Note: `skillpod --reindex` is NOT supported; use `skillpod serve --reindex`
    if not args:
        config = Config()
        run_server(config=config)
    else:
        app()


if __name__ == "__main__":
    main()
