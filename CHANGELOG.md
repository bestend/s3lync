# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-01-10

### 🚀 Performance
- **Parallel file operations**: Directory sync now uses `ThreadPoolExecutor` (sync) and `asyncio.gather` (async) for up to 8x faster transfers
- Semaphore-based concurrency control (max 8 concurrent operations)

### ✨ New Features
- **Logging system**: Added `configure_logging()` and `get_logger()` for structured logging
  - Hierarchical loggers (`s3lync.core`, `s3lync.async_core`, etc.)
  - Replaces all `print()` statements with proper logging
- **Retry with exponential backoff**: Automatic retry for transient AWS errors
  - `@retry` decorator for sync functions
  - `@async_retry` decorator for async functions  
  - Configurable via `RetryConfig` class
  - Auto-detects retryable errors: `ThrottlingException`, `ServiceUnavailable`, `SlowDown`, etc.

### 🐛 Bug Fixes
- **Fixed closure bug in loops**: Callback functions in directory sync were capturing loop variables incorrectly
- **Fixed duplicate return statement** in `progress.py`
- **Fixed `aioboto3` dependency**: Moved from required to optional dependency (install with `pip install s3lync[async]`)

### 🧪 Testing
- Added 50+ new tests (86 total, all passing)
- New test files: `test_retry.py`, `test_logging.py`, `test_async_core.py`, `test_progress.py`
- Configured `pytest-asyncio` for async test support

### 📦 Dependencies
- `aioboto3` is now optional (async extra)
- Added `pytest-asyncio` to dev dependencies

## [0.1.0] - 2025-12-21

**Core Features**
- S3Object class for S3 object management
- Automatic download/upload synchronization with change detection
- MD5 hash verification for file integrity
- Context manager support for file operations (`with` statement)
- Force sync option to override smart caching
- Smart caching with local filesystem

**Configuration & Control**
- Environment variable configuration support
- Progress display modes (progress, compact, disabled)
- Auto-exclude hidden files (.git, __pycache__, etc)
- Exclude patterns support (upload)
- Support for S3-compatible endpoints (MinIO, etc)

**API Features**
- Pythonic API: Use S3 objects like local files
- Automatic change detection using MD5 hashing
- URI format: `s3://[secret:access@][endpoint/]bucket/key`
- Chainable exclude methods
- Custom local path support
- Cross-platform cache management

