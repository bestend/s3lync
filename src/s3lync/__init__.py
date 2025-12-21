"""
s3lync - The Pythonic Bridge Between S3 and the Local Filesystem.

Use S3 objects like local files with automatic sync.
"""

__version__ = "0.1.0"
__author__ = "JunSeok Kim"

from .core import S3Object
from .exceptions import S3lyncError, HashMismatchError, SyncError, S3ObjectError
from .config import Config

__all__ = [
    "S3Object",
    "S3lyncError",
    "HashMismatchError",
    "SyncError",
    "S3ObjectError",
    "Config",
]





