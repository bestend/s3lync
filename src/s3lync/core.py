"""
Core S3Object class for s3lync.
"""

import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
import shutil

from .client import S3Client
from .exceptions import S3ObjectError, HashMismatchError, SyncError
from .hash import calculate_file_hash
from .utils import parse_s3_uri, normalize_path, ensure_parent_dir, get_cache_dir


class S3Object:
    """
    Represents an S3 object (file or directory) that can be synced with local filesystem.

    Provides automatic upload/download synchronization with MD5 hash verification.
    Handles both files and directories with recursive operations.
    """

    def __init__(
        self,
        s3_uri: str,
        local_path: Optional[str] = None,
        region_name: Optional[str] = None,
    ):
        """
        Initialize S3Object.

        Args:
            s3_uri: S3 URI in format "s3://bucket/key"
            local_path: Optional local file/directory path. If not provided, uses cache directory.
            region_name: AWS region name (optional)

        Raises:
            ValueError: If S3 URI format is invalid
        """
        self.s3_uri = s3_uri
        self.bucket, self.key = parse_s3_uri(s3_uri)
        self._local_path = normalize_path(local_path) if local_path else self._get_default_cache_path()
        self._client = S3Client(region_name=region_name)

    def _get_default_cache_path(self) -> str:
        """Get default cache path for this S3 object."""
        cache_dir = get_cache_dir()
        return str(cache_dir / self.bucket / self.key)

    @property
    def local_path(self) -> str:
        """Get the local file/directory path."""
        return self._local_path

    def download(self, check_hash: bool = True, force_sync: bool = False) -> str:
        """
        Download S3 object (file or directory) to local.

        Args:
            check_hash: Verify file integrity with MD5 (default: True)
            force_sync: When True, makes local identical to remote (default: False).
                - Downloads all remote files/directories
                - Deletes local files/directories not present in remote

        Returns:
            Local path

        Raises:
            SyncError: If download fails
            HashMismatchError: If hash verification fails
        """
        try:
            if self._client.is_file(self.bucket, self.key):
                self._download_file(self.key, self._local_path, check_hash, force_sync)
            else:
                self._download_dir(self.key, self._local_path, check_hash, force_sync)
        except SyncError:
            raise
        except Exception as e:
            raise SyncError(f"Download failed: {str(e)}")

        return self._local_path

    def _download_file(
        self, remote_key: str, local_path: str, check_hash: bool, force_sync: bool
    ) -> None:
        """Download single file from S3."""
        ensure_parent_dir(local_path)

        # Check if file exists and is up-to-date
        if not force_sync and self._is_equal_file(remote_key, local_path, check_hash):
            return

        # Download file
        metadata = self._client.download_file(self.bucket, remote_key, local_path)

        if check_hash:
            remote_etag = metadata.get("ETag", "").strip('"')
            local_hash = calculate_file_hash(local_path)
            # Skip hash check for multipart uploads (contains '-')
            if "-" not in remote_etag and local_hash != remote_etag:
                raise HashMismatchError(
                    f"Hash mismatch for {remote_key}: "
                    f"local={local_hash}, remote={remote_etag}"
                )

    def _download_dir(
        self, remote_prefix: str, local_dir: str, check_hash: bool, force_sync: bool
    ) -> None:
        """Download directory recursively from S3."""
        if not remote_prefix.endswith("/"):
            remote_prefix += "/"

        ensure_parent_dir(local_dir)

        # Handle force_sync - delete local files not in remote
        if force_sync and os.path.exists(local_dir):
            # Get all remote files recursively
            remote_files = set(self._client.list_files(self.bucket, remote_prefix, recursive=True))

            # Delete local files/dirs not in remote
            for root, dirs, files in os.walk(local_dir):
                # Delete files not in remote
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, local_dir).replace("\\", "/")
                    remote_key = f"{remote_prefix}{relative_path}"

                    if remote_key not in remote_files:
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass

                # Delete empty directories not in remote
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    relative_path = os.path.relpath(dir_path, local_dir).replace("\\", "/")
                    remote_dir = f"{remote_prefix}{relative_path}/"

                    # Check if this directory exists in remote
                    has_items = any(f.startswith(remote_dir) for f in remote_files)
                    if not has_items:
                        try:
                            shutil.rmtree(dir_path, ignore_errors=True)
                        except Exception:
                            pass

        # Download files and subdirectories
        paginator = self._client.client.get_paginator("list_objects_v2")
        for result in paginator.paginate(Bucket=self.bucket, Prefix=remote_prefix, Delimiter="/"):
            # Process files
            for file_obj in result.get("Contents", []):
                remote_key = file_obj["Key"]
                if remote_key == remote_prefix:
                    continue

                relative_path = os.path.relpath(remote_key, remote_prefix)
                local_file = os.path.join(local_dir, relative_path)
                self._download_file(remote_key, local_file, check_hash, force_sync)

            # Process subdirectories
            for prefix_obj in result.get("CommonPrefixes", []):
                remote_subdir = prefix_obj["Prefix"]
                relative_path = os.path.relpath(remote_subdir, remote_prefix)
                local_subdir = os.path.join(local_dir, relative_path)
                self._download_dir(remote_subdir, local_subdir, check_hash, force_sync)

    def upload(
        self,
        check_hash: bool = True,
        exclude_pattern: str = "",
        force_sync: bool = False,
    ) -> str:
        """
        Upload local object (file or directory) to S3.

        Args:
            check_hash: Verify file integrity (default: True)
            exclude_pattern: Regex pattern to exclude files (default: "")
            force_sync: When True, makes remote identical to local (default: False).
                - Uploads all local files/directories
                - Deletes remote files/directories not present in local

        Returns:
            S3 URI

        Raises:
            S3ObjectError: If local file/directory doesn't exist
            SyncError: If upload fails
        """
        if not os.path.exists(self._local_path):
            raise S3ObjectError(f"Local path does not exist: {self._local_path}")

        exclude_regex = None
        if exclude_pattern:
            exclude_regex = re.compile(exclude_pattern)

        try:
            if os.path.isfile(self._local_path):
                self._upload_file(self.key, self._local_path, check_hash, force_sync)
            else:
                self._upload_dir(
                    self.key, self._local_path, check_hash, exclude_regex, force_sync
                )
        except SyncError:
            raise
        except Exception as e:
            raise SyncError(f"Upload failed: {str(e)}")

        return self.s3_uri

    def _upload_file(
        self, remote_key: str, local_path: str, check_hash: bool, force_sync: bool
    ) -> None:
        """Upload single file to S3."""
        # Check if file exists and is up-to-date
        if not force_sync and self._is_equal_file(remote_key, local_path, check_hash):
            return

        # Upload file
        self._client.upload_file(self.bucket, remote_key, local_path)

    def _upload_dir(
        self,
        remote_prefix: str,
        local_dir: str,
        check_hash: bool,
        exclude_regex: Optional[object],
        force_sync: bool,
    ) -> None:
        """Upload directory recursively to S3."""
        if not remote_prefix.endswith("/"):
            remote_prefix += "/"

        # Handle force_sync - delete remote files not in local
        if force_sync:
            local_files = set()

            for root, dirs, files in os.walk(local_dir):
                for file in files:
                    file_path = os.path.join(root, file)

                    # Skip excluded files
                    if exclude_regex and exclude_regex.search(file_path):
                        continue

                    relative_path = os.path.relpath(file_path, local_dir).replace("\\", "/")
                    local_files.add(f"{remote_prefix}{relative_path}")

            # Delete remote files not in local
            remote_files = self._client.list_files(self.bucket, remote_prefix, recursive=True)
            for remote_file in remote_files:
                if remote_file not in local_files:
                    self._client.delete_object(self.bucket, remote_file)

        # Upload files
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_file = os.path.join(root, file)
                relative_path = os.path.relpath(local_file, local_dir).replace("\\", "/")

                # Check exclude pattern
                if exclude_regex and exclude_regex.search(local_file):
                    continue

                remote_key = f"{remote_prefix}{relative_path}"
                self._upload_file(remote_key, local_file, check_hash, force_sync)

    def _is_equal_file(self, remote_key: str, local_path: str, check_hash: bool) -> bool:
        """Check if remote and local files are equal."""
        if not self._client.is_file(self.bucket, remote_key):
            return False

        if not os.path.isfile(local_path):
            return False

        if not check_hash:
            return True

        try:
            metadata = self._client.client.head_object(Bucket=self.bucket, Key=remote_key)
            remote_etag = metadata.get("ETag", "").strip('"')
            local_hash = calculate_file_hash(local_path)

            # Skip hash check for multipart uploads
            if "-" in remote_etag:
                return True

            return local_hash == remote_etag
        except Exception:
            return False

    @contextmanager
    def open(self, mode: str = "r", encoding: str = "utf-8"):
        """
        Context manager to open S3 object as a file.

        Downloads from S3 on enter for read mode, uploads on exit for write mode.

        Args:
            mode: File mode ("r", "w", "rb", "wb", etc.)
            encoding: Text encoding (default: "utf-8")

        Yields:
            File object

        Example:
            with s3_obj.open("w") as f:
                f.write("hello world")
            # Automatically uploaded to S3 on exit
        """
        # Download if reading
        if "r" in mode:
            self.download()

        # Ensure parent directory exists for write modes
        if "w" in mode or "a" in mode or "+" in mode:
            ensure_parent_dir(self._local_path)

        # Open local file
        file_handle = open(
            self._local_path,
            mode=mode,
            encoding=encoding if "b" not in mode else None,
        )

        try:
            yield file_handle
        finally:
            file_handle.close()
            # Upload if writing
            if "w" in mode or "a" in mode or "+" in mode:
                self.upload()

    def exists(self) -> bool:
        """Check if S3 object exists."""
        return self._client.is_file(self.bucket, self.key) or self._client.is_dir(
            self.bucket, self.key
        )

    def delete(self) -> bool:
        """Delete S3 object (file or directory)."""
        return self._client.delete_object(self.bucket, self.key)

    def __repr__(self) -> str:
        """String representation of S3Object."""
        return f"S3Object(s3_uri='{self.s3_uri}', local_path='{self._local_path}')"

    def __str__(self) -> str:
        """String representation of S3Object."""
        return self.s3_uri

