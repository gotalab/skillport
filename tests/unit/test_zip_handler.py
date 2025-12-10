"""Unit tests for zip_handler module."""

import zipfile

import pytest

from skillport.modules.skills.internal.zip_handler import (
    MAX_EXTRACTED_BYTES,
    MAX_FILE_BYTES,
    MAX_ZIP_FILES,
    extract_zip,
)


class TestExtractZip:
    """Tests for extract_zip function."""

    def test_extract_single_skill_zip(self, tmp_path):
        """Single skill zip is extracted correctly."""
        # Create a zip with SKILL.md
        zip_path = tmp_path / "my-skill.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("SKILL.md", "---\nname: my-skill\n---\ncontent")
            zf.writestr("README.md", "# My Skill")

        result = extract_zip(zip_path)

        assert result.extracted_path.exists()
        assert result.file_count == 2
        assert (result.extracted_path / "SKILL.md").exists()
        assert (result.extracted_path / "README.md").exists()

        # Cleanup
        import shutil

        shutil.rmtree(result.extracted_path, ignore_errors=True)

    def test_extract_multiple_skills_zip(self, tmp_path):
        """Multiple skills in zip are extracted correctly."""
        zip_path = tmp_path / "skills.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("skill-a/SKILL.md", "---\nname: skill-a\n---\na")
            zf.writestr("skill-b/SKILL.md", "---\nname: skill-b\n---\nb")
            zf.writestr("skill-c/SKILL.md", "---\nname: skill-c\n---\nc")

        result = extract_zip(zip_path)

        assert result.extracted_path.exists()
        assert result.file_count == 3
        assert (result.extracted_path / "skill-a" / "SKILL.md").exists()
        assert (result.extracted_path / "skill-b" / "SKILL.md").exists()
        assert (result.extracted_path / "skill-c" / "SKILL.md").exists()

        import shutil

        shutil.rmtree(result.extracted_path, ignore_errors=True)

    def test_extract_preserves_directory_structure(self, tmp_path):
        """Directory structure is preserved after extraction."""
        zip_path = tmp_path / "nested.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("my-skill/SKILL.md", "---\nname: my-skill\n---\n")
            zf.writestr("my-skill/lib/utils.py", "# utils")
            zf.writestr("my-skill/assets/logo.txt", "logo")

        result = extract_zip(zip_path)

        assert (result.extracted_path / "my-skill" / "SKILL.md").exists()
        assert (result.extracted_path / "my-skill" / "lib" / "utils.py").exists()
        assert (result.extracted_path / "my-skill" / "assets" / "logo.txt").exists()

        import shutil

        shutil.rmtree(result.extracted_path, ignore_errors=True)


class TestExtractZipSecurity:
    """Security tests for extract_zip function."""

    def test_rejects_path_traversal(self, tmp_path):
        """Zip with path traversal is rejected."""
        zip_path = tmp_path / "malicious.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Create entry with path traversal
            info = zipfile.ZipInfo("../../../etc/passwd")
            zf.writestr(info, "malicious content")

        with pytest.raises(ValueError, match="Path traversal"):
            extract_zip(zip_path)

    def test_rejects_absolute_path(self, tmp_path):
        """Zip with absolute path is rejected."""
        zip_path = tmp_path / "absolute.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            info = zipfile.ZipInfo("/etc/passwd")
            zf.writestr(info, "malicious content")

        with pytest.raises(ValueError, match="Path traversal"):
            extract_zip(zip_path)

    def test_rejects_too_many_files(self, tmp_path):
        """Zip with too many files is rejected."""
        zip_path = tmp_path / "many_files.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for i in range(MAX_ZIP_FILES + 1):
                zf.writestr(f"file_{i}.txt", f"content {i}")

        with pytest.raises(ValueError, match="too many files"):
            extract_zip(zip_path)

    def test_rejects_oversized_file(self, tmp_path):
        """Zip with oversized single file is rejected."""
        zip_path = tmp_path / "large_file.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Create a file larger than MAX_FILE_BYTES
            large_content = "x" * (MAX_FILE_BYTES + 1)
            zf.writestr("large.txt", large_content)

        with pytest.raises(ValueError, match="File too large"):
            extract_zip(zip_path)

    def test_rejects_oversized_total(self, tmp_path):
        """Zip with total size over limit is rejected."""
        zip_path = tmp_path / "total_large.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Create multiple files that exceed total limit
            chunk_size = MAX_FILE_BYTES - 1000  # Just under single file limit
            num_chunks = (MAX_EXTRACTED_BYTES // chunk_size) + 2
            for i in range(num_chunks):
                zf.writestr(f"chunk_{i}.txt", "x" * chunk_size)

        with pytest.raises(ValueError, match="exceeds limit"):
            extract_zip(zip_path)

    def test_rejects_symlink(self, tmp_path):
        """Zip containing symlink is rejected."""
        zip_path = tmp_path / "symlink.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            info = zipfile.ZipInfo("link")
            info.external_attr = 0o120777 << 16  # POSIX symlink
            zf.writestr(info, "target")

        with pytest.raises(ValueError, match="Symlink"):
            extract_zip(zip_path)


class TestExtractZipEdgeCases:
    """Edge case tests for extract_zip function."""

    def test_empty_zip(self, tmp_path):
        """Empty zip is handled gracefully."""
        zip_path = tmp_path / "empty.zip"
        with zipfile.ZipFile(zip_path, "w"):
            pass  # Create empty zip

        result = extract_zip(zip_path)

        assert result.extracted_path.exists()
        assert result.file_count == 0

        import shutil

        shutil.rmtree(result.extracted_path, ignore_errors=True)

    def test_zip_without_skill_md(self, tmp_path):
        """Zip without SKILL.md is extracted (detect_skills handles validation)."""
        zip_path = tmp_path / "no_skill.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("README.md", "# README")
            zf.writestr("data.json", "{}")

        result = extract_zip(zip_path)

        assert result.extracted_path.exists()
        assert result.file_count == 2
        assert not (result.extracted_path / "SKILL.md").exists()

        import shutil

        shutil.rmtree(result.extracted_path, ignore_errors=True)

    def test_hidden_files_skipped(self, tmp_path):
        """Hidden files (.gitignore, etc.) are skipped."""
        zip_path = tmp_path / "hidden.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("SKILL.md", "---\nname: test\n---\n")
            zf.writestr(".gitignore", "*.pyc")
            zf.writestr(".env", "SECRET=xxx")
            zf.writestr("normal.txt", "normal")

        result = extract_zip(zip_path)

        # Only non-hidden files should be extracted
        assert result.file_count == 2
        assert (result.extracted_path / "SKILL.md").exists()
        assert (result.extracted_path / "normal.txt").exists()
        assert not (result.extracted_path / ".gitignore").exists()
        assert not (result.extracted_path / ".env").exists()

        import shutil

        shutil.rmtree(result.extracted_path, ignore_errors=True)

    def test_excluded_directories_skipped(self, tmp_path):
        """Excluded directories (__pycache__, .git) are skipped."""
        zip_path = tmp_path / "excluded.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("SKILL.md", "---\nname: test\n---\n")
            zf.writestr("__pycache__/module.pyc", "bytecode")
            zf.writestr(".git/config", "git config")
            zf.writestr("src/main.py", "# main")

        result = extract_zip(zip_path)

        assert (result.extracted_path / "SKILL.md").exists()
        assert (result.extracted_path / "src" / "main.py").exists()
        assert not (result.extracted_path / "__pycache__").exists()
        assert not (result.extracted_path / ".git").exists()

        import shutil

        shutil.rmtree(result.extracted_path, ignore_errors=True)

    def test_nonexistent_zip_raises(self, tmp_path):
        """Non-existent zip file raises FileNotFoundError."""
        zip_path = tmp_path / "nonexistent.zip"

        with pytest.raises(FileNotFoundError):
            extract_zip(zip_path)

    def test_invalid_zip_raises(self, tmp_path):
        """Invalid zip file raises ValueError."""
        invalid_path = tmp_path / "not_a_zip.zip"
        invalid_path.write_text("this is not a zip file")

        with pytest.raises(ValueError, match="Not a valid zip"):
            extract_zip(invalid_path)
