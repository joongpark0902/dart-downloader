import requests


# ── 내부 상수 ────────────────────────────────────────────────────────────────
_FINANCIALS_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
_DIVIDEND_URL   = "https://opendart.fss.or.kr/api/alotMatter.json"


# ── 5. 핵심재무 조회 ──────────────────────────────────────────────────────────
# 찾을 항목과 우선 매칭 키워드 (앞쪽 키워드일수록 우선)
_FIN_TARGETS = {
    "매출액":     ["매출액", "수익(매출액)", "영업수익"],
    "영업이익":   ["영업이익"],
    "당기순이익": ["당기순이익"],
    "자산총계":   ["자산총계"],
    "부채총계":   ["부채총계"],
    "자본총계":   ["자본총계"],
}

def _parse_amount(raw):
    """콤마 제거 후 정수 변환. 빈 값이면 None."""
    if not raw or raw.strip() == "":
        return None
    try:
        return int(raw.replace(",", "").replace(" ", ""))
    except ValueError:
        return None

def _find_account(items, keywords):
    """
    keywords 순서대로 account_nm 부분일치 검색.
    여러 키워드 중 앞 키워드를 먼저 시도하고, 같은 키워드 내에서는
    정확일치 → 시작일치 → 포함 순으로 우선한다.
    """
    for kw in keywords:
        exact   = [i for i in items if i["account_nm"] == kw]
        starts  = [i for i in items if i["account_nm"].startswith(kw) and i not in exact]
        contains = [i for i in items if kw in i["account_nm"] and i not in exact and i not in starts]
        for group in (exact, starts, contains):
            if group:
                return group[0]
    return None

def get_key_financials(api_key, corp_code, bsns_year, reprt_code="11011",
                       fs_div="CFS", log_fn=None):
    """
    DART 주요계정(fnlttSinglAcnt)에서 핵심재무 6개 항목을 반환한다.
    fs_div: "CFS"(연결) 또는 "OFS"(별도). 해당 구분 데이터가 없으면 available=False.
    반환값: {
        "fs_div": "CFS" | "OFS",
        "available": bool,   # 요청한 fs_div 데이터 존재 여부
        "매출액": int | None, ...
    }
    """
    def log(msg):
        if log_fn:
            log_fn(msg)

    resp = requests.get(_FINANCIALS_URL, params={
        "crtfc_key": api_key,
        "corp_code":  corp_code,
        "bsns_year":  bsns_year,
        "reprt_code": reprt_code,
    })
    data = resp.json()

    if data.get("status") != "000":
        raise RuntimeError(f"fnlttSinglAcnt 오류: {data.get('status')} {data.get('message')}")

    all_items = data.get("list", [])
    log(f"주요계정 수신: {len(all_items)}건 (연도={bsns_year}, {fs_div})")

    items = [i for i in all_items if i.get("fs_div") == fs_div]
    available = bool(items)
    if not available:
        log(f"  ※ {fs_div} 데이터 없음")
    log(f"재무제표 구분: {fs_div} ({len(items)}건, available={available})")

    result = {"fs_div": fs_div, "available": available}
    for label, keywords in _FIN_TARGETS.items():
        row = _find_account(items, keywords)
        result[label] = _parse_amount(row.get("thstrm_amount", "")) if row else None

    sample = items[0] if items else {}
    result["currency"] = sample.get("currency", "KRW")
    result["unit"] = "원"

    return result


# ── 6. 핵심재무 3개년 조회 ────────────────────────────────────────────────────
def get_key_financials_3y(api_key, corp_code, end_year, reprt_code="11011",
                          fs_div="CFS", log_fn=None):
    """
    end_year 포함 직전 2개년까지 총 3개년 핵심재무를 반환한다.
    fs_div: "CFS"(연결) 또는 "OFS"(별도).
    반환값: [{"year": "2022", ...}, ...] 연도 오름차순.
    """
    def log(msg):
        if log_fn:
            log_fn(msg)

    years = [str(int(end_year) - i) for i in range(2, -1, -1)]
    results = []
    for yr in years:
        log(f"{yr}년 조회 중...")
        try:
            row = get_key_financials(api_key, corp_code, yr, reprt_code,
                                     fs_div=fs_div, log_fn=log_fn)
            row["year"] = yr
        except Exception as e:
            log(f"  {yr}년 오류: {e}")
            row = {"year": yr, "fs_div": fs_div, "available": False,
                   "매출액": None, "영업이익": None, "당기순이익": None,
                   "자산총계": None, "부채총계": None, "자본총계": None,
                   "currency": "KRW", "unit": "원"}
        results.append(row)
    return results


# ── 7. 배당 조회 ──────────────────────────────────────────────────────────────
# alotMatter는 thstrm/frmtrm/lwfr 3개 연도를 한 번에 반환한다.
_DIV_ITEMS = [
    # (출력키,               se 부분일치,        stock_knd 필터, 값 타입)
    ("주당배당금(원)",       "주당 현금배당금",   "보통주",       "int"),
    ("배당성향(%)",          "현금배당성향",      None,           "float"),
    ("시가배당률(%)",        "현금배당수익률",    "보통주",       "float"),
    ("현금배당총액(백만원)", "현금배당금총액",    None,           "int"),
]

def _parse_div(raw, val_type):
    """'-' 또는 빈 값은 None, 나머지는 int/float 변환."""
    if not raw or raw.strip() in ("-", ""):
        return None
    clean = raw.replace(",", "").strip()
    try:
        return float(clean) if val_type == "float" else int(clean)
    except ValueError:
        return None

def _find_div(items, se_kw, stock_filter, col):
    """se 부분일치 + stock_knd 필터로 항목 찾아 해당 연도 컬럼 값 반환."""
    for item in items:
        if se_kw not in item.get("se", ""):
            continue
        if stock_filter and item.get("stock_knd") != stock_filter:
            continue
        return item.get(col, "")
    return ""

def get_dividend_info(api_key, corp_code, bsns_year, reprt_code="11011", log_fn=None):
    """
    단일 연도 배당 정보를 반환한다.
    반환값: {"주당배당금(원)": int|None, "배당성향(%)": float|None,
             "시가배당률(%)": float|None, "현금배당총액(백만원)": int|None}
    """
    def log(msg):
        if log_fn: log_fn(msg)

    resp = requests.get(_DIVIDEND_URL, params={
        "crtfc_key": api_key, "corp_code": corp_code,
        "bsns_year": bsns_year, "reprt_code": reprt_code,
    })
    data = resp.json()
    if data.get("status") != "000":
        raise RuntimeError(f"alotMatter 오류: {data.get('status')} {data.get('message')}")

    items = data.get("list", [])
    log(f"배당 수신: {len(items)}건 (연도={bsns_year})")

    result = {}
    for key, se_kw, stock_filter, val_type in _DIV_ITEMS:
        raw = _find_div(items, se_kw, stock_filter, "thstrm")
        result[key] = _parse_div(raw, val_type)
    return result

def get_dividend_info_3y(api_key, corp_code, end_year, reprt_code="11011", log_fn=None):
    """
    end_year 포함 직전 2개년까지 총 3개년 배당 정보를 반환한다.
    alotMatter는 1회 호출로 3개년(thstrm/frmtrm/lwfr)을 제공하므로 API 1번만 호출한다.
    반환값: [{"year": "2022", ...}, {"year": "2023", ...}, {"year": "2024", ...}]
    """
    def log(msg):
        if log_fn: log_fn(msg)

    log(f"배당 3개년 조회 중 (기준연도={end_year})...")
    resp = requests.get(_DIVIDEND_URL, params={
        "crtfc_key": api_key, "corp_code": corp_code,
        "bsns_year": end_year, "reprt_code": reprt_code,
    })
    data = resp.json()
    if data.get("status") != "000":
        raise RuntimeError(f"alotMatter 오류: {data.get('status')} {data.get('message')}")

    items = data.get("list", [])
    log(f"배당 수신: {len(items)}건")

    # thstrm=end_year, frmtrm=end_year-1, lwfr=end_year-2
    year_col = [
        (str(int(end_year) - 2), "lwfr"),
        (str(int(end_year) - 1), "frmtrm"),
        (str(int(end_year)),     "thstrm"),
    ]
    results = []
    for yr, col in year_col:
        row = {"year": yr}
        for key, se_kw, stock_filter, val_type in _DIV_ITEMS:
            raw = _find_div(items, se_kw, stock_filter, col)
            row[key] = _parse_div(raw, val_type)
        results.append(row)
    return results


# ── 8. 재무비율 계산 ──────────────────────────────────────────────────────────
def calculate_financial_ratios(financials_3y, extended_3y=None):
    """
    get_key_financials_3y() + (선택) get_extended_financials_3y() 결과로 연도별 재무비율을 계산한다.
    반환값: [{"year": "2022", "영업이익률": float|None, ...}, ...]
    """
    def safe_pct(numerator, denominator):
        if numerator is None or denominator is None or denominator == 0:
            return None
        return numerator / denominator * 100

    # extended_3y를 연도 키로 인덱싱
    ext_by_year = {}
    if extended_3y:
        for row in extended_3y:
            ext_by_year[row["year"]] = row

    results = []
    for row in financials_3y:
        rev = row.get("매출액")
        op  = row.get("영업이익")
        ni  = row.get("당기순이익")
        ta  = row.get("자산총계")
        tl  = row.get("부채총계")
        eq  = row.get("자본총계")
        yr  = row["year"]
        ext = ext_by_year.get(yr, {})
        gp  = ext.get("매출총이익")   # gross profit
        cogs= ext.get("매출원가")
        ci  = ext.get("총포괄이익")   # comprehensive income
        ratio = {
            "year":      yr,
            "영업이익률":  safe_pct(op,  rev),
            "순이익률":   safe_pct(ni,  rev),
            "부채비율":   safe_pct(tl,  eq),
            "ROE":       safe_pct(ni,  eq),
            "ROA":       safe_pct(ni,  ta),
            "매출총이익률": safe_pct(gp,  rev),
            "매출원가율":  safe_pct(cogs, rev),
            "총포괄이익률": safe_pct(ci,  rev),
        }
        results.append(ratio)
    return results


# ── 9. 확장재무 조회 (매출원가·매출총이익·총포괄이익) ─────────────────────────
_EXT_FIN_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"

_EXT_TARGETS = [
    # (출력키,       account_nm 부분일치 키워드)
    ("매출원가",    "매출원가"),
    ("매출총이익",  "매출총이익"),
    ("총포괄이익",  "총포괄이익"),
]

def _ext_find(cis_items, keyword):
    """CIS 항목에서 keyword 부분일치 첫 번째 결과 반환."""
    for item in cis_items:
        if keyword in item.get("account_nm", ""):
            return item
    return None

def _ext_parse(raw):
    if not raw or raw.strip() in ("-", ""):
        return None
    try:
        return int(raw.replace(",", "").strip())
    except ValueError:
        return None

def get_extended_financials(api_key, corp_code, bsns_year, reprt_code="11011", log_fn=None):
    """
    fnlttSinglAcntAll에서 매출원가·매출총이익·총포괄이익을 반환한다.
    CFS 우선, CIS 항목 없으면 OFS 재시도.
    반환값: {"매출원가": int|None, "매출총이익": int|None, "총포괄이익": int|None, "fs_div": str}
    """
    def log(msg):
        if log_fn: log_fn(msg)

    for fs in ("CFS", "OFS"):
        resp = requests.get(_EXT_FIN_URL, params={
            "crtfc_key": api_key, "corp_code": corp_code,
            "bsns_year": bsns_year, "reprt_code": reprt_code,
            "fs_div": fs,
        })
        data = resp.json()
        if data.get("status") != "000":
            raise RuntimeError(f"fnlttSinglAcntAll 오류: {data.get('status')} {data.get('message')}")
        cis = [i for i in data.get("list", []) if i.get("sj_div") == "CIS"]
        if cis:
            log(f"확장재무 CIS {len(cis)}건 수신 ({fs}, 연도={bsns_year})")
            result = {"fs_div": fs}
            for key, kw in _EXT_TARGETS:
                row = _ext_find(cis, kw)
                result[key] = _ext_parse(row.get("thstrm_amount", "") if row else "")
            return result

    log(f"확장재무: CIS 항목 없음 (연도={bsns_year})")
    return {"fs_div": None, "매출원가": None, "매출총이익": None, "총포괄이익": None}

def get_extended_financials_3y(api_key, corp_code, end_year, reprt_code="11011", log_fn=None):
    """
    fnlttSinglAcntAll는 thstrm/frmtrm/bfefrmtrm 3열을 한 번에 제공하므로 1회 호출로 3개년 반환.
    반환값: [{"year":"2022",...}, {"year":"2023",...}, {"year":"2024",...}]  (오름차순)
    """
    def log(msg):
        if log_fn: log_fn(msg)

    log(f"확장재무 3개년 조회 중 (기준연도={end_year})...")
    for fs in ("CFS", "OFS"):
        resp = requests.get(_EXT_FIN_URL, params={
            "crtfc_key": api_key, "corp_code": corp_code,
            "bsns_year": end_year, "reprt_code": reprt_code,
            "fs_div": fs,
        })
        data = resp.json()
        if data.get("status") != "000":
            raise RuntimeError(f"fnlttSinglAcntAll 오류: {data.get('status')} {data.get('message')}")
        cis = [i for i in data.get("list", []) if i.get("sj_div") == "CIS"]
        if not cis:
            continue
        log(f"확장재무 CIS {len(cis)}건 수신 ({fs})")

        # thstrm=end_year, frmtrm=end_year-1, bfefrmtrm=end_year-2
        year_col = [
            (str(int(end_year) - 2), "bfefrmtrm_amount"),
            (str(int(end_year) - 1), "frmtrm_amount"),
            (str(int(end_year)),     "thstrm_amount"),
        ]
        results = []
        for yr, col in year_col:
            row_data = {"year": yr, "fs_div": fs}
            for key, kw in _EXT_TARGETS:
                item = _ext_find(cis, kw)
                row_data[key] = _ext_parse(item.get(col, "") if item else "")
            results.append(row_data)
        return results

    # 모든 fs 실패 시 None 채워서 반환
    years = [str(int(end_year) - i) for i in range(2, -1, -1)]
    return [{"year": y, "fs_div": None, "매출원가": None, "매출총이익": None, "총포괄이익": None}
            for y in years]


# ── 10. 타법인출자 조회 ───────────────────────────────────────────────────────
_EQUITY_URL = "https://opendart.fss.or.kr/api/otrCprInvstmntSttus.json"

def get_equity_investments(api_key, corp_code, bsns_year, reprt_code="11011", log_fn=None):
    """
    타법인 출자현황을 반환한다. 지분율 내림차순 정렬.
    반환값: [{"법인명": str, "최초취득일": str, "지분율": float|None,
              "기말장부가액": int|None}, ...]
    """
    def log(msg):
        if log_fn: log_fn(msg)

    resp = requests.get(_EQUITY_URL, params={
        "crtfc_key": api_key, "corp_code": corp_code,
        "bsns_year": bsns_year, "reprt_code": reprt_code,
    })
    data = resp.json()
    if data.get("status") != "000":
        raise RuntimeError(f"otrCprInvstmntSttus 오류: {data.get('status')} {data.get('message')}")

    items = data.get("list", [])
    log(f"타법인출자 수신: {len(items)}건 (연도={bsns_year})")

    def _parse_float(raw):
        if not raw or raw.strip() in ("-", ""):
            return None
        try:
            return float(raw.replace(",", ""))
        except ValueError:
            return None

    def _parse_int(raw):
        if not raw or raw.strip() in ("-", ""):
            return None
        try:
            return int(raw.replace(",", ""))
        except ValueError:
            return None

    results = []
    for item in items:
        results.append({
            "법인명":     item.get("inv_prm", ""),
            "최초취득일":  item.get("frst_acqs_de", ""),
            "지분율":     _parse_float(item.get("trmend_blce_qota_rt", "")),
            "기말장부가액": _parse_int(item.get("trmend_blce_acntbk_amount", "")),
        })

    results.sort(key=lambda x: x["지분율"] if x["지분율"] is not None else -1, reverse=True)
    return results


# ── 11. 감사의견 조회 ─────────────────────────────────────────────────────────
_AUDIT_URL = "https://opendart.fss.or.kr/api/accnutAdtorNmNdAdtOpinion.json"

def get_audit_opinion_3y(api_key, corp_code, end_year, reprt_code="11011", log_fn=None):
    """
    3개년 감사인·감사의견·핵심감사사항을 반환한다.
    반환값: [{"year":str, "감사인":str, "감사의견":str, "강조사항":str, "핵심감사사항":str}, ...]
    연도당 복수 보고서(연결/별도 등)가 있을 경우 연결재무제표 언급 항목 우선, 없으면 첫 항목.
    """
    def log(msg):
        if log_fn: log_fn(msg)

    def _best(items):
        """연결재무제표 언급 항목 우선, 없으면 핵심감사 가장 긴 항목."""
        cfs = [i for i in items if "연결재무제표" in (i.get("core_adt_matter") or "")]
        pool = cfs if cfs else items
        return max(pool, key=lambda i: len(i.get("core_adt_matter") or ""), default=items[0])

    def _clean(text):
        if not text or text.strip() in ("-", "해당사항 없음", ""):
            return "해당사항 없음"
        # 공백/줄바꿈 정리
        import re
        return re.sub(r"[ \t]+", " ", text.strip())

    results = []
    years = [str(int(end_year) - i) for i in range(2, -1, -1)]
    for year in years:
        resp = requests.get(_AUDIT_URL, params={
            "crtfc_key": api_key, "corp_code": corp_code,
            "bsns_year": year, "reprt_code": reprt_code,
        })
        data = resp.json()
        if data.get("status") != "000":
            log(f"감사의견 조회 실패 ({year}): {data.get('message')}")
            results.append({"year": year, "감사인": "N/A", "감사의견": "N/A",
                            "강조사항": "", "핵심감사사항": ""})
            continue
        items = data.get("list", [])
        log(f"감사의견 {len(items)}건 수신 (연도={year})")
        if not items:
            results.append({"year": year, "감사인": "N/A", "감사의견": "N/A",
                            "강조사항": "", "핵심감사사항": ""})
            continue
        row = _best(items)
        results.append({
            "year":     year,
            "감사인":   row.get("adtor", "").replace("\n", "").strip(),
            "감사의견": row.get("adt_opinion", "").strip(),
            "강조사항": _clean(row.get("emphs_matter", "")),
            "핵심감사사항": _clean(row.get("core_adt_matter", "")),
        })
    return results


# ── 12. 최대주주 현황 조회 ────────────────────────────────────────────────────
_SHAREHOLDER_URL = "https://opendart.fss.or.kr/api/hyslrSttus.json"

def get_major_shareholder(api_key, corp_code, bsns_year, reprt_code="11011", log_fn=None):
    """
    최대주주 및 특수관계인 현황을 반환한다.
    반환값: [{"주주명":str, "관계":str, "주식종류":str, "기말주식수":int|None, "지분율":float|None}, ...]
    """
    def log(msg):
        if log_fn: log_fn(msg)

    resp = requests.get(_SHAREHOLDER_URL, params={
        "crtfc_key": api_key, "corp_code": corp_code,
        "bsns_year": bsns_year, "reprt_code": reprt_code,
    })
    data = resp.json()
    if data.get("status") != "000":
        raise RuntimeError(f"hyslrSttus 오류: {data.get('status')} {data.get('message')}")

    items = data.get("list", [])
    log(f"최대주주 현황 {len(items)}건 수신 (연도={bsns_year})")

    def _parse_float(raw):
        try: return float(raw.replace(",", ""))
        except: return None

    def _parse_int(raw):
        try: return int(raw.replace(",", ""))
        except: return None

    results = []
    for item in items:
        results.append({
            "주주명":   item.get("nm", "").strip(),
            "관계":     item.get("relate", "").strip(),
            "주식종류": item.get("stock_knd", "").strip(),
            "기말주식수": _parse_int(item.get("trmend_posesn_stock_co", "")),
            "지분율":   _parse_float(item.get("trmend_posesn_stock_qota_rt", "")),
        })
    return results


# ── 13. 직원 현황 ─────────────────────────────────────────────────────────────
_EMP_URL = "https://opendart.fss.or.kr/api/empSttus.json"

def get_employee_status(api_key, corp_code, bsns_year, reprt_code="11011", log_fn=None):
    """
    직원 현황을 반환한다. 남/녀 행을 집계해 합산 결과와 성별 세부를 함께 반환.
    반환값: {
      "총직원": int, "정규직": int, "계약직": int,
      "평균근속연수": float|None,   # 가중평균
      "1인평균급여": int|None,      # 연간 원화
      "성별": [{"성별":str, "직원수":int, "정규직":int, "계약직":int,
                "평균근속연수":float|None, "1인평균급여":int|None}, ...]
    }
    """
    def log(msg):
        if log_fn: log_fn(msg)

    resp = requests.get(_EMP_URL, params={
        "crtfc_key": api_key, "corp_code": corp_code,
        "bsns_year": bsns_year, "reprt_code": reprt_code,
    })
    data = resp.json()
    if data.get("status") != "000":
        raise RuntimeError(f"empSttus 오류: {data.get('status')} {data.get('message')}")
    items = data.get("list", [])
    log(f"직원 현황 {len(items)}건 수신 (연도={bsns_year})")

    def _int(raw):
        try: return int(raw.replace(",", ""))
        except: return None

    def _float(raw):
        try: return float(raw.strip())
        except: return None

    gender_rows = []
    for item in items:
        sm      = _int(item.get("sm", ""))
        rgllbr  = _int(item.get("rgllbr_co", ""))
        cnttk   = _int(item.get("cnttk_co", ""))
        tenure  = _float(item.get("avrg_cnwk_sdytrn", ""))
        salary  = _int(item.get("jan_salary_am", ""))  # 1인평균급여(연간)
        gender_rows.append({
            "성별":       item.get("sexdstn", "").strip(),
            "직원수":     sm,
            "정규직":     rgllbr,
            "계약직":     cnttk,
            "평균근속연수": tenure,
            "1인평균급여": salary,
        })

    # 집계
    total_sm    = sum(r["직원수"]  or 0 for r in gender_rows) or None
    total_reg   = sum(r["정규직"]  or 0 for r in gender_rows) or None
    total_cnt   = sum(r["계약직"]  or 0 for r in gender_rows) or None
    # 가중 평균 근속연수
    wt_tenure = None
    if total_sm:
        parts = [(r["평균근속연수"] or 0) * (r["직원수"] or 0) for r in gender_rows]
        wt_tenure = sum(parts) / total_sm
    # 1인 평균 급여 = 총급여 / 총직원  (각 행에 jan_salary_am * sm 으로 역산)
    avg_salary = None
    if total_sm:
        total_pay = sum((r["1인평균급여"] or 0) * (r["직원수"] or 0) for r in gender_rows)
        avg_salary = int(total_pay / total_sm) if total_pay else None

    return {
        "총직원":     total_sm,
        "정규직":     total_reg,
        "계약직":     total_cnt,
        "평균근속연수":  round(wt_tenure, 1) if wt_tenure is not None else None,
        "1인평균급여":  avg_salary,
        "성별":       gender_rows,
    }


# ── 14. 자본변동 조회 (증자감자 + 자기주식) ────────────────────────────────────
_ISSU_URL    = "https://opendart.fss.or.kr/api/irdsSttus.json"
_TREASURY_URL = "https://opendart.fss.or.kr/api/tesstkAcqsDspsSttus.json"

def get_capital_changes(api_key, corp_code, bsns_year, reprt_code="11011", log_fn=None):
    """
    증자(감자) 현황과 자기주식 취득/처분 현황을 반환한다.
    반환값: {
      "증자감자": [{"발행일":str, "발행형태":str, "주식종류":str,
                    "수량":str, "액면가":str, "발행가":str}, ...],
      "자기주식": [{"주식종류":str, "취득방법":str, "기초수량":str,
                    "취득":str, "처분":str, "소각":str, "기말수량":str}, ...]
    }
    내역이 없으면 빈 리스트.
    """
    def log(msg):
        if log_fn: log_fn(msg)

    def _has(raw):
        return raw and raw.strip() not in ("-", "")

    # ── 증자감자
    resp1 = requests.get(_ISSU_URL, params={
        "crtfc_key": api_key, "corp_code": corp_code,
        "bsns_year": bsns_year, "reprt_code": reprt_code,
    })
    d1 = resp1.json()
    if d1.get("status") != "000":
        raise RuntimeError(f"irdsSttus 오류: {d1.get('status')} {d1.get('message')}")
    issu_items = d1.get("list", [])
    log(f"증자감자 {len(issu_items)}건 수신 (연도={bsns_year})")

    issu_result = []
    for item in issu_items:
        if _has(item.get("isu_dcrs_de")) or _has(item.get("isu_dcrs_stle")):
            issu_result.append({
                "발행일":   item.get("isu_dcrs_de", "-").strip(),
                "발행형태": item.get("isu_dcrs_stle", "-").strip(),
                "주식종류": item.get("isu_dcrs_stock_knd", "-").strip(),
                "수량":    item.get("isu_dcrs_qy", "-").strip(),
                "액면가":   item.get("isu_dcrs_mstvdv_fval_amount", "-").strip(),
                "발행가":   item.get("isu_dcrs_mstvdv_amount", "-").strip(),
            })

    # ── 자기주식 (총계 행만 표시)
    resp2 = requests.get(_TREASURY_URL, params={
        "crtfc_key": api_key, "corp_code": corp_code,
        "bsns_year": bsns_year, "reprt_code": reprt_code,
    })
    d2 = resp2.json()
    if d2.get("status") != "000":
        raise RuntimeError(f"tesstkAcqsDspsSttus 오류: {d2.get('status')} {d2.get('message')}")
    treas_items = d2.get("list", [])
    log(f"자기주식 {len(treas_items)}건 수신 (연도={bsns_year})")

    treas_result = []
    for item in treas_items:
        if item.get("acqs_mth2") != "총계":
            continue
        vals = [item.get("bsis_qy"), item.get("change_qy_acqs"),
                item.get("change_qy_dsps"), item.get("trmend_qy")]
        if any(_has(v) for v in vals):
            treas_result.append({
                "주식종류": item.get("stock_knd", "-").strip(),
                "취득방법": item.get("acqs_mth2", "-").strip(),
                "기초수량": item.get("bsis_qy", "-").strip(),
                "취득":    item.get("change_qy_acqs", "-").strip(),
                "처분":    item.get("change_qy_dsps", "-").strip(),
                "소각":    item.get("change_qy_incnr", "-").strip(),
                "기말수량": item.get("trmend_qy", "-").strip(),
            })

    return {"증자감자": issu_result, "자기주식": treas_result}


def get_capital_changes_3y(api_key, corp_code, end_year, reprt_code="11011", log_fn=None):
    yr = int(end_year)
    results = []
    for y in (yr - 2, yr - 1, yr):
        data = get_capital_changes(api_key, corp_code, str(y), reprt_code, log_fn)
        results.append({"year": str(y), **data})
    return results
