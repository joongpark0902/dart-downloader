import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dart_engine import (
    load_corp_list, search_company,
    list_disclosures, download_document,
)

API_KEY = os.environ.get("DART_API_KEY", "")
if not API_KEY:
    raise SystemExit("환경변수 DART_API_KEY가 설정되지 않았습니다. README 참고.")

def log(msg):
    print(f"  {msg}")

print("=" * 60)
print("1. 회사 목록 로드")
corps = load_corp_list(API_KEY, log_fn=log)

print("\n2. 'SK하이닉스' 검색")
results = search_company(corps, "SK하이닉스")
for r in results:
    print(f"  {r['corp_code']}  {r['corp_name']}")

corp_code = results[0]["corp_code"]
corp_name = results[0]["corp_name"]

print("\n3. 사업보고서 목록 조회 (2020~2025)")
disclosures = list_disclosures(
    API_KEY, corp_code,
    bgn_de="20200101", end_de="20260101",
    report_types=["사업보고서"],
    log_fn=log,
)
print(f"\n  {'접수번호':<17} {'접수일자':<12} 보고서명")
print("  " + "-" * 55)
for d in disclosures:
    print(f"  {d['rcept_no']:<17} {d['rcept_dt']:<12} {d['report_nm']}")

print("\n4. 문서 다운로드 (최신 2건)")
summary = []
for d in disclosures[:2]:
    # 보고서명에서 연도 추출: "사업보고서 (2024.12)" → "2024"
    year = d["report_nm"].split("(")[-1][:4] if "(" in d["report_nm"] else "unknown"
    save_dir = os.path.join("downloads", corp_name, f"사업보고서_{year}")
    result = download_document(API_KEY, d["rcept_no"], save_dir, log_fn=log)
    summary.append((d["report_nm"], d["rcept_no"], result["status"], result["files"]))

print("\n5. 결과 요약")
print(f"  {'보고서':<25} {'접수번호':<17} 결과")
print("  " + "-" * 60)
for report_nm, rcept_no, status, files in summary:
    print(f"  {report_nm:<25} {rcept_no:<17} {status}")
    for f in files:
        print(f"    └ {f}")

print("\n전체 흐름 완료")
