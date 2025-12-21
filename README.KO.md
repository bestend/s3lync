# s3lync

**S3와 로컬 파일시스템의 Python Bridge**

> S3 객체를 로컬 파일처럼 사용하세요.  
> S3-로컬 동기화, 자동으로 처리됩니다.

s3lync는 Amazon S3 객체를 로컬 파일처럼 다룰 수 있게 해주는 Python 패키지입니다. Automatic synchronization, MD5 hash verification, 그리고 Pythonic한 깔끔한 API를 제공합니다.

## 기능

- 🚀 **Pythonic API**: S3 객체를 로컬 파일처럼 사용
- 🔄 **Automatic Sync**: 변경사항 감지로 자동 다운로드/업로드
- ✅ **Hash Verification**: MD5 체크섬 검증 (커스터마이징 가능)
- 💾 **Smart Caching**: 지능형 캐시 무효화를 통한 자동 로컬 캐싱
- 🎯 **Context Manager**: Python의 `with` 문과 함께 사용
- 🔒 **Force Sync**: Smart Caching 우회 옵션

## 설치

```bash
pip install s3lync
```

### 개발 버전 설치

```bash
git clone https://github.com/bestend/s3lync.git
cd s3lync
pip install -e ".[dev]"
```

## 빠른 시작

### 기본 사용법

```python
from s3lync import S3Object

# S3Object 생성
obj = S3Object('s3://my-bucket/path/to/file.txt')

# S3에서 다운로드
obj.download(check_hash=True)  # MD5 verification (기본값)

# S3로 업로드
obj.upload()

# 로컬 파일 경로 획득
local_file = obj.local_path
```

### Custom Local Path

```python
obj = S3Object(
    's3://my-bucket/path/to/file.txt',
    local_path='/Users/john/tech/data/file.txt'
)
```

### Context Manager (자동 업로드)

```python
# Write mode - 종료 시 자동으로 업로드
with obj.open(mode='w') as f:
    f.write('Hello, S3!')

# Read mode - 진입 시 자동으로 다운로드
with obj.open(mode='r') as f:
    content = f.read()
    print(content)
```

### Traditional File Operations

```python
# 수동 다운로드 및 로컬 파일 처리
obj.download()

import glob
for file in glob.glob(obj.local_path + '/*.json'):
    print(file)

# 로컬 파일 수정
with open(obj.local_path, 'w') as f:
    f.write('new content')

# 수동 업로드
obj.upload()
```

### Force Sync

```python
# Force Sync - 소스와 대상을 완벽히 동일하게 만듦 (필요시 파일 삭제)
obj.download(force_sync=True)  # Local을 Remote와 동일하게 (Remote 기준)
obj.upload(force_sync=True)    # Remote를 Local과 동일하게 (Local 기준)
```

**Force Sync의 동작:**

`download(force_sync=True)`:
- Remote의 파일/폴더를 모두 Local에 다운로드
- Local에만 있는 파일/폴더는 **삭제** (Remote 기준으로 동기화)

`upload(force_sync=True)`:
- Local의 파일/폴더를 모두 Remote에 업로드
- Remote에만 있는 파일/폴더는 **삭제** (Local 기준으로 동기화)

## API 레퍼런스

### S3Object

#### Constructor

```python
S3Object(
    s3_uri: str,
    local_path: Optional[str] = None,
    region_name: Optional[str] = None
)
```

- **s3_uri**: `s3://bucket/key` 형식의 S3 URI
- **local_path**: 선택적 로컬 파일 경로. 생략하면 시스템 캐시 디렉토리 사용
- **region_name**: AWS 지역 (선택적, 기본 AWS 설정 사용)

#### Methods

##### `download(check_hash: bool = True, force_sync: bool = False) -> str`

S3 객체 (파일 또는 디렉토리)를 로컬로 다운로드합니다.

- **check_hash**: MD5로 파일 무결성 검증 (기본값: `True`)
- **force_sync**: True일 경우, Local을 Remote와 완벽히 동일하게 만듦 (기본값: `False`)
  - Remote의 파일/폴더를 모두 다운로드
  - Local에만 있는 파일/폴더는 삭제

반환: Local 경로

**Exceptions**:
- `SyncError`: 다운로드 실패 시
- `HashMismatchError`: Hash verification 실패 시

##### `upload(check_hash: bool = True, exclude_pattern: str = "", force_sync: bool = False) -> str`

로컬 객체 (파일 또는 디렉토리)를 S3로 업로드합니다.

- **check_hash**: 파일 무결성 검증 (기본값: `True`)
- **exclude_pattern**: 업로드 시 제외할 파일의 정규표현식 패턴 (기본값: "")
- **force_sync**: True일 경우, Remote를 Local과 완벽히 동일하게 만듦 (기본값: `False`)
  - Local의 파일/폴더를 모두 업로드
  - Remote에만 있는 파일/폴더는 삭제

반환: S3 URI

**Exceptions**:
- `S3ObjectError`: 로컬 파일/폴더가 없음
- `SyncError`: 업로드 실패 시

##### `open(mode: str = 'r', encoding: str = 'utf-8')`

파일 작업을 위한 Context Manager입니다.

- **mode**: File mode (`'r'`, `'w'`, `'rb'`, `'wb'` 등)
- **encoding**: Text encoding (기본값: `'utf-8'`)

Read 작업 시 자동으로 다운로드되고, Write 작업 시 자동으로 업로드됩니다.

##### `exists() -> bool`

S3 객체 존재 여부를 확인합니다.

##### `delete() -> bool`

S3 객체를 삭제합니다 (파일 또는 디렉토리).

##### `local_path` (Property)

로컬 파일/디렉토리 경로를 반환합니다.

## 고급 기능

### Exclude Pattern (Upload Only)

업로드 시 특정 패턴의 파일을 제외합니다:

```python
# .tmp 파일을 제외하고 업로드
obj.upload(exclude_pattern=r'.*\.tmp$')

# 여러 패턴 제외
obj.upload(exclude_pattern=r'(.*\.tmp$|.*\.bak$)')
```

### Configuration

Config 클래스를 사용하여 s3lync 동작을 설정합니다:

```python
from s3lync import Config

# AWS 지역 획득
region = Config.get_aws_region()

# Debug mode 확인
is_debug = Config.is_debug_enabled()

# Log level 확인
log_level = Config.get_log_level()
```


환경 변수:
- `S3LYNC_DEBUG`: Debug mode 활성화 (1, true, yes)
- `S3LYNC_LOG_LEVEL`: Log level 설정 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `AWS_REGION` 또는 `AWS_DEFAULT_REGION`: AWS 지역 설정

## 작동 방식

### Smart Synchronization

s3lync는 MD5 hash 비교를 사용하여 동기화 필요 여부를 결정합니다:

1. **Download**: 로컬 파일 hash와 원격 S3 ETag 비교
2. **Upload**: 로컬 파일 hash와 원격 S3 ETag 비교
3. **Force Sync**: Hash 비교를 무시하고 항상 작업 수행

### Local Caching

- **Default Cache**: 모든 플랫폼에서 `~/.cache/s3lync` 사용 (Linux, macOS, Windows)
- **Environment Variable**: `XDG_CACHE_HOME`으로 커스터마이징 가능
- **Custom Path**: S3Object 생성 시 로컬 경로 지정

### Hash Verification

기본적으로 다운로드 후 MD5로 파일 무결성을 검증합니다:

```python
obj.download(check_hash=True)   # 기본 동작
obj.download(check_hash=False)  # Verification 스킵
```

**참고**: S3 multipart upload를 통해 업로드된 객체의 ETag는 유효한 MD5 hash가 아닙니다. 이 경우 hash verification은 자동으로 스킵됩니다.

## 예외 처리

```python
from s3lync import S3Object, S3lyncError, HashMismatchError, SyncError

obj = S3Object('s3://bucket/file.txt')

try:
    obj.download()
except HashMismatchError:
    print("파일 손상 감지!")
except SyncError:
    print("다운로드 중 네트워크 오류!")
except S3lyncError:
    print("알 수 없는 오류!")
```

## 설정

### AWS 자격증명

s3lync는 boto3의 표준 자격증명 체인을 사용합니다:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS credentials file (`~/.aws/credentials`)
3. IAM role (EC2 instances)

### Cache Directory

기본 캐시 위치는 `~/.cache/s3lync`입니다. 환경 변수로 커스터마이징합니다:

```bash
# Custom cache directory 설정 (모든 플랫폼)
export XDG_CACHE_HOME=/path/to/custom/cache
# 캐시 위치: /path/to/custom/cache/s3lync

# 또는 HOME 디렉토리 변경
export HOME=/custom/home
# 캐시 위치: /custom/home/.cache/s3lync
```

## 예제

### 예제 1: JSON 파일 다운로드 및 처리

```python
from s3lync import S3Object
import json

obj = S3Object('s3://my-bucket/data/config.json')
obj.download()

with open(obj.local_path) as f:
    config = json.load(f)
    print(config)
```

### 예제 2: 보고서 생성 및 업로드

```python
from s3lync import S3Object

obj = S3Object(
    's3://my-bucket/reports/report.txt',
    local_path='./reports/report.txt'
)

# 로컬에서 보고서 생성
with open(obj.local_path, 'w') as f:
    f.write('월간 보고서\n')
    f.write('...')

# S3로 업로드
obj.upload()
```

### 예제 3: Context Manager를 이용한 자동 동기화

```python
from s3lync import S3Object

obj = S3Object('s3://my-bucket/logs/app.log')

# 읽고 처리
with obj.open('r') as f:
    for line in f:
        print(line)

# 로그 추가
with obj.open('a') as f:
    f.write('\n[NEW] 추가된 로그 항목')
```

## 개발

### 테스트 실행

```bash
pytest tests/
```

### 코드 품질

```bash
# Code formatting
black src/ tests/

# Linting
ruff check src/ tests/

# Type checking
mypy src/
```

## 기여

기여를 환영합니다! [CONTRIBUTING.md](./CONTRIBUTING.md)를 참고하세요.

## 라이선스

MIT License - [LICENSE](./LICENSE) 파일을 참고하세요.

## 저자

**JunSeok Kim** - 🥰로 만들었습니다.

## 감사의 말

- Cloud storage를 위한 현대적 Python 패키지에서 영감
- [boto3](https://boto3.amazonaws.com/)를 기반으로 구축

