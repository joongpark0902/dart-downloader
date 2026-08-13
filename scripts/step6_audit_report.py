"""
감사보고서 단독공시(pblntf_ty=F) 경로 검증.

비상장 외부감사대상 법인은 사업보고서를 제출하지 않으므로 정기공시(A)만
조회하면 status=013(데이터 없음)이 돌아온다. 재무제표·주석은 F 유형의
'감사보고서 / 연결감사보고서'에 들어 있다.

  $env:DART_API_KEY = "발급받은_인증키"
  python scripts/step6_audit_report.py [회사명]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dart_engine import list_disclosures, load_corp_list, search_company  # noqa: E402

API_KEY = os.environ.get("DART_API_KEY", "")
if not API_KEY:
    raise SystemExit("환경변수 DART_API_KEY가 설정되지 않았습니다. README 참고.")

KEYWORD = sys.argv[1] if len(sys.argv) > 1 else "쿠팡"
BGN_DE, END_DE = "20210101", "20261231"

corps = load_corp_list(API_KEY, cache_path="CORPCODE.xml", log_fn=print)
hits = search_company(corps, KEYWORD)
if not hits:
    raise SystemExit(f"'{KEYWORD}' 검색 결과 없음")

corp = hits[0]
listed = "상장" if corp.get("stock_code") else "비상장"
print(f"\n대상: {corp['corp_name']} ({corp['corp_code']}, {listed})\n")

for label, types in [
    ("정기공시만 (기존 동작)", ["사업보고서", "반기보고서", "분기보고서"]),
    ("감사보고서 포함 (신규)", ["사업보고서", "반기보고서", "분기보고서", "감사보고서"]),
    ("감사보고서만", ["감사보고서"]),
]:
    print(f"── {label} " + "─" * (40 - len(label)))
    try:
        items = list_disclosures(API_KEY, corp["corp_code"], BGN_DE, END_DE,
                                 report_types=types, log_fn=print)
    except Exception as e:
        print(f"  예외 발생: {e}")
        print()
        continue
    for it in items:
        print(f"  {it['rcept_no']}  {it['rcept_dt']}  {it['report_nm']}")
    print()
