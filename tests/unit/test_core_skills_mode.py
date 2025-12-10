"""Unit tests for Core Skills Mode functionality."""

from unittest.mock import MagicMock, patch

from skillport.modules.indexing.public.query import get_core_skills
from skillport.shared.config import Config


class TestGetCoreSkillsAutoMode:
    """Core skills retrieval in auto mode."""

    def test_auto_mode_returns_always_apply_skills(self):
        """mode=auto returns skills with alwaysApply=true."""
        config = Config(core_skills_mode="auto")

        mock_store = MagicMock()
        mock_store.get_core_skills.return_value = [
            {"id": "skill-a", "always_apply": True},
        ]

        with patch(
            "skillport.modules.indexing.public.query.IndexStore",
            return_value=mock_store,
        ):
            result = get_core_skills(config=config)

        assert len(result) == 1
        assert result[0]["id"] == "skill-a"
        mock_store.get_core_skills.assert_called_once()


class TestGetCoreSkillsExplicitMode:
    """Core skills retrieval in explicit mode."""

    def test_explicit_mode_returns_only_specified_skills(self):
        """mode=explicit returns only skills in core_skills list."""
        config = Config(core_skills_mode="explicit", core_skills=["skill-b"])

        mock_store = MagicMock()
        mock_store.get_by_id.return_value = {
            "id": "skill-b",
            "always_apply": False,
        }

        with patch(
            "skillport.modules.indexing.public.query.IndexStore",
            return_value=mock_store,
        ):
            result = get_core_skills(config=config)

        assert len(result) == 1
        assert result[0]["id"] == "skill-b"
        mock_store.get_by_id.assert_called_once_with("skill-b")

    def test_explicit_mode_ignores_always_apply_flag(self):
        """mode=explicit ignores alwaysApply flag entirely."""
        # Empty core_skills means no core skills, even if alwaysApply exists
        config = Config(core_skills_mode="explicit", core_skills=[])

        mock_store = MagicMock()
        mock_store.get_core_skills.return_value = [
            {"id": "skill-a", "always_apply": True},
        ]

        with patch(
            "skillport.modules.indexing.public.query.IndexStore",
            return_value=mock_store,
        ):
            result = get_core_skills(config=config)

        assert result == []
        # get_core_skills should NOT be called in explicit mode
        mock_store.get_core_skills.assert_not_called()

    def test_explicit_mode_ignores_nonexistent_skills(self):
        """mode=explicit ignores skill IDs that don't exist."""
        config = Config(core_skills_mode="explicit", core_skills=["skill-a", "nonexistent"])

        mock_store = MagicMock()
        mock_store.get_by_id.side_effect = lambda sid: (
            {"id": "skill-a"} if sid == "skill-a" else None
        )

        with patch(
            "skillport.modules.indexing.public.query.IndexStore",
            return_value=mock_store,
        ):
            result = get_core_skills(config=config)

        assert len(result) == 1
        assert result[0]["id"] == "skill-a"


class TestGetCoreSkillsNoneMode:
    """Core skills retrieval in none mode."""

    def test_none_mode_returns_empty_list(self):
        """mode=none always returns empty list."""
        config = Config(core_skills_mode="none")

        mock_store = MagicMock()
        mock_store.get_core_skills.return_value = [
            {"id": "skill-a", "always_apply": True},
        ]

        with patch(
            "skillport.modules.indexing.public.query.IndexStore",
            return_value=mock_store,
        ):
            result = get_core_skills(config=config)

        assert result == []
        # IndexStore should not even be instantiated in none mode
        mock_store.get_core_skills.assert_not_called()
