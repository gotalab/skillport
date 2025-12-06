"""Helpers for automatic index freshness in CLI commands."""

from __future__ import annotations

import os

from skillport.modules.indexing import build_index, should_reindex
from skillport.shared.config import Config

from .theme import stderr_console


def _env_auto_reindex_default() -> bool | None:
    """Parse SKILLPORT_AUTO_REINDEX env var.

    Returns:
        True/False if set, None if unset.
    """
    env = os.getenv("SKILLPORT_AUTO_REINDEX")
    if env is None:
        return None
    return env.strip().lower() not in {"0", "false", "no", "off"}


def should_auto_reindex(ctx, default: bool = True) -> bool:
    """Resolve whether to auto-reindex for the current CLI run."""
    if ctx is not None and getattr(ctx, "meta", None):
        if "auto_reindex" in ctx.meta and ctx.meta["auto_reindex"] is not None:
            return bool(ctx.meta["auto_reindex"])

    env_val = _env_auto_reindex_default()
    if env_val is not None:
        return env_val

    return default


def ensure_index_fresh(ctx, config: Config, *, force: bool = False) -> None:
    """Auto-reindex if the index is stale.

    Args:
        ctx: Typer context (for flags/meta).
        config: Active Config.
        force: Force reindex (bypasses state check).
    """
    if not should_auto_reindex(ctx):
        return

    decision = should_reindex(config=config) if not force else None
    need = force or (decision and decision.need)

    if not need:
        return

    reason = "force" if force else decision.reason
    stderr_console.print(f"[dim]Auto reindexing (reason={reason})[/dim]", highlight=False)
    result = build_index(config=config, force=force)
    if not result.success:
        stderr_console.print(f"[error]Reindex failed: {result.message}[/error]")


__all__ = ["ensure_index_fresh", "should_auto_reindex"]
