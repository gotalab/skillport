import pytest

from skillpod.shared.config import Config


def test_openai_requires_key(monkeypatch):
    """provider=openai without key should fail fast."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        Config(embedding_provider="openai")


def test_gemini_requires_key(monkeypatch):
    """provider=gemini without key should fail fast."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError):
        Config(embedding_provider="gemini")
