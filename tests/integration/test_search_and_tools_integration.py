from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from skillport.modules.indexing import search as idx_search
from skillport.modules.skills import read_skill_file, search_skills
from skillport.shared.config import Config


class DummyTable:
    def __init__(self, data, fail_fts=False):
        self.data = data
        self.fail_fts = fail_fts
        self._limit = None
        self.filter_fn = lambda row: True

    def search(self, *args, **kwargs):
        if kwargs.get("query_type") == "fts" and self.fail_fts:
            raise RuntimeError("fts failed")
        return self

    def where(self, clause: str):
        # very small evaluator for tests
        clause_lower = clause.lower()

        def predicate(row):
            if clause_lower.startswith("category in"):
                options = [
                    c.strip(" '") for c in clause_lower.split("(")[1].split(")")[0].split(",")
                ]
                return (row.get("category") or "").lower() in options
            if clause_lower.startswith("id in"):
                options = [
                    c.strip(" '") for c in clause_lower.split("(")[1].split(")")[0].split(",")
                ]
                return (row.get("id") or "").lower() in options
            if clause_lower.startswith("lower(id) like"):
                prefix = clause_lower.split("like")[1].strip(" '")
                return (row.get("id") or "").lower().startswith(prefix.rstrip("%"))
            if "and" in clause_lower:
                parts = [p.strip() for p in clause_lower.split("and")]
                return all(DummyTable._eval_simple(p, row) for p in parts)
            return True

        new_tbl = DummyTable(self.data, self.fail_fts)
        new_tbl.filter_fn = lambda row: self.filter_fn(row) and predicate(row)
        return new_tbl

    @staticmethod
    def _eval_simple(text: str, row):
        if text.startswith("always_apply = true"):
            return bool(row.get("always_apply"))
        return True

    def limit(self, n: int):
        self._limit = n
        return self

    def to_list(self):
        rows = [r for r in self.data if self.filter_fn(r)]
        if self._limit is not None:
            rows = rows[: self._limit]
        return rows

    # Index creation stubs
    def create_fts_index(self, *args, **kwargs):
        return None

    def create_scalar_index(self, *args, **kwargs):
        return None


class DummyDB:
    def __init__(self, table: DummyTable | None = None):
        self.table = table

    def table_names(self):
        return ["skills"] if self.table else []

    def open_table(self, name):
        return self.table

    def drop_table(self, name):
        self.table = None

    def create_table(self, name, data, mode="overwrite"):
        self.table = DummyTable(data)
        return self.table


def _make_config(tmp_path: Path) -> Config:
    return Config(skills_dir=tmp_path / "skills", db_path=tmp_path / "db.lancedb")


def test_embedding_failure_falls_back_to_fts(tmp_path, monkeypatch):
    cfg = _make_config(tmp_path)

    rows = [
        {"id": "alpha", "name": "alpha", "description": "first", "_score": 0.9},
        {"id": "beta", "name": "beta", "description": "second", "_score": 0.8},
    ]
    dummy_db = DummyDB(DummyTable(rows))

    monkeypatch.setattr(
        "skillport.modules.indexing.internal.lancedb.lancedb.connect", lambda path: dummy_db
    )
    monkeypatch.setattr(
        "skillport.modules.indexing.internal.embeddings.get_embedding",
        lambda text, config: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = idx_search("anything", limit=2, config=cfg)
    assert [r["name"] for r in result] == ["alpha", "beta"]


def test_fts_failure_falls_back_to_substring(tmp_path, monkeypatch):
    cfg = _make_config(tmp_path)
    rows = [
        {"id": "beta-tool", "name": "beta-tool", "description": "does beta things"},
        {"id": "gamma", "name": "gamma", "description": "unrelated"},
    ]
    dummy_db = DummyDB(DummyTable(rows, fail_fts=True))
    monkeypatch.setattr(
        "skillport.modules.indexing.internal.lancedb.lancedb.connect", lambda path: dummy_db
    )
    monkeypatch.setattr(
        "skillport.modules.indexing.internal.embeddings.get_embedding", lambda text, config: None
    )

    results = idx_search("beta", limit=3, config=cfg)
    assert any(r["name"] == "beta-tool" for r in results)


def test_filter_respects_enabled_categories(tmp_path, monkeypatch):
    cfg = Config(
        skills_dir=tmp_path / "skills",
        db_path=tmp_path / "db.lancedb",
        enabled_categories=["  ML  "],
    )
    rows = [
        {
            "id": "ml-skill",
            "name": "ml-skill",
            "description": "ml",
            "category": "ml",
            "_score": 1.0,
        },
        {
            "id": "ops-skill",
            "name": "ops-skill",
            "description": "ops",
            "category": "ops",
            "_score": 0.9,
        },
    ]
    dummy_db = DummyDB(DummyTable(rows))
    monkeypatch.setattr(
        "skillport.modules.indexing.internal.lancedb.lancedb.connect", lambda path: dummy_db
    )
    monkeypatch.setattr(
        "skillport.modules.indexing.internal.embeddings.get_embedding", lambda text, config: None
    )

    result = search_skills("anything", config=cfg)
    assert [s.name for s in result.skills] == ["ml-skill"]


def test_read_skill_file_guards_traversal_and_supports_binary(tmp_path):
    """Test path traversal protection and binary file support.

    SPEC4: Binary files are now supported via base64 encoding.
    """
    cfg = _make_config(tmp_path)
    skill_dir = cfg.skills_dir / "secure"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: secure
description: Secure skill
metadata:
  skillport:
    category: sec
---
body
""",
        encoding="utf-8",
    )
    (skill_dir / "file.txt").write_text("hello", encoding="utf-8")
    binary_content = b"\xff\xfe\xfd"
    (skill_dir / "binary.bin").write_bytes(binary_content)

    record = {"id": "secure", "category": "sec", "path": str(skill_dir)}
    store = SimpleNamespace(get_by_id=lambda *args, **kwargs: record)

    # Monkeypatch public getter to use stub record
    with patch("skillport.modules.skills.public.read.idx_get_by_id", store.get_by_id):
        # Path traversal still blocked
        with pytest.raises(PermissionError):
            read_skill_file("secure", "../escape.txt", config=cfg)

        # Binary files now return base64-encoded content (SPEC4)
        import base64

        binary_result = read_skill_file("secure", "binary.bin", config=cfg)
        assert binary_result.encoding == "base64"
        assert base64.b64decode(binary_result.content) == binary_content

        # Text files still work as before
        text_result = read_skill_file("secure", "file.txt", config=cfg)
        assert text_result.content == "hello"
        assert text_result.encoding == "utf-8"
