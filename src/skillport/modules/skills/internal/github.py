import os
import re
import shutil
import tarfile
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import requests

GITHUB_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)(?:/tree/(?P<ref>[^/]+)(?P<path>/.*)?)?/?$"
)

MAX_FILE_BYTES = 25_000_000  # 25MB per file (large PDFs)
MAX_DOWNLOAD_BYTES = 200_000_000  # 200MB tarball download limit
MAX_EXTRACTED_BYTES = 100_000_000  # 100MB extracted skill limit (multimodal files)
EXCLUDE_NAMES = {
    ".git",
    ".env",
    "__pycache__",
    ".DS_Store",
    ".Spotlight-V100",
    ".Trashes",  # macOS
    "Thumbs.db",
    "desktop.ini",  # Windows
    "node_modules",  # JS dependencies
}


@dataclass
class ParsedGitHubURL:
    owner: str
    repo: str
    ref: str
    path: str

    @property
    def tarball_url(self) -> str:
        return f"https://api.github.com/repos/{self.owner}/{self.repo}/tarball/{self.ref}"

    @property
    def normalized_path(self) -> str:
        return self.path.lstrip("/")


@dataclass
class GitHubFetchResult:
    """Result of fetching from GitHub including extracted path and commit info."""

    extracted_path: Path
    commit_sha: str  # Short SHA (first 7 chars typically)


def _get_default_branch(owner: str, repo: str, token: str | None) -> str:
    """Fetch default branch from GitHub API."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.ok:
            return resp.json().get("default_branch", "main")
    except Exception:
        pass
    return "main"


def parse_github_url(url: str, *, resolve_default_branch: bool = False) -> ParsedGitHubURL:
    match = GITHUB_URL_RE.match(url.strip())
    if not match:
        raise ValueError(
            "Unsupported GitHub URL. Use https://github.com/<owner>/<repo>[/tree/<ref>/<path>]"
        )

    owner = match.group("owner")
    repo = match.group("repo")
    ref = match.group("ref")
    path = match.group("path") or ""

    if ".." in path.split("/"):
        raise ValueError("Path traversal detected in URL")

    # If no ref specified, resolve default branch from API
    if not ref:
        if resolve_default_branch:
            token = os.getenv("GITHUB_TOKEN")
            ref = _get_default_branch(owner, repo, token)
        else:
            ref = "main"

    return ParsedGitHubURL(owner=owner, repo=repo, ref=ref, path=path)


def _iter_members_for_prefix(tar: tarfile.TarFile, prefix: str) -> Iterable[tarfile.TarInfo]:
    for member in tar.getmembers():
        if not member.name.startswith(prefix):
            continue
        member.name = member.name[len(prefix) :].lstrip("/")
        yield member


def download_tarball(parsed: ParsedGitHubURL, token: str | None) -> Path:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(parsed.tarball_url, headers=headers, stream=True, timeout=60)
    if resp.status_code == 404:
        raise ValueError("Repository not found or private. Set GITHUB_TOKEN for private repos.")
    if resp.status_code == 403:
        raise ValueError("GitHub API rate limit. Set GITHUB_TOKEN.")
    if not resp.ok:
        raise ValueError(f"Failed to fetch tarball: HTTP {resp.status_code}")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz")
    total = 0
    try:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise ValueError("Repository exceeds 200MB download limit")
                tmp.write(chunk)
        tmp.flush()
        return Path(tmp.name)
    finally:
        tmp.close()


def _extract_commit_sha_from_root(root_dir_name: str, owner: str, repo: str) -> str:
    """Extract commit SHA from tarball root directory name.

    GitHub tarball root dirs follow format: owner-repo-commitsha
    e.g., "anthropics-skill-repo-abc1234def"
    """
    prefix = f"{owner}-{repo}-"
    if root_dir_name.startswith(prefix):
        return root_dir_name[len(prefix) :]
    # Fallback: try to get the last part after splitting by dash
    parts = root_dir_name.split("-")
    if len(parts) >= 3:
        return parts[-1]
    return ""


def extract_tarball(tar_path: Path, parsed: ParsedGitHubURL) -> tuple[Path, str]:
    """Extract tarball and return (extracted_path, commit_sha).

    The commit SHA is extracted from the tarball root directory name.
    """
    dest_root = Path(tempfile.mkdtemp(prefix="skillport-gh-"))
    commit_sha = ""

    with tarfile.open(tar_path, "r:gz") as tar:
        roots = {member.name.split("/")[0] for member in tar.getmembers() if member.name}
        if not roots:
            raise ValueError("Tarball is empty")
        root = sorted(roots)[0]

        # Extract commit SHA from root directory name
        commit_sha = _extract_commit_sha_from_root(root, parsed.owner, parsed.repo)

        target_prefix = f"{root}/{parsed.normalized_path}".rstrip("/")
        if parsed.normalized_path:
            target_prefix = target_prefix + "/"
        else:
            target_prefix = f"{root}/"

        total_bytes = 0
        for member in _iter_members_for_prefix(tar, target_prefix):
            if not member.name:
                continue
            parts = Path(member.name).parts
            if any(p in EXCLUDE_NAMES or p.startswith(".") for p in parts):
                continue
            if member.islnk() or member.issym():
                raise ValueError(f"Symlinks are not allowed in GitHub source: {member.name}")

            dest_path = dest_root / member.name
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if member.isdir():
                dest_path.mkdir(parents=True, exist_ok=True)
                continue

            if member.size > MAX_FILE_BYTES:
                raise ValueError(f"File too large (>1MB): {member.name}")

            extracted = tar.extractfile(member)
            if not extracted:
                continue
            data = extracted.read()
            total_bytes += len(data)
            if total_bytes > MAX_EXTRACTED_BYTES:
                raise ValueError("Extracted skill exceeds 10MB limit")
            with open(dest_path, "wb") as f:
                f.write(data)

    return dest_root, commit_sha


def fetch_github_source(url: str) -> Path:
    """Fetch GitHub source and return extracted path (legacy interface)."""
    result = fetch_github_source_with_info(url)
    return result.extracted_path


def fetch_github_source_with_info(url: str) -> GitHubFetchResult:
    """Fetch GitHub source and return extracted path with commit info."""
    parsed = parse_github_url(url, resolve_default_branch=True)
    token = os.getenv("GITHUB_TOKEN")
    tar_path = download_tarball(parsed, token)
    try:
        extracted_path, commit_sha = extract_tarball(tar_path, parsed)
        return GitHubFetchResult(
            extracted_path=extracted_path,
            commit_sha=commit_sha,
        )
    finally:
        try:
            tar_path.unlink(missing_ok=True)
        except Exception:
            pass


def get_latest_commit_sha(parsed: ParsedGitHubURL, token: str | None = None) -> str:
    """Fetch the latest commit SHA for a given ref from GitHub API.

    Args:
        parsed: ParsedGitHubURL with owner, repo, and ref
        token: Optional GitHub token for auth

    Returns:
        The full commit SHA string, or empty string on error
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Use commits endpoint to resolve ref to commit
    url = f"https://api.github.com/repos/{parsed.owner}/{parsed.repo}/commits/{parsed.ref}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.ok:
            return resp.json().get("sha", "")[:40]  # Full SHA
    except Exception:
        pass
    return ""


# --- Tree-based content hash (for update checking) ---
_tree_cache: dict[tuple[str, str, str], dict] = {}


def _fetch_tree(parsed: ParsedGitHubURL, token: str | None) -> dict:
    """Fetch repo tree (recursive) with simple in-process cache."""
    cache_key = (parsed.owner, parsed.repo, parsed.ref)
    if cache_key in _tree_cache:
        return _tree_cache[cache_key]

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{parsed.owner}/{parsed.repo}/git/trees/{parsed.ref}?recursive=1"
    resp = requests.get(url, headers=headers, timeout=15)
    if not resp.ok:
        raise ValueError(f"Failed to fetch tree: HTTP {resp.status_code}")
    data = resp.json()
    if data.get("truncated"):
        raise ValueError("GitHub tree response truncated")
    _tree_cache[cache_key] = data
    return data


def rename_single_skill_dir(extracted_dir: Path, skill_name: str) -> Path:
    """Rename extracted GitHub directory to match single skill name.

    When a GitHub repo contains a single skill, the extracted temp directory
    has a random name (skillport-gh-*). This renames it to match the skill name
    from SKILL.md frontmatter for consistency.

    Args:
        extracted_dir: The temporary extraction directory
        skill_name: The skill name from SKILL.md

    Returns:
        The renamed path (or original if no rename needed)
    """
    if skill_name == extracted_dir.name:
        return extracted_dir

    renamed = extracted_dir.parent / skill_name
    if renamed.exists():
        shutil.rmtree(renamed)
    extracted_dir.rename(renamed)
    return renamed


def get_remote_tree_hash(parsed: ParsedGitHubURL, token: str | None, path: str) -> str:
    """Compute remote content hash for a skill path using the GitHub tree API.

    Returns:
        hash string "sha256:..." or "" if unavailable.
    """
    try:
        tree = _fetch_tree(parsed, token)
    except Exception:
        return ""

    base_path = (path or parsed.normalized_path).rstrip("/")
    prefix = f"{base_path}/" if base_path else ""

    entries = tree.get("tree", [])
    if not isinstance(entries, list):
        return ""

    import hashlib

    # First pass: collect valid entries with their relative paths
    valid_entries: list[tuple[str, str]] = []  # (rel_path, blob_sha)
    total_files = 0
    total_bytes = 0

    for entry in entries:
        if entry.get("type") != "blob":
            continue
        entry_path = entry.get("path", "")
        if not entry_path.startswith(prefix):
            continue
        rel = entry_path[len(prefix) :] if prefix else entry_path
        if not rel:
            continue
        parts = Path(rel).parts
        if any(part.startswith(".") for part in parts):
            continue
        if any(part in ("__pycache__", ".git") for part in parts):
            continue
        size = entry.get("size", 0) or 0
        total_bytes += size
        total_files += 1
        # thresholds mirror local hash safeguards
        if total_files > 5000 or total_bytes > 100 * 1024 * 1024:
            return ""
        blob_sha = entry.get("sha", "")
        if not blob_sha:
            continue
        valid_entries.append((rel, blob_sha))

    if not valid_entries:
        return ""

    # Sort entries by relative path to match compute_content_hash_with_reason()
    valid_entries.sort(key=lambda x: x[0])

    # Second pass: compute hash in sorted order
    hasher = hashlib.sha256()
    for rel_path, blob_sha in valid_entries:
        hasher.update(rel_path.encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(blob_sha.encode("utf-8"))
        hasher.update(b"\x00")

    return f"sha256:{hasher.hexdigest()}"
