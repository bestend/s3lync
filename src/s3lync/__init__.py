"""
s3lync - The Pythonic Bridge Between S3 and the Local Filesystem.

Use S3 objects like local files with automatic sync.
"""

__version__ = "0.4.0"
__author__ = "JunSeok Kim"

from .core import S3Object
from .exceptions import HashMismatchError, S3lyncError, S3ObjectError, SyncError
from .logging import configure_logging, get_logger
from .progress import ProgressBar, chain_callbacks
from .retry import RetryConfig, async_retry, retry

# Async support (optional - requires aioboto3)
try:
    from .async_core import AsyncS3Object

    __all__ = [
        "S3Object",
        "AsyncS3Object",
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
except ImportError:
    # aioboto3 not installed - async support not available
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
