import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


def _normalize_score(row: Dict[str, Any]) -> float:
    """
    Normalize score across vector/FTS/substr searches.
    Prefer existing _score, then LanceDB 'score', then inverse distance.
    """
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
class SearchResult:
    row: Dict[str, Any]
    score: float
    source: str

    def to_dict(self) -> Dict[str, Any]:
        merged = dict(self.row)
        merged["_score"] = self.score
        merged["_source"] = self.source
        return merged


class SkillSearchService:
    """
    Encapsulates query execution + fallback logic.
    Keeps SkillDB thin and makes adding new search strategies easier.
    """

    def __init__(self, settings, embed_fn: Callable[[str], Optional[List[float]]]):
        self.settings = settings
        self.embed_fn = embed_fn

    def search(
        self,
        table,
        query: str,
        limit: int,
        prefilter: str,
        normalize_query: Callable[[str], str],
    ) -> List[Dict[str, Any]]:
        if not table:
            return []

        threshold = self.settings.search_threshold
        query_norm = normalize_query(query)

        vec: Optional[List[float]] = None
        try:
            vec = self.embed_fn(query_norm)
        except Exception as e:
            print(f"Embedding fetch failed, falling back to FTS: {e}", file=sys.stderr)
            vec = None

        try:
            if vec:
                results = self._vector_search(table, vec, prefilter, limit)
            else:
                try:
                    results = self._fts_search(table, query_norm, prefilter, limit)
                except Exception as e:
                    print(f"FTS search failed, using substring fallback: {e}", file=sys.stderr)
                    results = self._substring_search(table, query_norm, prefilter, limit)
        except Exception as e:
            print(f"Search error: {e}", file=sys.stderr)
            return []

        if not results:
            return []

        results.sort(key=lambda r: r.score, reverse=True)

        top_score = results[0].score
        if top_score <= 0:
            return [r.to_dict() for r in results[:limit]]

        filtered = [r for r in results if r.score / top_score >= threshold]
        return [r.to_dict() for r in filtered[:limit]]

    # --- Strategies ---
    def _vector_search(self, table, vec: List[float], prefilter: str, limit: int) -> List[SearchResult]:
        search_op = table.search(vec)
        if prefilter:
            search_op = search_op.where(prefilter)
        rows = search_op.limit(limit).to_list()
        return [self._to_result(row, "vector") for row in rows]

    def _fts_search(self, table, query: str, prefilter: str, limit: int) -> List[SearchResult]:
        search_op = table.search(query, query_type="fts")
        if prefilter:
            search_op = search_op.where(prefilter)
        rows = search_op.limit(limit).to_list()
        return [self._to_result(row, "fts") for row in rows]

    def _substring_search(self, table, query: str, prefilter: str, limit: int) -> List[SearchResult]:
        search_op = table.search()
        if prefilter:
            search_op = search_op.where(prefilter)
        rows = search_op.limit(limit * 3).to_list()

        qlow = query.lower()
        results: List[SearchResult] = []
        for row in rows:
            if qlow in str(row.get("name", "")).lower() or qlow in str(row.get("description", "")).lower():
                results.append(self._to_result(row, "substring", default_score=0.1))
                if len(results) >= limit:
                    break
        return results

    # --- Helpers ---
    def _to_result(self, row: Dict[str, Any], source: str, default_score: Optional[float] = None) -> SearchResult:
        score = _normalize_score(row)
        if score == 0.0 and default_score is not None:
            score = default_score
        return SearchResult(row=row, score=score, source=source)
