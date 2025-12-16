"""Unit tests for doc command (SPEC3 Section 3)."""

from pathlib import Path

from skillport.interfaces.cli.commands.doc import (
    MARKER_END,
    MARKER_START,
    _truncate_description,
    generate_skills_block,
    update_agents_md,
)
from skillport.modules.skills import SkillSummary


class TestTruncateDescription:
    """Description truncation tests."""

    def test_short_description_unchanged(self):
        """Short descriptions are not truncated."""
        result = _truncate_description("Hello world", max_len=50)
        assert result == "Hello world"

    def test_exact_length_unchanged(self):
        """Description at exactly max length is not truncated."""
        result = _truncate_description("x" * 50, max_len=50)
        assert result == "x" * 50

    def test_long_description_truncated(self):
        """Long descriptions are truncated with ellipsis."""
        result = _truncate_description("x" * 100, max_len=50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_newlines_replaced(self):
        """Newlines are replaced with spaces."""
        result = _truncate_description("line1\nline2\nline3", max_len=50)
        assert "\n" not in result
        assert result == "line1 line2 line3"

    def test_multiple_spaces_normalized(self):
        """Multiple spaces are normalized to single space."""
        result = _truncate_description("word1   word2    word3", max_len=50)
        assert result == "word1 word2 word3"


class TestGenerateSkillsBlockXml:
    """XML format generation tests."""

    def test_has_markers(self):
        """Output has start and end markers."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="xml")
        assert MARKER_START in result
        assert MARKER_END in result

    def test_has_available_skills_tag(self):
        """XML format has <available_skills> tag."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="xml")
        assert "<available_skills>" in result
        assert "</available_skills>" in result

    def test_contains_skill_elements(self):
        """Output contains skill elements with name and description."""
        skills = [
            SkillSummary(
                id="my-skill", name="my-skill", description="My description", category="dev"
            ),
        ]
        result = generate_skills_block(skills, format="xml")
        assert "<skill>" in result
        assert "<name>my-skill</name>" in result
        assert "<description>My description</description>" in result
        assert "</skill>" in result

    def test_has_workflow_instructions(self):
        """Output has workflow instructions for agents."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="xml")
        assert "### Workflow" in result
        assert "skillport show" in result
        # Should explain what skills are
        assert "expert knowledge" in result.lower() or "instructions" in result.lower()

    def test_instructions_come_before_skills_list(self):
        """Workflow instructions appear before skills list."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="xml")
        workflow_pos = result.find("### Workflow")
        skills_pos = result.find("<available_skills>")
        assert workflow_pos < skills_pos, "Workflow should come before skills list"

    def test_has_tips_section(self):
        """Output has tips for agents."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="xml")
        assert "### Tips" in result
        assert "{path}" in result

    def test_multiple_skills(self):
        """Multiple skills appear as XML elements."""
        skills = [
            SkillSummary(id="skill-a", name="skill-a", description="First", category=""),
            SkillSummary(id="skill-b", name="skill-b", description="Second", category=""),
        ]
        result = generate_skills_block(skills, format="xml")
        assert "<name>skill-a</name>" in result
        assert "<description>First</description>" in result
        assert "<name>skill-b</name>" in result
        assert "<description>Second</description>" in result

    def test_skills_inside_available_skills_tag(self):
        """Skill elements are wrapped inside <available_skills> tag."""
        skills = [
            SkillSummary(id="test", name="test", description="Test", category=""),
        ]
        result = generate_skills_block(skills, format="xml")
        # Find positions
        start_tag = result.find("<available_skills>")
        end_tag = result.find("</available_skills>")
        skill_element = result.find("<skill>")
        assert start_tag < skill_element < end_tag, "Skill should be inside <available_skills> tag"

    def test_long_description_not_truncated(self):
        """Long descriptions are NOT truncated in AGENTS.md."""
        long_desc = "x" * 100
        skills = [
            SkillSummary(id="test", name="test", description=long_desc, category=""),
        ]
        result = generate_skills_block(skills, format="xml")
        # Full description should be present
        assert long_desc in result


class TestGenerateSkillsBlockMcpMode:
    """MCP mode generation tests."""

    def test_mcp_mode_has_mcp_workflow(self):
        """MCP mode includes MCP-specific workflow."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="xml", mode="mcp")
        assert "search_skills" in result
        assert "load_skill" in result

    def test_mcp_mode_has_tools_section(self):
        """MCP mode includes Tools section."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="xml", mode="mcp")
        assert "### Tools" in result
        # read_skill_file is HTTP-only, so not included in sync output
        # (sync generates instructions for Local/stdio mode)
        assert "search_skills" in result
        assert "load_skill" in result

    def test_cli_mode_does_not_have_mcp_tools(self):
        """CLI mode does not include MCP tools."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="xml", mode="cli")
        assert "search_skills" not in result
        assert "skillport show" in result


class TestGenerateSkillsBlockSkillsOnly:
    """Skills-only output tests."""

    def test_skills_only_no_markers(self):
        """Skills-only mode excludes markers."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="xml", skills_only=True)
        assert MARKER_START not in result
        assert MARKER_END not in result

    def test_skills_only_no_instructions(self):
        """Skills-only mode excludes instructions."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="xml", skills_only=True)
        assert "### Workflow" not in result
        assert "### Tips" not in result

    def test_skills_only_has_available_skills_tag(self):
        """Skills-only mode still has <available_skills> wrapper."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="xml", skills_only=True)
        assert result.startswith("<available_skills>")
        assert result.endswith("</available_skills>")

    def test_skills_only_has_skill_elements(self):
        """Skills-only mode contains skill elements."""
        skills = [
            SkillSummary(id="my-skill", name="my-skill", description="My desc", category=""),
        ]
        result = generate_skills_block(skills, format="xml", skills_only=True)
        assert "<skill>" in result
        assert "<name>my-skill</name>" in result
        assert "<description>My desc</description>" in result

    def test_skills_only_markdown_format(self):
        """Skills-only mode works with markdown format."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category=""),
        ]
        result = generate_skills_block(skills, format="markdown", skills_only=True)
        assert MARKER_START not in result
        assert "- `test`: Test skill" in result


class TestGenerateSkillsBlockMarkdown:
    """Markdown format generation tests."""

    def test_has_markers(self):
        """Output has start and end markers."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="markdown")
        assert MARKER_START in result
        assert MARKER_END in result

    def test_no_available_skills_tag(self):
        """Markdown format does not have <available_skills> tag."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="markdown")
        assert "<available_skills>" not in result

    def test_has_header(self):
        """Markdown format has ## header."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="markdown")
        assert "## SkillPort Skills" in result

    def test_has_skill_list(self):
        """Markdown format has skill list."""
        skills = [
            SkillSummary(id="test", name="test", description="Test skill", category="test"),
        ]
        result = generate_skills_block(skills, format="markdown")
        assert "- `test`: Test skill" in result


class TestUpdateAgentsMd:
    """AGENTS.md file update tests."""

    def test_creates_new_file(self, tmp_path: Path):
        """Creates new file if doesn't exist."""
        output = tmp_path / "AGENTS.md"
        block = f"{MARKER_START}\ntest\n{MARKER_END}"

        result = update_agents_md(output, block)

        assert result is True
        assert output.exists()
        content = output.read_text()
        assert MARKER_START in content
        assert MARKER_END in content

    def test_replaces_existing_block(self, tmp_path: Path):
        """Replaces existing block between markers."""
        output = tmp_path / "AGENTS.md"
        output.write_text(f"# Header\n\n{MARKER_START}\nold content\n{MARKER_END}\n\n# Footer")
        new_block = f"{MARKER_START}\nnew content\n{MARKER_END}"

        result = update_agents_md(output, new_block)

        assert result is True
        content = output.read_text()
        assert "new content" in content
        assert "old content" not in content
        assert "# Header" in content
        assert "# Footer" in content

    def test_appends_to_existing_file(self, tmp_path: Path):
        """Appends to file without markers when append=True."""
        output = tmp_path / "AGENTS.md"
        output.write_text("# Existing content\n\nSome text here.")
        new_block = f"{MARKER_START}\nnew block\n{MARKER_END}"

        result = update_agents_md(output, new_block, append=True)

        assert result is True
        content = output.read_text()
        assert "# Existing content" in content
        assert "new block" in content

    def test_replaces_entire_file(self, tmp_path: Path):
        """Replaces entire file when append=False."""
        output = tmp_path / "AGENTS.md"
        output.write_text("# Existing content\n\nSome text here.")
        new_block = f"{MARKER_START}\nnew block\n{MARKER_END}"

        result = update_agents_md(output, new_block, append=False)

        assert result is True
        content = output.read_text()
        assert "# Existing content" not in content
        assert "new block" in content

    def test_preserves_content_around_markers(self, tmp_path: Path):
        """Content before and after markers is preserved."""
        output = tmp_path / "AGENTS.md"
        output.write_text(f"# Before\n\n{MARKER_START}\noriginal\n{MARKER_END}\n\n# After")
        new_block = f"{MARKER_START}\nreplaced\n{MARKER_END}"

        update_agents_md(output, new_block)

        content = output.read_text()
        assert "# Before" in content
        assert "# After" in content
        assert "replaced" in content
        assert "original" not in content

    def test_creates_parent_directories(self, tmp_path: Path):
        """Creates parent directories if they don't exist."""
        output = tmp_path / "subdir" / "nested" / "AGENTS.md"
        block = f"{MARKER_START}\ntest\n{MARKER_END}"

        result = update_agents_md(output, block)

        assert result is True
        assert output.exists()
        assert output.parent.exists()
        content = output.read_text()
        assert MARKER_START in content


class TestGenerateSkillsBlockSpecialChars:
    """Special character handling in descriptions."""

    def test_pipe_in_description_preserved(self):
        """Pipe characters are preserved in XML format."""
        skills = [
            SkillSummary(
                id="test",
                name="test",
                description="Use | for piping",
                category="",
            ),
        ]
        result = generate_skills_block(skills, format="xml")
        # Pipe should be preserved (no escaping needed in XML)
        assert "<description>Use | for piping</description>" in result

    def test_xml_special_chars_escaped(self):
        """XML special characters are escaped in XML format."""
        skills = [
            SkillSummary(
                id="test",
                name="test",
                description="Use <tag> & other",
                category="",
            ),
        ]
        result = generate_skills_block(skills, format="xml")
        assert "<description>Use &lt;tag&gt; &amp; other</description>" in result


class TestSyncWithProjectConfig:
    """Tests for sync using project config."""

    def test_update_agents_md_from_project_config(self, tmp_path: Path):
        """Update multiple files from project config instructions."""
        # This tests the underlying function, not the CLI option
        block = f"{MARKER_START}\ntest content\n{MARKER_END}"

        # Create instruction files
        agents_md = tmp_path / "AGENTS.md"
        gemini_md = tmp_path / "GEMINI.md"

        # Update files
        update_agents_md(agents_md, block)
        update_agents_md(gemini_md, block)

        # Files should be updated
        assert agents_md.exists()
        assert gemini_md.exists()
        assert MARKER_START in agents_md.read_text()
        assert MARKER_START in gemini_md.read_text()
