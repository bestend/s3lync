"""
Utility functions for s3lync.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple


def parse_s3_uri(
    s3_uri: str,
) -> Tuple[str, str, Optional[str], Optional[str], Optional[str]]:
    """
    Parse S3 URI to bucket, key, and optional credentials/endpoint.

    Supports multiple formats:
    - s3://bucket/key (basic, uses environment variables for credentials)
    - s3://https://endpoint/bucket/key (custom endpoint with protocol)
    - s3://endpoint@bucket/key (custom endpoint only)
    - s3://secret_key:access_key@endpoint/bucket/key (custom endpoint + credentials)
    - s3://secret_key:access_key@https://endpoint/bucket/key (with http/https protocol)

    Args:
        s3_uri: S3 URI in format "s3://[secret_key:access_key@][https://]endpoint/bucket/key"

    Returns:
        Tuple of (bucket, key, access_key, secret_key, endpoint)
        access_key, secret_key, and endpoint are None if not provided

    Raises:
        ValueError: If URI format is invalid
    """
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {s3_uri}. Must start with 's3://'")

    # Remove "s3://" prefix
    uri_body = s3_uri[5:]

    access_key = None
    secret_key = None
    endpoint = None

    # Check for @ symbol (credentials or endpoint)
    if "@" in uri_body:
        # Split by @ to separate credentials/endpoint from the rest
        at_index = uri_body.find("@")
        first_part = uri_body[:at_index]
        rest = uri_body[at_index + 1 :]

        # Check if first_part contains credentials (has : means secret_key:access_key)
        if ":" in first_part and not first_part.startswith("http"):
            # This is credentials: secret_key:access_key
            secret_key, access_key = first_part.split(":", 1)

            # Now parse endpoint/bucket/key from rest
            # rest format could be:
            # 1. endpoint/bucket/key
            # 2. https://endpoint/bucket/key
            # 3. http://endpoint/bucket/key
            if rest.startswith("http://") or rest.startswith("https://"):
                # Extract protocol and rest
                if rest.startswith("https://"):
                    protocol = "https://"
                    rest_without_protocol = rest[8:]  # len("https://") = 8
                else:
                    protocol = "http://"
                    rest_without_protocol = rest[7:]  # len("http://") = 7

                rest_parts = rest_without_protocol.split("/", 2)
                if len(rest_parts) < 3:
                    raise ValueError(
                        f"Invalid S3 URI: {s3_uri}. Format: s3://secret_key:access_key@https://endpoint/bucket/key"
                    )
                endpoint = protocol + rest_parts[0]
                bucket, key = rest_parts[1], rest_parts[2]
            else:
                # No protocol, just endpoint/bucket/key
                rest_parts = rest.split("/", 2)
                if len(rest_parts) < 3:
                    raise ValueError(
                        f"Invalid S3 URI: {s3_uri}. Format: s3://secret_key:access_key@endpoint/bucket/key"
                    )
                endpoint, bucket, key = rest_parts[0], rest_parts[1], rest_parts[2]
        else:
            # This is endpoint: endpoint@bucket/key
            endpoint = first_part
            rest_parts = rest.split("/", 1)
            if len(rest_parts) < 2:
                raise ValueError(
                    f"Invalid S3 URI: {s3_uri}. Format: s3://endpoint@bucket/key"
                )
            bucket, key = rest_parts[0], rest_parts[1]
    else:
        # No @ symbol - check if it starts with http:// or https://
        if uri_body.startswith("http://") or uri_body.startswith("https://"):
            # Format: s3://https://endpoint/bucket/key
            if uri_body.startswith("https://"):
                protocol = "https://"
                rest_without_protocol = uri_body[8:]  # len("https://") = 8
            else:
                protocol = "http://"
                rest_without_protocol = uri_body[7:]  # len("http://") = 7

            rest_parts = rest_without_protocol.split("/", 2)
            if len(rest_parts) < 3:
                raise ValueError(
                    f"Invalid S3 URI: {s3_uri}. Format: s3://https://endpoint/bucket/key"
                )
            endpoint = protocol + rest_parts[0]
            bucket = rest_parts[1]
            key = rest_parts[2]
        else:
            # Format: bucket/key (basic, no endpoint or credentials)
            parts = uri_body.split("/", 1)
            if len(parts) < 2:
                raise ValueError(f"Invalid S3 URI: {s3_uri}. Format: s3://bucket/key")
            bucket, key = parts[0], parts[1]

    if not bucket or not key:
        raise ValueError(f"Invalid S3 URI: {s3_uri}. Bucket and key cannot be empty")

    return bucket, key, access_key, secret_key, endpoint


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
