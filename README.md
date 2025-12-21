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
* You don’t think about S3 until you need to

---

## Features

* 🚀 **Pythonic API** — Work with S3 like local files
* 🔄 **Automatic Sync** — Download & upload with change detection
* ✅ **Hash Verification** — MD5-based integrity checks
* 💾 **Smart Caching** — Local cache with intelligent invalidation
* 🎯 **Context Manager Support** — `with open(...)`
* 🔒 **Force Sync Mode** — Make local and remote identical

---

## Installation

```bash
pip install s3lync
```

### Development Install

```bash
git clone https://github.com/bestend/s3lync.git
cd s3lync
pip install -e ".[dev]"
```

---

## Quick Start

### Basic Usage

```python
from s3lync import S3Object

obj = S3Object("s3://my-bucket/path/to/file.txt")

obj.download()
obj.upload()
```

### Context Manager (Recommended)

```python
# Auto-download on read, auto-upload on write
with obj.open("r") as f:
    data = f.read()

with obj.open("w") as f:
    f.write("new content")
```

---

## S3 URI Formats

s3lync supports multiple URI styles:

```text
s3://bucket/key
s3://endpoint@bucket/key
s3://secret:access@endpoint/bucket/key
s3://secret:access@https://endpoint/bucket/key
```

Examples:

```python
S3Object("s3://my-bucket/data.json")
S3Object("s3://minio.example.com@my-bucket/data.json")
S3Object("s3://key:secret@https://minio.example.com/my-bucket/data.json")
```

---

## Common Operations

### Download / Upload

```python
obj.download()
obj.upload(mirror=True)
```

### Exclude Patterns

Hidden files and Python cache are excluded by default.

```python
obj.upload(excludes=[r".*\.tmp$", r"node_modules"])
obj.add_exclude(r".*\.log$")
```

Disable hidden-file exclusion:

```bash
export S3LYNC_EXCLUDE_HIDDEN=0
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

## Configuration

Configuration can be set via:

1. Environment variables (highest priority)
2. Programmatic overrides
3. Library defaults

### Common Settings

| Setting        | Env Var                 | Default    |
| -------------- | ----------------------- | ---------- |
| Log level      | `S3LYNC_LOG_LEVEL`      | `INFO`     |
| Progress mode  | `S3LYNC_PROGRESS_MODE`  | `progress` |
| Exclude hidden | `S3LYNC_EXCLUDE_HIDDEN` | `True`     |
| AWS region     | `AWS_REGION`            | auto       |

Example:

```bash
export S3LYNC_LOG_LEVEL=DEBUG
export S3LYNC_PROGRESS_MODE=disabled
```

### Programmatic configuration (from s3lync import Config)

```python
from s3lync import Config

# Set at runtime (env vars still have higher priority)
Config.set_debug_enabled(True)           # or False
Config.set_log_level("WARNING")         # DEBUG | INFO | WARNING | ERROR | CRITICAL
Config.set_progress_mode("compact")     # progress | compact | disabled
Config.set_exclude_hidden(False)         # include hidden files
Config.set_aws_region("ap-northeast-2")

# Read values
region = Config.get_aws_region()
debug = Config.is_debug_enabled()
mode = Config.get_progress_mode()
exclude_hidden = Config.should_exclude_hidden()

# Reset overrides (useful for tests)
Config.reset_runtime_overrides()
```

---

## AWS Credentials

s3lync uses boto3’s standard credential provider chain. You don’t need to pass keys to s3lync explicitly.

Search order (simplified):

1. Environment variables
   - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (and optional `AWS_SESSION_TOKEN`)
2. AWS credentials file
   - `~/.aws/credentials` (respects `AWS_PROFILE`)

Notes:
- If `AWS_PROFILE` is set, boto3 will use that profile from your local AWS config.
- On AWS environments (EC2/ECS), instance/role credentials will be discovered automatically if env/files are not set.

Quick examples:

```bash
# Using environment variables
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=ap-northeast-2

# Or use a profile in ~/.aws/credentials and select it
export AWS_PROFILE=my-profile
```

---

## Error Handling

```python
from s3lync import S3Object, HashMismatchError, SyncError

try:
    S3Object("s3://bucket/file.txt").download()
except HashMismatchError:
    print("Integrity check failed")
except SyncError:
    print("Sync error")
```

---

## Development

### Tests

```bash
pytest tests/
```

### Quality

```bash
ruff format src/ tests/
ruff check src/ tests/
mypy src/
```

---

## License

MIT License — see [LICENSE](./LICENSE)

---

## Author

**JunSeok Kim**
Built with ❤️ to make S3 feel local