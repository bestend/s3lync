# Development Guide

This document outlines the development process and architecture of s3lync.

## Project Overview

s3lync is a Python package that simplifies working with S3 objects by making them behave like local files with automatic synchronization.

### Technology Stack
- Python: 3.9+
- Package Manager: pip, uv
- Build System: setuptools, wheel
- Testing: pytest (with unittest.mock), pytest-cov
- Code Quality: Ruff (format + lint), mypy
- AWS SDK: boto3

## Project Structure

```
s3lync/
├── src/s3lync/              # Main package (src-layout)
│   ├── __init__.py          # Public API (re-exports S3Object, Config, exceptions, ProgressBar)
│   ├── core.py              # S3Object class (high-level sync)
│   ├── client.py            # boto3 wrapper (low-level I/O)
│   ├── config.py            # Configuration (env + runtime overrides)
│   ├── progress.py          # Progress display utilities (tqdm + compact)
│   ├── hash.py              # Hash utilities (MD5, ETag helpers)
│   ├── utils.py             # Utility functions (S3 URI parsing, cache dirs, paths)
│   └── exceptions.py        # Custom exceptions
│
├── tests/                   # Test suite
│   ├── test_s3object.py
│   ├── test_utils.py
│   ├── test_config.py
│   └── conftest.py
│
├── pyproject.toml           # Project config
├── README.md                # User guide (EN)
├── README.KO.md             # User guide (KO)
├── CHANGELOG.md             # Version history
├── DEVELOPMENTS.md          # Development notes (this file)
└── LICENSE                  # MIT License
```

## Getting Started

### Prerequisites
- Python 3.9 or higher
- pip or uv

### Setup Development Environment

1. **Clone the repository**
   ```bash
   git clone https://github.com/bestend/s3lync.git
   cd s3lync
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src/s3lync tests/

# Run specific test file
pytest tests/test_s3object.py -v

# Run with output capture disabled
pytest tests/ -s
```

### Code Quality

```bash
# Format code with Ruff
ruff format src/ tests/

# Lint with Ruff
ruff check src/ tests/

# Type checking with mypy
mypy src/

# All checks at once
ruff format src/ tests/ && ruff check src/ tests/ && mypy src/
```

### Debugging

Enable debug logging:
```bash
export S3LYNC_DEBUG=1
export S3LYNC_LOG_LEVEL=DEBUG
```

Use breakpoints in tests:
```python
def test_something():
    import pdb; pdb.set_trace()
    # test code
```

## Architecture

### Core Components

#### S3Object (`core.py`)
- Main high-level class for managing files/directories on S3
- Download/upload synchronization (file and directory, recursive)
- Smart sync using ETag/MD5 comparison (skips multipart ETag MD5 check)
- Context manager interface (auto upload on exit for write mode)
- Exclude patterns (regex) and hidden-files default exclusion via Config

#### S3Client (`client.py`)
- Thin wrapper around boto3 S3 client
- Handles authentication, region/endpoint, and basic API calls
- Progress callback wiring for tqdm/compact modes

#### Progress (`progress.py`)
- Two display modes: "progress" (interactive tqdm) and "compact" (one-line summary on completion)
- Overall (position=0, leave=True) + per-file (position=1, leave=False) bars in progress mode
- Auto-downgrade to compact when run in PyCharm/JetBrains Run console or non-TTY

#### Configuration (`config.py`)
- Settings resolution priority: Environment variables > Programmatic overrides (via setters) > Library defaults
- Static getters/setters: set_aws_region, set_debug_enabled, set_log_level, set_progress_mode, set_exclude_hidden, reset_runtime_overrides
- Debug mode boolean flag; log level string; progress mode validation; hidden files exclusion default enabled

#### Utilities
- `hash.py`: MD5 calculation and verification helpers, ETag normalization
- `utils.py`: S3 URI parsing, cache directory resolution, path normalization, fs helpers
- `exceptions.py`: S3lyncError, HashMismatchError, SyncError, S3ObjectError

### Data Flow

1. Download (file or directory)
   ```
   S3Object.download(check_hash=True, excludes=None, force_sync=False)
   ├── For directory: pre-scan remote prefix → compute total files/bytes → print summary
   ├── Create overall ProgressBar (position=0) and chain per-file callbacks (position=1)
   ├── For each file: skip if equal (unless force_sync), then download via S3Client
   ├── If check_hash and ETag not multipart: compare MD5 vs ETag → raise on mismatch
   └── On force_sync: remove local files/dirs not present in remote
   ```

2. Upload (file or directory)
   ```
   S3Object.upload(check_hash=True, excludes=None, force_sync=False)
   ├── Validate local path exists
   ├── For directory: pre-scan local → compute total files/bytes → print summary
   ├── Create overall ProgressBar (position=0) and chain per-file callbacks (position=1)
   ├── For each file: skip if equal (unless force_sync), then upload via S3Client
   └── On force_sync: delete remote files not present locally
   ```

3. Progress modes and environments
   - progress: interactive tqdm with overall + single per-file sub bar
   - compact: per-file prints one-line summary on completion; overall summary printed by ProgressBar
   - In PyCharm/JetBrains Run console or non-TTY, progress automatically downgrades to compact

4. Context manager
   ```
   with obj.open('w') as f:
       # write file
   # upon exit, upload() is called automatically
   ```

## Testing Strategy

### Test Levels
1. **Unit Tests**: Test individual functions and classes in isolation
2. **Integration Tests**: Test components working together
3. **Mock Tests**: Use mocks for AWS API calls (no actual S3 access needed)

### Test Coverage
- Target: >85%

### Mock Strategy
- All S3 operations are mocked to avoid AWS costs
- Local file operations are real for authenticity
- Use pytest fixtures for setup/teardown

### Example Test Pattern

```python
from unittest.mock import patch
from s3lync import S3Object


def test_download_with_hash_check(tmp_path):
   with patch("s3lync.core.S3Client") as MockClient:
      mock_client = MockClient.return_value
      mock_client.download_file.return_value = {"ETag": '"abc123"'}

      obj = S3Object("s3://bucket/file.txt", local_path=str(tmp_path / "file.txt"))
      obj._client = mock_client

      obj.download(use_checksum=True)

      mock_client.download_file.assert_called_once()
```

## Configuration Management

### Resolution Priority
1) Environment variables
2) Programmatic overrides set via `Config.set_*`
3) Library defaults

### Environment Variables
- `AWS_REGION`, `AWS_DEFAULT_REGION` — AWS region
- `S3LYNC_DEBUG` — Enable debug mode when set to 1/true/yes
- `S3LYNC_LOG_LEVEL` — Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `S3LYNC_PROGRESS_MODE` — progress | compact | disabled
- `S3LYNC_EXCLUDE_HIDDEN` — Exclude hidden files when 1/true/yes (default: exclude)
- `XDG_CACHE_HOME` — Cache directory root
- `HOME` — Used for `~/.cache/s3lync` when XDG not set

### Programmatic Configuration
```python
from s3lync import Config

Config.set_debug_enabled(True)
Config.set_log_level("WARNING")
Config.set_progress_mode("compact")
Config.set_exclude_hidden(False)
Config.set_aws_region("ap-northeast-2")

# Clear overrides (tests)
Config.reset_runtime_overrides()
```

Note: When mode is set to "progress", the library auto-detects PyCharm/JetBrains Run console or a non-TTY stdout and downgrades to "compact" for clean output.

### AWS Credentials
- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Credential file: `~/.aws/credentials`
- IAM role: For EC2 instances

## Contributing

### Before Submitting PR
1. Run all tests: `pytest tests/`
2. Check code quality: `ruff format src/ tests/ && ruff check src/ tests/ && mypy src/`
3. Update documentation if needed
4. Add tests for new features
5. Ensure 100% test pass rate

### Commit Messages
Use conventional commit format:
```
feat: add new feature
fix: fix a bug
docs: update documentation
test: add tests
refactor: refactor code
```

### Pull Request Process
1. Fork the repository
2. Create feature branch: `git checkout -b feature/description`
3. Commit changes: `git commit -am "feat: description"`
4. Push branch: `git push origin feature/description`
5. Create Pull Request

## Release Process

### Version Numbering
Uses Semantic Versioning: MAJOR.MINOR.PATCH

### Release Steps
1. Update `version` in `pyproject.toml`
2. Update `changelog.md`
3. Commit: `git commit -am "release: v0.x.x"`
4. Create tag: `git tag -a v0.x.x -m "Release v0.x.x"`
5. Push: `git push origin main && git push origin --tags`
6. GitHub Actions will handle PyPI deployment

## Performance Considerations

### Caching Strategy
- Use MD5 hashing for change detection
- Cache hash values locally
- Skip hash verification for multipart uploads

### S3 Operations
- Uses botocore.Config for retries (defaults)
- Multipart uploads may produce non-MD5 ETags; hash check skipped accordingly

### Memory Management
- Stream large files when possible
- Clean up temporary files immediately
- Use context managers for resource cleanup

## Known Issues and Limitations

### Current
1. Multipart uploads don't have valid MD5 in ETag (skips verification)
2. No async support yet
3. Single-threaded operations only

### Future Improvements
1. Async API support
2. Multipart upload handling
3. Parallel operations
4. Streaming support
5. Custom retry policies

## Debugging Tips

### Common Issues

**ImportError: No module named 'boto3'**
```bash
pip install boto3 botocore
```

**Hash mismatch errors**
- Check if file was uploaded via multipart (ETag won't match MD5)
- Use `check_hash=False` temporarily to debug
- Enable debug logging to see hash values

**Timeout errors**
- Check AWS region settings
- Verify network connectivity
- Check AWS credentials

### Useful Debug Commands

```python
# Check if object exists
import boto3
s3 = boto3.client('s3')
s3.head_object(Bucket='bucket', Key='key')

# Get object metadata
metadata = s3.head_object(Bucket='bucket', Key='key')
print(metadata['ETag'])

# Test hash
from s3lync.hash import calculate_file_hash
hash_val = calculate_file_hash('/path/to/file')
print(hash_val)
```

## Resources

- [boto3 Documentation](https://boto3.amazonaws.com/)
- [pytest Documentation](https://docs.pytest.org/)
- [tqdm Documentation](https://tqdm.github.io/)
- [AWS S3 API Reference](https://docs.aws.amazon.com/s3/latest/API/)

## Contact

For questions or suggestions, please open an issue on GitHub.

