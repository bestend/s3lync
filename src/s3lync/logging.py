"""
Logging configuration for s3lync.
"""

import logging
import sys
from typing import Optional

# Create package logger
logger = logging.getLogger("s3lync")

# Default to not handling until configured
logger.addHandler(logging.NullHandler())


def configure_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    stream: Optional[object] = None,
) -> logging.Logger:
    """
    Configure s3lync logging.

    Args:
        level: Logging level (default: logging.INFO)
        format_string: Custom format string (optional)
        stream: Output stream (default: sys.stderr)

    Returns:
        Configured logger

    Example:
        from s3lync.logging import configure_logging
        import logging

        # Enable debug logging
        configure_logging(level=logging.DEBUG)

        # Custom format
        configure_logging(format_string="%(message)s")
    """
    # Remove existing handlers
    logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setLevel(level)

    # Set format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)

    # Add handler and set level
    logger.addHandler(handler)
    logger.setLevel(level)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger for s3lync components.

    Args:
        name: Child logger name (optional)

    Returns:
        Logger instance
    """
    if name:
        return logger.getChild(name)
    return logger
