"""
Tests for S3Object core functionality.
"""

import os
from unittest.mock import patch

import pytest

from s3lync.core import S3Object
from s3lync.exceptions import S3ObjectError
from s3lync.hash import calculate_file_hash


class TestS3ObjectInitialization:
    """Test S3Object initialization."""

    def test_init_with_s3_uri_only(self):
        """Test initialization with S3 URI only."""
        obj = S3Object("s3://my-bucket/path/to/file.txt")
        assert obj.bucket == "my-bucket"
        assert obj.key == "path/to/file.txt"
        assert obj.s3_uri == "s3://my-bucket/path/to/file.txt"
        # Local path should use cache by default
        assert "s3lync" in obj.local_path

    def test_init_with_custom_local_path(self):
        """Test initialization with custom local path."""
        local = "/tmp/myfile.txt"
        obj = S3Object("s3://my-bucket/file.txt", local_path=local)
        assert obj.local_path == local

    def test_init_with_invalid_s3_uri(self):
        """Test initialization with invalid S3 URI."""
        with pytest.raises(ValueError):
            S3Object("invalid://uri")

    def test_init_with_malformed_s3_uri(self):
        """Test initialization with malformed S3 URI."""
        with pytest.raises(ValueError):
            S3Object("s3://only-bucket")


class TestS3ObjectDownload:
    """Test S3Object download functionality."""

    def test_download_missing_local_file(self, temp_dir):
        """Test download when local file doesn't exist."""
        local_path = os.path.join(temp_dir, "test.txt")

        with patch("s3lync.core.S3Client") as MockClient:
            mock_client = MockClient.return_value
            mock_client.is_file.return_value = True
            mock_client.download_file.return_value = {"ETag": '"abc123"'}

            obj = S3Object("s3://bucket/file.txt", local_path=local_path)
            obj._client = mock_client

            obj.download(use_checksum=False)

            mock_client.download_file.assert_called_once()

    def test_download_with_hash_check(self, temp_dir):
        """Test download with hash verification."""
        local_path = os.path.join(temp_dir, "test.txt")

        with patch("s3lync.core.S3Client") as MockClient:
            mock_client = MockClient.return_value

            # Create a real file to get its hash
            with open(local_path, "w") as f:
                f.write("test content")

            file_hash = calculate_file_hash(local_path)
            mock_client.download_file.return_value = {"ETag": f'"{file_hash}"'}

            obj = S3Object("s3://bucket/file.txt", local_path=local_path)
            obj._client = mock_client

            # Should not raise
            obj.download(use_checksum=True)

    def test_download_force_sync(self, temp_dir):
        """Test download with mirror=True."""
        local_path = os.path.join(temp_dir, "test.txt")

        with open(local_path, "w") as f:
            f.write("old content")

        with patch("s3lync.core.S3Client") as MockClient:
            mock_client = MockClient.return_value
            mock_client.download_file.return_value = {"ETag": '"abc123"'}

            obj = S3Object("s3://bucket/file.txt", local_path=local_path)
            obj._client = mock_client

            obj.download(mirror=True, use_checksum=False)

            # Should be called even if local file exists
            mock_client.download_file.assert_called_once()


class TestS3ObjectUpload:
    """Test S3Object upload functionality."""

    def test_upload_success(self, temp_dir):
        """Test successful upload."""
        local_path = os.path.join(temp_dir, "test.txt")

        with open(local_path, "w") as f:
            f.write("test content")

        with patch("s3lync.core.S3Client") as MockClient:
            mock_client = MockClient.return_value
            mock_client.upload_file.return_value = {"ETag": '"abc123"'}

            obj = S3Object("s3://bucket/file.txt", local_path=local_path)
            obj._client = mock_client

            obj.upload()

            mock_client.upload_file.assert_called_once()

    def test_upload_missing_local_file(self):
        """Test upload when local file doesn't exist."""
        obj = S3Object("s3://bucket/file.txt", local_path="/nonexistent/file.txt")

        with pytest.raises(S3ObjectError):
            obj.upload()


class TestS3ObjectContextManager:
    """Test S3Object context manager functionality."""

    def test_open_read_mode(self, temp_dir):
        """Test opening S3 object in read mode."""
        local_path = os.path.join(temp_dir, "test.txt")

        with open(local_path, "w") as f:
            f.write("test content")

        with patch("s3lync.core.S3Client") as MockClient:
            mock_client = MockClient.return_value
            mock_client.is_file.return_value = True
            mock_client.download_file.return_value = {
                "ETag": '"9473fdd0d880a43c21b7778d34872157"'
            }

            obj = S3Object("s3://bucket/file.txt", local_path=local_path)
            obj._client = mock_client

            with obj.open("r") as f:
                content = f.read()

            assert "test content" in content

    def test_open_write_mode(self, temp_dir):
        """Test opening S3 object in write mode."""
        local_path = os.path.join(temp_dir, "test.txt")

        with patch("s3lync.core.S3Client") as MockClient:
            mock_client = MockClient.return_value
            mock_client.upload_file.return_value = {"ETag": '"abc123"'}

            obj = S3Object("s3://bucket/file.txt", local_path=local_path)
            obj._client = mock_client

            with obj.open("w") as f:
                f.write("new content")

            # Should call upload on context exit
            mock_client.upload_file.assert_called_once()

            # Verify local file was written
            with open(local_path, "r") as f:
                assert f.read() == "new content"
