"""
Async core S3Object class for s3lync.
"""

import asyncio
import os
import re
import shutil
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, List, Optional, Tuple, Union

from .async_client import AsyncS3Client
from .exceptions import HashMismatchError, S3ObjectError, SyncError
from .hash import calculate_file_hash
from .logging import get_logger
from .progress import ProgressBar
from .utils import ensure_parent_dir, get_cache_dir, normalize_path, parse_s3_uri

_logger = get_logger("async_core")


class AsyncS3Object:
    """
    Async version of S3Object - represents an S3 object with async operations.

    Provides automatic upload/download synchronization with MD5 hash
    verification. Handles both files and directories with recursive operations.
    All I/O operations are async.
    """

    _excludes: list[str]

    def __init__(
        self,
        s3_uri: str,
        local_path: Optional[str] = None,
        boto3_client: Optional[object] = None,
        aioboto3_session: Optional[object] = None,
        excludes: Union[str, List[str], None] = None,
        progress_mode: str = "progress",
    ):
        """
        Initialize AsyncS3Object.

        Args:
            s3_uri: S3 URI (s3://bucket/key, s3://endpoint@bucket/key, etc)
            local_path: Local file/directory path (optional)
            boto3_client: Pre-configured boto3 S3 client (will run in thread pool)
            aioboto3_session: Pre-configured aioboto3 Session (recommended for async)
            excludes: Exclude patterns (overrides default if provided)
            progress_mode: Progress display mode: "progress", "compact", "disabled"

        Example:
            import aioboto3

            session = aioboto3.Session()
            obj = AsyncS3Object("s3://bucket/key", aioboto3_session=session)
            await obj.download()
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
        if excludes:
            if isinstance(excludes, str):
                self._excludes = [excludes]
            else:
                self._excludes = excludes.copy()
        else:
            # Use default excludes
            self._excludes = [
                r"/\.",  # Hidden files/dirs
                r"__pycache__",  # Python cache
                r"\.egg-info",  # Egg info
            ]

        # Initialize AsyncS3Client
        if aioboto3_session is not None:
            self._client = AsyncS3Client(
                session=aioboto3_session, endpoint_url=self._endpoint
            )
        elif boto3_client is not None:
            # Use sync client with thread pool
            self._client = AsyncS3Client(client=boto3_client)
        else:
            # Create aioboto3 session from credentials
            import aioboto3

            session = aioboto3.Session(
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
            )
            self._client = AsyncS3Client(session=session, endpoint_url=self._endpoint)

    def _get_default_cache_path(self) -> str:
        """Get default cache path for this S3 object."""
        cache_dir = get_cache_dir()
        return str(cache_dir / self.bucket / self.key)

    @property
    def local_path(self) -> str:
        """Get the local file/directory path."""
        return self._local_path

    async def download(
        self,
        use_checksum: bool = True,
        excludes: Union[str, List[str], None] = None,
        progress_mode: Optional[str] = None,
        mirror: bool = False,
    ) -> str:
        """
        Download S3 object (file or directory) to local asynchronously.

        Args:
            use_checksum: Verify file integrity with MD5 (default: True)
            excludes: Additional regex pattern(s) to exclude
            progress_mode: Progress display mode ("progress", "compact", "disabled")
            mirror: When True, makes local identical to remote (default: False)

        Returns:
            Local path

        Raises:
            SyncError: If download fails
            HashMismatchError: If hash verification fails
        """
        actual_progress_mode = progress_mode or self.progress_mode

        # Combine excludes
        all_excludes = self._excludes.copy()
        if excludes:
            if isinstance(excludes, str):
                all_excludes.append(excludes)
            elif isinstance(excludes, list):
                all_excludes.extend(excludes)

        try:
            if await self._client.is_file(self.bucket, self.key):
                await self._download_file(
                    self.key,
                    self._local_path,
                    use_checksum,
                    mirror,
                    progress_mode=actual_progress_mode,
                )
            else:
                await self._download_dir(
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

    async def _download_file(
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
        """Download single file from S3 asynchronously."""
        ensure_parent_dir(local_path)

        # Check if file exists and is up-to-date
        if not mirror and await self._is_equal_file(
            remote_key, local_path, use_checksum
        ):
            return

        # Download file
        metadata = await self._client.download_file(
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

            # Run hash calculation in thread pool to avoid blocking
            local_hash = await asyncio.to_thread(calculate_file_hash, local_path)

            # Skip hash check for multipart uploads
            if "-" not in remote_etag and local_hash != remote_etag:
                raise HashMismatchError(
                    f"Hash mismatch for {remote_key}: "
                    f"local={local_hash}, remote={remote_etag}"
                )

    async def _download_dir(
        self,
        remote_prefix: str,
        local_dir: str,
        use_checksum: bool,
        mirror: bool,
        excludes: Union[str, List[str], None] = None,
        progress_mode: Optional[str] = None,
    ) -> None:
        """Download directory recursively from S3 asynchronously."""
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
            remote_files = set(
                await self._client.list_files(
                    self.bucket, remote_prefix, recursive=True
                )
            )

            # Delete local files/dirs not in remote (run in thread pool)
            await asyncio.to_thread(
                self._cleanup_local_files, local_dir, remote_prefix, remote_files
            )

        # Pre-scan to compute totals
        total_files = 0
        total_bytes = 0

        # Get paginator through client's session
        if self._client.session:
            async with self._client.session.client(
                "s3", endpoint_url=getattr(self._client, "_endpoint_url", None)
            ) as s3:
                paginator = s3.get_paginator("list_objects_v2")
                async for result in paginator.paginate(
                    Bucket=self.bucket, Prefix=remote_prefix
                ):
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
        else:
            # Use sync client in thread pool
            total_files, total_bytes = await asyncio.to_thread(
                self._count_files_sync,
                remote_prefix,
                local_dir,
                exclude_regexes,
            )

        _logger.info(f"Download: {total_files} files, {total_bytes} bytes")

        # Overall progress bar
        overall_pbar = ProgressBar(
            total=total_bytes,
            desc="[overall]",
            mode=actual_progress_mode,
            position=0,
            leave=True,
        )

        # Download files
        if self._client.session:
            await self._download_dir_async(
                remote_prefix,
                local_dir,
                use_checksum,
                mirror,
                exclude_regexes,
                actual_progress_mode,
                overall_pbar,
            )
        else:
            await self._download_dir_sync(
                remote_prefix,
                local_dir,
                use_checksum,
                mirror,
                exclude_regexes,
                actual_progress_mode,
                overall_pbar,
            )

        # Close overall progress
        try:
            overall_pbar.close()
        except Exception:
            pass

    def _cleanup_local_files(
        self, local_dir: str, remote_prefix: str, remote_files: set
    ) -> None:
        """Helper to cleanup local files (runs in thread pool)."""
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, local_dir).replace("\\", "/")
                remote_key = f"{remote_prefix}{relative_path}"
                if remote_key not in remote_files:
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass

            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                relative_path = os.path.relpath(dir_path, local_dir).replace("\\", "/")
                remote_dir = f"{remote_prefix}{relative_path}/"
                has_items = any(f.startswith(remote_dir) for f in remote_files)
                if not has_items:
                    try:
                        shutil.rmtree(dir_path, ignore_errors=True)
                    except Exception:
                        pass

    def _count_files_sync(
        self,
        remote_prefix: str,
        local_dir: str,
        exclude_regexes: list[re.Pattern[str]],
    ) -> tuple[int, int]:
        """Count files using sync client (runs in thread pool)."""
        from .client import S3Client

        sync_client = S3Client(client=self._client._external_client)
        total_files = 0
        total_bytes = 0

        paginator = sync_client.client.get_paginator("list_objects_v2")
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

        return total_files, total_bytes

    async def _download_dir_async(
        self,
        remote_prefix: str,
        local_dir: str,
        use_checksum: bool,
        mirror: bool,
        exclude_regexes: list[re.Pattern[str]],
        progress_mode: str,
        overall_pbar: ProgressBar,
    ) -> None:
        """Download directory using async client with parallel downloads."""

        # Callback factory to avoid closure bug
        def make_callback(pbar: ProgressBar) -> Callable[[int], None]:
            def callback(n: int) -> None:
                try:
                    pbar.update(n)
                except Exception:
                    pass

            return callback

        overall_callback = make_callback(overall_pbar)

        async with self._client.session.client(
            "s3", endpoint_url=getattr(self._client, "_endpoint_url", None)
        ) as s3:
            paginator = s3.get_paginator("list_objects_v2")

            # Collect files and subdirs first
            files_to_download: List[Tuple[str, str]] = []
            subdirs_to_process: List[Tuple[str, str]] = []

            async for result in paginator.paginate(
                Bucket=self.bucket, Prefix=remote_prefix, Delimiter="/"
            ):
                for file_obj in result.get("Contents", []):
                    remote_key = file_obj["Key"]
                    if remote_key == remote_prefix:
                        continue
                    relative_path = os.path.relpath(remote_key, remote_prefix)
                    local_file = os.path.join(local_dir, relative_path)
                    if any(regex.search(local_file) for regex in exclude_regexes):
                        continue
                    files_to_download.append((remote_key, local_file))

                for prefix_obj in result.get("CommonPrefixes", []):
                    remote_subdir = prefix_obj["Prefix"]
                    relative_path = os.path.relpath(remote_subdir, remote_prefix)
                    local_subdir = os.path.join(local_dir, relative_path)
                    subdirs_to_process.append((remote_subdir, local_subdir))

            # Download files in parallel using asyncio.gather with semaphore
            sem = asyncio.Semaphore(8)  # Limit concurrent downloads

            async def download_with_sem(remote_key: str, local_file: str) -> None:
                async with sem:
                    await self._download_file(
                        remote_key,
                        local_file,
                        use_checksum,
                        mirror,
                        callback=overall_callback,
                        progress_mode=progress_mode,
                        progress_position=1,
                        progress_leave=False,
                    )

            # Execute downloads in parallel
            tasks = [
                download_with_sem(remote_key, local_file)
                for remote_key, local_file in files_to_download
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    _logger.error(
                        f"Download failed for {files_to_download[i][0]}: {result}"
                    )

            # Process subdirectories recursively
            for remote_subdir, local_subdir in subdirs_to_process:
                await self._download_dir(
                    remote_subdir,
                    local_subdir,
                    use_checksum,
                    mirror,
                    exclude_regexes,
                    progress_mode,
                )

    async def _download_dir_sync(
        self,
        remote_prefix: str,
        local_dir: str,
        use_checksum: bool,
        mirror: bool,
        exclude_regexes: list[re.Pattern[str]],
        progress_mode: str,
        overall_pbar: ProgressBar,
    ) -> None:
        """Download directory using sync client in thread pool with parallel downloads."""
        from .client import S3Client

        # Callback factory to avoid closure bug
        def make_callback(pbar: ProgressBar) -> Callable[[int], None]:
            def callback(n: int) -> None:
                try:
                    pbar.update(n)
                except Exception:
                    pass

            return callback

        overall_callback = make_callback(overall_pbar)

        sync_client = S3Client(client=self._client._external_client)
        paginator = sync_client.client.get_paginator("list_objects_v2")

        # Collect files and subdirs first
        files_to_download: List[Tuple[str, str]] = []
        subdirs_to_process: List[Tuple[str, str]] = []

        for result in paginator.paginate(
            Bucket=self.bucket, Prefix=remote_prefix, Delimiter="/"
        ):
            for file_obj in result.get("Contents", []):
                remote_key = file_obj["Key"]
                if remote_key == remote_prefix:
                    continue
                relative_path = os.path.relpath(remote_key, remote_prefix)
                local_file = os.path.join(local_dir, relative_path)
                if any(regex.search(local_file) for regex in exclude_regexes):
                    continue
                files_to_download.append((remote_key, local_file))

            for prefix_obj in result.get("CommonPrefixes", []):
                remote_subdir = prefix_obj["Prefix"]
                relative_path = os.path.relpath(remote_subdir, remote_prefix)
                local_subdir = os.path.join(local_dir, relative_path)
                subdirs_to_process.append((remote_subdir, local_subdir))

        # Download files in parallel using asyncio.gather with semaphore
        sem = asyncio.Semaphore(8)

        async def download_with_sem(remote_key: str, local_file: str) -> None:
            async with sem:
                await self._download_file(
                    remote_key,
                    local_file,
                    use_checksum,
                    mirror,
                    callback=overall_callback,
                    progress_mode=progress_mode,
                    progress_position=1,
                    progress_leave=False,
                )

        tasks = [
            download_with_sem(remote_key, local_file)
            for remote_key, local_file in files_to_download
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                _logger.error(
                    f"Download failed for {files_to_download[i][0]}: {result}"
                )

        # Process subdirectories
        for remote_subdir, local_subdir in subdirs_to_process:
            await self._download_dir(
                remote_subdir,
                local_subdir,
                use_checksum,
                mirror,
                exclude_regexes,
                progress_mode,
            )

    async def upload(
        self,
        use_checksum: bool = True,
        excludes: Union[str, List[str], None] = None,
        progress_mode: Optional[str] = None,
        mirror: bool = False,
    ) -> str:
        """
        Upload local object (file or directory) to S3 asynchronously.

        Args:
            use_checksum: Verify file integrity (default: True)
            excludes: Additional regex pattern(s) to exclude
            progress_mode: Progress display mode
            mirror: When True, makes remote identical to local (default: False)

        Returns:
            S3 URI

        Raises:
            S3ObjectError: If local file/directory doesn't exist
            SyncError: If upload fails
        """
        if not os.path.exists(self._local_path):
            raise S3ObjectError(f"Local path does not exist: {self._local_path}")

        actual_progress_mode = progress_mode or self.progress_mode

        # Combine excludes
        all_excludes = self._excludes.copy()
        if excludes:
            if isinstance(excludes, str):
                all_excludes.append(excludes)
            elif isinstance(excludes, list):
                all_excludes.extend(excludes)

        # Convert to regex patterns
        exclude_regexes: list[re.Pattern[str]] = [
            re.compile(pattern) for pattern in all_excludes
        ]

        try:
            if os.path.isfile(self._local_path):
                await self._upload_file(
                    self.key,
                    self._local_path,
                    use_checksum,
                    mirror,
                    progress_mode=actual_progress_mode,
                )
            else:
                await self._upload_dir(
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

    async def _upload_file(
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
        """Upload single file to S3 asynchronously."""
        # Check if file exists and is up-to-date
        if not mirror and await self._is_equal_file(
            remote_key, local_path, use_checksum
        ):
            return

        # Upload file
        await self._client.upload_file(
            self.bucket,
            remote_key,
            local_path,
            callback=callback,
            progress_mode=progress_mode,
            progress_position=progress_position,
            progress_leave=progress_leave,
        )

    async def _upload_dir(
        self,
        remote_prefix: str,
        local_dir: str,
        use_checksum: bool,
        exclude_regexes: List[re.Pattern[str]],
        mirror: bool,
        progress_mode: Optional[str] = None,
    ) -> None:
        """Upload directory recursively to S3 asynchronously."""
        actual_progress_mode = progress_mode or self.progress_mode

        if not remote_prefix.endswith("/"):
            remote_prefix += "/"

        # Handle mirror - delete remote files not in local
        if mirror:
            local_files = set()

            for root, _dirs, files in os.walk(local_dir):
                for file in files:
                    file_path = os.path.join(root, file)

                    if any(regex.search(file_path) for regex in exclude_regexes):
                        continue

                    relative_path = os.path.relpath(file_path, local_dir).replace(
                        "\\", "/"
                    )
                    local_files.add(f"{remote_prefix}{relative_path}")

            # Delete remote files not in local
            remote_files = await self._client.list_files(
                self.bucket, remote_prefix, recursive=True
            )
            for remote_file in remote_files:
                if remote_file not in local_files:
                    await self._client.delete_object(self.bucket, remote_file)

        # Pre-scan local files to compute totals (run in thread pool)
        total_files, total_bytes = await asyncio.to_thread(
            self._count_local_files, local_dir, exclude_regexes
        )

        _logger.info(f"Upload: {total_files} files, {total_bytes} bytes")

        # Overall progress bar
        overall_pbar = ProgressBar(
            total=total_bytes,
            desc="[overall]",
            mode=actual_progress_mode,
            position=0,
            leave=True,
        )

        # Callback factory to avoid closure bug
        def make_callback(pbar: ProgressBar) -> Callable[[int], None]:
            def callback(n: int) -> None:
                try:
                    pbar.update(n)
                except Exception:
                    pass

            return callback

        overall_callback = make_callback(overall_pbar)

        # Collect files to upload
        files_to_upload: List[Tuple[str, str]] = []
        for root, _dirs, files in os.walk(local_dir):
            for file in files:
                local_file = os.path.join(root, file)
                if any(regex.search(local_file) for regex in exclude_regexes):
                    continue
                relative_path = os.path.relpath(local_file, local_dir).replace(
                    "\\", "/"
                )
                remote_key = f"{remote_prefix}{relative_path}"
                files_to_upload.append((remote_key, local_file))

        # Upload files in parallel using asyncio.gather with semaphore
        sem = asyncio.Semaphore(8)

        async def upload_with_sem(remote_key: str, local_file: str) -> None:
            async with sem:
                await self._upload_file(
                    remote_key,
                    local_file,
                    use_checksum,
                    mirror,
                    callback=overall_callback,
                    progress_mode=actual_progress_mode,
                    progress_position=1,
                    progress_leave=False,
                )

        tasks = [
            upload_with_sem(remote_key, local_file)
            for remote_key, local_file in files_to_upload
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                _logger.error(f"Upload failed for {files_to_upload[i][1]}: {result}")

        # Close overall progress
        try:
            overall_pbar.close()
        except Exception:
            pass

    def _count_local_files(
        self, local_dir: str, exclude_regexes: List[re.Pattern[str]]
    ) -> tuple[int, int]:
        """Count local files (runs in thread pool)."""
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
        return total_files, total_bytes

    async def _is_equal_file(
        self, remote_key: str, local_path: str, use_checksum: bool
    ) -> bool:
        """Check if remote and local files are equal asynchronously."""
        if not await self._client.is_file(self.bucket, remote_key):
            return False

        if not os.path.isfile(local_path):
            return False

        if not use_checksum:
            return True

        try:
            metadata = await self._client.get_object_metadata(self.bucket, remote_key)
            if metadata is None:
                return False

            remote_etag: str = metadata.get("ETag", "")
            remote_etag = remote_etag.strip('"')

            # Run hash calculation in thread pool
            local_hash = await asyncio.to_thread(calculate_file_hash, local_path)

            # Skip hash check for multipart uploads
            if "-" in remote_etag:
                return True

            return bool(local_hash == remote_etag)
        except Exception:
            return False

    @asynccontextmanager
    async def open(
        self, mode: str = "r", encoding: str = "utf-8"
    ) -> AsyncIterator[Any]:
        """
        Async context manager to open S3 object as a file.

        Downloads from S3 on enter for read mode, uploads on exit for write mode.

        Args:
            mode: File mode ("r", "w", "rb", "wb", etc.)
            encoding: Text encoding (default: "utf-8")

        Yields:
            File object

        Example:
            async with obj.open("w") as f:
                f.write("hello world")
            # Automatically uploaded to S3 on exit
        """
        # Download if reading
        if "r" in mode:
            await self.download()

        # Ensure parent directory exists for write modes
        if "w" in mode or "a" in mode or "+" in mode:
            ensure_parent_dir(self._local_path)

        # Open local file (in thread pool to avoid blocking)
        # We need to use a wrapper function to properly pass kwargs to open()
        def _open_file():
            if "b" not in mode:
                return open(self._local_path, mode=mode, encoding=encoding)
            else:
                return open(self._local_path, mode=mode)

        file_handle = await asyncio.to_thread(_open_file)

        try:
            yield file_handle
        finally:
            await asyncio.to_thread(file_handle.close)
            # Upload if writing
            if "w" in mode or "a" in mode or "+" in mode:
                await self.upload()

    async def exists(self) -> bool:
        """Check if S3 object exists asynchronously."""
        is_file = await self._client.is_file(self.bucket, self.key)
        if is_file:
            return True
        return await self._client.is_dir(self.bucket, self.key)

    async def delete(self) -> bool:
        """Delete S3 object (file or directory) asynchronously."""
        return await self._client.delete_object(self.bucket, self.key)

    def add_exclude(self, pattern: str) -> "AsyncS3Object":
        """Add an exclude pattern."""
        if pattern not in self._excludes:
            self._excludes.append(pattern)
        return self

    def add_excludes(self, patterns: list[str]) -> "AsyncS3Object":
        """Add multiple exclude patterns."""
        for pattern in patterns:
            self.add_exclude(pattern)
        return self

    def remove_exclude(self, pattern: str) -> "AsyncS3Object":
        """Remove an exclude pattern."""
        if pattern in self._excludes:
            self._excludes.remove(pattern)
        return self

    def clear_excludes(self) -> "AsyncS3Object":
        """Clear all exclude patterns."""
        self._excludes.clear()
        return self

    def get_excludes(self) -> list[str]:
        """Get all exclude patterns."""
        return self._excludes.copy()

    def __fspath__(self) -> str:
        """Return the file system path representation."""
        return self._local_path

    def __repr__(self) -> str:
        """String representation of AsyncS3Object."""
        return f"AsyncS3Object(s3_uri='{self.s3_uri}', local_path='{self._local_path}')"

    def __str__(self) -> str:
        """String representation of AsyncS3Object."""
        return self.s3_uri
