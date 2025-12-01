import os
import re
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import requests

GITHUB_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)(?:/tree/(?P<ref>[^/]+)(?P<path>/.*)?)?/?$"
)

MAX_FILE_BYTES = 5_000_000  # 5MB per file (fonts, images, etc.)
MAX_DOWNLOAD_BYTES = 200_000_000  # 200MB tarball download limit
MAX_EXTRACTED_BYTES = 10_000_000  # 10MB extracted skill limit
EXCLUDE_NAMES = {
    ".git", ".env", "__pycache__",
    ".DS_Store", ".Spotlight-V100", ".Trashes",  # macOS
    "Thumbs.db", "desktop.ini",  # Windows
}


@dataclass
class ParsedGitHubURL:
    owner: str
    repo: str
    ref: str
    path: str

    @property
    def tarball_url(self) -> str:
        return (
            f"https://api.github.com/repos/{self.owner}/{self.repo}/tarball/{self.ref}"
        )

    @property
    def normalized_path(self) -> str:
        return self.path.lstrip("/")


def _get_default_branch(owner: str, repo: str, token: Optional[str]) -> str:
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


def _iter_members_for_prefix(
    tar: tarfile.TarFile, prefix: str
) -> Iterable[tarfile.TarInfo]:
    for member in tar.getmembers():
        if not member.name.startswith(prefix):
            continue
        member.name = member.name[len(prefix) :].lstrip("/")
        yield member


def download_tarball(parsed: ParsedGitHubURL, token: Optional[str]) -> Path:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(parsed.tarball_url, headers=headers, stream=True, timeout=60)
    if resp.status_code == 404:
        raise ValueError(
            "Repository not found or private. Set GITHUB_TOKEN for private repos."
        )
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


def extract_tarball(tar_path: Path, parsed: ParsedGitHubURL) -> Path:
    dest_root = Path(tempfile.mkdtemp(prefix="skillport-gh-"))
    with tarfile.open(tar_path, "r:gz") as tar:
        roots = {
            member.name.split("/")[0] for member in tar.getmembers() if member.name
        }
        if not roots:
            raise ValueError("Tarball is empty")
        root = sorted(roots)[0]
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
                raise ValueError(
                    f"Symlinks are not allowed in GitHub source: {member.name}"
                )

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
    return dest_root


def fetch_github_source(url: str) -> Path:
    parsed = parse_github_url(url, resolve_default_branch=True)
    token = os.getenv("GITHUB_TOKEN")
    tar_path = download_tarball(parsed, token)
    try:
        extracted = extract_tarball(tar_path, parsed)
        return extracted
    finally:
        try:
            tar_path.unlink(missing_ok=True)
        except Exception:
            pass
