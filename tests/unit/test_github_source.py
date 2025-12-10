"""Unit tests for GitHub URL parsing and extraction (SPEC2-CLI Section 3.3)."""

import io
import tarfile
from pathlib import Path

import pytest

from skillport.modules.skills.internal.github import (
    GITHUB_URL_RE,
    ParsedGitHubURL,
    extract_tarball,
    parse_github_url,
)


def _make_tar(tmp_path: Path, structure: dict) -> Path:
    """Create a tar.gz with given structure under root folder."""
    tar_path = tmp_path / "repo.tar.gz"
    root = "owner-repo-sha"
    with tarfile.open(tar_path, "w:gz") as tar:
        for rel, content in structure.items():
            full_name = f"{root}/{rel}"
            data = content.encode("utf-8")
            info = tarfile.TarInfo(full_name)
            info.size = len(data)
            tar.addfile(info, fileobj=io.BytesIO(data))
    return tar_path


class TestParseGitHubURL:
    """GitHub URL parsing tests."""

    def test_url_root_defaults_to_main(self):
        """URL without branch → defaults to main."""
        parsed = parse_github_url("https://github.com/user/repo")
        assert parsed.owner == "user"
        assert parsed.repo == "repo"
        assert parsed.ref == "main"
        assert parsed.normalized_path == ""

    def test_url_with_ref_and_path(self):
        """URL with branch and path → parsed correctly."""
        parsed = parse_github_url("https://github.com/user/repo/tree/feat/skills/path")
        assert parsed.owner == "user"
        assert parsed.repo == "repo"
        assert parsed.ref == "feat"
        assert parsed.normalized_path == "skills/path"

    def test_url_with_trailing_slash(self):
        """URL with trailing slash → handled correctly."""
        parsed = parse_github_url("https://github.com/user/repo/")
        assert parsed.owner == "user"
        assert parsed.repo == "repo"
        assert parsed.ref == "main"

    def test_url_tree_with_trailing_slash(self):
        """URL /tree/branch/ with trailing slash → handled correctly."""
        parsed = parse_github_url("https://github.com/user/repo/tree/main/")
        assert parsed.owner == "user"
        assert parsed.repo == "repo"
        assert parsed.ref == "main"
        assert parsed.normalized_path == ""

    def test_url_with_deep_path(self):
        """URL with deep path → parsed correctly."""
        parsed = parse_github_url("https://github.com/user/repo/tree/main/path/to/skills")
        assert parsed.normalized_path == "path/to/skills"

    def test_url_rejects_traversal(self):
        """URL with path traversal → rejected."""
        with pytest.raises(ValueError, match="traversal"):
            parse_github_url("https://github.com/user/repo/tree/main/../secret")

    def test_url_invalid_format_rejected(self):
        """Invalid URL format → rejected."""
        invalid_urls = [
            "https://gitlab.com/user/repo",
            "http://github.com/user/repo",  # http not https
            "github.com/user/repo",  # missing https
            "https://github.com/user",  # missing repo
            "https://github.com/",  # missing owner/repo
        ]
        for url in invalid_urls:
            with pytest.raises(ValueError, match="Unsupported"):
                parse_github_url(url)


class TestGitHubURLRegex:
    """GITHUB_URL_RE regex pattern tests."""

    @pytest.mark.parametrize(
        "url,expected",
        [
            # Basic URLs
            (
                "https://github.com/owner/repo",
                {"owner": "owner", "repo": "repo", "ref": None, "path": None},
            ),
            (
                "https://github.com/owner/repo/",
                {"owner": "owner", "repo": "repo", "ref": None, "path": None},
            ),
            # With branch
            (
                "https://github.com/owner/repo/tree/main",
                {"owner": "owner", "repo": "repo", "ref": "main", "path": None},
            ),
            (
                "https://github.com/owner/repo/tree/main/",
                {"owner": "owner", "repo": "repo", "ref": "main", "path": "/"},
            ),
            (
                "https://github.com/owner/repo/tree/develop",
                {"owner": "owner", "repo": "repo", "ref": "develop", "path": None},
            ),
            # With path
            (
                "https://github.com/owner/repo/tree/main/skills",
                {"owner": "owner", "repo": "repo", "ref": "main", "path": "/skills"},
            ),
            (
                "https://github.com/owner/repo/tree/main/path/to/dir",
                {"owner": "owner", "repo": "repo", "ref": "main", "path": "/path/to/dir"},
            ),
            # Special characters in owner/repo
            (
                "https://github.com/my-org/my-repo",
                {"owner": "my-org", "repo": "my-repo", "ref": None, "path": None},
            ),
            (
                "https://github.com/org123/repo456",
                {"owner": "org123", "repo": "repo456", "ref": None, "path": None},
            ),
        ],
    )
    def test_regex_matches(self, url: str, expected: dict):
        """Valid URLs should match the pattern."""
        match = GITHUB_URL_RE.match(url)
        assert match is not None
        assert match.group("owner") == expected["owner"]
        assert match.group("repo") == expected["repo"]
        assert match.group("ref") == expected["ref"]
        assert match.group("path") == expected["path"]

    @pytest.mark.parametrize(
        "url",
        [
            "https://gitlab.com/owner/repo",
            "http://github.com/owner/repo",
            "github.com/owner/repo",
            "https://github.com/owner",
            "https://github.com/",
            "https://github.com",
        ],
    )
    def test_regex_rejects_invalid(self, url: str):
        """Invalid URLs should not match."""
        assert GITHUB_URL_RE.match(url) is None


class TestExtractTarball:
    """Tarball extraction tests."""

    def test_extract_subpath(self, tmp_path):
        """Extract specific subdirectory."""
        structure = {
            "skills/a/SKILL.md": "---\nname: a\n---\nbody",
            "skills/b/SKILL.md": "---\nname: b\n---\nbody",
        }
        tar_path = _make_tar(tmp_path, structure)
        parsed = ParsedGitHubURL(owner="user", repo="repo", ref="main", path="/skills")

        dest, commit_sha = extract_tarball(tar_path, parsed)

        assert (dest / "a" / "SKILL.md").exists()
        assert (dest / "b" / "SKILL.md").exists()
        assert commit_sha == "sha"  # From "owner-repo-sha" root

    def test_extract_rejects_symlink(self, tmp_path):
        """Symlinks in tarball → rejected."""
        tar_path = tmp_path / "repo.tar.gz"
        root = "owner-repo-sha"
        with tarfile.open(tar_path, "w:gz") as tar:
            info = tarfile.TarInfo(f"{root}/skills/link")
            info.type = tarfile.SYMTYPE
            info.linkname = "evil"
            tar.addfile(info)

        parsed = ParsedGitHubURL(owner="user", repo="repo", ref="main", path="/skills")
        with pytest.raises(ValueError, match="[Ss]ymlink"):
            extract_tarball(tar_path, parsed)

    def test_extract_rejects_hardlink(self, tmp_path):
        """Hardlinks in tarball → rejected."""
        tar_path = tmp_path / "repo.tar.gz"
        root = "owner-repo-sha"
        with tarfile.open(tar_path, "w:gz") as tar:
            info = tarfile.TarInfo(f"{root}/skills/hardlink")
            info.type = tarfile.LNKTYPE
            info.linkname = "target"
            tar.addfile(info)

        parsed = ParsedGitHubURL(owner="user", repo="repo", ref="main", path="/skills")
        with pytest.raises(ValueError, match="[Ss]ymlink"):
            extract_tarball(tar_path, parsed)

    def test_extract_excludes_dotfiles(self, tmp_path):
        """Dotfiles/dirs excluded from extraction."""
        structure = {
            "skills/a/SKILL.md": "---\nname: a\n---\nbody",
            "skills/a/.hidden": "hidden content",
            "skills/.git/config": "git config",
        }
        tar_path = _make_tar(tmp_path, structure)
        parsed = ParsedGitHubURL(owner="user", repo="repo", ref="main", path="/skills")

        dest, _ = extract_tarball(tar_path, parsed)

        assert (dest / "a" / "SKILL.md").exists()
        assert not (dest / "a" / ".hidden").exists()
        assert not (dest / ".git").exists()

    def test_extract_root_path(self, tmp_path):
        """Extract from repository root."""
        structure = {
            "skill-a/SKILL.md": "---\nname: skill-a\n---\nbody",
            "skill-b/SKILL.md": "---\nname: skill-b\n---\nbody",
        }
        tar_path = _make_tar(tmp_path, structure)
        parsed = ParsedGitHubURL(owner="user", repo="repo", ref="main", path="")

        dest, _ = extract_tarball(tar_path, parsed)

        assert (dest / "skill-a" / "SKILL.md").exists()
        assert (dest / "skill-b" / "SKILL.md").exists()


# Backward compatibility - keep original test function names
def test_parse_github_url_root_defaults_to_main():
    parsed = parse_github_url("https://github.com/user/repo")
    assert parsed.owner == "user"
    assert parsed.repo == "repo"
    assert parsed.ref == "main"
    assert parsed.normalized_path == ""


def test_parse_github_url_with_ref_and_path():
    parsed = parse_github_url("https://github.com/user/repo/tree/feat/skills/path")
    assert parsed.ref == "feat"
    assert parsed.normalized_path == "skills/path"


def test_parse_github_url_rejects_traversal():
    with pytest.raises(ValueError):
        parse_github_url("https://github.com/user/repo/tree/main/../secret")


def test_extract_tarball_subpath(tmp_path):
    structure = {
        "skills/a/SKILL.md": "---\nname: a\n---\nbody",
        "skills/b/SKILL.md": "---\nname: b\n---\nbody",
    }
    tar_path = _make_tar(tmp_path, structure)
    parsed = ParsedGitHubURL(owner="user", repo="repo", ref="main", path="/skills")

    dest, commit_sha = extract_tarball(tar_path, parsed)

    assert (dest / "a" / "SKILL.md").exists()
    assert (dest / "b" / "SKILL.md").exists()
    assert commit_sha == "sha"


def test_extract_tarball_rejects_symlink(tmp_path):
    tar_path = tmp_path / "repo.tar.gz"
    root = "owner-repo-sha"
    with tarfile.open(tar_path, "w:gz") as tar:
        info = tarfile.TarInfo(f"{root}/skills/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "evil"
        tar.addfile(info)

    parsed = ParsedGitHubURL(owner="user", repo="repo", ref="main", path="/skills")
    with pytest.raises(ValueError):
        extract_tarball(tar_path, parsed)
