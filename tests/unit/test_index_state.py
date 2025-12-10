from pathlib import Path
from unittest.mock import patch

from skillport.modules.indexing.internal.lancedb import IndexStore
from skillport.shared.config import Config


class DummyDB:
    def table_names(self):
        return []

    def open_table(self, name):
        return None

    def drop_table(self, name):
        return None

    def create_table(self, name, data, mode="overwrite"):
        return None


def _make_store(tmp_path: Path):
    cfg = Config(skills_dir=tmp_path / "skills", db_path=tmp_path / "db.lancedb")
    with patch(
        "skillport.modules.indexing.internal.lancedb.lancedb.connect", lambda path: DummyDB()
    ):
        return IndexStore(cfg)


def test_state_written_and_skipped_when_unchanged(tmp_path):
    skills_dir = tmp_path / "skills" / "demo"
    skills_dir.mkdir(parents=True)
    skill_md = skills_dir / "SKILL.md"
    skill_md.write_text("---\nname: demo\n---\nbody\n", encoding="utf-8")

    store = _make_store(tmp_path)

    decision = store.should_reindex()
    assert decision["need"] is True
    store.persist_state(decision["state"])

    decision2 = store.should_reindex()
    assert decision2["need"] is False
    assert decision2["reason"] == "unchanged"


def test_state_detects_change(tmp_path):
    skills_dir = tmp_path / "skills" / "demo"
    skills_dir.mkdir(parents=True)
    skill_md = skills_dir / "SKILL.md"
    skill_md.write_text("---\nname: demo\n---\nbody\n", encoding="utf-8")

    store = _make_store(tmp_path)
    decision = store.should_reindex()
    store.persist_state(decision["state"])

    skill_md.write_text("---\nname: demo\n---\nbody changed\n", encoding="utf-8")

    decision2 = store.should_reindex()
    assert decision2["need"] is True
    assert decision2["reason"] == "hash_changed"
