import re
import os
import xml.etree.ElementTree as ET

from xml_fix import _BR_SENTINEL, fix_xml
from dart_client import AUDIT_TYPE, list_disclosures, load_corp_list, search_company
from downloader import download_document, safe_filename
from financials import (
    calculate_financial_ratios,
    get_audit_opinion_3y,
    get_capital_changes,
    get_capital_changes_3y,
    get_dividend_info,
    get_dividend_info_3y,
    get_employee_status,
    get_equity_investments,
    get_extended_financials,
    get_extended_financials_3y,
    get_key_financials,
    get_key_financials_3y,
    get_major_shareholder,
)


# ── 9. XML → HTML 변환 ───────────────────────────────────────────────────────
import html as _html_mod


def _esc(text):
    """본문 텍스트 이스케이프. fix_xml이 남긴 줄바꿈 표식은 <br>로 편다."""
    return _html_mod.escape(text).replace(_BR_SENTINEL, "<br>")

_DART_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f5f5f5; font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
       font-size: 13px; color: #1a1a1a; line-height: 1.6; }
.page { max-width: 960px; margin: 0 auto; background: #fff;
        padding: 40px 48px; box-shadow: 0 2px 12px rgba(0,0,0,.12); }
h1 { font-size: 1.6em; font-weight: 700; margin: 24px 0 16px; color: #111; border-bottom: 2px solid #2563eb; padding-bottom: 8px; }
h2 { font-size: 1.25em; font-weight: 700; margin: 24px 0 10px; color: #1d4ed8; border-left: 4px solid #2563eb; padding-left: 10px; }
h3 { font-size: 1.1em;  font-weight: 700; margin: 18px 0 8px;  color: #1e40af; }
h4 { font-size: 1.0em;  font-weight: 700; margin: 14px 0 6px;  color: #374151; }
h5 { font-size: 0.95em; font-weight: 700; margin: 10px 0 4px;  color: #6b7280; }
p  { margin: 6px 0; }
hr.pgbrk { border: none; border-top: 1px dashed #d1d5db; margin: 20px 0; }
table { border-collapse: collapse; width: 100%; margin: 10px 0 16px; font-size: 12px; }
th, td { border: 1px solid #d1d5db; padding: 5px 8px; word-break: keep-all; }
th { background: #eff6ff; font-weight: 700; }
td.te { background: #fafafa; }
td.tu { background: #f0f9ff; }
.tg { margin: 8px 0; }
.cover { text-align: center; margin-bottom: 32px; }
.cover h1 { border: none; }
.section-1 { margin-top: 32px; }
.section-2 { margin: 16px 0 8px 12px; }
.section-3 { margin: 10px 0 6px 20px; }
.note { margin: 10px 0; padding: 8px 12px; background: #fafafa; border-left: 3px solid #e5e7eb; }

/* ── 목차 사이드바 ─────────────────────────────────────────── */
html { scroll-behavior: smooth; }
.wrap { display: flex; align-items: flex-start; gap: 20px;
        max-width: 1320px; margin: 0 auto; padding: 20px 16px; }
.wrap > .page { flex: 1; min-width: 0; margin: 0; padding: 32px 40px; overflow-x: auto; }
.tg { overflow-x: auto; }
.toc { position: sticky; top: 20px; width: 268px; flex: none;
       max-height: calc(100vh - 40px); overflow-y: auto;
       background: #fff; border: 1px solid #e5e7eb; border-radius: 6px;
       padding: 14px 8px 16px; box-shadow: 0 2px 12px rgba(0,0,0,.08); }
.toc .toc-h { font-size: 12px; font-weight: 700; letter-spacing: .08em;
              color: #6b7280; padding: 0 10px 10px; border-bottom: 1px solid #e5e7eb;
              margin-bottom: 8px; }
.toc a { display: block; padding: 5px 10px; border-radius: 4px;
         color: #374151; text-decoration: none; font-size: 12.5px;
         line-height: 1.45; word-break: keep-all; border-left: 2px solid transparent; }
.toc a:hover { background: #eff6ff; color: #1d4ed8; }
.toc a.lv0 { font-weight: 700; color: #1e3a8a; margin-top: 6px; }
.toc a.lv1 { padding-left: 22px; }
.toc a.lv2 { padding-left: 34px; color: #6b7280; font-size: 12px; }
:target { background: #fef9c3; scroll-margin-top: 16px; }

@media (max-width: 980px) {
  .wrap { display: block; padding: 12px; }
  .toc { position: static; width: auto; max-height: 320px; margin-bottom: 16px; }
  .wrap > .page { padding: 24px 20px; }
}
@media print { .toc { display: none; } .wrap { display: block; } }
"""

# 목차에 넣을 제목 깊이 상한 (h2·h3·h4 까지. h5 소제목은 너무 잘게 쪼개져 제외)
_TOC_MAX_LEVEL = 4

# DART 태그 → HTML 태그 (단순 컨테이너)
_DART_DIV = {"COVER", "BODY", "NOTE", "DOCUMENT"}
_DART_SEC = {"SECTION-1": 2, "SECTION-2": 3, "SECTION-3": 4, "SECTION-4": 5}
_DART_SKIP = {"DOCUMENT-NAME", "COMPANY-NAME", "FORMULA-VERSION",
              "SUMMARY", "EXTRACTION"}


def _dart_cell_attrs(elem):
    attrs = []
    rs = elem.get("ROWSPAN") or elem.get("rowspan")
    cs = elem.get("COLSPAN") or elem.get("colspan")
    if rs: attrs.append(f'rowspan="{rs}"')
    if cs: attrs.append(f'colspan="{cs}"')
    styles = []
    align = (elem.get("ALIGN") or "").lower()
    if align in ("left", "center", "right"):
        styles.append(f"text-align:{align}")
    valign = (elem.get("VALIGN") or "").lower()
    if valign in ("top", "middle", "bottom"):
        styles.append(f"vertical-align:{valign}")
    if styles: attrs.append(f'style="{";".join(styles)}"')
    return (" " + " ".join(attrs)) if attrs else ""


def _dart_span_style(usermark):
    styles = []
    for part in (usermark or "").split():
        if part == "B":   styles.append("font-weight:bold")
        elif part == "I": styles.append("font-style:italic")
        elif part == "U": styles.append("text-decoration:underline")
        elif part.startswith("F-"):
            m = re.search(r"(\d+)$", part)
            if m: styles.append(f"font-size:{m.group(1)}pt")
    return ";".join(styles)


def _toc_entry(toc, elem, level):
    """제목 elem을 목차에 등록하고 앵커 id를 돌려준다. toc가 None이면 앵커 없음."""
    if toc is None:
        return ""
    text = " ".join("".join(elem.itertext()).split())
    if not text:
        return ""
    anchor = f"sec{len(toc) + 1}"
    toc.append({"id": anchor, "level": level, "text": text})
    return anchor


def _dart_elem_to_html(elem, sec_depth=1, toc=None):
    """DART XML Element를 HTML 문자열로 재귀 변환. toc를 주면 제목에 앵커를 단다."""
    tag = elem.tag
    txt  = _esc(elem.text or "")
    tail = _esc(elem.tail or "")

    if tag in _DART_SKIP:
        return tail  # 자식 무시, tail만 유지

    # ── 섹션: 자식에게 새 깊이를 전달해야 하므로 먼저 처리
    if tag in _DART_SEC:
        new_depth = _DART_SEC[tag]
        inner = "".join(_dart_elem_to_html(c, new_depth, toc) for c in elem)
        return f'<div class="{tag.lower()}">{txt}{inner}</div>{tail}'

    # ── TITLE → hN (부모 섹션 깊이 기반). 목차 등록은 자식 변환 전에 해야
    #    문서 순서대로 번호가 매겨진다.
    if tag == "TITLE":
        level  = min(sec_depth + 1, 5)
        anchor = _toc_entry(toc, elem, level)
        kids   = "".join(_dart_elem_to_html(c, sec_depth, toc) for c in elem)
        ia     = f' id="{anchor}"' if anchor else ""
        return f"<h{level}{ia}>{txt}{kids}</h{level}>{tail}"

    # 이하 공통 kids (현재 sec_depth 유지)
    kids = "".join(_dart_elem_to_html(c, sec_depth, toc) for c in elem)

    # ── COVER-TITLE
    if tag == "COVER-TITLE":
        return f"<h1>{txt}{kids}</h1>{tail}"

    # ── P
    if tag == "P":
        content = txt + kids
        if not content.strip():
            return f"<br>{tail}"
        return f"<p>{content}</p>{tail}"

    # ── SPAN
    if tag == "SPAN":
        style = _dart_span_style(elem.get("USERMARK"))
        sa = f' style="{style}"' if style else ""
        return f"<span{sa}>{txt}{kids}</span>{tail}"

    # ── TABLE-GROUP
    if tag == "TABLE-GROUP":
        return f'<div class="tg">{txt}{kids}</div>{tail}'

    # ── TABLE
    if tag == "TABLE":
        return f"<table>{txt}{kids}</table>{tail}"

    # ── COLGROUP / COL
    if tag == "COLGROUP":
        return f"<colgroup>{txt}{kids}</colgroup>{tail}"
    if tag == "COL":
        w = elem.get("WIDTH")
        sa = f' style="width:{w}px"' if w else ""
        return f"<col{sa}>{tail}"

    # ── THEAD / TBODY
    if tag in ("THEAD", "TBODY"):
        t = tag.lower()
        return f"<{t}>{txt}{kids}</{t}>{tail}"

    # ── TR
    if tag == "TR":
        return f"<tr>{txt}{kids}</tr>{tail}"

    # ── TD / TH / TE(계산셀) / TU(단위셀)
    if tag == "TD":
        a = _dart_cell_attrs(elem)
        return f"<td{a}>{txt}{kids}</td>{tail}"
    if tag == "TH":
        a = _dart_cell_attrs(elem)
        return f"<th{a}>{txt}{kids}</th>{tail}"
    if tag == "TE":
        a = _dart_cell_attrs(elem)
        return f'<td class="te"{a}>{txt}{kids}</td>{tail}'
    if tag == "TU":
        a = _dart_cell_attrs(elem)
        return f'<td class="tu"{a}>{txt}{kids}</td>{tail}'

    # ── PGBRK
    if tag == "PGBRK":
        return f'<hr class="pgbrk">{tail}'

    # ── 컨테이너 div
    if tag in _DART_DIV:
        css = tag.lower()
        return f'<div class="{css}">{txt}{kids}</div>{tail}'

    # ── 나머지: 텍스트·자식만 통과
    return f"{txt}{kids}{tail}"


def _build_toc_html(toc):
    """
    수집한 제목 목록을 목차 사이드바 HTML로 만든다.
    항목이 2개 미만이면 빈 문자열 — 목차를 붙일 이유가 없다.
    """
    # 원문에 이미 들어 있는 '목 차' 장은 사이드바와 겹치므로 뺀다
    items = [t for t in toc
             if t["level"] <= _TOC_MAX_LEVEL and t["text"].replace(" ", "") != "목차"]
    if len(items) < 2:
        return ""

    base = min(t["level"] for t in items)
    links = []
    for t in items:
        cls  = f"lv{min(t['level'] - base, 2)}"
        text = _html_mod.escape(t["text"])
        links.append(f'<a class="{cls}" href="#{t["id"]}">{text}</a>')

    return ('<nav class="toc"><div class="toc-h">목차</div>'
            + "".join(links) + "</nav>")


def convert_to_html(xml_path, output_path, log_fn=None):
    """
    DART XML 파일을 읽기용 HTML 파일로 변환한다.
    fix_xml()로 먼저 보정한 뒤 DART 태그를 표준 HTML로 매핑.
    반환값: output_path (str)
    """
    def log(msg):
        if log_fn: log_fn(msg)

    log(f"HTML 변환: {os.path.basename(xml_path)}")

    with open(xml_path, encoding="utf-8", errors="replace") as f:
        raw = f.read()

    fixed = fix_xml(raw)

    try:
        root = ET.fromstring(fixed.encode("utf-8"))
    except ET.ParseError as e:
        raise RuntimeError(f"XML 파싱 실패: {e}")

    doc_name  = (root.findtext("DOCUMENT-NAME") or "DART 공시").strip()
    corp_name = (root.findtext("COMPANY-NAME")  or "").strip()
    title_str = _html_mod.escape(f"{corp_name} — {doc_name}" if corp_name else doc_name)

    toc = []
    body_html = _dart_elem_to_html(root, toc=toc)

    toc_html = _build_toc_html(toc)
    if toc_html:
        content = f'<div class="wrap">{toc_html}<div class="page">\n{body_html}\n</div></div>'
    else:
        content = f'<div class="page">\n{body_html}\n</div>'

    html_out = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_str}</title>
<style>{_DART_CSS}</style>
</head>
<body>
{content}
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    log(f"HTML 저장: {os.path.basename(output_path)}")
    return output_path

