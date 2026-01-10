"""
Async S3 client wrapper using aioboto3.
"""

from typing import Any, Callable, Optional

try:
    import aioboto3
    from botocore.exceptions import ClientError
except ImportError as e:
    raise ImportError(
        "aioboto3 is required for async support. Install it with: pip install aioboto3"
    ) from e

from .exceptions import S3lyncError
from .logging import get_logger
from .progress import chain_callbacks, create_progress_callback
from .retry import async_retry

_logger = get_logger("async_client")


class AsyncS3Client:
    """Async wrapper around aioboto3 S3 client - accepts pre-configured boto3 client or session."""

    def __init__(
        self,
        client: Optional[Any] = None,
        session: Optional[Any] = None,
        region_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ):
        """
        Initialize AsyncS3Client.

        Args:
            client: Pre-configured boto3 S3 client (will be wrapped for async use)
            session: Pre-configured aioboto3 Session (recommended for async)
            region_name: AWS region name (only used if session is None)
            endpoint_url: Custom S3 endpoint URL (only used if session is None)
        """
        if session is not None:
            # Use the provided aioboto3 session
            self.session = session
            self._external_client = None
            self._endpoint_url = (
                endpoint_url  # Store endpoint even for external session
            )
        elif client is not None:
            # Sync client provided - we'll use it with asyncio.to_thread
            self.session = None
            self._external_client = client
            self._endpoint_url = endpoint_url
        else:
            # Create aioboto3 session
            self.session = aioboto3.Session(region_name=region_name)
            self._external_client = None
            self._endpoint_url = endpoint_url

        self.transfer_config = None  # Use aioboto3 defaults

    @async_retry(max_attempts=3, base_delay=0.5, max_delay=30.0)
    async def download_file(
        self,
        bucket: str,
        key: str,
        local_path: str,
        callback: Optional[Callable[[int], None]] = None,
        progress_position: Optional[int] = None,
        progress_leave: Optional[bool] = None,
        progress_mode: Optional[str] = None,
        transfer_config: Optional[Any] = None,
    ) -> dict[str, object]:
        """
        Download a file from S3 asynchronously.

        Args:
            bucket: S3 bucket name
            key: S3 object key
            local_path: Local file path to save to
            callback: Optional callback function for download progress
            progress_position: Progress bar position (optional)
            progress_leave: Leave progress bar after completion (optional)
            progress_mode: Progress display mode ("progress", "compact", "disabled")
            transfer_config: Optional TransferConfig for performance tuning

        Returns:
            Response metadata dict

        Raises:
            S3lyncError: If download fails
        """
        if self._external_client:
            # Use sync client with to_thread
            import asyncio

            return await asyncio.to_thread(
                self._sync_download_file,
                bucket,
                key,
                local_path,
                callback,
                progress_position,
                progress_leave,
                progress_mode,
                transfer_config,
            )

        try:
            async with self.session.client(
                "s3", endpoint_url=getattr(self, "_endpoint_url", None)
            ) as s3:
                # Get file size for progress bar
                metadata = await s3.head_object(Bucket=bucket, Key=key)
                file_size = metadata.get("ContentLength", 0)

                # Create progress bar if needed
                pbar = None
                final_callback = callback
                if file_size > 0 and (progress_mode or "progress") != "disabled":
                    pbar, progress_callback = create_progress_callback(
                        file_size,
                        desc=f"[download: {key}]",
                        mode=progress_mode,
                        position=progress_position,
                        leave=progress_leave,
                    )
                    final_callback = chain_callbacks(progress_callback, callback)

                try:
                    config = transfer_config or self.transfer_config
                    await s3.download_file(
                        bucket, key, local_path, Callback=final_callback, Config=config
                    )
                finally:
                    if pbar:
                        pbar.close()

                return metadata  # type: ignore
        except ClientError as e:
            raise S3lyncError(
                f"Failed to download {bucket}/{key}: {e.response.get('Error', {}).get('Message', str(e))}"
            ) from e

        except Exception as e:
            raise S3lyncError(f"Failed to download {bucket}/{key}: {str(e)}") from e

    def _sync_download_file(
        self,
        bucket: str,
        key: str,
        local_path: str,
        callback: Optional[Callable[[int], None]],
        progress_position: Optional[int],
        progress_leave: Optional[bool],
        progress_mode: Optional[str],
        transfer_config: Optional[Any],
    ) -> dict[str, object]:
        """Sync download helper for external boto3 client."""
        from .client import S3Client

        sync_client = S3Client(client=self._external_client)
        return sync_client.download_file(
            bucket,
            key,
            local_path,
            callback,
            progress_position,
            progress_leave,
            progress_mode,
            transfer_config,
        )

    @async_retry(max_attempts=3, base_delay=0.5, max_delay=30.0)
    async def upload_file(
        self,
        bucket: str,
        key: str,
        local_path: str,
        callback: Optional[Callable[[int], None]] = None,
        progress_position: Optional[int] = None,
        progress_leave: Optional[bool] = None,
        progress_mode: Optional[str] = None,
        transfer_config: Optional[Any] = None,
    ) -> dict[str, object]:
        """
        Upload a file to S3 asynchronously.

        Args:
            bucket: S3 bucket name
            key: S3 object key
            local_path: Local file path to upload
            callback: Optional callback function for upload progress
            progress_position: Progress bar position (optional)
            progress_leave: Leave progress bar after completion (optional)
            progress_mode: Progress display mode ("progress", "compact", "disabled")
            transfer_config: Optional TransferConfig for performance tuning

        Returns:
            Response metadata dict

        Raises:
            S3lyncError: If upload fails
        """
        if self._external_client:
            # Use sync client with to_thread
            import asyncio

            return await asyncio.to_thread(
                self._sync_upload_file,
                bucket,
                key,
                local_path,
                callback,
                progress_position,
                progress_leave,
                progress_mode,
                transfer_config,
            )

        try:
            import os

            file_size = os.path.getsize(local_path)

            async with self.session.client(
                "s3", endpoint_url=getattr(self, "_endpoint_url", None)
            ) as s3:
                # Create progress bar if needed
                pbar = None
                final_callback = callback
                if file_size > 0 and (progress_mode or "progress") != "disabled":
                    pbar, progress_callback = create_progress_callback(
                        file_size,
                        desc=f"[upload: {key}]",
                        mode=progress_mode,
                        position=progress_position,
                        leave=progress_leave,
                    )
                    final_callback = chain_callbacks(progress_callback, callback)

                try:
                    config = transfer_config or self.transfer_config
                    await s3.upload_file(
                        local_path, bucket, key, Callback=final_callback, Config=config
                    )
                finally:
                    if pbar:
                        pbar.close()

                # Get object metadata
                response = await s3.head_object(Bucket=bucket, Key=key)
                return response  # type: ignore
        except ClientError as e:
            raise S3lyncError(
                f"Failed to upload {bucket}/{key}: {e.response.get('Error', {}).get('Message', str(e))}"
            ) from e

        except Exception as e:
            raise S3lyncError(f"Failed to upload {bucket}/{key}: {str(e)}") from e

    def _sync_upload_file(
        self,
        bucket: str,
        key: str,
        local_path: str,
        callback: Optional[Callable[[int], None]],
        progress_position: Optional[int],
        progress_leave: Optional[bool],
        progress_mode: Optional[str],
        transfer_config: Optional[Any],
    ) -> dict[str, object]:
        """Sync upload helper for external boto3 client."""
        from .client import S3Client

        sync_client = S3Client(client=self._external_client)
        return sync_client.upload_file(
            bucket,
            key,
            local_path,
            callback,
            progress_position,
            progress_leave,
            progress_mode,
            transfer_config,
        )

    async def get_object_metadata(
        self, bucket: str, key: str
    ) -> Optional[dict[str, Any]]:
        """
        Get S3 object metadata asynchronously.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            Object metadata dict or None if not found

        Raises:
            S3lyncError: If request fails (other than 404)
        """
        if self._external_client:
            import asyncio

            return await asyncio.to_thread(self._sync_get_object_metadata, bucket, key)

        try:
            async with self.session.client(
                "s3", endpoint_url=getattr(self, "_endpoint_url", None)
            ) as s3:
                metadata = await s3.head_object(Bucket=bucket, Key=key)
                return metadata  # type: ignore[no-any-return]
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return None
            raise S3lyncError(
                f"Failed to get metadata for {bucket}/{key}: "
                f"{e.response.get('Error', {}).get('Message', str(e))}"
            ) from e
        except Exception as e:
            raise S3lyncError(
                f"Failed to get metadata for {bucket}/{key}: {str(e)}"
            ) from e

    def _sync_get_object_metadata(
        self, bucket: str, key: str
    ) -> Optional[dict[str, Any]]:
        """Sync get metadata helper for external boto3 client."""
        from .client import S3Client

        sync_client = S3Client(client=self._external_client)
        return sync_client.get_object_metadata(bucket, key)

    async def object_exists(self, bucket: str, key: str) -> bool:
        """
        Check if S3 object exists asynchronously.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            True if object exists, False otherwise
        """
        if self._external_client:
            import asyncio

            return await asyncio.to_thread(self._sync_object_exists, bucket, key)

        try:
            async with self.session.client(
                "s3", endpoint_url=getattr(self, "_endpoint_url", None)
            ) as s3:
                await s3.head_object(Bucket=bucket, Key=key)
                return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return False
            raise
        except Exception:
            return False

    def _sync_object_exists(self, bucket: str, key: str) -> bool:
        """Sync object exists helper for external boto3 client."""
        from .client import S3Client

        sync_client = S3Client(client=self._external_client)
        return sync_client.object_exists(bucket, key)

    async def is_file(self, bucket: str, key: str) -> bool:
        """
        Check if key is a file (not a directory) asynchronously.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            True if key is a file
        """
        if self._external_client:
            import asyncio

            return await asyncio.to_thread(self._sync_is_file, bucket, key)

        try:
            async with self.session.client(
                "s3", endpoint_url=getattr(self, "_endpoint_url", None)
            ) as s3:
                response = await s3.list_objects_v2(
                    Bucket=bucket, Prefix=key, MaxKeys=2
                )
                if "Contents" in response:
                    for obj in response["Contents"]:
                        if obj["Key"] == key:
                            return True
                # Try head_object as fallback
                try:
                    await s3.head_object(Bucket=bucket, Key=key)
                    return True
                except Exception:
                    return False
        except Exception:
            return False

    def _sync_is_file(self, bucket: str, key: str) -> bool:
        """Sync is_file helper for external boto3 client."""
        from .client import S3Client

        sync_client = S3Client(client=self._external_client)
        return sync_client.is_file(bucket, key)

    async def is_dir(self, bucket: str, key: str) -> bool:
        """
        Check if key is a directory asynchronously.

        Args:
            bucket: S3 bucket name
            key: S3 object key (with or without trailing slash)

        Returns:
            True if key is a directory
        """
        if self._external_client:
            import asyncio

            return await asyncio.to_thread(self._sync_is_dir, bucket, key)

        if not key.endswith("/"):
            key += "/"

        try:
            async with self.session.client(
                "s3", endpoint_url=getattr(self, "_endpoint_url", None)
            ) as s3:
                response = await s3.list_objects_v2(
                    Bucket=bucket, Prefix=key, MaxKeys=2
                )
                return "Contents" in response or "CommonPrefixes" in response
        except Exception:
            return False

    def _sync_is_dir(self, bucket: str, key: str) -> bool:
        """Sync is_dir helper for external boto3 client."""
        from .client import S3Client

        sync_client = S3Client(client=self._external_client)
        return sync_client.is_dir(bucket, key)

    async def list_files(
        self, bucket: str, prefix: str, recursive: bool = True
    ) -> list[str]:
        """
        List all files under prefix asynchronously.

        Args:
            bucket: S3 bucket name
            prefix: S3 key prefix
            recursive: If True, recursively list all files

        Returns:
            List of file keys
        """
        if self._external_client:
            import asyncio

            return await asyncio.to_thread(
                self._sync_list_files, bucket, prefix, recursive
            )

        files = []

        if not prefix.endswith("/"):
            prefix += "/"

        async with self.session.client(
            "s3", endpoint_url=getattr(self, "_endpoint_url", None)
        ) as s3:
            paginator = s3.get_paginator("list_objects_v2")

            async for result in paginator.paginate(
                Bucket=bucket, Prefix=prefix, Delimiter="/" if not recursive else ""
            ):
                # Add files from Contents
                for obj in result.get("Contents", []):
                    key = obj["Key"]
                    if key != prefix:
                        files.append(key)

                # Recursively list subdirectories if needed
                if recursive and "CommonPrefixes" in result:
                    for subdir in result.get("CommonPrefixes", []):
                        subprefix = subdir["Prefix"]
                        subfiles = await self.list_files(bucket, subprefix, True)
                        files.extend(subfiles)

        return files

    def _sync_list_files(self, bucket: str, prefix: str, recursive: bool) -> list[str]:
        """Sync list_files helper for external boto3 client."""
        from .client import S3Client

        sync_client = S3Client(client=self._external_client)
        return sync_client.list_files(bucket, prefix, recursive)

    async def list_dirs(
        self, bucket: str, prefix: str, recursive: bool = True
    ) -> list[str]:
        """
        List all subdirectories under prefix asynchronously.

        Args:
            bucket: S3 bucket name
            prefix: S3 key prefix
            recursive: If True, recursively list all directories

        Returns:
            List of directory keys
        """
        if self._external_client:
            import asyncio

            return await asyncio.to_thread(
                self._sync_list_dirs, bucket, prefix, recursive
            )

        dirs = []

        if not prefix.endswith("/"):
            prefix += "/"

        async with self.session.client(
            "s3", endpoint_url=getattr(self, "_endpoint_url", None)
        ) as s3:
            paginator = s3.get_paginator("list_objects_v2")

            async for result in paginator.paginate(
                Bucket=bucket, Prefix=prefix, Delimiter="/"
            ):
                # Add subdirectories from CommonPrefixes
                for subdir in result.get("CommonPrefixes", []):
                    dir_key = subdir["Prefix"]
                    dirs.append(dir_key)

                    # Recursively list subdirectories if needed
                    if recursive:
                        subdirs = await self.list_dirs(bucket, dir_key, True)
                        dirs.extend(subdirs)

        return dirs

    def _sync_list_dirs(self, bucket: str, prefix: str, recursive: bool) -> list[str]:
        """Sync list_dirs helper for external boto3 client."""
        from .client import S3Client

        sync_client = S3Client(client=self._external_client)
        return sync_client.list_dirs(bucket, prefix, recursive)

    async def delete_object(self, bucket: str, key: str) -> bool:
        """
        Delete an S3 object (file or directory) asynchronously.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            True if deletion was successful

        Raises:
            S3lyncError: If deletion fails
        """
        if self._external_client:
            import asyncio

            return await asyncio.to_thread(self._sync_delete_object, bucket, key)

        try:
            async with self.session.client(
                "s3", endpoint_url=getattr(self, "_endpoint_url", None)
            ) as s3:
                if await self.is_file(bucket, key):
                    # Delete single file
                    await s3.delete_object(Bucket=bucket, Key=key)
                    return True
                elif await self.is_dir(bucket, key):
                    # Delete directory and all its contents
                    if not key.endswith("/"):
                        key += "/"

                    files = await self.list_files(bucket, key, recursive=True)
                    if files:
                        await s3.delete_objects(
                            Bucket=bucket,
                            Delete={"Objects": [{"Key": f} for f in files]},
                        )
                    return True
                else:
                    return True
        except Exception as e:
            raise S3lyncError(f"Failed to delete {key}: {str(e)}") from e

    def _sync_delete_object(self, bucket: str, key: str) -> bool:
        """Sync delete_object helper for external boto3 client."""
        from .client import S3Client

        sync_client = S3Client(client=self._external_client)
        return sync_client.delete_object(bucket, key)
