"""
Tests for hash and utility functions.
"""

import os

import pytest

from s3lync.hash import calculate_file_hash, get_file_size, verify_hash
from s3lync.utils import ensure_parent_dir, normalize_path, parse_s3_uri


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
        bucket, key, access_key, secret_key, endpoint = parse_s3_uri(
            "s3://my-bucket/path/to/file.txt"
        )
        assert bucket == "my-bucket"
        assert key == "path/to/file.txt"
        assert access_key is None
        assert secret_key is None
        assert endpoint is None

    def test_parse_s3_uri_with_endpoint(self):
        """Test S3 URI parsing with endpoint only."""
        bucket, key, access_key, secret_key, endpoint = parse_s3_uri(
            "s3://minio.example.com@my-bucket/path/to/file.txt"
        )
        assert bucket == "my-bucket"
        assert key == "path/to/file.txt"
        assert access_key is None
        assert secret_key is None
        assert endpoint == "minio.example.com"

    def test_parse_s3_uri_with_endpoint_and_credentials(self):
        """Test S3 URI parsing with endpoint and credentials."""
        bucket, key, access_key, secret_key, endpoint = parse_s3_uri(
            "s3://mysecret:myaccess@minio.example.com/my-bucket/path/to/file.txt"
        )
        assert bucket == "my-bucket"
        assert key == "path/to/file.txt"
        assert access_key == "myaccess"
        assert secret_key == "mysecret"
        assert endpoint == "minio.example.com"

    def test_parse_s3_uri_with_https_endpoint(self):
        """Test S3 URI parsing with https endpoint and credentials."""
        bucket, key, access_key, secret_key, endpoint = parse_s3_uri(
            "s3://mysecret:myaccess@https://minio.example.com/my-bucket/path/to/file.txt"
        )
        assert bucket == "my-bucket"
        assert key == "path/to/file.txt"
        assert access_key == "myaccess"
        assert secret_key == "mysecret"
        assert endpoint == "https://minio.example.com"

    def test_parse_s3_uri_with_http_endpoint(self):
        """Test S3 URI parsing with http endpoint and credentials."""
        bucket, key, access_key, secret_key, endpoint = parse_s3_uri(
            "s3://mysecret:myaccess@http://minio.example.com/my-bucket/path/to/file.txt"
        )
        assert bucket == "my-bucket"
        assert key == "path/to/file.txt"
        assert access_key == "myaccess"
        assert secret_key == "mysecret"
        assert endpoint == "http://minio.example.com"

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
