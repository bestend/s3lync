"""
Tests for progress bar utilities.
"""

import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from s3lync.progress import (
    ProgressBar,
    chain_callbacks,
    create_progress_callback,
    _format_bytes,
    _is_pycharm_console,
)


class TestFormatBytes:
    """Tests for _format_bytes function."""

    def test_bytes(self):
        """Test formatting bytes."""
        assert _format_bytes(0) == "0 B"
        assert _format_bytes(512) == "512 B"
        assert _format_bytes(1023) == "1023 B"

    def test_kibibytes(self):
        """Test formatting kibibytes."""
        assert _format_bytes(1024) == "1.0 KiB"
        assert _format_bytes(1536) == "1.5 KiB"

    def test_mebibytes(self):
        """Test formatting mebibytes."""
        assert _format_bytes(1024 * 1024) == "1.0 MiB"
        assert _format_bytes(1024 * 1024 * 5) == "5.0 MiB"

    def test_gibibytes(self):
        """Test formatting gibibytes."""
        assert _format_bytes(1024 * 1024 * 1024) == "1.0 GiB"


class TestChainCallbacks:
    """Tests for chain_callbacks function."""

    def test_single_callback(self):
        """Test with single callback."""
        calls = []

        def callback(n):
            calls.append(n)

        chained = chain_callbacks(callback)
        chained(10)

        assert calls == [10]

    def test_two_callbacks(self):
        """Test chaining two callbacks."""
        calls1 = []
        calls2 = []

        def callback1(n):
            calls1.append(n)

        def callback2(n):
            calls2.append(n)

        chained = chain_callbacks(callback1, callback2)
        chained(10)

        assert calls1 == [10]
        assert calls2 == [10]

    def test_none_secondary(self):
        """Test with None secondary callback."""
        calls = []

        def callback(n):
            calls.append(n)

        chained = chain_callbacks(callback, None)
        chained(10)

        assert calls == [10]


class TestProgressBar:
    """Tests for ProgressBar class."""

    def test_init_progress_mode(self):
        """Test initialization with progress mode."""
        # Note: In non-TTY environments (like test runners), progress mode
        # may auto-switch to compact mode
        pbar = ProgressBar(100, desc="test", mode="progress")
        assert pbar.mode in ("progress", "compact")  # May be compact in test env
        assert pbar.total == 100
        assert pbar.desc == "test"
        pbar.close()

    def test_init_compact_mode(self):
        """Test initialization with compact mode."""
        pbar = ProgressBar(100, desc="test", mode="compact")
        assert pbar.mode == "compact"
        assert pbar.pbar is None
        pbar.close()

    def test_init_disabled_mode(self):
        """Test initialization with disabled mode."""
        pbar = ProgressBar(100, desc="test", mode="disabled")
        assert pbar.mode == "disabled"
        assert pbar.pbar is None
        pbar.close()

    def test_invalid_mode_raises(self):
        """Test that invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid progress_mode"):
            ProgressBar(100, mode="invalid")

    def test_update_compact_mode(self):
        """Test update in compact mode accumulates bytes."""
        pbar = ProgressBar(100, mode="compact")
        pbar.update(10)
        pbar.update(20)
        assert pbar._transferred == 30
        pbar.close()

    def test_context_manager(self):
        """Test context manager protocol."""
        # Use compact mode explicitly to avoid tqdm
        with ProgressBar(100, mode="compact") as pbar:
            pbar.update(50)
            assert pbar._transferred == 50


class TestCreateProgressCallback:
    """Tests for create_progress_callback function."""

    def test_creates_pbar_and_callback(self):
        """Test that function returns progress bar and callback."""
        pbar, callback = create_progress_callback(100, desc="test", mode="disabled")

        assert isinstance(pbar, ProgressBar)
        assert callable(callback)
        pbar.close()

    def test_callback_updates_pbar(self):
        """Test that callback updates progress bar."""
        pbar, callback = create_progress_callback(100, mode="compact")

        callback(10)
        callback(20)

        assert pbar._transferred == 30
        pbar.close()


class TestIsPycharmConsole:
    """Tests for _is_pycharm_console function."""

    def test_pycharm_hosted_env(self):
        """Test detection via PYCHARM_HOSTED env var."""
        with patch.dict("os.environ", {"PYCHARM_HOSTED": "1"}):
            assert _is_pycharm_console() is True

    def test_jetbrains_ide_env(self):
        """Test detection via JETBRAINS_IDE env var."""
        with patch.dict("os.environ", {"JETBRAINS_IDE": "1"}, clear=True):
            assert _is_pycharm_console() is True

    def test_non_tty_stdout(self):
        """Test detection via non-TTY stdout."""
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(sys.stdout, "isatty", return_value=False):
                assert _is_pycharm_console() is True

    def test_normal_terminal(self):
        """Test normal terminal detection."""
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(sys.stdout, "isatty", return_value=True):
                assert _is_pycharm_console() is False
