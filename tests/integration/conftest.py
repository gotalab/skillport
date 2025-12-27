"""Integration-test-only pytest fixtures for SkillPort."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_skillport_indexes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure integration tests don't write under ~/.skillport/indexes.

    Many CLI/integration tests set only SKILLPORT_SKILLS_DIR, and rely on Config's
    auto-derived db/meta paths. Without this fixture, those derived paths point to
    ~/.skillport/indexes/<slug>/..., which pollutes the developer machine.
    """
    monkeypatch.setenv("SKILLPORT_DB_PATH", str(tmp_path / "index" / "skills.lancedb"))
    monkeypatch.setenv("SKILLPORT_META_DIR", str(tmp_path / "index" / "meta"))
