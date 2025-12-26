"""Search strategy with vector → FTS → substring fallback."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


def _normalize_score(row: dict[str, Any]) -> float:
    if row.get("_score") is not None:
        try:
            return float(row["_score"])
        except Exception:
            return 0.0
    if row.get("score") is not None:
        try:
            return float(row["score"])
        except Exception:
            return 0.0
    if row.get("_distance") is not None:
        try:
            return -float(row["_distance"])
        except Exception:
            return 0.0
    return 0.0


@dataclass
class SearchHit:
    """Internal search hit (not to be confused with public SearchResult)."""

    row: dict[str, Any]
    score: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        merged = dict(self.row)
        merged["_score"] = self.score
        merged["_source"] = self.source
        return merged


class SearchService:
    """Encapsulates query execution + fallback chain."""

    def __init__(
        self,
        *,
        search_threshold: float,
        embed_fn: Callable[[str], list[float] | None],
    ):
        self.search_threshold = search_threshold
        self.embed_fn = embed_fn

    def search(
        self,
        table,
        query: str,
        *,
        limit: int,
        prefilter: str,
        normalize_query: Callable[[str], str],
    ) -> list[dict[str, Any]]:
        if not table:
            return []

        query_norm = normalize_query(query)
        vec: list[float] | None = None
        try:
            vec = self.embed_fn(query_norm)
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Embedding fetch failed, falling back to FTS: {exc}", file=sys.stderr)
            vec = None

        try:
            if vec:
                try:
                    results = self._vector_search(table, vec, prefilter, limit)
                except Exception as exc:
                    print(
                        f"Vector search failed, falling back to FTS: {exc}",
                        file=sys.stderr,
                    )
                    results = self._fts_then_substring(table, query_norm, prefilter, limit)
                else:
                    if not results:
                        results = self._fts_then_substring(table, query_norm, prefilter, limit)
            else:
                results = self._fts_then_substring(table, query_norm, prefilter, limit)
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Search error: {exc}", file=sys.stderr)
            return []

        if not results:
            return []

        results.sort(key=lambda r: r.score, reverse=True)
        top_score = results[0].score

        if top_score <= 0:
            return [r.to_dict() for r in results[:limit]]

        filtered = [r for r in results if r.score / top_score >= self.search_threshold]
        return [r.to_dict() for r in filtered[:limit]]

    # --- strategies ---
    def _vector_search(
        self, table, vec: list[float], prefilter: str, limit: int
    ) -> list[SearchHit]:
        op = table.search(vec)
        if prefilter:
            op = op.where(prefilter)
        rows = op.limit(limit).to_list()
        return [self._to_hit(row, "vector") for row in rows]

    def _fts_search(self, table, query: str, prefilter: str, limit: int) -> list[SearchHit]:
        op = table.search(query, query_type="fts")
        if prefilter:
            op = op.where(prefilter)
        rows = op.limit(limit).to_list()
        return [self._to_hit(row, "fts") for row in rows]

    def _substring_search(self, table, query: str, prefilter: str, limit: int) -> list[SearchHit]:
        op = table.search()
        if prefilter:
            op = op.where(prefilter)
        rows = op.limit(limit * 3).to_list()

        qlow = query.lower()
        hits: list[SearchHit] = []
        for row in rows:
            if (
                qlow in str(row.get("id", "")).lower()
                or qlow in str(row.get("name", "")).lower()
                or qlow in str(row.get("description", "")).lower()
            ):
                hits.append(self._to_hit(row, "substring", default_score=0.1))
                if len(hits) >= limit:
                    break
        return hits

    # --- helpers ---
    def _fts_then_substring(self, table, query: str, prefilter: str, limit: int) -> list[SearchHit]:
        try:
            return self._fts_search(table, query, prefilter, limit)
        except Exception as exc:
            print(f"FTS search failed, using substring fallback: {exc}", file=sys.stderr)
            return self._substring_search(table, query, prefilter, limit)

    def _to_hit(
        self, row: dict[str, Any], source: str, default_score: float | None = None
    ) -> SearchHit:
        score = _normalize_score(row)
        if score == 0.0 and default_score is not None:
            score = default_score
        return SearchHit(row=row, score=score, source=source)
