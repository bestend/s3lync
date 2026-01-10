<p align="center">
  <img src="https://raw.githubusercontent.com/bestend/s3lync/main/assets/logo.png" width="360" />
</p>

<div align="center">

**Language:** [한국어](./README.KO.md) | English

**Use S3 objects like local files.**
*A Pythonic, automatic local sync layer for S3*

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/status-alpha-yellow)](https://github.com/bestend/s3lync)
[![Tests](https://github.com/bestend/s3lync/actions/workflows/tests.yml/badge.svg)](https://github.com/bestend/s3lync/actions/workflows/tests.yml)

</div>

---

## What is s3lync?

**s3lync** is a Python package that lets you work with **S3 objects as if they were local files**.

It automatically handles:

* 📥 Download on read
* 📤 Upload on write
* 🔍 Change detection via hashes
* 💾 Local caching
* 🔁 Optional force synchronization

All behind a **clean, Pythonic API**.

---

## Why s3lync?

Most S3 libraries focus on **object operations**.
s3lync focuses on **developer experience**.

* You open a file → it syncs
* You write to a file → it uploads
* You don't think about S3 until you need to

---

## Features

* 🚀 **Pythonic API** — Work with S3 like local files
* 🔄 **Automatic Sync** — Download & upload with change detection
* ✅ **Hash Verification** — MD5-based integrity checks
* 💾 **Smart Caching** — Local cache with intelligent invalidation
* 🔒 **Force Sync Mode** — Make local and remote identical
* ⚡ **Parallel Transfers** — Up to 8x faster directory sync
* 🔁 **Auto Retry** — Exponential backoff for transient failures
* 📝 **Structured Logging** — Configurable logging system

---

## Installation

```bash
pip install s3lync
```

### Async Support (Optional)

For async I/O operations, install `aioboto3`:

```bash
pip install s3lync[async]
# or
pip install aioboto3
```

---

## Quick Start

### Basic Usage (Sync)

```python
from s3lync import S3Object

# Create S3 object reference
obj = S3Object("s3://my-bucket/path/to/file.txt")

# Download from S3
obj.download()

# Upload to S3
obj.upload()
```

### Async Usage

```python
from s3lync import AsyncS3Object
import asyncio

async def main():
    # Create S3 object reference
    obj = AsyncS3Object("s3://my-bucket/path/to/file.txt")
    
    # Download from S3 asynchronously
    await obj.download()
    
    # Upload to S3 asynchronously
    await obj.upload()

asyncio.run(main())
```

### With boto3 Client (Recommended)

**Sync version:**
```python
from s3lync import S3Object
import boto3

# Create boto3 session and client
session = boto3.Session(profile_name="dev")
s3_client = session.client("s3")

# Create S3Object with client
obj = S3Object(
    "s3://bucket/key",
    local_path="./local",
    boto3_client=s3_client,
)

obj.upload()
```

**Async version:**
```python
from s3lync import AsyncS3Object
import aioboto3
import asyncio

async def main():
    # Create aioboto3 session
    session = aioboto3.Session()
    
    # Create AsyncS3Object with session
    obj = AsyncS3Object(
        "s3://bucket/key",
        local_path="./local",
        aioboto3_session=session,
    )
    
    await obj.upload()

asyncio.run(main())
```

---

## S3 URI Formats

s3lync supports multiple URI styles:

```text
s3://bucket/key
s3://endpoint@bucket/key
s3://secret_key:access_key@endpoint/bucket/key
s3://secret_key:access_key@https://endpoint/bucket/key
```

Examples:

```python
# Basic URI (credentials from environment variables)
S3Object("s3://my-bucket/data.json")

# Custom S3-compatible endpoint
S3Object("s3://minio.example.com@my-bucket/data.json")

# With credentials and HTTPS endpoint
S3Object("s3://mysecret:mykey@https://minio.example.com/my-bucket/data.json")
```

---

## How It Works

### Smart Synchronization

* Local file hash ↔ S3 ETag comparison
* Multipart uploads automatically skip hash checks
* `mirror=True` makes remote/local identical (also deletes extra files)

### Local Cache

* Default: `~/.cache/s3lync`
* Configurable via `XDG_CACHE_HOME`
* Or explicitly via `local_path`

---

## Common Operations

### Working with S3 Objects Like Files

**Method 1: Context manager with automatic sync (Recommended!)**

Sync:
```python
# Auto-downloads on read, auto-uploads on write
obj = S3Object("s3://bucket/token.json")
with obj.open("w") as f:
    json.dump({"access_token": "abc123"}, f)

with obj.open("r") as f:
    token = json.load(f)
```

Async:
```python
import asyncio
from s3lync import AsyncS3Object

async def main():
    obj = AsyncS3Object("s3://bucket/token.json")
    
    # Auto-uploads on write
    async with obj.open("w") as f:
        f.write('{"access_token": "abc123"}')
    
    # Auto-downloads on read
    async with obj.open("r") as f:
        data = f.read()

asyncio.run(main())
```

**Method 2: Standard Python `open()` (pathlib-compatible)**
```python
# S3Object implements __fspath__() protocol
obj.download()  # Manual sync
with open(obj, "r") as f:  # Works like a path!
    data = json.load(f)
obj.upload()  # Manual sync
```

**Method 3: Direct local_path access**
```python
# Direct file path manipulation
obj.download()
with open(obj.local_path, "r") as f:
    data = f.read()
obj.upload()
```

### Basic Download / Upload

```python
# Basic download
obj.download()

# Force sync: make remote identical to local (delete extra remote files if needed)
obj.upload(mirror=True)
```

### Directory Synchronization

s3lync supports recursive directory download and upload with smart change detection.

**Sync version:**
```python
# Download entire directory
obj = S3Object("s3://bucket/path/to/dir")
obj.download()

# Upload entire directory (excludes hidden files by default)
obj.upload()

# Mirror mode: delete files not present in source
obj.download(mirror=True)  # Deletes local files not in S3
obj.upload(mirror=True)    # Deletes remote files not in local
```

**Async version (faster with parallel processing):**
```python
import asyncio
from s3lync import AsyncS3Object

async def main():
    obj = AsyncS3Object("s3://bucket/path/to/dir")
    
    # Download entire directory asynchronously
    await obj.download()
    
    # Upload entire directory asynchronously
    await obj.upload()
    
    # Mirror mode
    await obj.download(mirror=True)
    await obj.upload(mirror=True)

asyncio.run(main())
```

**Sync multiple directories in parallel:**
```python
import asyncio
from s3lync import AsyncS3Object

async def sync_multiple():
    # Download multiple directories concurrently
    tasks = [
        AsyncS3Object("s3://bucket/dir1").download(),
        AsyncS3Object("s3://bucket/dir2").download(),
        AsyncS3Object("s3://bucket/dir3").download(),
    ]
    await asyncio.gather(*tasks)

asyncio.run(sync_multiple())
```

### Exclude Patterns

Control which files to include/exclude during sync operations using regex patterns.

#### Default Exclusions

- `/.*/` — Hidden files and directories (`.git`, `.venv`, etc)
- `__pycache__` — Python cache directories
- `.egg-info` — Python package metadata

#### How Excludes Work

**Object creation** — replaces all defaults:

```python
obj = S3Object(
    "s3://bucket/path",
    excludes=[r".*\.tmp$", r"\.git/.*"]
)
obj.upload()  # Uses ONLY: [.*\.tmp$, \.git/.*]
```

**Method call** — adds to defaults:

```python
obj = S3Object("s3://bucket/path")
obj.upload(excludes=[r".*\.tmp$"])
# Uses: [/.*/,  __pycache__, .egg-info, .*\.tmp$]

obj.download(excludes=[r"node_modules/.*"])
# Uses: [/.*/,  __pycache__, .egg-info, node_modules/.*]
```

---

## AWS Credentials

s3lync uses boto3's standard credential provider chain. 

### Profile Selection

boto3 supports **3 ways** to choose AWS profile. In production, explicit 
selection or environment variables are most common:

#### ✅ 1. Session with profile (Recommended)

```python
import boto3

session = boto3.Session(profile_name="dev")
s3_client = session.client("s3")

obj = S3Object("s3://bucket/key", boto3_client=s3_client)
```

**Advantages:**
- Explicit in code
- Works for multi-account scenarios
- Most flexible

#### ✅ 2. Environment Variable

```bash
export AWS_PROFILE=dev
```

```python
import boto3

session = boto3.Session()  # Auto-uses AWS_PROFILE
s3_client = session.client("s3")
```

**Advantages:**
- Environment-specific configuration
- CI/CD friendly
- No code changes

#### ⚠️ 3. Default Profile (Implicit)

```python
import boto3

session = boto3.Session()  # Uses [default] profile
s3_client = session.client("s3")
```

### Credentials Search Order

1. Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. AWS credentials file: `~/.aws/credentials` (respects `AWS_PROFILE`)
3. AWS config file: `~/.aws/config`
4. IAM Role (EC2, EKS, ECS environments)

### Quick Examples

```bash
# Using environment variables
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=ap-northeast-2

# Or using a profile
export AWS_PROFILE=my-profile
```

---

## Additional Features

### Logging Configuration

Configure structured logging for debugging and monitoring:

```python
from s3lync import configure_logging, get_logger
import logging

# Enable debug logging
configure_logging(level=logging.DEBUG)

# Or get a logger for custom use
logger = get_logger("my_app")
logger.info("Starting sync operation")

# Disable logging output
configure_logging(level=logging.CRITICAL)
```

### Automatic Retry

s3lync automatically retries on transient AWS errors with exponential backoff:

- `ThrottlingException`
- `ServiceUnavailable`  
- `SlowDown`
- `RequestTimeout`
- Connection errors

Default: 3 attempts with 0.5s base delay (max 30s).

You can also use retry decorators in your own code:

```python
from s3lync import retry, async_retry, RetryConfig

# Sync function with retry
@retry(max_attempts=5, base_delay=1.0)
def my_operation():
    # Your code here
    pass

# Async function with retry
@async_retry(max_attempts=3)
async def my_async_operation():
    # Your async code here
    pass
```

### Custom Callbacks

Chain custom callbacks with progress tracking:

```python
from s3lync import S3Object, chain_callbacks

def my_callback(bytes_transferred: int):
    print(f"Transferred: {bytes_transferred} bytes")

obj = S3Object("s3://bucket/large-file.bin", local_path="/tmp/file.bin")

# Use custom callback during download
metadata = obj._client.download_file(
    bucket="bucket",
    key="large-file.bin",
    local_path="/tmp/file.bin",
    callback=my_callback,
    show_progress=True
)
```

### Progress Display Control

Control progress bar display mode:

```python
from s3lync import S3Object
import boto3

# Option 1: Set default progress mode when creating object
obj = S3Object(
    "s3://bucket/key",
    local_path="./local",
    progress_mode="compact"  # "progress" (default), "compact", or "disabled"
)
obj.upload()

# Option 2: Override for specific operation
obj.download(progress_mode="disabled")

# Option 3: With boto3 client
session = boto3.Session(profile_name="dev")
s3_client = session.client("s3")
obj = S3Object(
    "s3://bucket/key",
    boto3_client=s3_client,
    progress_mode="compact"
)
```

**Progress Mode Options:**
- `"progress"` (default): Live tqdm progress bar with real-time updates
- `"compact"`: Summary output only on completion (non-interactive, great for CI/CD)
- `"disabled"`: No progress display

**Note:** In non-TTY environments (e.g., PyCharm console), progress bar rendering is auto-adjusted for compatibility.

---

## License

MIT License — see [LICENSE](./LICENSE)

---

## Author

**JunSeok Kim**
Built with ❤️ to make S3 feel local

