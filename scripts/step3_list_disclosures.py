import os
import requests

def filter_annual(items):
    return [
        item for item in items
        if "사업보고서" in item["report_nm"] and "정정" not in item["report_nm"]
    ]

API_KEY = os.environ.get("DART_API_KEY", "")
if not API_KEY:
    raise SystemExit("환경변수 DART_API_KEY가 설정되지 않았습니다. README 참고.")

params = {
    "crtfc_key": API_KEY,
    "corp_code": "00164779",
    "bgn_de": "20210101",
    "end_de": "20260101",
    "pblntf_ty": "A",
    "pblntf_detail_ty": "A001",
    "page_count": 100,
}

response = requests.get("https://opendart.fss.or.kr/api/list.json", params=params)
data = response.json()

status = data.get("status")
if status != "000":
    print(f"에러: {status} - {data.get('message')}")
else:
    total = int(data.get("total_count", 0))
    items = data.get("list", [])
    print(f"전체 {total}건 (이번 페이지 {len(items)}건)")
    if total > 100:
        print("※ 100건 초과 — 페이지 추가 조회 필요")

    filtered = filter_annual(items)
    print(f"필터 후 사업보고서(정정 제외): {len(filtered)}건\n")
    print(f"{'접수번호':<15} {'접수일자':<12} 보고서명")
    print("-" * 70)
    for item in filtered:
        print(f"{item['rcept_no']:<15} {item['rcept_dt']:<12} {item['report_nm']}")
