"""
Custom exceptions for s3lync.
"""


class S3lyncError(Exception):
    """Base exception for s3lync."""

    pass


class HashMismatchError(S3lyncError):
    """Raised when MD5 hash verification fails."""

    pass


class SyncError(S3lyncError):
    """Raised when sync operation fails."""

    pass


class S3ObjectError(S3lyncError):
    """Raised for S3Object specific errors."""

    pass
