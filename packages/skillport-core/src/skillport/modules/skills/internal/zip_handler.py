"""Zip file handling for skill extraction."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .manager import EXCLUDE_NAMES

# Security limits (consistent with GitHub tarball handling)
MAX_EXTRACTED_BYTES = 100 * 1024 * 1024  # 100MB total (multimodal files: images, PDFs)
MAX_ZIP_FILES = 1000  # Maximum number of files in zip
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25MB per file (large PDFs)


@dataclass
class ZipExtractResult:
    """Result of extracting a zip file."""

    extracted_path: Path
    file_count: int


def _zip_rel_posix_path(name: str) -> str:
    """Normalize a zip member name to a safe POSIX-style relative path."""
    if not name:
        raise ValueError("Invalid zip entry: empty name")

    normalized = name.replace("\\", "/")
    p = PurePosixPath(normalized)

    # Reject absolute paths (covers "/x" and UNC-like "\\\\server\\share" after normalization)
    if p.is_absolute():
        raise ValueError(f"Path traversal detected: {name}")

    parts = [part for part in p.parts if part not in (".", "")]
    if not parts or any(part == ".." for part in parts):
        raise ValueError(f"Path traversal detected: {name}")

    # Reject drive-like prefixes / invalid Windows characters early (':' is invalid on Windows)
    if any(":" in part for part in parts):
        raise ValueError(f"Path traversal detected: {name}")

    return "/".join(parts)


def extract_zip(zip_path: Path) -> ZipExtractResult:
    """Extract a zip file to a temporary directory.

    Args:
        zip_path: Path to the zip file to extract

    Returns:
        ZipExtractResult: Path to extracted directory and file count

    Raises:
        FileNotFoundError: If zip file does not exist
        ValueError: If zip is invalid or violates security constraints
    """
    if not zip_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"Not a valid zip file: {zip_path}")

    temp_dir = Path(tempfile.mkdtemp(prefix="skillport-zip-"))
    total_size = 0
    file_count = 0

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Check total file count
            if len(zf.namelist()) > MAX_ZIP_FILES:
                raise ValueError(
                    f"Zip contains too many files: {len(zf.namelist())} > {MAX_ZIP_FILES}"
                )

            for info in zf.infolist():
                # Skip directories
                if info.is_dir():
                    continue

                name = info.filename
                rel_posix = _zip_rel_posix_path(name)

                # Symlink detection (posix mode 0xA000)
                if (info.external_attr >> 16) & 0xF000 == 0xA000:
                    raise ValueError(f"Symlink detected in zip: {name}")

                # Skip hidden files and excluded names
                parts = PurePosixPath(rel_posix).parts
                if any(part.startswith(".") or part in EXCLUDE_NAMES for part in parts):
                    continue

                # Single file size check
                if info.file_size > MAX_FILE_BYTES:
                    raise ValueError(
                        f"File too large: {name} ({info.file_size} > {MAX_FILE_BYTES})"
                    )

                # Cumulative size check
                total_size += info.file_size
                if total_size > MAX_EXTRACTED_BYTES:
                    raise ValueError(
                        f"Extracted size exceeds limit: {total_size} > {MAX_EXTRACTED_BYTES}"
                    )

                # Extract file (manual to avoid platform-specific path quirks)
                dest_path = temp_dir.joinpath(*PurePosixPath(rel_posix).parts)
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src, open(dest_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                file_count += 1

        return ZipExtractResult(extracted_path=temp_dir, file_count=file_count)

    except Exception:
        # Cleanup temp dir on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


__all__ = [
    "ZipExtractResult",
    "extract_zip",
    "MAX_EXTRACTED_BYTES",
    "MAX_ZIP_FILES",
    "MAX_FILE_BYTES",
]
