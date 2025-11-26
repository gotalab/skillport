from pathlib import Path
from types import SimpleNamespace

import pytest

from skillhub_mcp.db import search as search_mod
import skillhub_mcp.tools.discovery as discovery
import skillhub_mcp.tools.execution as execution
from skillhub_mcp.tools.discovery import DiscoveryTools
from skillhub_mcp.tools.execution import ExecutionTools
from skillhub_mcp.tools.loading import LoadingTools
from skillhub_mcp import utils


class DummySettings:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.search_threshold = 0.2
        self.search_limit = 5
        self.embedding_provider = "none"
        self.openai_api_key = None
        self.gemini_api_key = None
        self.embedding_model = None
        self.gemini_embedding_model = None
        self.skillhub_enabled_skills = []
        self.skillhub_enabled_categories = []
        self.skillhub_enabled_namespaces = []
        self.allowed_commands = ["python", "python3", "uv", "node", "cat", "ls", "grep", "echo"]
        self.exec_timeout_seconds = 2
        self.exec_max_output_bytes = 16
        self.max_file_bytes = 8
        self.log_level = "INFO"
        self.skills_dir = base_dir / "skills"
        self.db_path = base_dir / "db.lancedb"

    def get_effective_skills_dir(self) -> Path:
        return self.skills_dir

    def get_effective_db_path(self) -> Path:
        return self.db_path

    def get_enabled_skills(self):
        return self.skillhub_enabled_skills

    def get_enabled_categories(self):
        return self.skillhub_enabled_categories

    def get_enabled_namespaces(self):
        return self.skillhub_enabled_namespaces


class DummyTable:
    def __init__(self, data, fail_fts=False, parent=None):
        self.data = list(data)
        self.fail_fts = fail_fts
        self._limit = None
        self.filter_fn = lambda row: True
        self.parent = parent

    # LanceDB-like API
    def search(self, *args, **kwargs):
        # FTS path signaled by query_type="fts"
        if kwargs.get("query_type") == "fts" and self.fail_fts:
            raise RuntimeError("FTS failure simulated")
        return self

    def where(self, clause: str):
        def predicate(row):
            return self._eval_clause(row, clause)

        new_table = DummyTable(self.data, self.fail_fts, self.parent)
        new_table.filter_fn = lambda row: self.filter_fn(row) and predicate(row)
        return new_table

    def limit(self, n: int):
        self._limit = n
        return self

    def to_list(self):
        rows = [row for row in self.data if self.filter_fn(row)]
        if self._limit is not None:
            rows = rows[: self._limit]
        return rows

    # Index creation hooks
    def create_fts_index(self, fields, replace=True, use_tantivy=True):
        if self.parent is not None:
            self.parent.created_fts_fields = fields

    def create_scalar_index(self, *args, **kwargs):
        return None

    # Helpers
    def _eval_clause(self, row, clause: str) -> bool:
        text = clause.lower()
        if " and " in text:
            parts = [p.strip() for p in text.split("and")]
            return all(self._eval_clause(row, p) for p in parts)

        if text.startswith("name in"):
            names = text.split("(")[1].split(")")[0]
            options = [n.strip(" ' \"") for n in names.split(",")]
            return row.get("name", "").lower() in options

        if text.startswith("lower(id) in"):
            ids = text.split("(")[1].split(")")[0]
            options = [i.strip(" ' \"") for i in ids.split(",")]
            return row.get("id", "").lower() in options

        if text.startswith("id in"):
            ids = text.split("(")[1].split(")")[0]
            options = [i.strip(" ' \"") for i in ids.split(",")]
            return row.get("id", "") in options

        if text.startswith("category in"):
            cats = text.split("(")[1].split(")")[0]
            options = [c.strip(" ' \"") for c in cats.split(",")]
            return (row.get("category") or "").lower() in options

        if text.startswith("name ="):
            target = text.split("=")[1].strip(" ' \"")
            return row.get("name", "").lower() == target

        if text.startswith("id ="):
            target = text.split("=")[1].strip(" ' \"")
            return row.get("id", "").lower() == target

        if text.startswith("always_apply = true"):
            return bool(row.get("always_apply")) is True

        return True


class DummyDB:
    def __init__(self, table: DummyTable | None = None):
        self.table = table
        self.created_fts_fields = None

    def table_names(self):
        return ["skills"] if self.table else []

    def open_table(self, name):
        return self.table

    def drop_table(self, name):
        self.table = None

    def create_table(self, name, data, mode="overwrite"):
        self.table = DummyTable(data, parent=self)
        return self.table


def _patch_settings(monkeypatch, settings: DummySettings):
    # Align all modules to the same settings instance
    monkeypatch.setattr(search_mod, "settings", settings)
    monkeypatch.setattr(utils, "settings", settings)
    monkeypatch.setattr(discovery, "settings", settings)
    monkeypatch.setattr(execution, "settings", settings)


def _make_skill_db(monkeypatch, settings: DummySettings, dummy_db: DummyDB):
    monkeypatch.setattr(search_mod.lancedb, "connect", lambda path: dummy_db)
    return search_mod.SkillDB()


def test_s3a_embedding_failure_falls_back_to_fts(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    _patch_settings(monkeypatch, settings)

    rows = [
        {"id": "alpha", "name": "alpha", "description": "first", "_score": 0.9},
        {"id": "beta", "name": "beta", "description": "second", "_score": 0.8},
    ]
    dummy_db = DummyDB(DummyTable(rows, fail_fts=False))
    monkeypatch.setattr(search_mod, "get_embedding", lambda q: (_ for _ in ()).throw(RuntimeError("boom")))

    db = _make_skill_db(monkeypatch, settings, dummy_db)

    results = db.search("anything", limit=2)
    assert [r["name"] for r in results] == ["alpha", "beta"]  # FTS path used


def test_s3b_fts_failure_falls_back_to_substring(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    _patch_settings(monkeypatch, settings)

    rows = [
        {"id": "beta-tool", "name": "beta-tool", "description": "does beta things"},
        {"id": "gamma", "name": "gamma", "description": "unrelated"},
    ]
    dummy_db = DummyDB(DummyTable(rows, fail_fts=True))
    monkeypatch.setattr(search_mod, "get_embedding", lambda q: None)

    db = _make_skill_db(monkeypatch, settings, dummy_db)

    results = db.search("beta", limit=3)
    assert any(r["name"] == "beta-tool" for r in results)
    assert all("_score" in r for r in results)


def test_s4_filter_respects_enabled_categories_with_normalization(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    settings.skillhub_enabled_categories = ["  ML  "]  # mixed case + whitespace
    _patch_settings(monkeypatch, settings)

    rows = [
        {"id": "ml-skill", "name": "ml-skill", "description": "ml", "category": "ml", "_score": 1.0},
        {"id": "ops-skill", "name": "ops-skill", "description": "ops", "category": "ops", "_score": 0.9},
    ]
    dummy_db = DummyDB(DummyTable(rows))
    monkeypatch.setattr(search_mod, "get_embedding", lambda q: None)

    db = _make_skill_db(monkeypatch, settings, dummy_db)
    search_tools = DiscoveryTools(db)

    result = search_tools.search_skills("anything")
    assert [s["name"] for s in result["skills"]] == ["ml-skill"]


def test_s5b_vector_results_skip_threshold(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    _patch_settings(monkeypatch, settings)

    rows = [
        {"id": "v1", "name": "v1", "description": "", "_distance": 0.1},
        {"id": "v2", "name": "v2", "description": "", "_distance": 0.2},
        {"id": "v3", "name": "v3", "description": "", "_distance": 0.3},
    ]
    dummy_db = DummyDB(DummyTable(rows))
    monkeypatch.setattr(search_mod, "get_embedding", lambda q: [0.1, 0.2])

    db = _make_skill_db(monkeypatch, settings, dummy_db)
    results = db.search("q", limit=2)
    assert len(results) == 2  # capped to limit, no threshold crash


def test_s6_instructions_excluded_from_fts_index(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    _patch_settings(monkeypatch, settings)

    skill_dir = settings.skills_dir / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("""---
name: demo
description: Demo skill
category: utils
tags: [demo]
alwaysApply: true
---
# Body content
""", encoding="utf-8")

    dummy_db = DummyDB()
    monkeypatch.setattr(search_mod, "get_embedding", lambda text: None)
    db = _make_skill_db(monkeypatch, settings, dummy_db)

    db.initialize_index()

    assert dummy_db.created_fts_fields is not None
    assert "instructions" not in dummy_db.created_fts_fields
    assert "id" in dummy_db.created_fts_fields


def test_namespace_ids_added_to_index(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    _patch_settings(monkeypatch, settings)

    nested = settings.skills_dir / "awesome-skills" / "code-review"
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text(
        """---
name: code-review
description: Code review checklist
metadata:
  skillhub:
    category: dev
---
body
""",
        encoding="utf-8",
    )

    flat = settings.skills_dir / "solo"
    flat.mkdir(parents=True)
    (flat / "SKILL.md").write_text(
        """---
name: solo
description: Solo skill
---
body
""",
        encoding="utf-8",
    )

    dummy_db = DummyDB()
    monkeypatch.setattr(search_mod, "get_embedding", lambda text: None)

    db = _make_skill_db(monkeypatch, settings, dummy_db)
    db.initialize_index()

    ids = [row["id"] for row in dummy_db.table.data]
    assert "solo" in ids
    assert "awesome-skills/code-review" in ids


def test_load_skill_ambiguous_name_raises(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    _patch_settings(monkeypatch, settings)

    rows = [
        {"id": "a/code-review", "name": "code-review", "description": "", "category": "", "instructions": ""},
        {"id": "b/code-review", "name": "code-review", "description": "", "category": "", "instructions": ""},
    ]
    dummy_db = DummyDB(DummyTable(rows))
    monkeypatch.setattr(search_mod.lancedb, "connect", lambda path: dummy_db)
    monkeypatch.setattr(search_mod, "get_embedding", lambda q: None)

    db = _make_skill_db(monkeypatch, settings, dummy_db)
    loader = LoadingTools(db)

    with pytest.raises(ValueError) as e:
        loader.load_skill(skill_name="code-review")
    assert "Ambiguous" in str(e.value)


def test_f1_read_skill_file_rejects_traversal_and_non_utf8(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    _patch_settings(monkeypatch, settings)

    skill_dir = settings.skills_dir / "secure"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("""---
name: secure
description: Secure skill
category: sec
---
body
""", encoding="utf-8")
    (skill_dir / "file.txt").write_text("hello", encoding="utf-8")
    (skill_dir / "binary.bin").write_bytes(b"\xff\xfe\xfd")

    # Stub DB responses
    stub_record = {"category": "sec", "path": str(skill_dir)}
    exec_tools = ExecutionTools(SimpleNamespace(get_skill=lambda name: stub_record))

    with pytest.raises(PermissionError):
        exec_tools.read_skill_file("secure", "../escape.txt")

    with pytest.raises(ValueError):
        exec_tools.read_skill_file("secure", "binary.bin")


def test_x1_run_skill_command_uses_cwd_and_shell_false(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    _patch_settings(monkeypatch, settings)

    skill_dir = settings.skills_dir / "run"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("""---
name: run
description: runner
category: utils
---
body
""", encoding="utf-8")

    stub_record = {"category": "utils", "path": str(skill_dir)}
    exec_tools = ExecutionTools(SimpleNamespace(get_skill=lambda name: stub_record))

    called = {}

    def fake_run(cmd_list, cwd, capture_output, text, timeout, shell):
        called.update({
            "cmd": cmd_list,
            "cwd": cwd,
            "capture_output": capture_output,
            "text": text,
            "timeout": timeout,
            "shell": shell,
        })
        return SimpleNamespace(stdout="ok", stderr="", returncode=0)

    monkeypatch.setattr(execution.subprocess, "run", fake_run)

    result = exec_tools.run_skill_command("run", "python", ["-V"])

    assert called["cwd"] == skill_dir
    assert called["shell"] is False
    # Command should use uv run python when uv is available
    assert called["cmd"] == ["uv", "run", "python", "-V"] or called["cmd"] == ["python3", "-V"]
    assert result["exit_code"] == 0
    assert result["timeout"] is False


def test_reindex_drops_table_when_no_skills(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    _patch_settings(monkeypatch, settings)

    class DropTrackingDB(DummyDB):
        def __init__(self):
            super().__init__(DummyTable([]))
            self.dropped = False

        def table_names(self):
            return ["skills"]

        def drop_table(self, name):
            self.dropped = True
            self.table = None

    db = DropTrackingDB()
    monkeypatch.setattr(search_mod.lancedb, "connect", lambda path: db)

    settings.skills_dir.mkdir(parents=True)

    skill_db = search_mod.SkillDB()
    skill_db.initialize_index()

    assert db.dropped is True


def test_reindex_skips_skill_with_non_mapping_frontmatter(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    _patch_settings(monkeypatch, settings)

    class DropTrackingDB(DummyDB):
        def __init__(self):
            super().__init__(DummyTable([]))
            self.dropped = False

        def table_names(self):
            return ["skills"]

        def drop_table(self, name):
            self.dropped = True
            self.table = None

    db = DropTrackingDB()
    monkeypatch.setattr(search_mod.lancedb, "connect", lambda path: db)

    skill_dir = settings.skills_dir / "bad-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
- not-a-map
---
body
""",
        encoding="utf-8",
    )

    skill_db = search_mod.SkillDB()
    skill_db.initialize_index()

    # No valid records -> table dropped; ensure no crash and drop occurred.
    assert db.dropped is True


# --- S7: Empty/wildcard query lists all ---

def test_s7_empty_query_lists_all_skills(tmp_path, monkeypatch):
    """S7: Empty query returns all enabled skills up to SEARCH_LIMIT."""
    settings = DummySettings(tmp_path)
    _patch_settings(monkeypatch, settings)

    rows = [
        {"id": "skill-a", "name": "skill-a", "description": "alpha", "category": "cat1", "_score": 1.0},
        {"id": "skill-b", "name": "skill-b", "description": "beta", "category": "cat1", "_score": 1.0},
        {"id": "skill-c", "name": "skill-c", "description": "gamma", "category": "cat2", "_score": 1.0},
    ]
    dummy_db = DummyDB(DummyTable(rows))
    monkeypatch.setattr(search_mod, "get_embedding", lambda q: None)

    db = _make_skill_db(monkeypatch, settings, dummy_db)
    search_tools = DiscoveryTools(db)

    result = search_tools.search_skills("")
    names = [s["name"] for s in result["skills"]]

    assert len(names) == 3
    assert set(names) == {"skill-a", "skill-b", "skill-c"}


def test_s7_wildcard_query_lists_all_skills(tmp_path, monkeypatch):
    """S7: Wildcard '*' query returns all enabled skills."""
    settings = DummySettings(tmp_path)
    _patch_settings(monkeypatch, settings)

    rows = [
        {"id": "x", "name": "x", "description": "x-desc", "category": "", "_score": 1.0},
        {"id": "y", "name": "y", "description": "y-desc", "category": "", "_score": 1.0},
    ]
    dummy_db = DummyDB(DummyTable(rows))
    monkeypatch.setattr(search_mod, "get_embedding", lambda q: None)

    db = _make_skill_db(monkeypatch, settings, dummy_db)
    search_tools = DiscoveryTools(db)

    result = search_tools.search_skills("*")
    names = [s["name"] for s in result["skills"]]

    assert set(names) == {"x", "y"}


def test_s7_whitespace_only_query_treated_as_empty(tmp_path, monkeypatch):
    """S7: Whitespace-only query is treated as empty (list all)."""
    settings = DummySettings(tmp_path)
    _patch_settings(monkeypatch, settings)

    rows = [
        {"id": "one", "name": "one", "description": "first", "category": "", "_score": 1.0},
        {"id": "two", "name": "two", "description": "second", "category": "", "_score": 1.0},
    ]
    dummy_db = DummyDB(DummyTable(rows))
    monkeypatch.setattr(search_mod, "get_embedding", lambda q: None)

    db = _make_skill_db(monkeypatch, settings, dummy_db)
    search_tools = DiscoveryTools(db)

    result = search_tools.search_skills("   ")
    names = [s["name"] for s in result["skills"]]

    assert set(names) == {"one", "two"}


def test_s7_empty_query_respects_enabled_filter(tmp_path, monkeypatch):
    """S7: Empty query still respects enabled_skills filter."""
    settings = DummySettings(tmp_path)
    settings.skillhub_enabled_skills = ["allowed"]
    _patch_settings(monkeypatch, settings)

    rows = [
        {"id": "allowed", "name": "allowed", "description": "ok", "category": "", "_score": 1.0},
        {"id": "blocked", "name": "blocked", "description": "no", "category": "", "_score": 1.0},
    ]
    dummy_db = DummyDB(DummyTable(rows))
    monkeypatch.setattr(search_mod, "get_embedding", lambda q: None)

    db = _make_skill_db(monkeypatch, settings, dummy_db)
    search_tools = DiscoveryTools(db)

    result = search_tools.search_skills("")
    names = [s["name"] for s in result["skills"]]

    assert names == ["allowed"]


def test_enabled_namespace_filters_results(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    settings.skillhub_enabled_namespaces = ["group/"]
    _patch_settings(monkeypatch, settings)

    rows = [
        {"id": "group/a", "name": "a", "description": "one", "category": "", "_score": 1.0},
        {"id": "other/b", "name": "b", "description": "two", "category": "", "_score": 1.0},
    ]
    dummy_db = DummyDB(DummyTable(rows))
    monkeypatch.setattr(search_mod, "get_embedding", lambda q: None)

    db = _make_skill_db(monkeypatch, settings, dummy_db)
    search_tools = DiscoveryTools(db)

    result = search_tools.search_skills("")
    ids = [s["name"] for s in result["skills"]]
    assert ids == ["a"]


def test_s7_empty_query_respects_search_limit(tmp_path, monkeypatch):
    """S7: Empty query caps results at SEARCH_LIMIT."""
    settings = DummySettings(tmp_path)
    settings.search_limit = 2
    _patch_settings(monkeypatch, settings)

    rows = [
        {"id": f"skill-{i}", "name": f"skill-{i}", "description": f"desc-{i}", "category": "", "_score": 1.0}
        for i in range(10)
    ]
    dummy_db = DummyDB(DummyTable(rows))
    monkeypatch.setattr(search_mod, "get_embedding", lambda q: None)

    db = _make_skill_db(monkeypatch, settings, dummy_db)
    search_tools = DiscoveryTools(db)

    result = search_tools.search_skills("")

    assert len(result["skills"]) == 2  # capped at SEARCH_LIMIT
