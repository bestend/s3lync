"""
Configuration management for s3lync.
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Configuration for s3lync."""

    # Default settings
    DEFAULT_CHUNK_SIZE = 8192
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 30

    # Cache settings
    ENABLE_CACHE = True
    CACHE_EXPIRE_DAYS = 30

    @staticmethod
    def get_aws_region() -> Optional[str]:
        """Get AWS region from environment or config."""
        return os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")

    @staticmethod
    def is_debug_enabled() -> bool:
        """Check if debug mode is enabled."""
        return os.getenv("S3LYNC_DEBUG", "").lower() in ("1", "true", "yes")

    @staticmethod
    def get_log_level() -> str:
        """Get log level from environment."""
        return os.getenv("S3LYNC_LOG_LEVEL", "INFO")

