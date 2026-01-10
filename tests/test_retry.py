"""
Tests for retry utilities.
"""

import pytest
from botocore.exceptions import ClientError

from s3lync.retry import (
    RetryConfig,
    async_retry,
    calculate_backoff,
    is_retryable_error,
    retry,
)


class TestIsRetryableError:
    """Tests for is_retryable_error function."""

    def test_retryable_client_error(self):
        """Test that throttling errors are retryable."""
        error = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "HeadObject",
        )
        assert is_retryable_error(error) is True

    def test_non_retryable_client_error(self):
        """Test that 404 errors are not retryable."""
        error = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "HeadObject",
        )
        assert is_retryable_error(error) is False

    def test_connection_error_types(self):
        """Test that connection errors are retryable by name."""

        # Custom class with ConnectionError name to test name-based detection
        class MockConnectionError(Exception):
            pass

        MockConnectionError.__name__ = "ConnectionError"
        error = MockConnectionError("Connection failed")
        assert is_retryable_error(error) is True

    def test_generic_exception(self):
        """Test that generic exceptions are not retryable."""
        error = ValueError("Invalid value")
        assert is_retryable_error(error) is False


class TestCalculateBackoff:
    """Tests for calculate_backoff function."""

    def test_exponential_growth(self):
        """Test that delay grows exponentially."""
        delays = [calculate_backoff(i, jitter=False) for i in range(5)]
        assert delays[0] == 0.5
        assert delays[1] == 1.0
        assert delays[2] == 2.0
        assert delays[3] == 4.0
        assert delays[4] == 8.0

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        delay = calculate_backoff(10, base_delay=1.0, max_delay=5.0, jitter=False)
        assert delay == 5.0

    def test_jitter_within_bounds(self):
        """Test that jitter produces values within expected range."""
        for _ in range(100):
            delay = calculate_backoff(2, base_delay=1.0, jitter=True)
            # With jitter, delay should be between 0 and 4.0 (2^2)
            assert 0 <= delay <= 4.0


class TestRetryDecorator:
    """Tests for retry decorator."""

    def test_success_no_retry(self):
        """Test that successful function doesn't retry."""
        call_count = 0

        @retry(max_attempts=3)
        def always_succeeds():
            nonlocal call_count
            call_count += 1
            return "success"

        result = always_succeeds()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_retryable_error(self):
        """Test that retryable errors trigger retry."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ClientError(
                    {
                        "Error": {
                            "Code": "ThrottlingException",
                            "Message": "Rate exceeded",
                        }
                    },
                    "test",
                )
            return "success"

        result = fails_then_succeeds()
        assert result == "success"
        assert call_count == 3

    def test_no_retry_on_non_retryable_error(self):
        """Test that non-retryable errors don't trigger retry."""
        call_count = 0

        @retry(max_attempts=3)
        def raises_non_retryable():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            raises_non_retryable()

        assert call_count == 1

    def test_max_attempts_exceeded(self):
        """Test that max attempts is respected."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ClientError(
                {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
                "test",
            )

        with pytest.raises(ClientError):
            always_fails()

        assert call_count == 3

    def test_on_retry_callback(self):
        """Test that on_retry callback is called."""
        retry_attempts = []

        def on_retry(error, attempt):
            retry_attempts.append(attempt)

        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, on_retry=on_retry)
        def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ClientError(
                    {
                        "Error": {
                            "Code": "ThrottlingException",
                            "Message": "Rate exceeded",
                        }
                    },
                    "test",
                )
            return "success"

        fails_twice()
        assert retry_attempts == [0, 1]


class TestAsyncRetryDecorator:
    """Tests for async_retry decorator."""

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """Test that successful async function doesn't retry."""
        call_count = 0

        @async_retry(max_attempts=3)
        async def always_succeeds():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await always_succeeds()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_retryable_error(self):
        """Test that retryable errors trigger retry in async."""
        call_count = 0

        @async_retry(max_attempts=3, base_delay=0.01)
        async def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ClientError(
                    {
                        "Error": {
                            "Code": "ThrottlingException",
                            "Message": "Rate exceeded",
                        }
                    },
                    "test",
                )
            return "success"

        result = await fails_then_succeeds()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test that max attempts is respected in async."""
        call_count = 0

        @async_retry(max_attempts=3, base_delay=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ClientError(
                {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
                "test",
            )

        with pytest.raises(ClientError):
            await always_fails()

        assert call_count == 3


class TestRetryConfig:
    """Tests for RetryConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.jitter is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=60.0,
            jitter=False,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.jitter is False

    def test_get_delay(self):
        """Test get_delay method."""
        config = RetryConfig(base_delay=1.0, jitter=False)
        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0
