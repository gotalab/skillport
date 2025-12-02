import pytest

from skillport.shared.config import Config


def test_openai_requires_key(monkeypatch):
    """provider=openai without key should fail fast."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        Config(embedding_provider="openai")
