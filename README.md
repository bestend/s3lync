# s3lync

<div align="center">

**Language:** [한국어](./README.KO.md) | English

**The Pythonic Bridge Between S3 and the Local Filesystem**

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/status-alpha-yellow)](https://github.com/bestend/s3lync)
[![Tests](https://github.com/bestend/s3lync/actions/workflows/tests.yml/badge.svg)](https://github.com/bestend/s3lync/actions/workflows/tests.yml)

</div>

---

> Use S3 objects like local files.  
> S3 local sync, done automatically.

s3lync is a Python package that simplifies working with Amazon S3 objects by making them behave like local files. It provides automatic synchronization, MD5 hash verification, and a clean, Pythonic API.

## Features

- 🚀 **Pythonic API**: Use S3 objects just like local files
- 🔄 **Automatic Sync**: Download and upload with change detection
- ✅ **Hash Verification**: MD5 checksum validation (customizable)
- 💾 **Smart Caching**: Automatic local caching with intelligent invalidation
- 🎯 **Context Manager**: Use with Python's `with` statement
- 🔒 **Force Sync**: Override smart caching when needed

## Installation

```bash
pip install s3lync
```

### Development Installation

```bash
git clone https://github.com/bestend/s3lync.git
cd s3lync
pip install -e ".[dev]"
```

## Quick Start

### Basic Usage

```python
from s3lync import S3Object

# Create S3 object reference
obj = S3Object('s3://my-bucket/path/to/file.txt')

# Download from S3
obj.download(check_hash=True)  # MD5 verification by default

# Upload to S3
obj.upload()

# Get local file path
local_file = obj.local_path
```

### With Custom Local Path

```python
obj = S3Object(
    's3://my-bucket/path/to/file.txt',
    local_path='/Users/john/tech/data/file.txt'
)
```

### Context Manager (Automatic Upload)

```python
# Write mode - automatically uploads on exit
with obj.open(mode='w') as f:
    f.write('Hello, S3!')

# Read mode - automatically downloads on enter
with obj.open(mode='r') as f:
    content = f.read()
    print(content)
```

### Traditional File Operations

```python
# Manual download and local file manipulation
obj.download()

import glob
for file in glob.glob(obj.local_path + '/*.json'):
    print(file)

# Modify local file
with open(obj.local_path, 'w') as f:
    f.write('new content')

# Manual upload
obj.upload()
```

### Force Sync

```python
# Always sync, ignore hash verification
obj.download(force_sync=True)
obj.upload(force_sync=True)
```

### Exclude Pattern (Upload Only)

```python
# Upload directory excluding .tmp files
obj.upload(exclude_pattern=r'.*\.tmp$')
```

## API Reference

### S3Object

#### Constructor

```python
S3Object(
    s3_uri: str,
    local_path: Optional[str] = None,
    region_name: Optional[str] = None
)
```

- **s3_uri**: S3 URI in format `s3://bucket/key`
- **local_path**: Optional local file/directory path. If omitted, uses system cache directory
- **region_name**: AWS region (optional, uses default AWS configuration)

#### Methods

##### `download(check_hash: bool = True, force_sync: bool = False) -> str`

Download S3 object (file or directory) to local.

- **check_hash**: Verify file integrity with MD5 (default: `True`)
- **force_sync**: When True, makes local identical to remote (default: `False`). Downloads all remote files/directories and deletes any local files/directories not present in remote.

Returns: Local path

**Raises**:
- `SyncError`: If download fails
- `HashMismatchError`: If hash verification fails

##### `upload(check_hash: bool = True, exclude_pattern: str = "", force_sync: bool = False) -> str`

Upload local object (file or directory) to S3.

- **check_hash**: Verify file integrity (default: `True`)
- **exclude_pattern**: Regex pattern to exclude files during upload (default: "")
- **force_sync**: When True, makes remote identical to local (default: `False`). Uploads all local files/directories and deletes any remote files/directories not present in local.

Returns: S3 URI

**Raises**:
- `S3ObjectError`: If local file doesn't exist
- `SyncError`: If upload fails

##### `open(mode: str = 'r', encoding: str = 'utf-8')`

Context manager for file operations.

- **mode**: File mode (`'r'`, `'w'`, `'rb'`, `'wb'`, etc.)
- **encoding**: Text encoding (default: `'utf-8'`)

Automatically downloads on read operations and uploads on write operations.

##### `exists() -> bool`

Check if S3 object exists.

##### `delete() -> bool`

Delete S3 object (file or directory).

##### `local_path` (property)

Get the local file/directory path.

## How It Works

### Smart Synchronization

s3lync uses MD5 hash comparison to determine if synchronization is needed:

1. **Download**: Compares local file hash with remote S3 ETag
2. **Upload**: Compares local file hash with remote S3 ETag
3. **Force Sync**: Bypasses hash comparison and always performs operation

### Local Caching

- **Default Cache**: Uses `~/.cache/s3lync` on all platforms (Linux, macOS, Windows)
- **Environment Variable**: Can be customized with `XDG_CACHE_HOME`
- **Custom Path**: Specify any local path when creating S3Object

### Hash Verification

By default, file integrity is verified after download using MD5:

```python
obj.download(check_hash=True)  # Default behavior
obj.download(check_hash=False)  # Skip verification
```

**Note**: For S3 objects uploaded via multipart upload, the ETag is not a valid MD5 hash. In such cases, hash verification is automatically skipped.

## Exception Handling

```python
from s3lync import S3Object, S3lyncError, HashMismatchError, SyncError

obj = S3Object('s3://bucket/file.txt')

try:
    obj.download()
except HashMismatchError:
    print("File corruption detected!")
except SyncError:
    print("Network error during download")
except S3lyncError:
    print("Unknown error")
```

## Configuration

### AWS Credentials

s3lync uses boto3's standard credential chain:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS credentials file (`~/.aws/credentials`)
3. IAM role (EC2 instances)

### Cache Directory

Default cache location is `~/.cache/s3lync`. Customize with environment variables:

```bash
# Set custom cache directory (all platforms)
export XDG_CACHE_HOME=/path/to/custom/cache
# Then cache will be at: /path/to/custom/cache/s3lync

# Or set HOME to change home directory
export HOME=/custom/home
# Then cache will be at: /custom/home/.cache/s3lync
```

## Examples

### Example 1: Download and Process JSON Files

```python
from s3lync import S3Object
import json

obj = S3Object('s3://my-bucket/data/config.json')
obj.download()

with open(obj.local_path) as f:
    config = json.load(f)
    print(config)
```

### Example 2: Generate Report and Upload

```python
from s3lync import S3Object

obj = S3Object(
    's3://my-bucket/reports/report.txt',
    local_path='./reports/report.txt'
)

# Generate report locally
with open(obj.local_path, 'w') as f:
    f.write('Monthly Report\n')
    f.write('...')

# Upload to S3
obj.upload()
```

### Example 3: Automatic Sync with Context Manager

```python
from s3lync import S3Object

obj = S3Object('s3://my-bucket/logs/app.log')

# Read and process
with obj.open('r') as f:
    for line in f:
        print(line)

# Append logs
with obj.open('a') as f:
    f.write('\n[NEW] Appended log entry')
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

## Contributing

Contributions are welcome! Please refer to [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## Development Resources

- [Development Guide](./DEVELOPMENTS.md) - Architecture and development workflow
- [Changelog](./CHANGELOG.md) - Version history and release notes
- [Contributing Guide](./CONTRIBUTING.md) - How to contribute to the project

## License

MIT License - see [LICENSE](./LICENSE) file for details

## Author

**JunSeok Kim** - Created with ❤️

## Acknowledgments

- Inspired by modern Python packages for cloud storage
- Built on top of [boto3](https://boto3.amazonaws.com/)

