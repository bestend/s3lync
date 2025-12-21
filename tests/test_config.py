"""
Tests for Config class.
"""

import os
from unittest.mock import patch

from s3lync.config import Config


class TestConfig:
    """Test Config class."""

    def test_get_region_from_aws_region(self):
        """Test getting AWS region from AWS_REGION."""
        with patch.dict(os.environ, {"AWS_REGION": "us-west-2"}):
            assert Config.get_region() == "us-west-2"

    def test_get_region_from_aws_default_region(self):
        """Test getting AWS region from AWS_DEFAULT_REGION."""
        with patch.dict(os.environ, {"AWS_DEFAULT_REGION": "eu-west-1"}, clear=False):
            # Clear AWS_REGION if set
            env = os.environ.copy()
            env.pop("AWS_REGION", None)
            with patch.dict(os.environ, env, clear=True):
                assert Config.get_region() == "eu-west-1"

    def test_runtime_region_override_when_env_missing(self):
        """Runtime AWS region should be used when env is missing."""
        with patch.dict(os.environ, {}, clear=True):
            Config.reset_runtime_overrides()
            Config.set_region("ap-northeast-2")
            assert Config.get_region() == "ap-northeast-2"
            # env wins if provided
            with patch.dict(os.environ, {"AWS_REGION": "us-east-1"}, clear=True):
                assert Config.get_region() == "us-east-1"

    def test_is_debug_enabled_true(self):
        """Test debug mode enabled."""
        with patch.dict(os.environ, {"S3LYNC_DEBUG": "1"}):
            assert Config.is_debug_enabled() is True

    def test_is_debug_enabled_false(self):
        """Test debug mode disabled."""
        with patch.dict(os.environ, {}, clear=False):
            env = os.environ.copy()
            env.pop("S3LYNC_DEBUG", None)
            with patch.dict(os.environ, env, clear=True):
                assert Config.is_debug_enabled() is False

    def test_runtime_debug_override_without_env(self):
        """Debug can be enabled/disabled via runtime when env is absent."""
        with patch.dict(os.environ, {}, clear=True):
            Config.reset_runtime_overrides()
            Config.set_debug_enabled(True)
            assert Config.is_debug_enabled() is True
            Config.set_debug_enabled(False)
            assert Config.is_debug_enabled() is False
            # env wins
            with patch.dict(os.environ, {"S3LYNC_DEBUG": "true"}, clear=True):
                Config.set_debug_enabled(False)
                assert Config.is_debug_enabled() is True

    def test_get_log_level_default(self):
        """Test default log level."""
        with patch.dict(os.environ, {}, clear=False):
            env = os.environ.copy()
            env.pop("S3LYNC_LOG_LEVEL", None)
            with patch.dict(os.environ, env, clear=True):
                assert Config.get_log_level() == "INFO"

    def test_get_log_level_custom(self):
        """Test custom log level."""
        with patch.dict(os.environ, {"S3LYNC_LOG_LEVEL": "DEBUG"}):
            assert Config.get_log_level() == "DEBUG"

    def test_runtime_log_level_override_and_env_priority(self):
        """Runtime log level should apply when env is missing; env wins when set."""
        with patch.dict(os.environ, {}, clear=True):
            Config.reset_runtime_overrides()
            Config.set_log_level("WARNING")
            assert Config.get_log_level() == "WARNING"
            Config.set_log_level(None)
            assert Config.get_log_level() == "INFO"
        with patch.dict(os.environ, {"S3LYNC_LOG_LEVEL": "ERROR"}, clear=True):
            Config.set_log_level("DEBUG")
            assert Config.get_log_level() == "ERROR"

    def test_runtime_progress_mode_override_and_validation(self):
        """Progress mode respects overrides and validates values."""
        with patch.dict(os.environ, {}, clear=True):
            Config.reset_runtime_overrides()
            Config.set_progress_mode("compact")
            assert Config.get_progress_mode() == "compact"
            Config.set_progress_mode("invalid")
            # invalid override should be ignored -> default
            assert Config.get_progress_mode() == "progress"
            Config.set_progress_mode(None)
            assert Config.get_progress_mode() == "progress"
        with patch.dict(os.environ, {"S3LYNC_PROGRESS_MODE": "disabled"}, clear=True):
            Config.set_progress_mode("progress")
            assert Config.get_progress_mode() == "disabled"

    def test_runtime_exclude_hidden_override_and_env_priority(self):
        """Exclude hidden can be controlled via runtime; env has priority."""
        with patch.dict(os.environ, {}, clear=True):
            Config.reset_runtime_overrides()
            # default True
            assert Config.should_exclude_hidden() is True
            Config.set_exclude_hidden(False)
            assert Config.should_exclude_hidden() is False
        with patch.dict(os.environ, {"S3LYNC_EXCLUDE_HIDDEN": "1"}, clear=True):
            Config.set_exclude_hidden(False)
            assert Config.should_exclude_hidden() is True
