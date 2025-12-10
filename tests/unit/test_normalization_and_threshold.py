from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from skillport.modules.indexing.internal.lancedb import IndexStore
from skillport.modules.indexing.internal.search_service import SearchService
from skillport.shared.config import Config
from skillport.shared.utils import normalize_token

THRESHOLD = 0.2


class DummyTable:
    def __init__(self, data, fail_fts=False):
        self.data = data
        self.fail_fts = fail_fts
        self._limit = None
        self.query_type = None

    def search(self, *args, **kwargs):
        self.query_type = kwargs.get("query_type")
        if self.query_type == "fts" and self.fail_fts:
            raise RuntimeError("fts failure")
        return self

    def where(self, *args, **kwargs):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def to_list(self):
        data = list(self.data)
        if self._limit is not None:
            data = data[: self._limit]
        return data


@settings(max_examples=150)
@given(st.text())
def test_query_normalization(text):
    """Normalize queries by trimming/compressing whitespace."""
    cfg = Config(skills_dir=Path("/tmp/skills"), db_path=Path("/tmp/db.lancedb"))
    # Patch lancedb.connect to avoid real IO
    from unittest.mock import patch

    class DummyDB:
        def table_names(self):
            return []

    with patch(
        "skillport.modules.indexing.internal.lancedb.lancedb.connect", lambda path: DummyDB()
    ):
        store = IndexStore(cfg)
        expected = " ".join(text.strip().split())
        assert store._normalize_query(text) == expected


@settings(max_examples=150)
@given(st.text())
def test_category_tag_normalization(text):
    """Normalization helper lowercases and trims."""
    expected = " ".join(text.strip().split()).lower()
    assert normalize_token(text) == expected


@settings(max_examples=120)
@given(
    st.lists(
        st.floats(min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=25,
    )
)
def test_threshold_filters_low_scores(scores):
    """SearchService drops results below threshold and respects limit."""
    scores_sorted = sorted(scores, reverse=True)
    top = scores_sorted[0]
    expected = [s for s in scores_sorted if s / top >= THRESHOLD][:5]

    table = DummyTable([{"_score": s} for s in scores_sorted])
    service = SearchService(search_threshold=THRESHOLD, embed_fn=lambda q: None)

    results = service.search(
        table=table, query="anything", limit=5, prefilter="", normalize_query=lambda q: q
    )
    assert [r["_score"] for r in results] == expected
