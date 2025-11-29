import sys

from fastmcp import FastMCP

from skillsouko.interfaces.mcp.instructions import build_xml_instructions
from skillsouko.interfaces.mcp.tools import register_tools
from skillsouko.modules.indexing import build_index, should_reindex
from skillsouko.shared.config import Config

BANNER = r"""
░██████╗██╗░░██╗██╗██╗░░░░░██╗░░░░░██████╗░░█████╗░██████╗░
██╔════╝██║░██╔╝██║██║░░░░░██║░░░░░██╔══██╗██╔══██╗██╔══██╗
╚█████╗░█████═╝░██║██║░░░░░██║░░░░░██████╔╝██║░░██║██║░░██║
░╚═══██╗██╔═██╗░██║██║░░░░░██║░░░░░██╔═══╝░██║░░██║██║░░██║
██████╔╝██║░╚██╗██║███████╗███████╗██║░░░░░╚█████╔╝██████╔╝
╚═════╝░╚═╝░░╚═╝╚═╝╚══════╝╚══════╝╚═╝░░░░░░╚════╝░╚═════╝░
"""


def run_server(
    *, config: Config, force_reindex: bool = False, skip_auto_reindex: bool = False
):
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

    instructions = build_xml_instructions(config)
    mcp = FastMCP("skillsouko", version="0.0.0", instructions=instructions)
    register_tools(mcp, config)
    mcp.run()
