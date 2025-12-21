"""
Utility functions for s3lync.
"""

import os
from pathlib import Path
import tempfile


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    """
    Parse S3 URI to bucket and key.

    Args:
        s3_uri: S3 URI in format "s3://bucket/key"

    Returns:
        Tuple of (bucket, key)

    Raises:
        ValueError: If URI format is invalid
    """
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {s3_uri}. Must start with 's3://'")

    parts = s3_uri[5:].split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid S3 URI: {s3_uri}. Format: s3://bucket/key")

    bucket, key = parts
    if not bucket or not key:
        raise ValueError(f"Invalid S3 URI: {s3_uri}. Bucket and key cannot be empty")

    return bucket, key


def get_cache_dir() -> Path:
    """
    Get the cache directory for s3lync.

    Uses XDG_CACHE_HOME environment variable if set, otherwise ~/.cache/s3lync.
    Works consistently across Linux, macOS, and Windows.

    Returns:
        Path to cache directory
    """
    cache_home = os.getenv("XDG_CACHE_HOME")
    if cache_home:
        cache_dir = Path(cache_home) / "s3lync"
    else:
        home = os.getenv("HOME")
        if home:
            cache_dir = Path(home) / ".cache" / "s3lync"
        else:
            cache_dir = Path(tempfile.gettempdir()) / "s3lync"

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def normalize_path(path: str) -> str:
    """
    Normalize a file path.

    Args:
        path: File path

    Returns:
        Normalized path
    """
    return os.path.normpath(os.path.expanduser(path))


def ensure_parent_dir(file_path: str) -> None:
    """
    Ensure parent directory of a file exists.

    Args:
        file_path: Path to file
    """
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

