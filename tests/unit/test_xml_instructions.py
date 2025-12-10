"""Unit tests for XML-structured instructions (SPEC3 Section 2)."""

from unittest.mock import patch

from skillport.interfaces.mcp.instructions import (
    _escape_xml,
    build_xml_instructions,
)
from skillport.shared.config import Config


class TestXmlEscaping:
    """XML character escaping tests."""

    def test_escape_ampersand(self):
        """Ampersand is escaped."""
        assert _escape_xml("foo & bar") == "foo &amp; bar"

    def test_escape_less_than(self):
        """Less-than is escaped."""
        assert _escape_xml("a < b") == "a &lt; b"

    def test_escape_greater_than(self):
        """Greater-than is escaped."""
        assert _escape_xml("a > b") == "a &gt; b"

    def test_escape_multiple(self):
        """Multiple special characters are escaped."""
        assert _escape_xml("<a & b>") == "&lt;a &amp; b&gt;"

    def test_escape_no_special_chars(self):
        """Text without special characters unchanged."""
        assert _escape_xml("hello world") == "hello world"


class TestBuildXmlInstructionsStructure:
    """XML structure tests."""

    def test_has_skills_system_root(self):
        """Output has <skills_system> root element."""
        config = Config(core_skills_mode="none")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(config)

        assert result.startswith("<skills_system>")
        assert result.endswith("</skills_system>")

    def test_has_usage_section(self):
        """Output has <usage> section."""
        config = Config(core_skills_mode="none")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(config)

        assert "<usage>" in result
        assert "</usage>" in result

    def test_usage_contains_workflow(self):
        """Usage section contains workflow instructions."""
        config = Config(core_skills_mode="none")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(config)

        assert "## Workflow" in result
        assert "search_skills" in result
        assert "load_skill" in result

    def test_usage_contains_tools_section(self):
        """Usage section contains tools documentation."""
        config = Config(core_skills_mode="none")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            # With read_skill_file registered
            result = build_xml_instructions(
                config, ["search_skills", "load_skill", "read_skill_file"]
            )

        assert "## Tools" in result
        assert "read_skill_file" in result


class TestBuildXmlInstructionsNoCoreSkills:
    """Tests when no core skills are present."""

    def test_no_core_skills_section_when_empty(self):
        """No <core_skills> section when no core skills."""
        config = Config(core_skills_mode="none")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(config)

        assert "<core_skills>" not in result
        assert "</core_skills>" not in result

    def test_no_skill_elements_when_empty(self):
        """No <skill> elements when no core skills."""
        config = Config(core_skills_mode="none")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(config)

        assert "<skill>" not in result


class TestBuildXmlInstructionsWithCoreSkills:
    """Tests when core skills are present."""

    def test_core_skills_section_present(self):
        """<core_skills> section present when core skills exist."""
        config = Config(core_skills_mode="auto")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[
                {"id": "skill-a", "description": "Skill A description"},
            ],
        ):
            result = build_xml_instructions(config)

        assert "<core_skills>" in result
        assert "</core_skills>" in result

    def test_skill_elements_present(self):
        """<skill> elements present for each core skill."""
        config = Config(core_skills_mode="auto")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[
                {"id": "skill-a", "description": "First skill"},
                {"id": "skill-b", "description": "Second skill"},
            ],
        ):
            result = build_xml_instructions(config)

        assert result.count("<skill>") == 2
        assert result.count("</skill>") == 2

    def test_skill_has_name_element(self):
        """Each skill has <name> element."""
        config = Config(core_skills_mode="auto")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[
                {"id": "my-skill", "description": "My description"},
            ],
        ):
            result = build_xml_instructions(config)

        assert "<name>my-skill</name>" in result

    def test_skill_has_description_element(self):
        """Each skill has <description> element."""
        config = Config(core_skills_mode="auto")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[
                {"id": "my-skill", "description": "My description"},
            ],
        ):
            result = build_xml_instructions(config)

        assert "<description>My description</description>" in result

    def test_skill_uses_name_when_id_missing(self):
        """Falls back to 'name' key when 'id' is missing."""
        config = Config(core_skills_mode="auto")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[
                {"name": "fallback-name", "description": "Description"},
            ],
        ):
            result = build_xml_instructions(config)

        assert "<name>fallback-name</name>" in result

    def test_skill_handles_empty_description(self):
        """Handles skill with empty description."""
        config = Config(core_skills_mode="auto")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[
                {"id": "no-desc", "description": ""},
            ],
        ):
            result = build_xml_instructions(config)

        assert "<name>no-desc</name>" in result
        assert "<description></description>" in result


class TestBuildXmlInstructionsEscaping:
    """Tests for XML escaping in skill data."""

    def test_escapes_special_chars_in_name(self):
        """Special characters in skill name are escaped."""
        config = Config(core_skills_mode="auto")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[
                {"id": "foo<bar>", "description": "Test"},
            ],
        ):
            result = build_xml_instructions(config)

        assert "<name>foo&lt;bar&gt;</name>" in result

    def test_escapes_special_chars_in_description(self):
        """Special characters in description are escaped."""
        config = Config(core_skills_mode="auto")

        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[
                {"id": "test", "description": "Use & enjoy <skills>"},
            ],
        ):
            result = build_xml_instructions(config)

        assert "<description>Use &amp; enjoy &lt;skills&gt;</description>" in result


class TestDynamicInstructionContent:
    """Tests for dynamically generated instruction content."""

    def test_instructions_has_workflow_section(self):
        """Generated instructions contain Workflow section."""
        config = Config(core_skills_mode="none")
        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(config)
        assert "## Workflow" in result

    def test_instructions_has_tools_section(self):
        """Generated instructions contain Tools section."""
        config = Config(core_skills_mode="none")
        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(config)
        assert "## Tools" in result

    def test_instructions_has_tips_section(self):
        """Generated instructions contain Tips section."""
        config = Config(core_skills_mode="none")
        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(config)
        assert "## Tips" in result

    def test_instructions_documents_search_skills(self):
        """Generated instructions document search_skills tool."""
        config = Config(core_skills_mode="none")
        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(config)
        assert "search_skills" in result

    def test_instructions_documents_load_skill(self):
        """Generated instructions document load_skill tool."""
        config = Config(core_skills_mode="none")
        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(config)
        assert "load_skill" in result

    def test_instructions_mentions_path_placeholder(self):
        """Generated instructions mention {path} placeholder usage."""
        config = Config(core_skills_mode="none")
        with patch(
            "skillport.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(config)
        assert "{path}" in result
