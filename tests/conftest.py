"""Shared pytest fixtures for SkillPort tests."""

from pathlib import Path

import pytest

from skillport.shared.config import Config


@pytest.fixture
def test_config(tmp_path: Path) -> Config:
    """Create a Config that uses temporary directories.

    This ensures tests don't pollute ~/.skillport/ with indexes or metadata.
    """
    return Config(
        skills_dir=tmp_path / "skills",
        db_path=tmp_path / "index" / "skills.lancedb",
    )
