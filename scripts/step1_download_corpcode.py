import requests
import zipfile
import io
import os

API_KEY = os.environ.get("DART_API_KEY", "")
if not API_KEY:
    raise SystemExit("환경변수 DART_API_KEY가 설정되지 않았습니다. README 참고.")

URL = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={API_KEY}"

print("회사 고유번호 목록 다운로드 중...")
response = requests.get(URL)

# 에러 응답 확인 (zip이 아닌 XML이 오면 오류)
content_type = response.headers.get("Content-Type", "")
if "xml" in content_type and not response.content.startswith(b"PK"):
    print("에러 응답:")
    print(response.text)
else:
    zip_data = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_data) as z:
        z.extractall(".")
    print("압축 해제 완료")

    xml_path = "CORPCODE.xml"
    size = os.path.getsize(xml_path)
    print(f"파일 크기: {size:,} bytes ({size / 1024 / 1024:.1f} MB)")

    print("\n--- 첫 5줄 ---")
    with open(xml_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            print(line, end="")
            if i >= 4:
                break
