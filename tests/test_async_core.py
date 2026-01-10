"""
Tests for async S3Object operations.
"""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from s3lync.async_core import AsyncS3Object
from s3lync.exceptions import HashMismatchError, S3ObjectError, SyncError


@pytest.fixture
def mock_aioboto3_session():
    """Create a mock aioboto3 session."""
    session = MagicMock()
    s3_client = AsyncMock()

    # Setup context manager
    session.client.return_value.__aenter__ = AsyncMock(return_value=s3_client)
    session.client.return_value.__aexit__ = AsyncMock(return_value=None)

    return session, s3_client


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestAsyncS3ObjectInit:
    """Tests for AsyncS3Object initialization."""

    def test_basic_init(self, mock_aioboto3_session):
        """Test basic initialization."""
        session, _ = mock_aioboto3_session

        obj = AsyncS3Object(
            "s3://test-bucket/test-key.txt",
            aioboto3_session=session,
        )

        assert obj.bucket == "test-bucket"
        assert obj.key == "test-key.txt"
        assert obj.s3_uri == "s3://test-bucket/test-key.txt"

    def test_custom_local_path(self, mock_aioboto3_session, temp_dir):
        """Test initialization with custom local path."""
        session, _ = mock_aioboto3_session

        local_path = os.path.join(temp_dir, "custom.txt")
        obj = AsyncS3Object(
            "s3://test-bucket/test-key.txt",
            local_path=local_path,
            aioboto3_session=session,
        )

        assert obj.local_path == local_path

    def test_default_excludes(self, mock_aioboto3_session):
        """Test default exclude patterns are set."""
        session, _ = mock_aioboto3_session

        obj = AsyncS3Object(
            "s3://test-bucket/test-key.txt",
            aioboto3_session=session,
        )

        excludes = obj.get_excludes()
        assert r"/\." in excludes
        assert r"__pycache__" in excludes


class TestAsyncS3ObjectExcludes:
    """Tests for exclude pattern management."""

    def test_add_exclude(self, mock_aioboto3_session):
        """Test adding exclude pattern."""
        session, _ = mock_aioboto3_session

        obj = AsyncS3Object(
            "s3://test-bucket/test-key.txt",
            aioboto3_session=session,
        )

        result = obj.add_exclude(r"\.pyc$")
        assert r"\.pyc$" in obj.get_excludes()
        assert result is obj  # Method chaining

    def test_add_excludes(self, mock_aioboto3_session):
        """Test adding multiple exclude patterns."""
        session, _ = mock_aioboto3_session

        obj = AsyncS3Object(
            "s3://test-bucket/test-key.txt",
            aioboto3_session=session,
        )

        patterns = [r"\.log$", r"\.tmp$"]
        obj.add_excludes(patterns)

        excludes = obj.get_excludes()
        assert r"\.log$" in excludes
        assert r"\.tmp$" in excludes

    def test_remove_exclude(self, mock_aioboto3_session):
        """Test removing exclude pattern."""
        session, _ = mock_aioboto3_session

        obj = AsyncS3Object(
            "s3://test-bucket/test-key.txt",
            aioboto3_session=session,
        )

        obj.add_exclude(r"\.test$")
        obj.remove_exclude(r"\.test$")

        assert r"\.test$" not in obj.get_excludes()

    def test_clear_excludes(self, mock_aioboto3_session):
        """Test clearing all exclude patterns."""
        session, _ = mock_aioboto3_session

        obj = AsyncS3Object(
            "s3://test-bucket/test-key.txt",
            aioboto3_session=session,
        )

        obj.clear_excludes()
        assert obj.get_excludes() == []


class TestAsyncS3ObjectDownload:
    """Tests for async download operations."""

    @pytest.mark.asyncio
    async def test_download_file_exists_and_equal(
        self, mock_aioboto3_session, temp_dir
    ):
        """Test download skips when file exists and is equal."""
        session, s3_client = mock_aioboto3_session

        # Create local file
        local_path = os.path.join(temp_dir, "test.txt")
        with open(local_path, "w") as f:
            f.write("test content")

        obj = AsyncS3Object(
            "s3://test-bucket/test.txt",
            local_path=local_path,
            aioboto3_session=session,
        )

        # Mock _is_equal_file to return True
        with patch.object(obj, "_is_equal_file", new_callable=AsyncMock) as mock_equal:
            mock_equal.return_value = True
            with patch.object(
                obj._client, "is_file", new_callable=AsyncMock
            ) as mock_is_file:
                mock_is_file.return_value = True

                result = await obj.download()

        assert result == local_path


class TestAsyncS3ObjectUpload:
    """Tests for async upload operations."""

    @pytest.mark.asyncio
    async def test_upload_file_not_exists(self, mock_aioboto3_session, temp_dir):
        """Test upload raises error when local file doesn't exist."""
        session, _ = mock_aioboto3_session

        local_path = os.path.join(temp_dir, "nonexistent.txt")
        obj = AsyncS3Object(
            "s3://test-bucket/test.txt",
            local_path=local_path,
            aioboto3_session=session,
        )

        with pytest.raises(S3ObjectError, match="does not exist"):
            await obj.upload()


class TestAsyncS3ObjectOpen:
    """Tests for async open context manager."""

    @pytest.mark.asyncio
    async def test_open_write_mode(self, mock_aioboto3_session, temp_dir):
        """Test opening file in write mode."""
        session, _ = mock_aioboto3_session

        local_path = os.path.join(temp_dir, "write_test.txt")
        obj = AsyncS3Object(
            "s3://test-bucket/test.txt",
            local_path=local_path,
            aioboto3_session=session,
        )

        # Mock upload
        with patch.object(obj, "upload", new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = "s3://test-bucket/test.txt"

            async with obj.open("w") as f:
                f.write("test content")

            mock_upload.assert_called_once()

        # Verify file was written
        with open(local_path, "r") as f:
            assert f.read() == "test content"

    @pytest.mark.asyncio
    async def test_open_read_mode(self, mock_aioboto3_session, temp_dir):
        """Test opening file in read mode."""
        session, _ = mock_aioboto3_session

        local_path = os.path.join(temp_dir, "read_test.txt")

        # Create local file first
        with open(local_path, "w") as f:
            f.write("existing content")

        obj = AsyncS3Object(
            "s3://test-bucket/test.txt",
            local_path=local_path,
            aioboto3_session=session,
        )

        # Mock download
        with patch.object(obj, "download", new_callable=AsyncMock) as mock_download:
            mock_download.return_value = local_path

            async with obj.open("r") as f:
                content = f.read()

            mock_download.assert_called_once()

        assert content == "existing content"


class TestAsyncS3ObjectMethods:
    """Tests for other async methods."""

    @pytest.mark.asyncio
    async def test_exists(self, mock_aioboto3_session):
        """Test exists method."""
        session, _ = mock_aioboto3_session

        obj = AsyncS3Object(
            "s3://test-bucket/test.txt",
            aioboto3_session=session,
        )

        with patch.object(
            obj._client, "is_file", new_callable=AsyncMock
        ) as mock_is_file:
            mock_is_file.return_value = True

            result = await obj.exists()

        assert result is True

    @pytest.mark.asyncio
    async def test_delete(self, mock_aioboto3_session):
        """Test delete method."""
        session, _ = mock_aioboto3_session

        obj = AsyncS3Object(
            "s3://test-bucket/test.txt",
            aioboto3_session=session,
        )

        with patch.object(
            obj._client, "delete_object", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.return_value = True

            result = await obj.delete()

        assert result is True
        mock_delete.assert_called_once_with("test-bucket", "test.txt")

    def test_fspath(self, mock_aioboto3_session, temp_dir):
        """Test __fspath__ protocol."""
        session, _ = mock_aioboto3_session

        local_path = os.path.join(temp_dir, "test.txt")
        obj = AsyncS3Object(
            "s3://test-bucket/test.txt",
            local_path=local_path,
            aioboto3_session=session,
        )

        assert os.fspath(obj) == local_path

    def test_repr(self, mock_aioboto3_session):
        """Test string representation."""
        session, _ = mock_aioboto3_session

        obj = AsyncS3Object(
            "s3://test-bucket/test.txt",
            aioboto3_session=session,
        )

        repr_str = repr(obj)
        assert "AsyncS3Object" in repr_str
        assert "s3://test-bucket/test.txt" in repr_str

    def test_str(self, mock_aioboto3_session):
        """Test str conversion."""
        session, _ = mock_aioboto3_session

        obj = AsyncS3Object(
            "s3://test-bucket/test.txt",
            aioboto3_session=session,
        )

        assert str(obj) == "s3://test-bucket/test.txt"
