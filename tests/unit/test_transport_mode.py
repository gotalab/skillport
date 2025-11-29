"""Unit tests for Transport Mode (SPEC4)."""

import base64
from unittest.mock import patch

import pytest

from skillsouko.interfaces.mcp.instructions import build_xml_instructions
from skillsouko.interfaces.mcp.server import _get_registered_tools_list
from skillsouko.modules.skills.public.types import FileContent
from skillsouko.shared.config import Config


class TestRegisteredToolsList:
    """Tests for _get_registered_tools_list helper."""

    def test_local_mode_two_tools(self):
        """Local mode (stdio) registers 2 tools."""
        tools = _get_registered_tools_list(is_remote=False)
        assert tools == ["search_skills", "load_skill"]
        assert "read_skill_file" not in tools

    def test_remote_mode_three_tools(self):
        """Remote mode (HTTP) registers 3 tools including read_skill_file."""
        tools = _get_registered_tools_list(is_remote=True)
        assert tools == ["search_skills", "load_skill", "read_skill_file"]


class TestDynamicInstructions:
    """Dynamic instruction generation tests."""

    def test_local_mode_instructions_no_read_skill_file(self):
        """Local mode instructions don't mention read_skill_file in tools list."""
        cfg = Config(core_skills_mode="none")
        tools = ["search_skills", "load_skill"]

        with patch(
            "skillsouko.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(cfg, tools)

        # Should mention using native Read tool
        assert "Use your Read tool" in result or "your native Read" in result
        # Tools section should not have read_skill_file
        lines = result.split("\n")
        tools_section = False
        tips_section = False
        for line in lines:
            if "## Tools" in line:
                tools_section = True
            if "## Tips" in line:
                tips_section = True
                tools_section = False
            if tools_section and not tips_section:
                if "read_skill_file" in line:
                    pytest.fail("read_skill_file should not be in Tools section for local mode")

    def test_remote_mode_instructions_has_read_skill_file(self):
        """Remote mode instructions include read_skill_file."""
        cfg = Config(core_skills_mode="none")
        tools = ["search_skills", "load_skill", "read_skill_file"]

        with patch(
            "skillsouko.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(cfg, tools)

        # Should mention read_skill_file
        assert "read_skill_file" in result
        # Should mention encoding
        assert "encoding" in result or "base64" in result

    def test_instructions_workflow_differs_by_mode(self):
        """Workflow step 3 differs between local and remote mode."""
        cfg = Config(core_skills_mode="none")

        with patch(
            "skillsouko.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            local = build_xml_instructions(cfg, ["search_skills", "load_skill"])
            remote = build_xml_instructions(cfg, ["search_skills", "load_skill", "read_skill_file"])

        # Local mentions Read tool
        assert "Read tool" in local or "{path}/file" in local
        # Remote mentions read_skill_file
        assert "read_skill_file" in remote

    def test_default_tools_when_none_provided(self):
        """When registered_tools is None, defaults to local mode."""
        cfg = Config(core_skills_mode="none")

        with patch(
            "skillsouko.interfaces.mcp.instructions.get_core_skills",
            return_value=[],
        ):
            result = build_xml_instructions(cfg, None)

        # Should be local mode (no read_skill_file in Tools)
        assert "your Read tool" in result or "native Read" in result


class TestFileContentType:
    """FileContent type tests."""

    def test_file_content_encoding_default_utf8(self):
        """encoding defaults to utf-8."""
        fc = FileContent(content="hello", path="/test.txt", size=5)
        assert fc.encoding == "utf-8"

    def test_file_content_mime_type_default_text_plain(self):
        """mime_type defaults to text/plain."""
        fc = FileContent(content="hello", path="/test.txt", size=5)
        assert fc.mime_type == "text/plain"

    def test_file_content_with_base64_encoding(self):
        """FileContent can have base64 encoding."""
        fc = FileContent(
            content="SGVsbG8=",
            path="/test.bin",
            size=5,
            encoding="base64",
            mime_type="application/octet-stream",
        )
        assert fc.encoding == "base64"
        assert fc.mime_type == "application/octet-stream"

    def test_file_content_with_image_mime_type(self):
        """FileContent can have image mime type."""
        fc = FileContent(
            content="iVBORw0KGgo=",
            path="/test.png",
            size=100,
            encoding="base64",
            mime_type="image/png",
        )
        assert fc.mime_type == "image/png"


class TestReadSkillFileBinarySupport:
    """Binary file support in read_skill_file."""

    def test_text_file_returns_utf8(self, tmp_path):
        """Text files return encoding=utf-8."""
        # Setup test skill
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        text_file = skill_dir / "readme.txt"
        text_file.write_text("Hello, World!", encoding="utf-8")

        skill_record = {
            "id": "test-skill",
            "path": str(skill_dir),
            "category": "",
        }

        with patch(
            "skillsouko.modules.skills.public.read.idx_get_by_id",
            return_value=skill_record,
        ):
            from skillsouko.modules.skills.public.read import read_skill_file

            cfg = Config()
            result = read_skill_file("test-skill", "readme.txt", config=cfg)

        assert result.encoding == "utf-8"
        assert result.content == "Hello, World!"
        assert "text" in result.mime_type

    def test_binary_file_returns_base64(self, tmp_path):
        """Binary files return encoding=base64."""
        # Setup test skill with binary file
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        binary_file = skill_dir / "image.png"
        # Minimal PNG header
        png_bytes = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        binary_file.write_bytes(png_bytes)

        skill_record = {
            "id": "test-skill",
            "path": str(skill_dir),
            "category": "",
        }

        with patch(
            "skillsouko.modules.skills.public.read.idx_get_by_id",
            return_value=skill_record,
        ):
            from skillsouko.modules.skills.public.read import read_skill_file

            cfg = Config()
            result = read_skill_file("test-skill", "image.png", config=cfg)

        assert result.encoding == "base64"
        assert result.mime_type == "image/png"
        # Verify base64 can be decoded
        decoded = base64.b64decode(result.content)
        assert decoded == png_bytes

    def test_json_file_returns_utf8(self, tmp_path):
        """JSON files (text extension) return encoding=utf-8."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        json_file = skill_dir / "config.json"
        json_file.write_text('{"key": "value"}', encoding="utf-8")

        skill_record = {
            "id": "test-skill",
            "path": str(skill_dir),
            "category": "",
        }

        with patch(
            "skillsouko.modules.skills.public.read.idx_get_by_id",
            return_value=skill_record,
        ):
            from skillsouko.modules.skills.public.read import read_skill_file

            cfg = Config()
            result = read_skill_file("test-skill", "config.json", config=cfg)

        assert result.encoding == "utf-8"
        assert result.content == '{"key": "value"}'

    def test_yaml_file_returns_utf8(self, tmp_path):
        """YAML files return encoding=utf-8."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        yaml_file = skill_dir / "config.yaml"
        yaml_file.write_text("key: value", encoding="utf-8")

        skill_record = {
            "id": "test-skill",
            "path": str(skill_dir),
            "category": "",
        }

        with patch(
            "skillsouko.modules.skills.public.read.idx_get_by_id",
            return_value=skill_record,
        ):
            from skillsouko.modules.skills.public.read import read_skill_file

            cfg = Config()
            result = read_skill_file("test-skill", "config.yaml", config=cfg)

        assert result.encoding == "utf-8"
        assert result.content == "key: value"

    def test_unknown_extension_binary_returns_base64(self, tmp_path):
        """Unknown extensions with binary content return base64."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        # Use a truly unknown extension
        bin_file = skill_dir / "data.qqqxxx"
        bin_file.write_bytes(bytes([0x00, 0x01, 0x02, 0xFF]))

        skill_record = {
            "id": "test-skill",
            "path": str(skill_dir),
            "category": "",
        }

        with patch(
            "skillsouko.modules.skills.public.read.idx_get_by_id",
            return_value=skill_record,
        ):
            from skillsouko.modules.skills.public.read import read_skill_file

            cfg = Config()
            result = read_skill_file("test-skill", "data.qqqxxx", config=cfg)

        assert result.encoding == "base64"
        assert result.mime_type == "application/octet-stream"
