"""GitHub authentication token resolution with fallback chain.

Design: Function-based with pluggable resolvers for easy extension.

Fallback chain (in order):
1. GH_TOKEN environment variable (fine-grained PAT recommended by GitHub)
2. GITHUB_TOKEN environment variable (classic, widely used)
3. gh CLI auth token (for local development)

Usage:
    from skillport.shared.auth import resolve_github_token

    result = resolve_github_token()
    if result.token:
        headers["Authorization"] = f"Bearer {result.token}"
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass

# Type alias for resolver functions
TokenResolver = Callable[[], "TokenResult | None"]


@dataclass(frozen=True)
class TokenResult:
    """Result of token resolution with source information."""

    token: str | None
    source: str | None  # e.g., "GH_TOKEN", "GITHUB_TOKEN", "gh_cli"

    @property
    def has_token(self) -> bool:
        return bool(self.token)

    def __bool__(self) -> bool:
        return self.has_token


# --- Token Resolvers (each returns TokenResult or None) ---


def _resolve_from_gh_token_env() -> TokenResult | None:
    """Resolve from GH_TOKEN (preferred for fine-grained PAT)."""
    if token := os.getenv("GH_TOKEN"):
        return TokenResult(token=token, source="GH_TOKEN")
    return None


def _resolve_from_github_token_env() -> TokenResult | None:
    """Resolve from GITHUB_TOKEN (classic, widely used)."""
    if token := os.getenv("GITHUB_TOKEN"):
        return TokenResult(token=token, source="GITHUB_TOKEN")
    return None


def _resolve_from_gh_cli() -> TokenResult | None:
    """Resolve from gh CLI auth token."""
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and (token := result.stdout.strip()):
            return TokenResult(token=token, source="gh_cli")
    except FileNotFoundError:
        # gh CLI not installed
        pass
    except subprocess.TimeoutExpired:
        # gh CLI timed out
        pass
    except Exception:
        # Any other error (permissions, etc.)
        pass
    return None


# --- Fallback Chain Configuration ---

# Order matters: first match wins
# To customize, modify this list or use resolve_github_token(resolvers=[...])
DEFAULT_RESOLVERS: list[TokenResolver] = [
    _resolve_from_gh_token_env,
    _resolve_from_github_token_env,
    _resolve_from_gh_cli,
]


def resolve_github_token(
    resolvers: list[TokenResolver] | None = None,
) -> TokenResult:
    """Resolve GitHub token using fallback chain.

    Args:
        resolvers: Custom list of resolver functions. Defaults to DEFAULT_RESOLVERS.

    Returns:
        TokenResult with token and source, or empty TokenResult if none found.
    """
    for resolver in resolvers or DEFAULT_RESOLVERS:
        if result := resolver():
            return result
    return TokenResult(token=None, source=None)


def is_gh_cli_available() -> bool:
    """Check if gh CLI is installed and available."""
    try:
        result = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False
