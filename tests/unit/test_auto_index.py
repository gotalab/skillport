"""Unit tests for CLI auto index helpers."""

from pathlib import Path
from types import SimpleNamespace

from skillport.interfaces.cli import auto_index
from skillport.shared.config import Config


class DummyCtx(SimpleNamespace):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, "meta"):
            self.meta = {}


def test_should_auto_reindex_env_overrides(monkeypatch):
    monkeypatch.setenv("SKILLPORT_AUTO_REINDEX", "0")
    ctx = DummyCtx()
    assert auto_index.should_auto_reindex(ctx) is False

    monkeypatch.setenv("SKILLPORT_AUTO_REINDEX", "1")
    assert auto_index.should_auto_reindex(ctx) is True


def test_should_auto_reindex_ctx_flag(monkeypatch):
    monkeypatch.delenv("SKILLPORT_AUTO_REINDEX", raising=False)
    ctx = DummyCtx()
    ctx.meta["auto_reindex"] = False
    assert auto_index.should_auto_reindex(ctx) is False
    ctx.meta["auto_reindex"] = True
    assert auto_index.should_auto_reindex(ctx) is True


def test_ensure_index_fresh_calls_build(monkeypatch, tmp_path: Path):
    calls = []

    def fake_should_reindex(config):
        return SimpleNamespace(need=True, reason="hash_changed")

    def fake_build_index(config, force=False):
        calls.append(("build", force))
        return SimpleNamespace(success=True, message="ok")

    monkeypatch.setenv("SKILLPORT_AUTO_REINDEX", "1")
    monkeypatch.setattr(auto_index, "should_reindex", fake_should_reindex)
    monkeypatch.setattr(auto_index, "build_index", fake_build_index)

    cfg = Config(skills_dir=tmp_path / "skills", db_path=tmp_path / "db.lancedb")
    ctx = DummyCtx()

    auto_index.ensure_index_fresh(ctx, cfg)
    assert calls == [("build", False)]


def test_ensure_index_fresh_skip_when_disabled(monkeypatch, tmp_path: Path):
    calls = []

    def fake_should_reindex(config):
        return SimpleNamespace(need=True, reason="hash_changed")

    def fake_build_index(config, force=False):
        calls.append("build")
        return SimpleNamespace(success=True, message="ok")

    monkeypatch.setenv("SKILLPORT_AUTO_REINDEX", "0")
    monkeypatch.setattr(auto_index, "should_reindex", fake_should_reindex)
    monkeypatch.setattr(auto_index, "build_index", fake_build_index)

    cfg = Config(skills_dir=tmp_path / "skills", db_path=tmp_path / "db.lancedb")
    ctx = DummyCtx()

    auto_index.ensure_index_fresh(ctx, cfg)
    assert calls == [], "should not build when disabled"
