"""
s3lync 사용 예제

이 파일은 s3lync의 기본적인 사용 방법을 보여줍니다.
"""

from s3lync import S3Object

# 예제 1: 기본 사용법
print("=" * 60)
print("예제 1: 기본 S3Object 생성")
print("=" * 60)

# S3 URI로 객체 생성
obj = S3Object('s3://my-bucket/path/to/file.txt')
print(f"S3 URI: {obj.s3_uri}")
print(f"Bucket: {obj.bucket}")
print(f"Key: {obj.key}")
print(f"Local Path: {obj.local_path}")

# 예제 2: 커스텀 로컬 경로
print("\n" + "=" * 60)
print("예제 2: 커스텀 로컬 경로")
print("=" * 60)

obj_custom = S3Object(
    's3://my-bucket/data/config.json',
    local_path='/Users/john/tech/data/config.json'
)
print(f"S3 URI: {obj_custom.s3_uri}")
print(f"Local Path: {obj_custom.local_path}")

# 예제 3: Context Manager를 사용한 자동 동기화
print("\n" + "=" * 60)
print("예제 3: Context Manager (자동 업로드/다운로드)")
print("=" * 60)

"""
# 읽기 모드 - S3에서 자동 다운로드
with obj.open('r') as f:
    content = f.read()
    print(f"파일 내용: {content}")

# 쓰기 모드 - S3로 자동 업로드
with obj.open('w') as f:
    f.write('Hello S3!')
    # context 종료 시 자동으로 S3에 업로드됨
"""

# 예제 4: 수동 다운로드/업로드
print("\n" + "=" * 60)
print("예제 4: 수동 다운로드/업로드")
print("=" * 60)

"""
# 다운로드 (MD5 검증 포함, 기본값)
obj.download(check_hash=True)

# MD5 검증 없이 다운로드
obj.download(check_hash=False)

# 강제 동기화 (hash 무시)
obj.download(force_sync=True)

# 로컬 파일 수정
with open(obj.local_path, 'w') as f:
    f.write('새로운 내용')

# 업로드
obj.upload()

# 강제 업로드
obj.upload(force_sync=True)
"""

# 예제 5: 예외 처리
print("\n" + "=" * 60)
print("예제 5: 예외 처리")
print("=" * 60)

"""
from s3lync import S3lyncError, HashMismatchError, SyncError

try:
    obj.download()
except HashMismatchError:
    print("파일 무결성 검증 실패!")
except SyncError:
    print("동기화 중 오류 발생!")
except S3lyncError:
    print("알 수 없는 오류!")
"""

# 예제 6: 로컬 파일 경로 사용
print("\n" + "=" * 60)
print("예제 6: 로컬 파일 경로 사용 (glob)")
print("=" * 60)

"""
import glob

# 다운로드
obj.download()

# 로컬 경로로 파일 검색
for file in glob.glob(obj.local_path + '/*.json'):
    print(f"발견: {file}")
"""

print("\n" + "=" * 60)
print("✓ 예제 완료!")
print("=" * 60)

