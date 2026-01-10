"""
s3lync - The Pythonic Bridge Between S3 and the Local Filesystem.

Use S3 objects like local files with automatic sync.
"""

from .core import S3Object
from .exceptions import HashMismatchError, S3lyncError, S3ObjectError, SyncError
from .logging import configure_logging, get_logger
from .progress import ProgressBar, chain_callbacks
from .retry import RetryConfig, async_retry, retry

__all__ = [
    "S3Object",
    "S3lyncError",
    "HashMismatchError",
    "SyncError",
    "S3ObjectError",
    "ProgressBar",
    "chain_callbacks",
    "configure_logging",
    "get_logger",
    "retry",
    "async_retry",
    "RetryConfig",
]

# Async support (optional - requires aioboto3)
try:
    from .async_core import AsyncS3Object as _AsyncS3Object

    __all__.insert(1, "AsyncS3Object")
    AsyncS3Object = _AsyncS3Object
except ImportError:
    pass
