<p align="center">
  <img src="https://raw.githubusercontent.com/bestend/s3lync/main/assets/logo.png" width="360" />
</p>

<div align="center">

**Language:** 한국어 | [English](./README.md)

**S3 객체를 로컬 파일처럼 사용하세요.**

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/bestend/s3lync/actions/workflows/tests.yml/badge.svg)](https://github.com/bestend/s3lync/actions/workflows/tests.yml)

</div>

---

## 왜 s3lync인가요?

대부분의 S3 라이브러리는 **객체 단위 조작**에 초점이 맞춰져 있습니다.
s3lync는 **개발자 경험(DX)**에 집중합니다.

* 파일을 열면 → 자동으로 동기화
* 파일에 쓰면 → 자동 업로드
* 평소엔 S3를 신경 쓰지 않아도 됩니다

## 주요 기능

🚀 Pythonic API • 🔄 자동 동기화 • ✅ Hash 검증 • 💾 스마트 캐싱 • ⚡ 병렬 전송 • 🔁 자동 재시도

## 설치

```bash
pip install s3lync

# 비동기 지원
pip install s3lync[async]
```

## 빠른 시작

```python
from s3lync import S3Object

obj = S3Object("s3://my-bucket/path/to/file.txt")

# 컨텍스트 매니저 (권장) - 읽기/쓰기 시 자동 동기화
with obj.open("w") as f:
    f.write("Hello, S3!")

with obj.open("r") as f:
    print(f.read())

# 또는 수동 제어
obj.download()
obj.upload()
```

### 비동기

```python
from s3lync import AsyncS3Object

async def main():
    obj = AsyncS3Object("s3://my-bucket/file.txt")
    await obj.download()
    await obj.upload()
```

### boto3 Client 사용

```python
import boto3
from s3lync import S3Object

session = boto3.Session(profile_name="dev")
obj = S3Object("s3://bucket/key", boto3_client=session.client("s3"))
```

## S3 URI 포맷

```
s3://bucket/key
s3://endpoint@bucket/key
s3://secret:access@endpoint/bucket/key
```

## 디렉토리 동기화

```python
obj = S3Object("s3://bucket/path/to/dir")
obj.download()  # 전체 디렉토리 다운로드
obj.upload()    # 전체 디렉토리 업로드

# Mirror 모드: 원본에 없는 파일 삭제
obj.download(mirror=True)
obj.upload(mirror=True)
```

## Exclude 패턴

```python
# 기본 제외: 숨김파일, __pycache__, .egg-info
obj = S3Object("s3://bucket/path", excludes=[r".*\.tmp$"])

# 또는 메서드 호출 시 기본값에 추가
obj.upload(excludes=[r"node_modules/.*"])
```

## 설정

### 환경변수

| 변수 | 설명 |
|------|------|
| `S3LYNC_MAX_WORKERS` | 최대 동시 전송 수 (기본값: 8) |
| `AWS_PROFILE` | AWS 프로필 이름 |

### Progress 모드

```python
obj = S3Object("s3://bucket/key", progress_mode="compact")
# "progress" (기본값), "compact", "disabled"
```

### 로깅

```python
from s3lync import configure_logging
import logging

configure_logging(level=logging.DEBUG)
```

## 라이선스

MIT License — [LICENSE](./LICENSE)
