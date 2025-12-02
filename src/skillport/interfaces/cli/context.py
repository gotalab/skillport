"""CLI context helpers for sharing Config between commands."""

from typing import Any

import typer

from skillport.shared.config import Config


def get_config(ctx: typer.Context, *, default: Config | None = None) -> Config:
    """Return Config injected via Typer context or fallback to default/Config()."""
    obj: Any = getattr(ctx, "obj", None)
    if isinstance(obj, Config):
        return obj
    if default is not None:
        return default
    return Config()


__all__ = ["get_config"]
