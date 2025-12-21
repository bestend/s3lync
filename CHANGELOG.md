# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-12-21

### Added
- Initial alpha release
- S3Object class for S3 object management
- Automatic download/upload synchronization
- MD5 hash verification for file integrity
- Context manager support for file operations
- S3ObjectManager for batch operations
- Configuration management (Config class)
- Logging support with get_logger() and configure_logging()
- Smart caching with local filesystem
- 38 test cases with ~90% code coverage
- Complete documentation (README, CONTRIBUTING)
- MIT License

### Features
- Pythonic API for S3 operations
- Automatic change detection using MD5
- Force sync option to bypass hash checks
- OS-specific cache directory management
- Support for custom local file paths
- Batch operations for multiple S3 objects
- Environment variable configuration
- Debug mode support

### Infrastructure
- src-layout project structure
- pyproject.toml with modern Python packaging
- pytest-based testing framework
- Type hints for all functions
- Comprehensive docstrings

---

## Format

This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

Versions follow [Semantic Versioning](https://semver.org/) (Major.Minor.Patch).

## Future Releases

### Planned for v0.2.0
- Async API support
- Multipart upload optimization
- S3 statistics (file counts, sizes)
- Scheduling support
- CLI tool

### Considered for future versions
- LRU cache management
- Monitoring and metrics
- Custom retry policies
- Streaming support

