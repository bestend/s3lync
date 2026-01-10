"""
Tests for logging utilities.
"""

import logging
from io import StringIO

import pytest

from s3lync.logging import configure_logging, get_logger, logger


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_default_configuration(self):
        """Test default logging configuration."""
        stream = StringIO()
        result = configure_logging(stream=stream)

        assert result is logger
        assert result.level == logging.INFO
        assert len(result.handlers) == 1

    def test_custom_level(self):
        """Test custom logging level."""
        stream = StringIO()
        configure_logging(level=logging.DEBUG, stream=stream)

        assert logger.level == logging.DEBUG

    def test_custom_format(self):
        """Test custom format string."""
        stream = StringIO()
        configure_logging(
            format_string="%(levelname)s: %(message)s",
            stream=stream,
        )

        logger.info("test message")
        output = stream.getvalue()
        assert "INFO: test message" in output

    def test_clears_existing_handlers(self):
        """Test that existing handlers are cleared."""
        stream = StringIO()
        configure_logging(stream=stream)
        configure_logging(stream=stream)

        # Should only have one handler after reconfiguration
        assert len(logger.handlers) == 1


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_root_logger(self):
        """Test getting root s3lync logger."""
        result = get_logger()
        assert result.name == "s3lync"

    def test_get_child_logger(self):
        """Test getting child logger."""
        result = get_logger("core")
        assert result.name == "s3lync.core"

    def test_child_logger_inherits_config(self):
        """Test that child logger inherits configuration."""
        stream = StringIO()
        configure_logging(level=logging.DEBUG, stream=stream)

        child = get_logger("test_child")
        child.debug("debug message")

        output = stream.getvalue()
        assert "debug message" in output


class TestLoggerIntegration:
    """Integration tests for logging system."""

    def test_logging_from_module(self):
        """Test that module loggers work correctly."""
        stream = StringIO()
        configure_logging(level=logging.INFO, stream=stream)

        # Simulate module-level logging
        module_logger = get_logger("core")
        module_logger.info("Download: 10 files, 1024 bytes")

        output = stream.getvalue()
        assert "Download: 10 files, 1024 bytes" in output
        assert "s3lync.core" in output

    def test_disabled_logging(self):
        """Test that logging can be disabled."""
        stream = StringIO()
        configure_logging(level=logging.CRITICAL, stream=stream)

        module_logger = get_logger("core")
        module_logger.info("This should not appear")

        output = stream.getvalue()
        assert output == ""
