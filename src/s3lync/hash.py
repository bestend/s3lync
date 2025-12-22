"""
Utility functions for hash calculation and verification.
"""

import hashlib
import os


def calculate_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """
    Calculate hash of a local file.

    Args:
        file_path: Path to the local file
        algorithm: Hash algorithm (default: "md5")

    Returns:
        Hex digest of the file hash
    """
    hash_obj = hashlib.new(algorithm)

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()


def verify_hash(file_path: str, expected_hash: str, algorithm: str = "md5") -> bool:
    """
    Verify if a file matches the expected hash.

    Args:
        file_path: Path to the local file
        expected_hash: Expected hash value
        algorithm: Hash algorithm (default: "md5")

    Returns:
        True if hash matches, False otherwise
    """
    return calculate_file_hash(file_path, algorithm) == expected_hash


def get_s3_etag(s3_response: dict[str, str]) -> str:
    """
    Extract and clean S3 ETag from response.

    Note: S3 ETags for multipart uploads are not valid MD5 hashes.
    This function returns the ETag as-is.

    Args:
        s3_response: S3 response dict containing 'ETag'

    Returns:
        Clean ETag value (without quotes)
    """
    etag: str = s3_response.get("ETag", "")
    return etag.strip('"')


def get_file_size(file_path: str) -> int:
    """
    Get size of a file in bytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in bytes
    """
    return os.path.getsize(file_path)
