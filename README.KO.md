<p align="center">
  <img src="https://raw.githubusercontent.com/bestend/s3lync/main/assets/logo.png" width="360" />
</p>

<div align="center">

**Language:** 한국어 | [English](./README.md)

**S3 객체를 로컬 파일처럼 사용하세요.**
*S3를 위한 Pythonic한 자동 로컬 싱크 레이어*

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/status-alpha-yellow)](https://github.com/bestend/s3lync)
[![Tests](https://github.com/bestend/s3lync/actions/workflows/tests.yml/badge.svg)](https://github.com/bestend/s3lync/actions/workflows/tests.yml)

</div>

---

## s3lync란?

**s3lync**는 Amazon S3 객체를 **마치 로컬 파일처럼 다룰 수 있게 해주는 Python 패키지**입니다.

자동으로 처리하는 작업들:

* 📥 읽을 때 자동 다운로드
* 📤 쓸 때 자동 업로드
* 🔍 Hash 기반 변경 감지
* 💾 로컬 캐싱
* 🔁 필요 시 강제 동기화

모든 기능은 **간결하고 Pythonic한 API** 뒤에 숨겨져 있습니다.

---

## 왜 s3lync인가요?

대부분의 S3 라이브러리는 **객체 단위 조작**에 초점이 맞춰져 있습니다.
s3lync는 **개발자 경험(DX)**에 집중합니다.

* 파일을 열면 → 자동으로 동기화
* 파일에 쓰면 → 자동 업로드
* 평소엔 S3를 신경 쓰지 않아도 됩니다

---

## 주요 기능

* 🚀 **Pythonic API** — S3 객체를 로컬 파일처럼 사용
* 🔄 **자동 동기화** — 변경 감지를 통한 자동 다운로드/업로드
* ✅ **Hash 검증** — MD5 기반 무결성 검사
* 💾 **스마트 캐싱** — 지능형 무효화를 포함한 로컬 캐시
* 🔒 **강제 동기화 모드** — 로컬과 원격을 동일하게 만들기
* ⚡ **병렬 전송** — 디렉토리 동기화 시 최대 8개 파일 동시 전송
* 🔁 **자동 재시도** — 일시적 오류에 대한 지수 백오프 재시도
* 📝 **구조화된 로깅** — 디버깅을 위한 계층적 로거

---

## 설치

```bash
pip install s3lync
```

### 비동기 지원 (선택 사항)

비동기 I/O 기능을 사용하려면 `aioboto3`를 추가로 설치하세요:

```bash
pip install s3lync[async]
# 또는
pip install aioboto3
```

---

## 빠른 시작

### 기본 사용법 (동기)

```python
from s3lync import S3Object

# S3 객체 참조 생성
obj = S3Object("s3://my-bucket/path/to/file.txt")

# S3에서 다운로드
obj.download()

# S3에 업로드
obj.upload()
```

### 비동기 사용법

```python
from s3lync import AsyncS3Object
import asyncio

async def main():
    # S3 객체 참조 생성
    obj = AsyncS3Object("s3://my-bucket/path/to/file.txt")
    
    # S3에서 비동기 다운로드
    await obj.download()
    
    # S3에 비동기 업로드
    await obj.upload()

asyncio.run(main())
```

### boto3 Client 사용 (권장)

**동기 방식:**
```python
from s3lync import S3Object
import boto3

# boto3 session과 client 생성
session = boto3.Session(profile_name="dev")
s3_client = session.client("s3")

# S3Object 생성 (client 주입)
obj = S3Object(
    "s3://bucket/key",
    local_path="./local",
    boto3_client=s3_client,
)

obj.upload()
```

**비동기 방식:**
```python
from s3lync import AsyncS3Object
import aioboto3
import asyncio

async def main():
    # aioboto3 session 생성
    session = aioboto3.Session()
    
    # AsyncS3Object 생성 (session 주입)
    obj = AsyncS3Object(
        "s3://bucket/key",
        local_path="./local",
        aioboto3_session=session,
    )
    
    await obj.upload()

asyncio.run(main())
```

---

## S3 URI 포맷

s3lync는 다양한 URI 스타일을 지원합니다:

```text
s3://bucket/key
s3://endpoint@bucket/key
s3://secret_key:access_key@endpoint/bucket/key
s3://secret_key:access_key@https://endpoint/bucket/key
```

예시:

```python
# 기본 URI (환경변수에서 자격증명 사용)
S3Object("s3://my-bucket/data.json")

# 커스텀 S3 호환 엔드포인트
S3Object("s3://minio.example.com@my-bucket/data.json")

# 자격증명과 HTTPS 엔드포인트 포함
S3Object("s3://mysecret:mykey@https://minio.example.com/my-bucket/data.json")
```

---

## 동작 방식

### Smart Synchronization

* 로컬 파일 hash ↔ S3 ETag 비교
* Multipart upload는 자동으로 hash 검사 스킵
* `mirror=True`는 로컬/원격을 동일하게 만듦 (추가 파일도 삭제)

### Local Cache

* 기본값: `~/.cache/s3lync`
* `XDG_CACHE_HOME`으로 설정 가능
* 또는 `local_path`로 직접 지정

---

## 자주 사용하는 작업

### S3 객체를 파일처럼 사용하기

**방법 1: 컨텍스트 매니저 (자동 동기화, 권장!)**

동기:
```python
# 읽기 시 자동 다운로드, 쓰기 시 자동 업로드
obj = S3Object("s3://bucket/token.json")
with obj.open("w") as f:
    json.dump({"access_token": "abc123"}, f)

with obj.open("r") as f:
    token = json.load(f)
```

비동기:
```python
import asyncio
from s3lync import AsyncS3Object

async def main():
    obj = AsyncS3Object("s3://bucket/token.json")
    
    # 쓰기 시 자동 업로드
    async with obj.open("w") as f:
        f.write('{"access_token": "abc123"}')
    
    # 읽기 시 자동 다운로드
    async with obj.open("r") as f:
        data = f.read()

asyncio.run(main())
```

**방법 2: 표준 Python `open()` (pathlib 호환)**
```python
# S3Object는 __fspath__() 프로토콜 구현
obj.download()  # 수동 동기화
with open(obj, "r") as f:  # 경로처럼 동작!
    data = json.load(f)
obj.upload()  # 수동 동기화
```

**방법 3: local_path 직접 접근**
```python
# 파일 경로 직접 조작
obj.download()
with open(obj.local_path, "r") as f:
    data = f.read()
obj.upload()
```

### 기본 다운로드 / 업로드

```python
# 기본 다운로드
obj.download()

# 강제 동기화: 로컬과 원격을 동일하게 만듦 (필요시 추가 원격 파일 삭제)
obj.upload(mirror=True)
```

### 디렉토리 동기화

s3lync는 스마트한 변경 감지를 통한 재귀적 디렉토리 다운로드/업로드를 지원합니다.

**동기 방식:**
```python
# 전체 디렉토리 다운로드
obj = S3Object("s3://bucket/path/to/dir")
obj.download()

# 전체 디렉토리 업로드 (기본적으로 숨김파일 제외)
obj.upload()

# Mirror 모드: 원본에 없는 파일 삭제
obj.download(mirror=True)  # S3에 없는 로컬 파일 삭제
obj.upload(mirror=True)    # 로컬에 없는 원격 파일 삭제
```

**비동기 방식 (병렬 처리로 더 빠름):**
```python
import asyncio
from s3lync import AsyncS3Object

async def main():
    obj = AsyncS3Object("s3://bucket/path/to/dir")
    
    # 비동기로 전체 디렉토리 다운로드
    await obj.download()
    
    # 비동기로 전체 디렉토리 업로드
    await obj.upload()
    
    # Mirror 모드
    await obj.download(mirror=True)
    await obj.upload(mirror=True)

asyncio.run(main())
```

**여러 디렉토리 병렬 동기화:**
```python
import asyncio
from s3lync import AsyncS3Object

async def sync_multiple():
    # 여러 디렉토리를 동시에 다운로드
    tasks = [
        AsyncS3Object("s3://bucket/dir1").download(),
        AsyncS3Object("s3://bucket/dir2").download(),
        AsyncS3Object("s3://bucket/dir3").download(),
    ]
    await asyncio.gather(*tasks)

asyncio.run(sync_multiple())
```

### Exclude Patterns

동기화 작업 중 정규식 패턴으로 포함/제외할 파일을 제어합니다.

#### 기본 제외 항목

- `/.*/` — 숨김파일과 디렉토리 (`.git`, `.venv` 등)
- `__pycache__` — Python 캐시 디렉토리
- `.egg-info` — Python 패키지 메타데이터

#### Exclude 작동 방식

**객체 생성** — 모든 기본값을 대체:

```python
obj = S3Object(
    "s3://bucket/path",
    excludes=[r".*\.tmp$", r"\.git/.*"]
)
obj.upload()  # 오직: [.*\.tmp$, \.git/.*] 만 사용
```

**메서드 호출** — 기본값에 추가:

```python
obj = S3Object("s3://bucket/path")
obj.upload(excludes=[r".*\.tmp$"])
# 사용: [/.*/,  __pycache__, .egg-info, .*\.tmp$]

obj.download(excludes=[r"node_modules/.*"])
# 사용: [/.*/,  __pycache__, .egg-info, node_modules/.*]
```

---

## AWS 자격증명

s3lync는 boto3의 표준 자격증명 제공자 체인을 사용합니다.

### 프로필 선택

boto3에서는 **3가지** 방식으로 AWS 프로필을 선택할 수 있습니다. 
실무에서는 명시적 선택 또는 환경변수가 가장 많이 사용됩니다.

#### ✅ 1. Session에서 프로필 명시 (권장)

```python
import boto3

session = boto3.Session(profile_name="dev")
s3_client = session.client("s3")

obj = S3Object("s3://bucket/key", boto3_client=s3_client)
```

**장점:**
- 코드에서 명확
- 다중 계정 시나리오에 적합
- 가장 유연함

#### ✅ 2. 환경변수

```bash
export AWS_PROFILE=dev
```

```python
import boto3

session = boto3.Session()  # 자동으로 AWS_PROFILE 사용
s3_client = session.client("s3")
```

**장점:**
- 환경별 설정 분리
- CI/CD 친화적
- 코드 변경 없음

#### ⚠️ 3. 기본 프로필 (암시적)

```python
import boto3

session = boto3.Session()  # [default] 프로필 사용
s3_client = session.client("s3")
```

### 자격증명 검색 순서

1. 환경변수: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. AWS 자격증명 파일: `~/.aws/credentials` (`AWS_PROFILE` 준수)
3. AWS 설정 파일: `~/.aws/config`
4. IAM 역할 (EC2, EKS, ECS 환경)

### 빠른 예시

```bash
# 환경변수 사용
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=ap-northeast-2

# 또는 프로필 사용
export AWS_PROFILE=my-profile
```

---

## 추가 기능

### 로깅 설정

디버깅을 위한 상세 로깅 활성화:

```python
from s3lync import configure_logging
import logging

# 기본 로깅 활성화 (INFO 레벨)
configure_logging()

# 상세 디버깅
configure_logging(level=logging.DEBUG)

# 파일에 로그 저장
configure_logging(level=logging.DEBUG, log_file="s3lync.log")
```

로거 계층:
- `s3lync` - 루트 로거
- `s3lync.core` - 핵심 동기화 작업
- `s3lync.async_core` - 비동기 작업
- `s3lync.client` - boto3 클라이언트 작업

### 자동 재시도

일시적 AWS 오류는 지수 백오프로 자동 재시도됩니다:

```python
from s3lync.retry import RetryConfig, retry

# 기본 설정: 3회 시도, 1초 지연, 2배 백오프
# 커스텀 설정으로 자신만의 함수 래핑 가능

@retry(RetryConfig(max_attempts=5, base_delay=2.0))
def my_s3_operation():
    ...
```

재시도 가능한 오류:
- `ThrottlingException` - API 속도 제한
- `ServiceUnavailable` - 일시적 서비스 장애
- `SlowDown` - S3 요청 속도 제한
- `RequestTimeout` - 네트워크 타임아웃

### Custom Callbacks

진행도 추적을 포함한 callback 체인:

```python
from s3lync import S3Object, chain_callbacks

def my_callback(bytes_transferred: int):
    print(f"전송됨: {bytes_transferred} bytes")

obj = S3Object("s3://bucket/large-file.bin", local_path="/tmp/file.bin")

# 다운로드 중 callback 사용
metadata = obj._client.download_file(
    bucket="bucket",
    key="large-file.bin",
    local_path="/tmp/file.bin",
    callback=my_callback,
    show_progress=True
)
```

### Progress 표시 제어

Progress bar 표시 모드를 제어합니다:

```python
from s3lync import S3Object
import boto3

# 방법 1: 객체 생성시 기본 progress 모드 지정
obj = S3Object(
    "s3://bucket/key",
    local_path="./local",
    progress_mode="compact"  # "progress" (기본값), "compact", "disabled"
)
obj.upload()

# 방법 2: 특정 작업에서 오버라이드
obj.download(progress_mode="disabled")

# 방법 3: boto3 client 사용
session = boto3.Session(profile_name="dev")
s3_client = session.client("s3")
obj = S3Object(
    "s3://bucket/key",
    boto3_client=s3_client,
    progress_mode="compact"
)
```

**Progress 모드 옵션:**
- `"progress"` (기본값): 실시간 업데이트 tqdm 진행률 표시
- `"compact"`: 완료 시 요약 정보만 출력 (비대화형, CI/CD 환경에 적합)
- `"disabled"`: 진행률 표시 안 함

**참고:** 비-TTY 환경 (예: PyCharm 콘솔)에서는 자동으로 호환성을 위해 진행률 바 표시가 조정됩니다.

---

## 라이선스

MIT License — 자세한 내용은 [LICENSE](./LICENSE)

---

## 제작자

**김준석 (JunSeok Kim)**
S3를 로컬처럼 쓰기 위해 ❤️로 만들었습니다

