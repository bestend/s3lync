"""
Tests for hash and utility functions.
"""

import pytest
import os
import tempfile

from s3lync.hash import calculate_file_hash, verify_hash, get_file_size
from s3lync.utils import parse_s3_uri, normalize_path, ensure_parent_dir


class TestHashFunctions:
    """Test hash calculation functions."""

    def test_calculate_file_hash(self, temp_dir):
        """Test hash calculation."""
        file_path = os.path.join(temp_dir, "test.txt")
        content = "test content"

        with open(file_path, "w") as f:
            f.write(content)

        hash_val = calculate_file_hash(file_path)
        assert isinstance(hash_val, str)
        assert len(hash_val) == 32  # MD5 hex digest

    def test_verify_hash_success(self, temp_dir):
        """Test hash verification success."""
        file_path = os.path.join(temp_dir, "test.txt")
        content = "test content"

        with open(file_path, "w") as f:
            f.write(content)

        hash_val = calculate_file_hash(file_path)
        assert verify_hash(file_path, hash_val) is True

    def test_verify_hash_failure(self, temp_dir):
        """Test hash verification failure."""
        file_path = os.path.join(temp_dir, "test.txt")

        with open(file_path, "w") as f:
            f.write("test content")

        assert verify_hash(file_path, "wronghash") is False

    def test_get_file_size(self, temp_dir):
        """Test file size calculation."""
        file_path = os.path.join(temp_dir, "test.txt")
        content = "test content"

        with open(file_path, "w") as f:
            f.write(content)

        size = get_file_size(file_path)
        assert size == len(content)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_parse_s3_uri_valid(self):
        """Test valid S3 URI parsing."""
        bucket, key = parse_s3_uri("s3://my-bucket/path/to/file.txt")
        assert bucket == "my-bucket"
        assert key == "path/to/file.txt"

    def test_parse_s3_uri_invalid_format(self):
        """Test invalid S3 URI format."""
        with pytest.raises(ValueError):
            parse_s3_uri("invalid://uri")

    def test_parse_s3_uri_missing_key(self):
        """Test S3 URI with missing key."""
        with pytest.raises(ValueError):
            parse_s3_uri("s3://bucket-only")

    def test_normalize_path(self):
        """Test path normalization."""
        path = "~/test/path"
        normalized = normalize_path(path)
        assert "~" not in normalized
        assert os.path.isabs(normalized)

    def test_ensure_parent_dir(self, temp_dir):
        """Test parent directory creation."""
        file_path = os.path.join(temp_dir, "subdir", "file.txt")
        ensure_parent_dir(file_path)
        assert os.path.exists(os.path.dirname(file_path))

