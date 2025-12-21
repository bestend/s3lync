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

**s3lync**는 Amazon S3 객체를  
**마치 로컬 파일처럼 다룰 수 있게 해주는 Python 패키지**입니다.

다음 작업을 자동으로 처리합니다:

- 📥 읽을 때 자동 다운로드
- 📤 쓸 때 자동 업로드
- 🔍 해시 기반 변경 감지
- 💾 로컬 캐싱
- 🔁 필요 시 강제 동기화

모든 기능은 **간결하고 Pythonic한 API** 뒤에 숨겨져 있습니다.

---

## 왜 s3lync인가요?

대부분의 S3 라이브러리는 **객체 단위 조작**에 초점이 맞춰져 있습니다.  
s3lync는 **개발자 경험(DX)**에 집중합니다.

- 파일을 열면 → 자동으로 동기화
- 파일에 쓰면 → 자동 업로드
- 평소엔 S3를 신경 쓰지 않아도 됩니다

---

## 주요 기능

- 🚀 **Pythonic API** — S3 객체를 로컬 파일처럼 사용
- 🔄 **Automatic Sync** — 변경 감지 기반 다운로드/업로드
- ✅ **Hash Verification** — MD5 해시 체크
- 💾 **Smart Caching** — 로컬 캐시 + 자동 무효화
- 🎯 **Context Manager 지원** — `with open(...)`
- 🔒 **Force Sync 모드** — 로컬과 원격을 완전히 동일하게 유지

---

## 설치

```bash
pip install s3lync
````

---

## 빠른 시작

### 기본 사용법

```python
from s3lync import S3Object

# S3 객체 참조 생성
obj = S3Object('s3://my-bucket/path/to/file.txt')

# S3에서 로컬로 다운로드
obj.download()

# 로컬에서 S3로 업로드
obj.upload()
```

### Context Manager

```python
# 읽기 모드: S3에서 자동으로 다운로드
with obj.open('r') as f:
    content = f.read()

# 쓰기 모드: 자동으로 S3에 업로드
with obj.open('w') as f:
    f.write('새로운 내용')
```

---

## S3 URI 형식

s3lync는 다양한 S3 URI 형식을 지원합니다.

```text
s3://bucket/key
s3://endpoint@bucket/key
s3://secret:access@endpoint/bucket/key
s3://secret:access@https://endpoint/bucket/key
```

예시:

```python
# 기본 URI (환경변수에서 자격증명 사용)
S3Object("s3://my-bucket/data.json")

# 커스텀 S3-compatible endpoint
S3Object("s3://minio.example.com@my-bucket/data.json")

# 자격증명과 HTTPS endpoint 포함
S3Object("s3://key:secret@https://minio.example.com/my-bucket/data.json")
```

---

## 자주 사용하는 작업

### 다운로드 / 업로드

```python
# 기본 다운로드
obj.download()

# 강제 동기화: 원격을 로컬과 동일하게 만들기 (필요시 파일 삭제)
obj.upload(mirror=True)
```

### 제외 패턴 설정

기본적으로 숨김 파일(`.git`, `.pytest_cache` 등)과
Python 캐시(`__pycache__`, `.egg-info`)는 업로드에서 제외됩니다.

```python
# .tmp와 node_modules 파일 제외
obj.upload(excludes=[r".*\.tmp$", r"node_modules"])

# 추가 제외 패턴 추가
obj.add_exclude(r".*\.log$")
```

숨김 파일 제외를 끄려면:

```bash
export S3LYNC_EXCLUDE_HIDDEN=0
```

---

## 동작 방식

### 스마트 동기화

* 로컬 파일 해시 ↔ S3 ETag 비교
* Multipart 업로드의 경우 자동으로 해시 검증 생략
* `mirror=True` 사용 시 원격/로컬을 동일하게 맞춤(남는 파일 삭제 포함)

### 로컬 캐시

* 기본 경로: `~/.cache/s3lync`
* `XDG_CACHE_HOME` 환경 변수로 변경 가능
* 또는 `local_path` 직접 지정 가능

---

## 설정(Configuration)

설정 값은 다음 우선순위로 적용됩니다:

1. 환경 변수 (최우선)
2. 코드 내 설정
3. 라이브러리 기본값

### 주요 설정 항목

| 항목       | 환경 변수                   | 기본값        |
| -------- | ----------------------- | ---------- |
| 로그 레벨    | `S3LYNC_LOG_LEVEL`      | `INFO`     |
| 진행 표시    | `S3LYNC_PROGRESS_MODE`  | `progress` |
| 숨김 파일 제외 | `S3LYNC_EXCLUDE_HIDDEN` | `True`     |
| AWS 리전   | `AWS_REGION`            | 자동         |

예시:

```bash
export S3LYNC_LOG_LEVEL=DEBUG
export S3LYNC_PROGRESS_MODE=disabled
```

### 코드에서 직접 설정하기(from s3lync import Config)

```python
from s3lync import Config

# 런타임에 설정 (환경 변수가 있으면 그 값이 우선)
Config.set_debug_enabled(True)            # 디버그 모드 활성화
Config.set_log_level("WARNING")          # 로그 레벨 설정
Config.set_progress_mode("compact")      # 진행 표시 모드 변경
Config.set_exclude_hidden(False)          # 숨김 파일 포함
Config.set_region("ap-northeast-2")      # AWS 리전 설정

# 설정값 읽기
region = Config.get_region()
debug = Config.is_debug_enabled()
mode = Config.get_progress_mode()
exclude_hidden = Config.should_exclude_hidden()

# 런타임 설정 초기화 (테스트에 유용)
Config.reset_runtime_overrides()
```

---

## AWS 자격증명

s3lync는 boto3의 표준 자격증명 체인을 사용합니다. 별도의 키 전달 없이도 아래 순서로 자격증명을 자동으로 찾습니다.

검색 순서(간단 버전):

1. 환경 변수
   - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (옵션: `AWS_SESSION_TOKEN`)
2. AWS 자격증명 파일
   - `~/.aws/credentials` (프로필은 `AWS_PROFILE`로 선택)

참고:
- `AWS_PROFILE`이 설정되어 있으면 해당 프로필을 사용합니다.
- AWS 환경(EC2/ECS)에서는 위 항목이 없을 경우 인스턴스/작업 역할의 자격증명을 자동으로 사용합니다.

사용 예:

```bash
# 환경 변수를 통한 자격증명 설정
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=ap-northeast-2

# 또는 ~/.aws/credentials의 프로필 선택
export AWS_PROFILE=my-profile
```

---

## 예외 처리

```python
from s3lync import S3Object, HashMismatchError, SyncError

try:
    # S3에서 파일 다운로드
    S3Object("s3://bucket/file.txt").download()
except HashMismatchError:
    # 파일 무결성 검증 실패
    print("파일 무결성 검증 실패")
except SyncError:
    # 동기화 오류 발생
    print("동기화 오류 발생")
```

---

## 개발

### 테스트 실행

```bash
pytest tests/
```

---

## 라이선스

MIT License — 자세한 내용은 [LICENSE](./LICENSE)

---

## 제작자

**김준석 (JunSeok Kim)**
S3를 로컬처럼 쓰기 위해 ❤️로 만들었습니다
