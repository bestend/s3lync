"""
Core S3Object class for s3lync.
"""

import os
import re
import shutil
from contextlib import contextmanager
from typing import Any, Callable, Iterator, List, Optional, Union

from .client import S3Client
from .exceptions import HashMismatchError, S3ObjectError, SyncError
from .hash import calculate_file_hash
from .progress import ProgressBar
from .utils import ensure_parent_dir, get_cache_dir, normalize_path, parse_s3_uri


class S3Object:
    """
    Represents an S3 object (file or directory) synchronized with local filesystem.

    Provides automatic upload/download synchronization with MD5 hash
    verification. Handles both files and directories with recursive operations.
    """

    _excludes: list[str]

    def __init__(
        self,
        s3_uri: str,
        local_path: Optional[str] = None,
        boto3_client: Optional[object] = None,
        excludes: Union[str, List[str], None] = None,
        progress_mode: str = "progress",
    ):
        """
        Initialize S3Object.

        Args:
            s3_uri: S3 URI (s3://bucket/key, s3://endpoint@bucket/key, etc)
            local_path: Local file/directory path (optional)
            boto3_client: Pre-configured boto3 S3 client (recommended)
            excludes: Exclude patterns (overrides default if provided)
            progress_mode: Progress display mode: "progress", "compact",
                          "disabled" (default: "progress")

        Example:
            session = boto3.Session(profile_name="dev")
            obj = S3Object("s3://bucket/key", boto3_client=session.client("s3"))
        """
        self.s3_uri = s3_uri
        self.progress_mode = progress_mode
        (
            self.bucket,
            self.key,
            self._access_key,
            self._secret_key,
            self._endpoint,
        ) = parse_s3_uri(s3_uri)
        self._local_path = (
            normalize_path(local_path) if local_path else self._get_default_cache_path()
        )

        # Initialize excludes with default hidden file patterns
        # Or override with user-provided excludes if given
        if excludes:
            # User provided excludes - override defaults completely
            if isinstance(excludes, str):
                self._excludes = [excludes]
            else:  # list
                self._excludes = excludes.copy()
        else:
            # Use default excludes: hidden files, Python cache, and egg info
            self._excludes = [
                r"/\.",  # Hidden files/dirs (.git, .pytest_cache, .venv, etc)
                r"__pycache__",  # Python cache
                r"\.egg-info",  # Egg info
            ]

        # Initialize S3Client
        if boto3_client is not None:
            # Use the provided boto3 client directly
            self._client = S3Client(client=boto3_client)
        else:
            # Create boto3 client from S3 URI credentials and endpoint
            import boto3

            session = boto3.Session(
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
            )
            created_client = session.client("s3", endpoint_url=self._endpoint)
            self._client = S3Client(client=created_client)

    def _get_default_cache_path(self) -> str:
        """Get default cache path for this S3 object."""
        cache_dir = get_cache_dir()
        return str(cache_dir / self.bucket / self.key)

    @property
    def local_path(self) -> str:
        """Get the local file/directory path."""
        return self._local_path

    def download(
        self,
        use_checksum: bool = True,
        excludes: Union[str, List[str], None] = None,
        progress_mode: Optional[str] = None,
        mirror: bool = False,
    ) -> str:
        """
        Download S3 object (file or directory) to local.

        Args:
            use_checksum: Verify file integrity with MD5 (default: True)
            excludes: Additional regex pattern(s) to exclude (in addition to defaults)
            progress_mode: Progress display mode ("progress", "compact", "disabled").
                          If None, uses object's default
            mirror: When True, makes local identical to remote (default: False)

        Returns:
            Local path

        Raises:
            SyncError: If download fails
            HashMismatchError: If hash verification fails
        """
        # Use provided progress_mode or fall back to object's default
        actual_progress_mode = progress_mode or self.progress_mode

        # Combine self._excludes with excludes parameter
        all_excludes = self._excludes.copy()
        if excludes:
            if isinstance(excludes, str):
                all_excludes.append(excludes)
            elif isinstance(excludes, list):
                all_excludes.extend(excludes)

        try:
            if self._client.is_file(self.bucket, self.key):
                self._download_file(
                    self.key,
                    self._local_path,
                    use_checksum,
                    mirror,
                    progress_mode=actual_progress_mode,
                )
            else:
                self._download_dir(
                    self.key,
                    self._local_path,
                    use_checksum,
                    mirror,
                    all_excludes,
                    actual_progress_mode,
                )
        except SyncError:
            raise
        except Exception as e:
            raise SyncError(f"Download failed: {str(e)}") from e

        return self._local_path

    def _download_file(
        self,
        remote_key: str,
        local_path: str,
        use_checksum: bool,
        mirror: bool,
        callback: Optional[Callable[[int], None]] = None,
        progress_mode: Optional[str] = None,
        progress_position: Optional[int] = None,
        progress_leave: Optional[bool] = None,
    ) -> None:
        """Download single file from S3."""
        ensure_parent_dir(local_path)

        # Check if file exists and is up-to-date
        if not mirror and self._is_equal_file(remote_key, local_path, use_checksum):
            return

        # Download file
        metadata = self._client.download_file(
            self.bucket,
            remote_key,
            local_path,
            callback=callback,
            progress_mode=progress_mode,
            progress_position=progress_position,
            progress_leave=progress_leave,
        )

        if use_checksum:
            if metadata is None:
                raise S3ObjectError(f"Failed to get metadata for {remote_key}")
            etag_value = metadata.get("ETag", "")
            remote_etag: str = str(etag_value).strip('"')
            local_hash = calculate_file_hash(local_path)
            # Skip hash check for multipart uploads (contains '-')
            if "-" not in remote_etag and local_hash != remote_etag:
                raise HashMismatchError(
                    f"Hash mismatch for {remote_key}: "
                    f"local={local_hash}, remote={remote_etag}"
                )

    def _download_dir(
        self,
        remote_prefix: str,
        local_dir: str,
        use_checksum: bool,
        mirror: bool,
        excludes: Union[str, List[str], None] = None,
        progress_mode: Optional[str] = None,
    ) -> None:
        """Download directory recursively from S3."""
        # Use provided progress_mode or fall back to object's default
        actual_progress_mode = progress_mode or self.progress_mode

        # Convert excludes to regex patterns
        exclude_regexes: list[re.Pattern[str]] = []
        if excludes:
            if isinstance(excludes, str):
                exclude_regexes = [re.compile(excludes)]
            elif isinstance(excludes, list):
                exclude_regexes = [re.compile(pattern) for pattern in excludes]

        if not remote_prefix.endswith("/"):
            remote_prefix += "/"

        ensure_parent_dir(local_dir)

        # Handle mirror - delete local files not in remote
        if mirror and os.path.exists(local_dir):
            # Get all remote files recursively
            remote_files = set(
                self._client.list_files(self.bucket, remote_prefix, recursive=True)
            )

            # Delete local files/dirs not in remote
            for root, dirs, files in os.walk(local_dir):
                # Delete files not in remote
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, local_dir).replace(
                        "\\", "/"
                    )
                    remote_key = f"{remote_prefix}{relative_path}"

                    if remote_key not in remote_files:
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass

                # Delete empty directories not in remote
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    relative_path = os.path.relpath(dir_path, local_dir).replace(
                        "\\", "/"
                    )
                    remote_dir = f"{remote_prefix}{relative_path}/"

                    # Check if this directory exists in remote
                    has_items = any(f.startswith(remote_dir) for f in remote_files)
                    if not has_items:
                        try:
                            shutil.rmtree(dir_path, ignore_errors=True)
                        except Exception:
                            pass

        # Pre-scan to compute totals (files and bytes)
        total_files = 0
        total_bytes = 0
        paginator = self._client.client.get_paginator("list_objects_v2")
        for result in paginator.paginate(Bucket=self.bucket, Prefix=remote_prefix):
            for file_obj in result.get("Contents", []):
                remote_key = file_obj["Key"]
                if remote_key == remote_prefix:
                    continue
                relative_path = os.path.relpath(remote_key, remote_prefix)
                local_file = os.path.join(local_dir, relative_path)
                if any(regex.search(local_file) for regex in exclude_regexes):
                    continue
                total_files += 1
                try:
                    total_bytes += int(file_obj.get("Size", 0))
                except Exception:
                    pass

        # Print initial summary
        print(f"Total: {total_files} files, {total_bytes} bytes")

        # Overall progress bar (bytes-based)
        overall_pbar = ProgressBar(
            total=total_bytes,
            desc="[overall]",
            mode=actual_progress_mode,
            position=0,
            leave=True,
        )

        # Download files and subdirectories (hierarchical walk)
        paginator = self._client.client.get_paginator("list_objects_v2")
        for result in paginator.paginate(
            Bucket=self.bucket, Prefix=remote_prefix, Delimiter="/"
        ):
            # Process files
            for file_obj in result.get("Contents", []):
                remote_key = file_obj["Key"]
                if remote_key == remote_prefix:
                    continue

                relative_path = os.path.relpath(remote_key, remote_prefix)
                local_file = os.path.join(local_dir, relative_path)

                # Check exclude pattern
                if any(regex.search(local_file) for regex in exclude_regexes):
                    continue

                # Create callback for overall progress
                def overall_callback(n: int) -> None:
                    try:
                        overall_pbar.update(n)
                    except Exception:
                        pass

                self._download_file(
                    remote_key,
                    local_file,
                    use_checksum,
                    mirror,
                    callback=overall_callback,
                    progress_mode=actual_progress_mode,
                    progress_position=1,
                    progress_leave=False,
                )

            # Process subdirectories
            for prefix_obj in result.get("CommonPrefixes", []):
                remote_subdir = prefix_obj["Prefix"]
                relative_path = os.path.relpath(remote_subdir, remote_prefix)
                local_subdir = os.path.join(local_dir, relative_path)
                self._download_dir(
                    remote_subdir,
                    local_subdir,
                    use_checksum,
                    mirror,
                    excludes,
                    progress_mode,
                )

        # Close overall progress
        try:
            overall_pbar.close()
        except Exception:
            pass

    def upload(
        self,
        use_checksum: bool = True,
        excludes: Union[str, List[str], None] = None,
        progress_mode: Optional[str] = None,
        mirror: bool = False,
    ) -> str:
        """
        Upload local object (file or directory) to S3.

        Args:
            use_checksum: Verify file integrity (default: True)
            excludes: Additional regex pattern(s) to exclude (in addition to defaults)
            progress_mode: Progress display mode ("progress", "compact", "disabled").
                          If None, uses object's default
            mirror: When True, makes remote identical to local (default: False)

        Returns:
            S3 URI

        Raises:
            S3ObjectError: If local file/directory doesn't exist
            SyncError: If upload fails
        """
        if not os.path.exists(self._local_path):
            raise S3ObjectError(f"Local path does not exist: {self._local_path}")

        # Use provided progress_mode or fall back to object's default
        actual_progress_mode = progress_mode or self.progress_mode

        # Combine self._excludes with excludes parameter
        all_excludes = self._excludes.copy()
        if excludes:
            if isinstance(excludes, str):
                all_excludes.append(excludes)
            elif isinstance(excludes, list):
                all_excludes.extend(excludes)

        # Convert excludes to regex patterns
        exclude_regexes: list[re.Pattern[str]] = [
            re.compile(pattern) for pattern in all_excludes
        ]

        try:
            if os.path.isfile(self._local_path):
                self._upload_file(
                    self.key,
                    self._local_path,
                    use_checksum,
                    mirror,
                    progress_mode=actual_progress_mode,
                )
            else:
                self._upload_dir(
                    self.key,
                    self._local_path,
                    use_checksum,
                    exclude_regexes,
                    mirror,
                    actual_progress_mode,
                )
        except SyncError:
            raise
        except Exception as e:
            raise SyncError(f"Upload failed: {str(e)}") from e

        return self.s3_uri

    def _upload_file(
        self,
        remote_key: str,
        local_path: str,
        use_checksum: bool,
        mirror: bool,
        callback: Optional[Callable[[int], None]] = None,
        progress_mode: Optional[str] = None,
        progress_position: Optional[int] = None,
        progress_leave: Optional[bool] = None,
    ) -> None:
        """Upload single file to S3."""
        # Check if file exists and is up-to-date
        if not mirror and self._is_equal_file(remote_key, local_path, use_checksum):
            return

        # Upload file
        self._client.upload_file(
            self.bucket,
            remote_key,
            local_path,
            callback=callback,
            progress_mode=progress_mode,
            progress_position=progress_position,
            progress_leave=progress_leave,
        )

    def _upload_dir(
        self,
        remote_prefix: str,
        local_dir: str,
        use_checksum: bool,
        exclude_regexes: List[re.Pattern[str]],
        mirror: bool,
        progress_mode: Optional[str] = None,
    ) -> None:
        """Upload directory recursively to S3."""
        # Use provided progress_mode or fall back to object's default
        actual_progress_mode = progress_mode or self.progress_mode

        if not remote_prefix.endswith("/"):
            remote_prefix += "/"

        # Handle mirror - delete remote files not in local
        if mirror:
            local_files = set()

            for root, _dirs, files in os.walk(local_dir):
                for file in files:
                    file_path = os.path.join(root, file)

                    # Skip excluded files
                    if any(regex.search(file_path) for regex in exclude_regexes):
                        continue

                    relative_path = os.path.relpath(file_path, local_dir).replace(
                        "\\", "/"
                    )
                    local_files.add(f"{remote_prefix}{relative_path}")

            # Delete remote files not in local
            remote_files = self._client.list_files(
                self.bucket, remote_prefix, recursive=True
            )
            for remote_file in remote_files:
                if remote_file not in local_files:
                    self._client.delete_object(self.bucket, remote_file)

        # Pre-scan local files to compute totals
        total_files = 0
        total_bytes = 0
        for root, _dirs, files in os.walk(local_dir):
            for file in files:
                local_file = os.path.join(root, file)
                if any(regex.search(local_file) for regex in exclude_regexes):
                    continue
                total_files += 1
                try:
                    total_bytes += os.path.getsize(local_file)
                except Exception:
                    pass

        # Print initial summary
        print(f"Total: {total_files} files, {total_bytes} bytes")

        # Overall progress bar (bytes-based)
        overall_pbar = ProgressBar(
            total=total_bytes,
            desc="[overall]",
            mode=actual_progress_mode,
            position=0,
            leave=True,
        )

        # Upload files
        for root, _dirs, files in os.walk(local_dir):
            for file in files:
                local_file = os.path.join(root, file)
                relative_path = os.path.relpath(local_file, local_dir).replace(
                    "\\", "/"
                )

                # Check exclude pattern
                if any(regex.search(local_file) for regex in exclude_regexes):
                    continue

                remote_key = f"{remote_prefix}{relative_path}"

                # Create callback for overall progress
                def overall_callback(n: int) -> None:
                    try:
                        overall_pbar.update(n)
                    except Exception:
                        pass

                self._upload_file(
                    remote_key,
                    local_file,
                    use_checksum,
                    mirror,
                    callback=overall_callback,
                    progress_mode=actual_progress_mode,
                    progress_position=1,
                    progress_leave=False,
                )

        # Close overall progress
        try:
            overall_pbar.close()
        except Exception:
            pass

    def _is_equal_file(
        self, remote_key: str, local_path: str, use_checksum: bool
    ) -> bool:
        """Check if remote and local files are equal."""
        if not self._client.is_file(self.bucket, remote_key):
            return False

        if not os.path.isfile(local_path):
            return False

        if not use_checksum:
            return True

        try:
            metadata = self._client.client.head_object(
                Bucket=self.bucket, Key=remote_key
            )
            remote_etag: str = metadata.get("ETag", "")
            remote_etag = remote_etag.strip('"')
            local_hash = calculate_file_hash(local_path)

            # Skip hash check for multipart uploads
            if "-" in remote_etag:
                return True

            return bool(local_hash == remote_etag)
        except Exception:
            return False

    @contextmanager
    def open(self, mode: str = "r", encoding: str = "utf-8") -> Iterator[Any]:
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

    def add_exclude(self, pattern: str) -> "S3Object":
        """
        Add an exclude pattern.

        Args:
            pattern: Regex pattern to exclude

        Returns:
            self for method chaining
        """
        if pattern not in self._excludes:
            self._excludes.append(pattern)
        return self

    def add_excludes(self, patterns: list[str]) -> "S3Object":
        """
        Add multiple exclude patterns.

        Args:
            patterns: List of regex patterns to exclude

        Returns:
            self for method chaining
        """
        for pattern in patterns:
            self.add_exclude(pattern)
        return self

    def remove_exclude(self, pattern: str) -> "S3Object":
        """
        Remove an exclude pattern.

        Args:
            pattern: Regex pattern to remove

        Returns:
            self for method chaining
        """
        if pattern in self._excludes:
            self._excludes.remove(pattern)
        return self

    def clear_excludes(self) -> "S3Object":
        """
        Clear all exclude patterns.

        Returns:
            self for method chaining
        """
        self._excludes.clear()
        return self

    def get_excludes(self) -> list[str]:
        """
        Get all exclude patterns.

        Returns:
            List of exclude patterns
        """
        return self._excludes.copy()

    def __repr__(self) -> str:
        """String representation of S3Object."""
        return f"S3Object(s3_uri='{self.s3_uri}', local_path='{self._local_path}')"

    def __str__(self) -> str:
        """String representation of S3Object."""
        return self.s3_uri
