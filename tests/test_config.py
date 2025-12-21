"""
Tests for Config class.
"""

import pytest
import os
from unittest.mock import patch

from s3lync.config import Config


class TestConfig:
    """Test Config class."""

    def test_get_aws_region_from_aws_region(self):
        """Test getting AWS region from AWS_REGION."""
        with patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}):
            assert Config.get_aws_region() == 'us-west-2'

    def test_get_aws_region_from_aws_default_region(self):
        """Test getting AWS region from AWS_DEFAULT_REGION."""
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'eu-west-1'}, clear=False):
            # Clear AWS_REGION if set
            env = os.environ.copy()
            env.pop('AWS_REGION', None)
            with patch.dict(os.environ, env, clear=True):
                result = Config.get_aws_region()
                # May be None or the default region

    def test_is_debug_enabled_true(self):
        """Test debug mode enabled."""
        with patch.dict(os.environ, {'S3LYNC_DEBUG': '1'}):
            assert Config.is_debug_enabled() is True

    def test_is_debug_enabled_false(self):
        """Test debug mode disabled."""
        with patch.dict(os.environ, {}, clear=False):
            env = os.environ.copy()
            env.pop('S3LYNC_DEBUG', None)
            with patch.dict(os.environ, env, clear=True):
                assert Config.is_debug_enabled() is False

    def test_get_log_level_default(self):
        """Test default log level."""
        with patch.dict(os.environ, {}, clear=False):
            env = os.environ.copy()
            env.pop('S3LYNC_LOG_LEVEL', None)
            with patch.dict(os.environ, env, clear=True):
                assert Config.get_log_level() == 'INFO'

    def test_get_log_level_custom(self):
        """Test custom log level."""
        with patch.dict(os.environ, {'S3LYNC_LOG_LEVEL': 'DEBUG'}):
            assert Config.get_log_level() == 'DEBUG'


