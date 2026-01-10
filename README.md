<p align="center">
  <img src="https://raw.githubusercontent.com/bestend/s3lync/main/assets/logo.png" width="360" />
</p>

<div align="center">

**Language:** [한국어](./README.KO.md) | English

**Use S3 objects like local files.**

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/bestend/s3lync/actions/workflows/tests.yml/badge.svg)](https://github.com/bestend/s3lync/actions/workflows/tests.yml)

</div>

---

## Why s3lync?

Most S3 libraries focus on **object operations**.
s3lync focuses on **developer experience**.

* You open a file → it syncs
* You write to a file → it uploads
* You don't think about S3 until you need to

## Features

🚀 Pythonic API • 🔄 Auto Sync • ✅ Hash Verification • 💾 Smart Caching • ⚡ Parallel Transfers • 🔁 Auto Retry

## Installation

```bash
pip install s3lync

# With async support
pip install s3lync[async]
```

## Quick Start

```python
from s3lync import S3Object

obj = S3Object("s3://my-bucket/path/to/file.txt")

# Context manager (recommended) - auto sync on read/write
with obj.open("w") as f:
    f.write("Hello, S3!")

with obj.open("r") as f:
    print(f.read())

# Or manual control
obj.download()
obj.upload()
```

### Async

```python
from s3lync import AsyncS3Object

async def main():
    obj = AsyncS3Object("s3://my-bucket/file.txt")
    await obj.download()
    await obj.upload()
```

### With boto3 Client

```python
import boto3
from s3lync import S3Object

session = boto3.Session(profile_name="dev")
obj = S3Object("s3://bucket/key", boto3_client=session.client("s3"))
```

## S3 URI Formats

```
s3://bucket/key
s3://endpoint@bucket/key
s3://secret:access@endpoint/bucket/key
```

## Directory Sync

```python
obj = S3Object("s3://bucket/path/to/dir")
obj.download()  # Download entire directory
obj.upload()    # Upload entire directory

# Mirror mode: delete files not in source
obj.download(mirror=True)
obj.upload(mirror=True)
```

## Exclude Patterns

```python
# Default excludes: hidden files, __pycache__, .egg-info
obj = S3Object("s3://bucket/path", excludes=[r".*\.tmp$"])

# Or add to defaults at method call
obj.upload(excludes=[r"node_modules/.*"])
```

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `S3LYNC_MAX_WORKERS` | Max concurrent transfers (default: 8) |
| `AWS_PROFILE` | AWS profile name |

### Progress Modes

```python
obj = S3Object("s3://bucket/key", progress_mode="compact")
# "progress" (default), "compact", "disabled"
```

### Logging

```python
from s3lync import configure_logging
import logging

configure_logging(level=logging.DEBUG)
```

## License

MIT License — see [LICENSE](./LICENSE)
