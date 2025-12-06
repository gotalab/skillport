"""Index build-related public APIs."""

import sys

from skillport.modules.skills.internal import prune_orphan_origins
from skillport.shared.config import Config

from ..internal.lancedb import IndexStore
from .types import IndexBuildResult, ReindexDecision


def build_index(*, config: Config, force: bool = False) -> IndexBuildResult:
    # Clean up stale origin entries before deciding on reindex
    removed = prune_orphan_origins(config=config)
    if removed:
        print(
            f"Pruned {len(removed)} orphan origin(s): {', '.join(removed)}",
            file=sys.stderr,
        )

    store = IndexStore(config)
    decision = store.should_reindex(force=force, skip_auto=False)

    if not decision["need"]:
        # No reindex needed, return current state
        table = store.list_all(limit=1_000_000)
        count = len(table)
        return IndexBuildResult(success=True, skill_count=count, message=decision["reason"])

    try:
        store.initialize_index()
        store.persist_state(decision["state"])
        table = store.list_all(limit=1_000_000)
        count = len(table)
        return IndexBuildResult(success=True, skill_count=count, message=decision["reason"])
    except Exception as exc:
        return IndexBuildResult(success=False, skill_count=0, message=str(exc))


def should_reindex(*, config: Config) -> ReindexDecision:
    store = IndexStore(config)
    decision = store.should_reindex()
    return ReindexDecision(
        need=bool(decision["need"]), reason=decision["reason"], state=decision["state"]
    )
