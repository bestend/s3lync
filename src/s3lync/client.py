"""
S3 client wrapper using boto3.
"""

from typing import Any, Callable, Optional

try:
    import boto3
    from boto3.s3.transfer import TransferConfig
    from botocore.exceptions import ClientError
except ImportError as e:
    raise ImportError("boto3 is required. Install it with: pip install boto3") from e

from .exceptions import S3lyncError
from .progress import chain_callbacks, create_progress_callback


class S3Client:
    """Wrapper around boto3 S3 client - accepts pre-configured boto3 client."""

    def __init__(
        self,
        client: Optional[Any] = None,
        region_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ):
        """
        Initialize S3Client.

        Args:
            client: Pre-configured boto3 S3 client (recommended)
                   If provided, region_name and endpoint_url are ignored
            region_name: AWS region name (only used if client is None)
            endpoint_url: Custom S3 endpoint URL (only used if client is None)
        """
        if client is not None:
            # Use the provided boto3 client directly
            self.client = client
            self.resource = None
        else:
            # Fallback: create a basic client
            session = boto3.Session(region_name=region_name)
            self.client = session.client("s3", endpoint_url=endpoint_url)
            self.resource = session.resource("s3", endpoint_url=endpoint_url)

        # Build transfer config from environment or defaults
        self.transfer_config = self._build_transfer_config()

    def _build_transfer_config(self) -> Optional[TransferConfig]:
        """
        Build transfer config from environment or defaults.

        Returns:
            TransferConfig object or None
        """
        return None  # Use boto3 defaults

    def download_file(
        self,
        bucket: str,
        key: str,
        local_path: str,
        callback: Optional[Callable[[int], None]] = None,
        progress_position: Optional[int] = None,
        progress_leave: Optional[bool] = None,
        progress_mode: Optional[str] = None,
        transfer_config: Optional[TransferConfig] = None,
    ) -> dict[str, object]:
        """
        Download a file from S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key
            local_path: Local file path to save to
            callback: Optional callback function for download progress
            progress_position: Progress bar position (optional)
            progress_leave: Leave progress bar after completion (optional)
            progress_mode: Progress display mode ("progress", "compact",
                          "disabled", default: "progress")
            transfer_config: Optional TransferConfig for performance tuning

        Returns:
            Response metadata dict

        Raises:
            S3lyncError: If download fails
        """
        try:
            # Get file size for progress bar
            metadata = self.client.head_object(Bucket=bucket, Key=key)
            file_size = metadata.get("ContentLength", 0)

            # Create progress bar if needed (progress_mode controls whether to show)
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

                self.client.download_file(
                    bucket, key, local_path, Callback=final_callback, config=config
                )
            finally:
                if pbar:
                    pbar.close()

            return metadata  # type: ignore
        except ClientError as e:
            raise S3lyncError(
                f"Failed to download {bucket}/{key}: {e.response['Error']['Message']}"
            ) from e
        except Exception as e:
            raise S3lyncError(f"Failed to download {bucket}/{key}: {str(e)}") from e

    def upload_file(
        self,
        bucket: str,
        key: str,
        local_path: str,
        callback: Optional[Callable[[int], None]] = None,
        progress_position: Optional[int] = None,
        progress_leave: Optional[bool] = None,
        progress_mode: Optional[str] = None,
        transfer_config: Optional[TransferConfig] = None,
    ) -> dict[str, object]:
        """
        Upload a file to S3.

        Args:
            local_path: Local file path to upload
            bucket: S3 bucket name
            key: S3 object key
            callback: Optional callback function for upload progress
            progress_position: Progress bar position (optional)
            progress_leave: Leave progress bar after completion (optional)
            progress_mode: Progress display mode ("progress", "compact",
                          "disabled", default: "progress")
            transfer_config: Optional TransferConfig for performance tuning

        Returns:
            Response metadata dict

        Raises:
            S3lyncError: If upload fails
        """
        try:
            import os

            file_size = os.path.getsize(local_path)

            # Create progress bar if needed (progress_mode controls whether to show)
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
                self.client.upload_file(
                    local_path, bucket, key, Callback=final_callback, Config=config
                )
            finally:
                if pbar:
                    pbar.close()

            # Get object metadata
            response = self.client.head_object(Bucket=bucket, Key=key)
            return response  # type: ignore
        except ClientError as e:
            raise S3lyncError(
                f"Failed to upload {bucket}/{key}: {e.response['Error']['Message']}"
            ) from e
        except Exception as e:
            raise S3lyncError(f"Failed to upload {bucket}/{key}: {str(e)}") from e

    def get_object_metadata(self, bucket: str, key: str) -> Optional[dict[str, Any]]:
        """
        Get S3 object metadata.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            Object metadata dict or None if not found

        Raises:
            S3lyncError: If request fails (other than 404)
        """
        try:
            metadata = self.client.head_object(Bucket=bucket, Key=key)
            return metadata  # type: ignore[no-any-return]
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return None
            raise S3lyncError(
                f"Failed to get metadata for {bucket}/{key}: "
                f"{e.response['Error']['Message']}"
            ) from e
        except Exception as e:
            raise S3lyncError(
                f"Failed to get metadata for {bucket}/{key}: {str(e)}"
            ) from e

    def object_exists(self, bucket: str, key: str) -> bool:
        """
        Check if S3 object exists.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            True if object exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise
        except Exception:
            return False

    def is_file(self, bucket: str, key: str) -> bool:
        """
        Check if key is a file (not a directory).

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            True if key is a file
        """
        try:
            response = self.client.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=2)
            if "Contents" in response:
                for obj in response["Contents"]:
                    if obj["Key"] == key:
                        return True
            # Try head_object as fallback
            try:
                self.client.head_object(Bucket=bucket, Key=key)
                return True
            except Exception:
                return False
        except Exception:
            return False

    def is_dir(self, bucket: str, key: str) -> bool:
        """
        Check if key is a directory.

        Args:
            bucket: S3 bucket name
            key: S3 object key (with or without trailing slash)

        Returns:
            True if key is a directory
        """
        if not key.endswith("/"):
            key += "/"

        try:
            response = self.client.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=2)
            return "Contents" in response or "CommonPrefixes" in response
        except Exception:
            return False

    def list_files(self, bucket: str, prefix: str, recursive: bool = True) -> list[str]:
        """
        List all files under prefix.

        Args:
            bucket: S3 bucket name
            prefix: S3 key prefix
            recursive: If True, recursively list all files

        Returns:
            List of file keys
        """
        files = []

        if not prefix.endswith("/"):
            prefix += "/"

        paginator = self.client.get_paginator("list_objects_v2")

        for result in paginator.paginate(
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
                    files.extend(self.list_files(bucket, subprefix, recursive=True))

        return files

    def list_dirs(self, bucket: str, prefix: str, recursive: bool = True) -> list[str]:
        """
        List all subdirectories under prefix.

        Args:
            bucket: S3 bucket name
            prefix: S3 key prefix
            recursive: If True, recursively list all directories

        Returns:
            List of directory keys
        """
        dirs = []

        if not prefix.endswith("/"):
            prefix += "/"

        paginator = self.client.get_paginator("list_objects_v2")

        for result in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
            # Add subdirectories from CommonPrefixes
            for subdir in result.get("CommonPrefixes", []):
                dir_key = subdir["Prefix"]
                dirs.append(dir_key)

                # Recursively list subdirectories if needed
                if recursive:
                    dirs.extend(self.list_dirs(bucket, dir_key, recursive=True))

        return dirs

    def delete_object(self, bucket: str, key: str) -> bool:
        """
        Delete an S3 object (file or directory).

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            True if deletion was successful

        Raises:
            S3lyncError: If deletion fails
        """
        try:
            if self.is_file(bucket, key):
                # Delete single file
                self.client.delete_object(Bucket=bucket, Key=key)
                return True
            elif self.is_dir(bucket, key):
                # Delete directory and all its contents
                if not key.endswith("/"):
                    key += "/"

                files = self.list_files(bucket, key, recursive=True)
                if files:
                    self.client.delete_objects(
                        Bucket=bucket, Delete={"Objects": [{"Key": f} for f in files]}
                    )
                return True
            else:
                return True
        except Exception as e:
            raise S3lyncError(f"Failed to delete {key}: {str(e)}") from e
