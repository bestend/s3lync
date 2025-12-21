"""
Configuration management for s3lync.
"""

import os
from typing import Optional


class Config:
    """Configuration for s3lync.

    Precedence (resolution order):
    1) Environment variables
    2) Runtime (in-code) overrides
    3) Library defaults

    You can control behavior consistently within the process using static setters.
    """

    # Default settings
    DEFAULT_CHUNK_SIZE = 8192
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 30

    # Cache settings
    ENABLE_CACHE = True
    CACHE_EXPIRE_DAYS = 30

    # Runtime overrides (set via setters)
    _aws_region: Optional[str] = None
    _debug_enabled: Optional[bool] = None
    _log_level: Optional[str] = None
    _progress_mode: Optional[str] = None
    _exclude_hidden: Optional[bool] = None

    @staticmethod
    def get_region() -> Optional[str]:
        """Get AWS region from environment, then runtime override, else None."""
        return (
            os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or Config._aws_region
        )

    @staticmethod
    def set_region(region: Optional[str]) -> None:
        """Set AWS region programmatically (lower priority than env)."""
        Config._aws_region = region

    @staticmethod
    def is_debug_enabled() -> bool:
        """Check if debug mode is enabled.

        Env var S3LYNC_DEBUG has priority over runtime override.
        """
        env = os.getenv("S3LYNC_DEBUG")
        if env is not None:
            return env.lower() in ("1", "true", "yes")
        if Config._debug_enabled is not None:
            return bool(Config._debug_enabled)
        return False

    @staticmethod
    def set_debug_enabled(enabled: Optional[bool]) -> None:
        """Enable/disable debug mode programmatically."""
        Config._debug_enabled = enabled

    @staticmethod
    def get_log_level() -> str:
        """Get log level from environment, then runtime override, else default."""
        env = os.getenv("S3LYNC_LOG_LEVEL")
        if env:
            return env
        if Config._log_level:
            return Config._log_level
        return "INFO"

    @staticmethod
    def set_log_level(level: Optional[str]) -> None:
        """Set log level programmatically (e.g., "DEBUG", "INFO", ...)."""
        Config._log_level = level or None

    @staticmethod
    def get_progress_mode() -> str:
        """
        Get progress display mode from environment.

        Returns:
            "progress" (interactive), "compact", or "disabled"
            Default: "progress"
        """
        # 1) env, 2) runtime override, 3) default
        mode = (
            os.getenv("S3LYNC_PROGRESS_MODE") or Config._progress_mode or "progress"
        ).lower()
        if mode not in ("progress", "compact", "disabled"):
            return "progress"
        return mode

    @staticmethod
    def set_progress_mode(mode: Optional[str]) -> None:
        """Set progress display mode programmatically.

        Allowed values: "progress", "compact", "disabled". None clears override.
        """
        if mode is None:
            Config._progress_mode = None
            return
        lower = mode.lower()
        Config._progress_mode = (
            lower if lower in ("progress", "compact", "disabled") else None
        )

    @staticmethod
    def should_exclude_hidden() -> bool:
        """
        Check if hidden files/directories should be excluded.

        Returns:
            True to exclude hidden files (default), False to include them
        """
        env = os.getenv("S3LYNC_EXCLUDE_HIDDEN")
        if env is not None:
            return env.lower() in ("1", "true", "yes")
        if Config._exclude_hidden is not None:
            return bool(Config._exclude_hidden)
        return True

    @staticmethod
    def set_exclude_hidden(exclude: Optional[bool]) -> None:
        """Set whether to exclude hidden files programmatically."""
        Config._exclude_hidden = exclude

    @staticmethod
    def reset_runtime_overrides() -> None:
        """Reset all runtime overrides (useful for tests)."""
        Config._aws_region = None
        Config._debug_enabled = None
        Config._log_level = None
        Config._progress_mode = None
        Config._exclude_hidden = None
