"""MCP server CLI entrypoint (skillport-mcp)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from skillport.shared.config import Config

from .server import run_server


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillport-mcp",
        description="SkillPort MCP server (indexed search + tools).",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run as HTTP server (Remote mode).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP server host (only with --http).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP server port (only with --http).",
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Force reindex before starting server.",
    )
    parser.add_argument(
        "--skip-auto-reindex",
        action="store_true",
        help="Skip automatic reindex check.",
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        help="Override skills directory (CLI > env > default).",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        help="Override LanceDB path (CLI > env > default).",
    )
    parser.add_argument(
        "--embedding-provider",
        choices=["none", "openai"],
        help="Embedding provider (overrides SKILLPORT_EMBEDDING_PROVIDER).",
    )
    parser.add_argument(
        "--openai-api-key",
        help="OpenAI API key (overrides OPENAI_API_KEY).",
    )
    parser.add_argument(
        "--openai-embedding-model",
        help="OpenAI embedding model (overrides OPENAI_EMBEDDING_MODEL).",
    )
    return parser


def _build_config(args: argparse.Namespace) -> Config:
    overrides = {}
    if args.skills_dir:
        overrides["skills_dir"] = args.skills_dir.expanduser().resolve()
    if args.db_path:
        overrides["db_path"] = args.db_path.expanduser().resolve()
    if args.embedding_provider:
        overrides["embedding_provider"] = args.embedding_provider
    if args.openai_api_key:
        overrides["openai_api_key"] = args.openai_api_key
    if args.openai_embedding_model:
        overrides["openai_embedding_model"] = args.openai_embedding_model
    return Config(**overrides) if overrides else Config()


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    config = _build_config(args)
    transport = "http" if args.http else "stdio"

    print("[INFO] SkillPort MCP Server", file=sys.stderr)
    print(f"[INFO] Skills: {config.skills_dir}", file=sys.stderr)
    print(f"[INFO] Index:  {config.db_path}", file=sys.stderr)
    print(f"[INFO] Provider: {config.embedding_provider}", file=sys.stderr)
    print(f"[INFO] Transport: {transport}", file=sys.stderr)
    if args.http:
        print(f"[INFO] Endpoint: http://{args.host}:{args.port}/mcp", file=sys.stderr)
    print("[INFO] ----------------------------------------", file=sys.stderr)

    run_server(
        config=config,
        transport=transport,
        host=args.host,
        port=args.port,
        force_reindex=args.reindex,
        skip_auto_reindex=args.skip_auto_reindex,
    )


if __name__ == "__main__":
    main()
