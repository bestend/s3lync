# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/).

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

