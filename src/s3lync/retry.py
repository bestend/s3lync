"""
Retry utilities for s3lync.
"""

import asyncio
import functools
import random
import time
from typing import Any, Awaitable, Callable, Optional, Tuple, Type, TypeVar

from botocore.exceptions import ClientError

from .logging import get_logger

_logger = get_logger("retry")

# Common retryable error codes from AWS
RETRYABLE_ERROR_CODES = frozenset(
    {
        "RequestTimeout",
        "RequestTimeoutException",
        "ThrottlingException",
        "Throttling",
        "SlowDown",
        "ServiceUnavailable",
        "InternalError",
        "RequestLimitExceeded",
        "BandwidthLimitExceeded",
        "ProvisionedThroughputExceededException",
    }
)

T = TypeVar("T")


def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable.

    Args:
        error: The exception to check

    Returns:
        True if the error is retryable
    """
    if isinstance(error, ClientError):
        error_code = error.response.get("Error", {}).get("Code", "")
        return error_code in RETRYABLE_ERROR_CODES

    # Connection errors are generally retryable
    error_name = type(error).__name__
    retryable_types = {
        "ConnectionError",
        "ConnectTimeoutError",
        "ReadTimeoutError",
        "EndpointConnectionError",
        "ConnectionClosedError",
    }
    return error_name in retryable_types


def calculate_backoff(
    attempt: int,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    jitter: bool = True,
) -> float:
    """
    Calculate exponential backoff delay with optional jitter.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter

    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * 2^attempt
    delay: float = min(base_delay * (2**attempt), max_delay)

    if jitter:
        # Full jitter: random value between 0 and calculated delay
        delay = random.uniform(0, delay)

    return delay


def retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for synchronous functions with retry logic.

    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called on each retry (exception, attempt)

    Returns:
        Decorated function

    Example:
        @retry(max_attempts=3)
        def download_file(bucket, key):
            ...
    """
    if retryable_exceptions is None:
        retryable_exceptions = (Exception,)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if not is_retryable_error(e):
                        raise

                    if attempt == max_attempts - 1:
                        _logger.warning(
                            f"Max retries ({max_attempts}) reached for {func.__name__}"
                        )
                        raise

                    delay = calculate_backoff(attempt, base_delay, max_delay)
                    _logger.debug(
                        f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                        f"after {delay:.2f}s due to: {e}"
                    )

                    if on_retry:
                        on_retry(e, attempt)

                    time.sleep(delay)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator for async functions with retry logic.

    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called on each retry (exception, attempt)

    Returns:
        Decorated async function

    Example:
        @async_retry(max_attempts=3)
        async def download_file(bucket, key):
            ...
    """
    if retryable_exceptions is None:
        retryable_exceptions = (Exception,)

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if not is_retryable_error(e):
                        raise

                    if attempt == max_attempts - 1:
                        _logger.warning(
                            f"Max retries ({max_attempts}) reached for {func.__name__}"
                        )
                        raise

                    delay = calculate_backoff(attempt, base_delay, max_delay)
                    _logger.debug(
                        f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                        f"after {delay:.2f}s due to: {e}"
                    )

                    if on_retry:
                        on_retry(e, attempt)

                    await asyncio.sleep(delay)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 30.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            jitter: Whether to add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Get delay for given attempt number."""
        return calculate_backoff(attempt, self.base_delay, self.max_delay, self.jitter)


# Default retry configuration
DEFAULT_RETRY_CONFIG = RetryConfig()
