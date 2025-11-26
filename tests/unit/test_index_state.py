from pathlib import Path

from skillhub_mcp.db import search as search_mod


class DummySettings:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.search_threshold = 0.2
        self.search_limit = 5
        self.embedding_provider = "none"
        self.skillhub_enabled_skills = []
        self.skillhub_enabled_categories = []
        self.skillhub_enabled_namespaces = []
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


class DummyDB:
    def table_names(self):
        return []

    def open_table(self, name):
        return None

    def drop_table(self, name):
        return None

    def create_table(self, name, data, mode="overwrite"):
        return None


def _make_db(tmp_path: Path, monkeypatch):
    settings = DummySettings(tmp_path)
    monkeypatch.setattr(search_mod, "settings", settings)
    monkeypatch.setattr(search_mod.lancedb, "connect", lambda path: DummyDB())
    return search_mod.SkillDB()


def test_state_written_and_skipped_when_unchanged(tmp_path, monkeypatch):
    skills_dir = tmp_path / "skills" / "demo"
    skills_dir.mkdir(parents=True)
    skill_md = skills_dir / "SKILL.md"
    skill_md.write_text("---\nname: demo\n---\nbody\n", encoding="utf-8")

    db = _make_db(tmp_path, monkeypatch)

    decision = db.should_reindex()
    assert decision["need"] is True
    db.persist_state(decision["state"])

    # Should load state and skip next time
    decision2 = db.should_reindex()
    assert decision2["need"] is False
    assert decision2["reason"] == "unchanged"


def test_state_detects_change(tmp_path, monkeypatch):
    skills_dir = tmp_path / "skills" / "demo"
    skills_dir.mkdir(parents=True)
    skill_md = skills_dir / "SKILL.md"
    skill_md.write_text("---\nname: demo\n---\nbody\n", encoding="utf-8")

    db = _make_db(tmp_path, monkeypatch)
    decision = db.should_reindex()
    db.persist_state(decision["state"])

    # Modify SKILL.md
    skill_md.write_text("---\nname: demo\n---\nbody changed\n", encoding="utf-8")

    decision2 = db.should_reindex()
    assert decision2["need"] is True
    assert decision2["reason"] == "hash_changed"
