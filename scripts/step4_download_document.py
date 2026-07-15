import requests
import zipfile
import io
import os

API_KEY = os.environ.get("DART_API_KEY", "")
if not API_KEY:
    raise SystemExit("환경변수 DART_API_KEY가 설정되지 않았습니다. README 참고.")

REPORTS = [
    {"rcept_no": "20250319000665", "corp_name": "SK하이닉스", "report_type": "사업보고서", "fiscal_year": "2024"},
    {"rcept_no": "20240319000684", "corp_name": "SK하이닉스", "report_type": "사업보고서", "fiscal_year": "2023"},
    {"rcept_no": "20230321001209", "corp_name": "SK하이닉스", "report_type": "사업보고서", "fiscal_year": "2022"},
    {"rcept_no": "20220322000590", "corp_name": "SK하이닉스", "report_type": "사업보고서", "fiscal_year": "2021"},
    {"rcept_no": "20210322000782", "corp_name": "SK하이닉스", "report_type": "사업보고서", "fiscal_year": "2020"},
]

def download_report(report):
    folder = os.path.join(
        "downloads",
        report["corp_name"],
        f"{report['report_type']}_{report['fiscal_year']}",
    )
    done_marker = os.path.join(folder, ".done")

    if os.path.exists(done_marker):
        files = [f for f in os.listdir(folder) if f != ".done"]
        return "건너뜀", files

    os.makedirs(folder, exist_ok=True)

    url = "https://opendart.fss.or.kr/api/document.xml"
    response = requests.get(url, params={"crtfc_key": API_KEY, "rcept_no": report["rcept_no"]})

    # 에러 응답 확인 (zip은 PK 시그니처로 시작)
    if not response.content.startswith(b"PK"):
        return f"실패({response.text[:80]})", []

    zip_path = os.path.join(folder, f"{report['rcept_no']}.zip")
    with open(zip_path, "wb") as f:
        f.write(response.content)

    with zipfile.ZipFile(zip_path) as z:
        z.extractall(folder)
        extracted = z.namelist()

    open(done_marker, "w").close()
    return "성공", extracted

print("=" * 70)
results = []
for r in REPORTS:
    label = f"{r['corp_name']} 사업보고서 {r['fiscal_year']}"
    print(f"[{label}] 처리 중...")
    status, files = download_report(r)
    print(f"  → {status}")
    if files:
        for f in files:
            print(f"     {f}")
    results.append((label, r["rcept_no"], status))

print()
print("=" * 70)
print(f"{'보고서':<30} {'접수번호':<17} 결과")
print("-" * 70)
for label, rcept_no, status in results:
    print(f"{label:<30} {rcept_no:<17} {status}")
