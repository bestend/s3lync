# Development Guide

This document outlines the development process and architecture of s3lync.

## Project Overview

s3lync is a Python package that simplifies working with S3 objects by making them behave like local files with automatic synchronization.

### Technology Stack
- **Python**: 3.9+
- **Package Manager**: pip, uv
- **Build System**: setuptools, wheel
- **Testing**: pytest, pytest-cov, pytest-mock
- **Code Quality**: black, ruff, mypy
- **AWS SDK**: boto3

## Project Structure

```
s3lync/
├── src/s3lync/              # Main package (src-layout)
│   ├── __init__.py          # Public API
│   ├── core.py              # S3Object class
│   ├── client.py            # boto3 wrapper
│   ├── exceptions.py        # Custom exceptions
│   ├── hash.py              # Hash utilities
│   ├── utils.py             # Utility functions
│   ├── config.py            # Configuration
│   ├── logging_config.py    # Logging utilities
│   └── manager.py           # Batch management
│
├── tests/                   # Test suite
│   ├── test_s3object.py
│   ├── test_utils.py
│   ├── test_manager.py
│   ├── test_config.py
│   └── conftest.py
│
├── pyproject.toml           # Project config
├── README.md                # User guide
├── readme.ko.md             # Korean guide
├── CONTRIBUTING.md          # Contribution guide
├── changelog.md             # Version history
├── developments.md          # Development notes
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
# Format code with Black
black src/ tests/

# Lint with Ruff
ruff check src/ tests/

# Type checking with mypy
mypy src/

# All checks at once
black src/ tests/ && ruff check src/ tests/ && mypy src/
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
- Main class for managing individual S3 objects
- Handles download/upload synchronization
- Implements MD5 hash verification
- Provides context manager interface

#### S3Client (`client.py`)
- Wrapper around boto3 S3 client
- Handles AWS authentication and API calls
- Implements retry logic

#### S3ObjectManager (`manager.py`)
- Manages multiple S3 objects
- Supports batch operations
- Tracks object state

#### Configuration (`config.py`)
- Manages application settings
- Reads from environment variables
- Provides defaults

#### Utilities
- `hash.py`: MD5 calculation and verification
- `utils.py`: Path handling, cache management
- `logging_config.py`: Logging setup

### Data Flow

1. **Download Process**
   ```
   S3Object.download()
   ├── Check if sync needed (hash comparison)
   ├── Create local directories
   ├── Download via S3Client
   ├── Calculate local hash
   └── Verify hash (optional)
   ```

2. **Upload Process**
   ```
   S3Object.upload()
   ├── Verify local file exists
   ├── Check if sync needed (hash comparison)
   ├── Upload via S3Client
   └── Update hash cache
   ```

3. **Context Manager Flow**
   ```
   with obj.open('w') as f:
   ├── Open local file
   └── On exit: upload()
   ```

## Testing Strategy

### Test Levels
1. **Unit Tests**: Test individual functions and classes in isolation
2. **Integration Tests**: Test components working together
3. **Mock Tests**: Use mocks for AWS API calls (no actual S3 access needed)

### Test Coverage
- Current: ~90%
- Target: >85%

### Mock Strategy
- All S3 operations are mocked to avoid AWS costs
- Local file operations are real for authenticity
- Use pytest fixtures for setup/teardown

### Example Test Pattern
```python
def test_download_with_hash_check(temp_dir):
    """Test download with hash verification."""
    with patch("s3lync.core.S3Client") as MockClient:
        mock_client = MockClient.return_value
        mock_client.download_file.return_value = {"ETag": '"abc123"'}
        
        obj = S3Object("s3://bucket/file.txt", local_path=...)
        obj._client = mock_client
        
        obj.download(check_hash=True)
        
        mock_client.download_file.assert_called_once()
```

## Configuration Management

### Environment Variables
- `AWS_REGION`: AWS region
- `AWS_DEFAULT_REGION`: Fallback AWS region
- `S3LYNC_DEBUG`: Enable debug mode
- `S3LYNC_LOG_LEVEL`: Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `XDG_CACHE_HOME`: Cache directory (all platforms - Linux, macOS, Windows)
- `HOME`: Home directory (used for `~/.cache/s3lync` if XDG_CACHE_HOME not set)

### AWS Credentials
- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Credential file: `~/.aws/credentials`
- IAM role: For EC2 instances

## Contributing

### Before Submitting PR
1. Run all tests: `pytest tests/`
2. Check code quality: `black src/ tests/ && ruff check src/ tests/ && mypy src/`
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
- Implement retry logic (default: 3 attempts)
- Use adaptive retry with exponential backoff
- Support multipart upload for large files (future)

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
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.org/)
- [AWS S3 API Reference](https://docs.aws.amazon.com/s3/latest/API/)

## Contact

For questions or suggestions, please open an issue on GitHub.

