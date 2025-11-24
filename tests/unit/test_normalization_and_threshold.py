from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from hypothesis import given, settings, strategies as st

from skillhub_mcp.db import SkillDB


THRESHOLD = 0.2


class DummySettings:
    def __init__(self, base_dir, threshold=THRESHOLD):
        self.search_threshold = threshold
        self.embedding_provider = "none"
        self.skillhub_enabled_skills = []
        self.skillhub_enabled_categories = []
        self.skills_dir = base_dir / "skills"
        self.db_path = base_dir / "db.lancedb"

    def get_effective_skills_dir(self):
        return self.skills_dir

    def get_effective_db_path(self):
        return self.db_path


class DummyTable:
    def __init__(self, data):
        self.data = data
        self._limit = None

    def search(self, *args, **kwargs):
        return self

    def where(self, *args, **kwargs):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def to_list(self):
        if self._limit is None:
            return list(self.data)
        return list(self.data)[: self._limit]


class DummyDB:
    def __init__(self, data):
        self.data = data

    def table_names(self):
        return ["skills"]

    def open_table(self, name):
        return DummyTable(self.data)


def make_db(base_dir: Path, data):
    dummy_settings = DummySettings(base_dir)
    dummy_db = DummyDB(data)
    with patch("skillhub_mcp.db.search.settings", dummy_settings), patch(
        "skillhub_mcp.db.search.lancedb.connect", lambda path: dummy_db
    ), patch("skillhub_mcp.db.search.get_embedding", lambda query: None):
        return SkillDB()


@settings(max_examples=150)
@given(st.text())
def test_s1_query_normalization(text):
    """WHEN query has extra whitespace THEN it is trimmed/space-compressed before search (EARS:S1)."""
    with TemporaryDirectory() as tmp:
        db = make_db(Path(tmp), [])
        expected = " ".join(text.strip().split())
        assert db._normalize(text) == expected


@settings(max_examples=150)
@given(st.text())
def test_s2_category_tag_normalization(text):
    """WHEN category/tags include mixed case/whitespace THEN they are lowercase-trimmed (EARS:S2)."""
    with TemporaryDirectory() as tmp:
        db = make_db(Path(tmp), [])
        expected = " ".join(text.strip().split()).lower()
        assert db._norm_token(text) == expected


@settings(max_examples=120)
@given(
    st.lists(
        st.floats(min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=25,
    )
)
def test_s5_threshold_filters_low_scores(scores):
    """WHEN hits are fetched THEN threshold drops low scores and caps to limit (EARS:S5)."""
    scores_sorted = sorted(scores, reverse=True)
    top = scores_sorted[0]
    expected = [s for s in scores_sorted if s / top >= THRESHOLD][:5]
    with TemporaryDirectory() as tmp:
        db = make_db(Path(tmp), [{"_score": s} for s in scores_sorted])
        results = db.search("anything", limit=5)
        assert [r["_score"] for r in results] == expected
