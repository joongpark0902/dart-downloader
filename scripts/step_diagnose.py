import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dart_engine import load_corp_list, search_company

API_KEY = os.environ.get("DART_API_KEY", "")
if not API_KEY:
    raise SystemExit("환경변수 DART_API_KEY가 설정되지 않았습니다. README 참고.")

KEYWORD = "한강버스"

# ── 1. search_company ─────────────────────────────────────────────────────────
print("=" * 60)
print(f"1. search_company('{KEYWORD}')")
corps = load_corp_list(API_KEY, log_fn=lambda m: None)
results = search_company(corps, KEYWORD)
print(f"   결과: {len(results)}건")
for r in results:
    print(f"   {r['corp_code']}  {r['corp_name']}")

# ── 2. corp_code 있으면 기업개황 확인 ─────────────────────────────────────────
if results:
    for corp in results:
        code = corp["corp_code"]
        name = corp["corp_name"]
        print()
        print(f"2. 기업개황 (company.json) — {name} [{code}]")
        resp = requests.get("https://opendart.fss.or.kr/api/company.json", params={
            "crtfc_key": API_KEY, "corp_code": code,
        })
        info = resp.json()
        cls_map = {"Y": "유가증권(Y)", "K": "코스닥(K)", "N": "코넥스(N)", "E": "기타(E)"}
        print(f"   법인구분: {cls_map.get(info.get('corp_cls', '?'), info.get('corp_cls', 'N/A'))}")
        print(f"   업종:     {info.get('induty_code', 'N/A')} / {info.get('corp_cls', 'N/A')}")
        print(f"   설립일:   {info.get('est_dt', 'N/A')}")
        print(f"   결산월:   {info.get('acc_mt', 'N/A')}월")

        print()
        print(f"3. 공시목록 전체 (list.json) — {name} [{code}]")
        resp2 = requests.get("https://opendart.fss.or.kr/api/list.json", params={
            "crtfc_key": API_KEY, "corp_code": code,
            "bgn_de": "20000101", "end_de": "20261231",
            "page_count": 100,
        })
        data2 = resp2.json()
        items = data2.get("list", [])
        total = data2.get("total_count", 0)
        print(f"   전체 공시 건수: {total}건 (최대 100건 표시)")
        if items:
            print(f"   {'접수일자':<12} {'보고서명'}")
            print("   " + "-" * 50)
            for it in items:
                print(f"   {it['rcept_dt']:<12} {it['report_nm']}")
        else:
            print(f"   공시 없음 (status={data2.get('status')}, msg={data2.get('message')})")

# ── 4. corp_code 없으면 CORPCODE.xml 직접 grep ────────────────────────────────
else:
    print()
    print(f"4. CORPCODE.xml 직접 검색 ('{KEYWORD}' 포함 항목)")
    import xml.etree.ElementTree as ET
    tree = ET.parse("CORPCODE.xml")
    found = [
        (item.findtext("corp_code", ""), item.findtext("corp_name", ""))
        for item in tree.getroot().findall("list")
        if KEYWORD in item.findtext("corp_name", "")
    ]
    if found:
        for code, name in found:
            print(f"   {code}  {name}")
    else:
        print(f"   '{KEYWORD}' — CORPCODE.xml에 없음")
        # 유사어 검색
        for alt in ["한강", "버스", "수상버스", "리버버스", "수상"]:
            hits = [
                (item.findtext("corp_code", ""), item.findtext("corp_name", ""))
                for item in tree.getroot().findall("list")
                if alt in item.findtext("corp_name", "")
                and "버스" in item.findtext("corp_name", "")
            ]
            if hits:
                print(f"\n   '{alt}+버스' 유사 검색 결과:")
                for code, name in hits:
                    print(f"   {code}  {name}")
