# DART 다운로더 모듈화 + 뷰어 네비게이션 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 모놀리식 2파일(2,848줄)을 coms-suite식 역할별 모듈로 분리하고, 읽기용 HTML의 목차 이동을 즉시 점프로 바꾸고, 주석 참조를 클릭 가능한 링크로 만든다.

**Architecture:** 기능 변경 없는 코드 이동이 대부분이다. 각 분리 단계마다 골든 HTML 회귀 테스트와 임포트 호환 테스트를 돌려 동작 동일성을 지킨다. `dart_engine.py`·`dart_gui.py`는 기존 이름을 재수출하는 shim으로 남아 `scripts/` 7개와 배포 런처가 깨지지 않는다. 주석 링크는 `convert_to_html`이 만든 본문 HTML에 대한 순수 문자열 후처리라 기존 변환 경로를 건드리지 않는다.

**Tech Stack:** Python 3, tkinter/customtkinter, requests, 표준 라이브러리 `unittest`(pytest 미설치·추가 안 함)

## Global Constraints

- 새 서드파티 의존성 추가 금지. `requirements.txt`는 `requests>=2.31`, `customtkinter>=5.2` 두 줄을 유지한다.
- 테스트는 `unittest`로 작성하고 `python -m unittest discover -s tests -v`로 돈다.
- 모든 소스 파일은 UTF-8. 주석과 문자열은 한국어를 유지한다.
- 기능 변경 금지. 이 계획의 산출물은 (a) 파일 재배치, (b) 스크롤 CSS 1줄, (c) 신규 주석 링크뿐이다.
- `dart_engine.py`가 내보내던 공개 이름 20개 + 상수 `AUDIT_TYPE`은 리팩터링 후에도 `from dart_engine import ...`로 그대로 임포트돼야 한다:
  `load_corp_list, search_company, list_disclosures, safe_filename, download_document, get_key_financials, get_key_financials_3y, get_dividend_info, get_dividend_info_3y, calculate_financial_ratios, get_extended_financials, get_extended_financials_3y, get_equity_investments, get_audit_opinion_3y, get_major_shareholder, get_employee_status, get_capital_changes, get_capital_changes_3y, convert_to_html, fix_xml, AUDIT_TYPE`
- 작업 브랜치는 `refactor/modularize`. 각 Task 끝에서 커밋한다.
- Windows 환경이다. 경로 구분자는 코드에서 `os.path.join`을 쓴다.

---

### Task 1: 테스트 골격과 회귀 기준선

리팩터링 전에 "지금 출력"을 골든 파일로 박아 둔다. 이후 모든 분리 작업은 이 테스트를 깨지 않아야 한다.

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/fixtures/annual_report.xml`
- Create: `tests/fixtures/audit_report.xml`
- Create: `tests/test_convert_regression.py`
- Create: `tests/test_public_api.py`
- Create: `tests/golden/annual_report.html` (테스트가 생성)
- Create: `tests/golden/audit_report.html` (테스트가 생성)

**Interfaces:**
- Consumes: `dart_engine.convert_to_html(xml_path, output_path, log_fn=None) -> str`
- Produces: `tests/fixtures/*.xml` 2종 — 이후 Task 13의 주석 링크 테스트가 같은 픽스처를 쓴다.
  `tests/golden/*.html` — 이후 모든 분리 Task의 회귀 기준선.

- [ ] **Step 1: 픽스처 XML 2종 작성**

`tests/fixtures/annual_report.xml` — 사업보고서형. 연결·별도 주석 2세트, 합쳐진 제목(`4. … 5. …`), 하이픈 번호(`7-1.`), 하위 항목(`(11)`, `1)`), 없는 번호 참조(`주석 77`), 표 셀 참조를 담는다.

```xml
<DOCUMENT>
<DOCUMENT-NAME>사업보고서</DOCUMENT-NAME>
<COMPANY-NAME>테스트주식회사</COMPANY-NAME>
<COVER><COVER-TITLE>사 업 보 고 서</COVER-TITLE></COVER>
<BODY>
<SECTION-1><TITLE>III. 재무에 관한 사항</TITLE>
<SECTION-2><TITLE>2-1. 연결 재무상태표</TITLE>
<TABLE-GROUP><TABLE><TBODY>
<TR><TD>재고자산(주석3,4)</TD><TD>1,000</TD></TR>
<TR><TD>매출채권(주석 8 참조)</TD><TD>2,000</TD></TR>
</TBODY></TABLE></TABLE-GROUP>
</SECTION-2>
<SECTION-2><TITLE>3. 연결재무제표 주석</TITLE></SECTION-2>
<SECTION-2><TITLE>1. 지배기업의 개요 (연결)</TITLE><P>지배기업의 개요입니다.</P></SECTION-2>
<SECTION-2><TITLE>2. 중요한 회계처리방침 (연결)</TITLE><P>주석 4, 5에서 설명하고 있습니다.</P></SECTION-2>
<SECTION-2><TITLE>3. 중요한 회계정책 (연결)</TITLE><P>회계정책입니다.</P></SECTION-2>
<SECTION-2><TITLE>4. 종속기업의 현황 5. 관계기업및공동기업투자주식 (연결)</TITLE><P>합쳐진 제목입니다.</P></SECTION-2>
<SECTION-2><TITLE>6. 영업부문 (연결)</TITLE><P>영업부문입니다.</P></SECTION-2>
<SECTION-2><TITLE>7-1. 범주별 금융상품 (연결)</TITLE><P>범주별 금융상품입니다.</P></SECTION-2>
<SECTION-2><TITLE>8. 매출채권 및 기타채권 (연결)</TITLE><P>매출채권입니다.</P></SECTION-2>
<SECTION-2><TITLE>16. 사채, 차입금 (연결)</TITLE><P>(1) 차입금 내역<SPAN USERMARK="B">굵게</SPAN></P></SECTION-2>
<SECTION-2><TITLE>17. 충당부채 (연결)</TITLE><P>추정의 주요 가정- 주석 17 및 28: 충당부채와 우발부채</P></SECTION-2>
<SECTION-2><TITLE>28. 우발부채 및 약정사항 (연결)</TITLE><P>재무제표 주석의 2. 재무제표 작성기준을 참고하십시오.</P></SECTION-2>
<SECTION-2><TITLE>4. 재무제표</TITLE>
<TABLE-GROUP><TABLE><TBODY>
<TR><TD>재고자산(주석3,4)</TD><TD>900</TD></TR>
</TBODY></TABLE></TABLE-GROUP>
</SECTION-2>
<SECTION-2><TITLE>5. 재무제표 주석</TITLE></SECTION-2>
<SECTION-2><TITLE>1. 회사의 개요</TITLE><P>회사의 개요입니다.</P></SECTION-2>
<SECTION-2><TITLE>2. 중요한 회계처리방침</TITLE><P>(11) 자산손상은 별도 항목이 아닙니다.</P></SECTION-2>
<SECTION-2><TITLE>3. 중요한 회계정책</TITLE><P>1) 리스제공자도 항목이 아닙니다.</P></SECTION-2>
<SECTION-2><TITLE>15. 사채, 차입금</TITLE><P>분류되어 있습니다(주석 15 참조).</P></SECTION-2>
<SECTION-2><TITLE>99. 없는번호참조</TITLE><P>없는 번호입니다(주석 77 참조).</P></SECTION-2>
</SECTION-1>
</BODY>
</DOCUMENT>
```

`tests/fixtures/audit_report.xml` — 감사보고서형. 주석 세트 1벌이고 항목이 제목이 아니라 문단이며, 17번은 문단 중간에서 시작한다. 세트 뒤에 `외부감사 실시내용` 장이 와서 세트가 닫히는지도 본다.

```xml
<DOCUMENT>
<DOCUMENT-NAME>감사보고서</DOCUMENT-NAME>
<COMPANY-NAME>비상장테스트</COMPANY-NAME>
<COVER><COVER-TITLE>감 사 보 고 서</COVER-TITLE></COVER>
<BODY>
<SECTION-1><TITLE>(첨부)재 무 제 표</TITLE>
<SECTION-2><TITLE>재 무 상 태 표</TITLE>
<TABLE-GROUP><TABLE><TBODY>
<TR><TE>현금및현금성자산(주석3,4)</TE><TD>5,000</TD></TR>
<TR><TE>매출채권(주석14,15)</TE><TD>6,000</TD></TR>
<TR><TE>급여(주석17)</TE><TD>700</TD></TR>
</TBODY></TABLE></TABLE-GROUP>
</SECTION-2>
<SECTION-2><TITLE>주석</TITLE>
<P>1. 회사의 개요당사는 테스트 목적으로 설립되었습니다.</P>
<P>2. 재무제표 작성기준(1) 회계기준의 적용</P>
<P>(11) 자산손상은 하위 항목입니다.</P>
<P>3. 유의적 회계정책</P>
<P>4. 사용이 제한된 금융상품없습니다.</P>
<P>14. 특수관계자(1) 특수관계자 현황</P>
<P>15. 현금흐름표당기와 전기의 내역입니다.</P>
<P>16. 주당손익(1) 가중평균 유통보통주식수</P>
<P>(3) 반희석 효과로 기본주당손익과 희석주당손익은 동일합니다.17. 부가가치 관련자료당기와 전기의 자료는 다음과 같습니다.</P>
</SECTION-2>
</SECTION-1>
<SECTION-1><TITLE>외부감사 실시내용</TITLE>
<SECTION-2><TITLE>1. 감사대상업무</TITLE><P>감사대상업무입니다.</P></SECTION-2>
<SECTION-2><TITLE>3. 주요 감사실시내용</TITLE><P>주요 감사실시내용입니다.</P></SECTION-2>
</SECTION-1>
</BODY>
</DOCUMENT>
```

- [ ] **Step 2: 빈 패키지 파일 생성**

`tests/__init__.py` — 빈 파일.

- [ ] **Step 3: 회귀 테스트 작성**

`tests/test_convert_regression.py`. 골든 파일이 없으면 만들고 통과시킨다(최초 실행이 기준선을 박는다). 있으면 비교한다.

```python
"""convert_to_html 출력이 리팩터링 전후로 같은지 지킨다.

골든 파일이 없으면 현재 출력을 기준선으로 저장한다. 기준선을 일부러
바꿔야 할 때는 tests/golden/ 의 해당 파일을 지우고 다시 돌린다.
"""
import os
import unittest

import dart_engine

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
GOLDEN = os.path.join(HERE, "golden")
OUT = os.path.join(HERE, "_out")

FIXTURE_NAMES = ["annual_report", "audit_report"]


class ConvertRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(GOLDEN, exist_ok=True)
        os.makedirs(OUT, exist_ok=True)

    def _convert(self, name):
        xml_path = os.path.join(FIXTURES, name + ".xml")
        out_path = os.path.join(OUT, name + ".html")
        dart_engine.convert_to_html(xml_path, out_path)
        with open(out_path, encoding="utf-8") as f:
            return f.read()

    def test_output_matches_golden(self):
        for name in FIXTURE_NAMES:
            with self.subTest(fixture=name):
                actual = self._convert(name)
                golden_path = os.path.join(GOLDEN, name + ".html")
                if not os.path.exists(golden_path):
                    with open(golden_path, "w", encoding="utf-8") as f:
                        f.write(actual)
                    self.skipTest(f"기준선 생성: {name}.html")
                with open(golden_path, encoding="utf-8") as f:
                    expected = f.read()
                self.assertEqual(expected, actual, f"{name} 출력이 기준선과 다르다")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: 공개 API 호환 테스트 작성**

`tests/test_public_api.py`.

```python
"""dart_engine이 내보내던 이름이 리팩터링 후에도 살아 있는지 지킨다."""
import ast
import importlib
import os
import unittest

PUBLIC_NAMES = [
    "load_corp_list", "search_company", "list_disclosures",
    "safe_filename", "download_document",
    "get_key_financials", "get_key_financials_3y",
    "get_dividend_info", "get_dividend_info_3y",
    "calculate_financial_ratios",
    "get_extended_financials", "get_extended_financials_3y",
    "get_equity_investments", "get_audit_opinion_3y",
    "get_major_shareholder", "get_employee_status",
    "get_capital_changes", "get_capital_changes_3y",
    "convert_to_html", "fix_xml", "AUDIT_TYPE",
]

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")


class PublicApiTest(unittest.TestCase):
    def test_dart_engine_exports(self):
        engine = importlib.import_module("dart_engine")
        missing = [n for n in PUBLIC_NAMES if not hasattr(engine, n)]
        self.assertEqual([], missing, f"dart_engine에서 사라진 이름: {missing}")

    def test_scripts_imports_resolve(self):
        """scripts/ 도구가 dart_engine에서 끌어 쓰는 이름이 전부 살아 있어야 한다.

        스크립트를 실제로 임포트하면 네트워크를 타므로 AST로만 확인한다.
        """
        engine = importlib.import_module("dart_engine")
        for fname in sorted(os.listdir(SCRIPTS)):
            if not fname.endswith(".py"):
                continue
            path = os.path.join(SCRIPTS, fname)
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
            wanted = [
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module == "dart_engine"
                for alias in node.names
            ]
            with self.subTest(script=fname):
                missing = [n for n in wanted if not hasattr(engine, n)]
                self.assertEqual([], missing, f"{fname}가 못 찾는 이름: {missing}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5: 테스트를 돌려 기준선을 박는다**

Run: `python -m unittest discover -s tests -v`
Expected: `test_output_matches_golden` 이 skip("기준선 생성"), `test_dart_engine_exports` 가 PASS.

- [ ] **Step 6: 다시 돌려 기준선이 안정적인지 확인**

Run: `python -m unittest discover -s tests -v`
Expected: 두 테스트 모두 PASS (skip 없음).

- [ ] **Step 7: `_out` 산출물을 gitignore에 추가**

`.gitignore`의 `# ── 빌드 산출물` 블록에 한 줄 추가:

```
tests/_out/
```

- [ ] **Step 8: 커밋**

```bash
git add tests .gitignore
git commit -m "test: 변환 회귀 기준선과 공개 API 호환 테스트 추가"
```

---

### Task 2: `xml_fix.py` 분리

**Files:**
- Create: `xml_fix.py`
- Modify: `dart_engine.py` (§10 제거, `from xml_fix import ...` 추가)
- Test: `tests/test_convert_regression.py` (기존)

**Interfaces:**
- Produces: `xml_fix.fix_xml(xml_text) -> str`, `xml_fix.BR_SENTINEL` (기존 `_BR_SENTINEL` 값 `" "`)

- [ ] **Step 1: `xml_fix.py` 생성**

`dart_engine.py:1299-1429`의 `_scan_real_tags`, `fix_xml`, `_parse_tag`를 그대로 옮긴다. 이들이 쓰는 모듈 상수 `_VALID_ENTITY`(15행), `_TAG_START`(16행), `_ANY_TAG`(17행), `_DART_BR_ENTITY`(21행), `_BR_SENTINEL`(22행)도 함께 옮긴다. 파일 머리에 `import re`가 필요하다.

`_BR_SENTINEL`은 `dart_viewer`도 써야 하므로 공개 이름을 하나 더 둔다. 파일 끝에 추가:

```python
# HTML 변환 쪽에서도 이 표식을 <br>로 펴야 한다
BR_SENTINEL = _BR_SENTINEL
```

- [ ] **Step 2: `dart_engine.py`에서 §10 제거하고 임포트로 대체**

`# ── 10. XML 보정` 주석부터 파일 끝까지 삭제하고, 15~22행의 위 5개 상수도 삭제한다. 파일 머리 `import requests` 아래에 추가:

```python
from xml_fix import _BR_SENTINEL, fix_xml
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m unittest discover -s tests -v`
Expected: 두 테스트 PASS. 출력이 기준선과 한 글자도 다르지 않아야 한다.

- [ ] **Step 4: 커밋**

```bash
git add xml_fix.py dart_engine.py
git commit -m "refactor: XML 보정 로직을 xml_fix.py로 분리"
```

---

### Task 3: `dart_client.py` 분리

**Files:**
- Create: `dart_client.py`
- Modify: `dart_engine.py`
- Test: `tests/test_public_api.py` (기존)

**Interfaces:**
- Produces:
  - `dart_client.load_corp_list(api_key, cache_path="CORPCODE.xml", log_fn=None) -> list[dict]`
  - `dart_client.search_company(corp_list, keyword) -> list[dict]`
  - `dart_client.list_disclosures(api_key, corp_code, bgn_de, end_de, ...) -> list[dict]`
  - `dart_client.AUDIT_TYPE`

- [ ] **Step 1: `dart_client.py` 생성**

`dart_engine.py:26-203`(`load_corp_list`, `search_company`, `_fetch_disclosure_pages`, `list_disclosures`)를 그대로 옮긴다. 함께 옮길 모듈 상수는 `_CORP_CODE_URL`(9행), `_LIST_URL`(10행), 그리고 `AUDIT_TYPE`(현재 dart_engine에 정의된 상수)이다. 파일 머리:

```python
import io
import os
import zipfile
import xml.etree.ElementTree as ET

import requests
```

- [ ] **Step 2: `dart_engine.py`에서 해당 블록 제거**

옮긴 함수와 상수를 지우고 임포트로 대체한다.

```python
from dart_client import AUDIT_TYPE, list_disclosures, load_corp_list, search_company
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m unittest discover -s tests -v`
Expected: 두 테스트 PASS.

- [ ] **Step 4: GUI가 여전히 뜨는지 확인**

Run: `python -c "import dart_gui; print('import ok')"`
Expected: `import ok`

- [ ] **Step 5: 커밋**

```bash
git add dart_client.py dart_engine.py
git commit -m "refactor: 회사목록·공시조회를 dart_client.py로 분리"
```

---

### Task 4: `downloader.py` 분리

**Files:**
- Create: `downloader.py`
- Modify: `dart_engine.py`

**Interfaces:**
- Produces:
  - `downloader.safe_filename(name, fallback="문서") -> str`
  - `downloader.download_document(api_key, rcept_no, save_dir, log_fn=None, base_name=None) -> list[str]`

- [ ] **Step 1: `downloader.py` 생성**

`dart_engine.py:204-364`(`safe_filename`, `_read_document_name`, `_rename_extracted`, `download_document`)를 옮긴다. 상수 `_DOC_URL`(11행)도 함께. 파일 머리:

```python
import io
import os
import re
import zipfile

import requests
```

- [ ] **Step 2: `dart_engine.py`에서 해당 블록 제거하고 임포트**

```python
from downloader import download_document, safe_filename
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m unittest discover -s tests -v`
Expected: 두 테스트 PASS.

- [ ] **Step 4: 커밋**

```bash
git add downloader.py dart_engine.py
git commit -m "refactor: 문서 다운로드를 downloader.py로 분리"
```

---

### Task 5: `financials.py` 분리

**Files:**
- Create: `financials.py`
- Modify: `dart_engine.py`

**Interfaces:**
- Produces: `financials` 모듈이 아래 이름을 노출한다.
  `get_key_financials`, `get_key_financials_3y`, `get_dividend_info`, `get_dividend_info_3y`, `calculate_financial_ratios`, `get_extended_financials`, `get_extended_financials_3y`, `get_equity_investments`, `get_audit_opinion_3y`, `get_major_shareholder`, `get_employee_status`, `get_capital_changes`, `get_capital_changes_3y`

- [ ] **Step 1: `financials.py` 생성**

`dart_engine.py:365-1010` 전체(`_parse_amount`부터 `get_capital_changes_3y`까지)를 옮긴다. 상수 `_FINANCIALS_URL`(12행), `_DIVIDEND_URL`(13행), 그리고 이 구간이 쓰는 `_DIV_ITEMS` 등 모듈 수준 자료구조를 함께 옮긴다. 파일 머리:

```python
import requests
```

옮긴 뒤 `financials.py` 안에서 정의되지 않은 이름이 남아 있지 않은지 확인한다.

Run: `python -c "import ast,sys;ast.parse(open('financials.py',encoding='utf-8').read());print('parse ok')"`
Expected: `parse ok`

- [ ] **Step 2: `dart_engine.py`에서 해당 블록 제거하고 임포트**

```python
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
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m unittest discover -s tests -v`
Expected: 두 테스트 PASS.

- [ ] **Step 4: 커밋**

```bash
git add financials.py dart_engine.py
git commit -m "refactor: 재무 API 파싱을 financials.py로 분리"
```

---

### Task 6: `dart_viewer.py` 분리와 `dart_engine` shim 완성

**Files:**
- Create: `dart_viewer.py`
- Modify: `dart_engine.py` (shim만 남는다)

**Interfaces:**
- Produces:
  - `dart_viewer.convert_to_html(xml_path, output_path, log_fn=None) -> str`
  - `dart_viewer.DART_CSS` (기존 `_DART_CSS`)
  - `dart_viewer.build_body_html(root, toc) -> str` — Task 13이 주석 링크를 끼워 넣을 지점

- [ ] **Step 1: `dart_viewer.py` 생성**

`dart_engine.py`에 남은 §9 전체(`_esc`, `_DART_CSS`, `_TOC_MAX_LEVEL`, `_DART_DIV`, `_DART_SEC`, `_DART_SKIP`, `_dart_cell_attrs`, `_dart_span_style`, `_toc_entry`, `_dart_elem_to_html`, `_build_toc_html`, `convert_to_html`)를 옮긴다. 파일 머리:

```python
import html as _html_mod
import re
import xml.etree.ElementTree as ET

from xml_fix import BR_SENTINEL, fix_xml
```

`_esc`가 쓰던 `_BR_SENTINEL`을 `BR_SENTINEL`로 바꾼다.

```python
def _esc(text):
    """본문 텍스트 이스케이프. fix_xml이 남긴 줄바꿈 표식은 <br>로 편다."""
    return _html_mod.escape(text).replace(BR_SENTINEL, "<br>")
```

`_DART_CSS`는 공개 별칭을 둔다. `_DART_CSS` 정의 바로 아래에 추가:

```python
DART_CSS = _DART_CSS
```

- [ ] **Step 2: `convert_to_html`에서 본문 생성을 함수로 뽑는다**

Task 13이 이 자리에 후처리를 끼운다. `convert_to_html` 안의

```python
    toc = []
    body_html = _dart_elem_to_html(root, toc=toc)
```

를 다음으로 바꾸고, 모듈에 함수를 추가한다.

```python
def build_body_html(root, toc):
    """DART XML 루트를 본문 HTML로 바꾼다. toc에 제목 목록이 채워진다."""
    return _dart_elem_to_html(root, toc=toc)
```

```python
    toc = []
    body_html = build_body_html(root, toc)
```

- [ ] **Step 3: `dart_engine.py`를 shim으로 축소**

파일 전체를 다음으로 교체한다.

```python
"""이전 이름 호환용 shim.

기능은 dart_client / downloader / financials / dart_viewer / xml_fix 로
옮겨 갔다. scripts/ 아래 도구와 기존 배포본이 `from dart_engine import ...`
를 그대로 쓰고 있어 이 파일이 남아 있다. 새 코드는 각 모듈을 직접 임포트할 것.
"""
from dart_client import (  # noqa: F401
    AUDIT_TYPE,
    list_disclosures,
    load_corp_list,
    search_company,
)
from dart_viewer import convert_to_html  # noqa: F401
from downloader import download_document, safe_filename  # noqa: F401
from financials import (  # noqa: F401
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
from xml_fix import fix_xml  # noqa: F401
```

- [ ] **Step 4: 테스트 실행**

Run: `python -m unittest discover -s tests -v`
Expected: 두 테스트 PASS. 골든 비교가 통과하면 엔진 분리가 무손실이다.

- [ ] **Step 5: scripts 도구가 여전히 임포트되는지 확인**

Run: `python -c "import dart_engine as e; print(len([n for n in dir(e) if not n.startswith('_')]), 'names')"`
Expected: `21 names` 이상

- [ ] **Step 6: 커밋**

```bash
git add dart_viewer.py dart_engine.py
git commit -m "refactor: HTML 변환을 dart_viewer.py로 분리하고 dart_engine을 shim으로 축소"
```

---

### Task 7: `settings.py`와 `ui_theme.py` 분리

**Files:**
- Create: `settings.py`
- Create: `ui_theme.py`
- Modify: `dart_gui.py:29-155`

**Interfaces:**
- Produces:
  - `settings.APP_DIR`, `settings.DEFAULT_DOWNLOADS`, `settings.CORPCODE_PATH`, `settings.CONFIG_PATH`
  - `settings.load_api_key() -> str`, `settings.save_api_key(key) -> None`
  - `ui_theme.apply_theme() -> None`
  - `ui_theme.LISTBOX_STYLE -> dict` — `tk.Listbox`에 넘길 키워드 인자
  - `ui_theme.fmt_val(val) -> str`, `ui_theme.fmt_div_val(val, key) -> str`, `ui_theme.fmt_ratio_val(val) -> str`

- [ ] **Step 1: `settings.py` 생성**

`dart_gui.py:29-75`의 `_APP_DIR` 판별, 경로 상수, `_CONFIG_HEADER`, `load_api_key`, `save_api_key`를 옮기고 이름에서 밑줄을 뗀다.

```python
"""실행 경로와 인증키 저장을 다룬다.

exe로 묶으면 __file__ 은 임시 해제 폴더(_MEIxxxx)를 가리키므로
저장 폴더·CORPCODE 캐시는 실행파일이 놓인 폴더 기준으로 잡는다.
"""
import os
import sys

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_DOWNLOADS = os.path.join(APP_DIR, "downloads")
CORPCODE_PATH = os.path.join(APP_DIR, "CORPCODE.xml")
CONFIG_PATH = os.path.join(APP_DIR, "config.txt")

CONFIG_HEADER = (
    "# DART OpenAPI 인증키 (https://opendart.fss.or.kr 에서 발급)\n"
    "# 이 파일에는 본인 인증키가 들어 있습니다. 공유하거나 git에 올리지 마세요.\n"
)
```

이어서 `load_api_key`, `save_api_key` 본문을 그대로 옮기되 `_CONFIG_PATH` → `CONFIG_PATH`, `_CONFIG_HEADER` → `CONFIG_HEADER`로 바꾼다.

- [ ] **Step 2: `ui_theme.py` 생성**

```python
"""GUI 공통 테마와 표시 포맷."""
import customtkinter as ctk


def apply_theme():
    """앱 시작 때 한 번 부른다."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")


# tk.Listbox는 customtkinter가 감싸주지 않아 색을 직접 맞춘다
LISTBOX_STYLE = {
    "bg": "#2b2b2b",
    "fg": "white",
    "selectbackground": "#1f6aa5",
    "activestyle": "none",
    "relief": "flat",
    "borderwidth": 0,
    "font": ("Consolas", 10),
    "exportselection": False,
}
```

이어서 `dart_gui.py`의 `_fmt_val`(77행), `_fmt_div_val`(95행), `_fmt_ratio_val`(148행)을 본문 그대로 옮기고 이름을 `fmt_val`, `fmt_div_val`, `fmt_ratio_val`로 바꾼다.

- [ ] **Step 3: `dart_gui.py`가 새 모듈을 쓰도록 수정**

29-75행과 77-106행, 148-155행을 지우고 머리에 추가한다.

```python
import settings
import ui_theme
from settings import load_api_key, save_api_key
from ui_theme import fmt_div_val, fmt_ratio_val, fmt_val
```

본문의 `_fmt_val` → `fmt_val`, `_fmt_div_val` → `fmt_div_val`, `_fmt_ratio_val` → `fmt_ratio_val`, `_DEFAULT_DOWNLOADS` → `settings.DEFAULT_DOWNLOADS`, `_CORPCODE_PATH` → `settings.CORPCODE_PATH`로 일괄 치환한다. 모듈 수준의 `ctk.set_appearance_mode`/`set_default_color_theme` 두 줄은 지우고, `DartApp.__init__` 첫 줄 `super().__init__()` 앞에서 `ui_theme.apply_theme()`을 부른다.

`_build_search`의 `tk.Listbox(...)` 인자 중 색·폰트 관련 8개를 `**ui_theme.LISTBOX_STYLE`로 바꾼다.

```python
        self.listbox = tk.Listbox(
            lb_wrap, height=6, selectmode=tk.SINGLE, **ui_theme.LISTBOX_STYLE
        )
```

- [ ] **Step 4: 임포트와 테스트 확인**

Run: `python -c "import dart_gui; print('ok')" && python -m unittest discover -s tests -v`
Expected: `ok` 출력 후 테스트 PASS.

- [ ] **Step 5: GUI를 실제로 띄워 확인**

Run: `python dart_gui.py`
Expected: 창이 뜨고 좌측 검색 리스트박스가 어두운 배경으로 보인다. 확인 후 창을 닫는다.

- [ ] **Step 6: 커밋**

```bash
git add settings.py ui_theme.py dart_gui.py
git commit -m "refactor: 경로·인증키를 settings.py로, 테마·포맷을 ui_theme.py로 분리"
```

---

### Task 8: `download_tab.py` 분리

**Files:**
- Create: `download_tab.py`
- Modify: `dart_gui.py`

**Interfaces:**
- Consumes: `settings.*`, `ui_theme.LISTBOX_STYLE`, `dart_client.*`, `downloader.download_document`, `dart_viewer.convert_to_html`
- Produces: `download_tab.DownloadPanel(parent, app)` — 아래 속성·메서드를 노출한다.
  - `panel.log(msg) -> None` — 로그 상자에 한 줄 추가
  - `panel.api_key_var`, `panel.save_dir_var` — `tk.StringVar`
  - `panel.selected_corp` 는 두지 않는다. 회사 선택은 `app.set_selected_corp(corp)` 로 올린다.

- [ ] **Step 1: `download_tab.py` 생성**

파일 머리 임포트:

```python
import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

import settings
import ui_theme
from dart_client import AUDIT_TYPE, list_disclosures, load_corp_list, search_company
from dart_viewer import convert_to_html
from downloader import download_document
from settings import save_api_key
```

`dart_gui.py`에서 다음을 `DownloadPanel` 클래스로 옮긴다. 각 메서드 본문은 그대로 두고 `self`가 가리키던 `DartApp` 속성만 조정한다.

- `_report_year`, `_report_folder`, `_report_basename` (모듈 수준 함수로 유지)
- `_build_top`, `_build_mid`, `_build_search`, `_build_options`, `_build_log`
- `_save_key`, `_browse_dir`, `_log`, `_do_search`, `_fill_listbox`, `_on_select`, `_do_download`

클래스 골격:

```python
class DownloadPanel:
    """좌측 다운로드 패널. 검색·조회옵션·로그·다운로드를 담는다."""

    def __init__(self, parent, app):
        self.app = app
        self.frame = ctk.CTkFrame(parent)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(2, weight=1)

        self.corp_list = None
        self._search_results = []

        self._build_top(self.frame)
        self._build_mid(self.frame)
        self._build_log(self.frame)

    def log(self, msg):
        """로그 상자에 한 줄 붙인다. 작업 스레드에서 불러도 안전하다."""
        def _upd():
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"[{ts}] {msg}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.app.after(0, _upd)
```

`DartApp`이 아니라 `DownloadPanel`이므로 `self.after(...)`는 모두 `self.app.after(...)`로, `self._log`는 `self.log`로 바꾼다. `_CORPCODE_PATH`는 `settings.CORPCODE_PATH`, `_DEFAULT_DOWNLOADS`는 `settings.DEFAULT_DOWNLOADS`를 쓴다.

`_on_select`(현재 `dart_gui.py:646-673`)는 회사를 고른 뒤 분석 탭 8개를 직접 부르고 있다. 그 부분을 앱에 넘긴다. 기존 꼬리의

```python
        self._update_titles(name)
        self._load_financials()
        self._load_dividends()
        self._load_equity()
        self._load_audit()
        self._load_shareholder()
        self._load_employee()
        self._load_capital()
```

를 다음 한 줄로 바꾼다. `self._analysis_label.configure(...)` 줄도 함께 지운다(분석 패널이 맡는다).

```python
        self.app.set_selected_corp(corp)
```

여기서 `corp`는 기존 `self.selected_corp = self._search_results[sel[0]]` 로 잡던 값이다. 지역 변수로 바꾼다.

```python
        corp = self._search_results[sel[0]]
        name = corp["corp_name"]
        code = corp["corp_code"]
```

- [ ] **Step 2: `dart_gui.py`에서 해당 메서드 제거**

옮긴 메서드와 함수를 지운다. `DartApp._build_ui`의 좌측 조립부를 다음으로 바꾼다.

```python
        self.download_panel = DownloadPanel(self, self)
        self.download_panel.frame.grid(
            row=0, column=0, sticky="nsew", padx=(12, 4), pady=12
        )
```

`DartApp`에 임시로 다음을 둔다(Task 10에서 정리한다).

```python
    def set_selected_corp(self, corp):
        self.selected_corp = corp
        self._update_titles(corp["corp_name"])
```

- [ ] **Step 3: 임포트·테스트·실행 확인**

Run: `python -c "import dart_gui; print('ok')" && python -m unittest discover -s tests -v`
Expected: `ok` 후 테스트 PASS.

Run: `python dart_gui.py`
Expected: 창이 뜬다. 인증키가 채워져 있으면 회사명을 검색해 목록이 나오고, 회사를 고르면 우측 헤더 제목이 그 회사명으로 바뀐다. 확인 후 닫는다.

- [ ] **Step 4: 커밋**

```bash
git add download_tab.py dart_gui.py
git commit -m "refactor: 다운로드 패널을 download_tab.py로 분리"
```

---

### Task 9: `analysis/` 패키지 — 탭 8개 분리

**Files:**
- Create: `analysis/__init__.py`
- Create: `analysis/fin.py`, `analysis/div.py`, `analysis/ratio.py`, `analysis/equity.py`
- Create: `analysis/audit.py`, `analysis/shareholder.py`, `analysis/employee.py`, `analysis/capital.py`
- Modify: `dart_gui.py`

**Interfaces:**
- Produces: 각 탭 모듈이 다음 5개를 노출한다.
  - `TITLE: str` — 탭 이름. `dart_gui.py:74`의 `_ANALYSIS_TABS` 값을 그대로 쓴다
  - `SCOPE: str` — 제목 줄 접미사 규칙. `"3y_fs" | "3y" | "1y"` 중 하나
  - `build(parent, app) -> ctx` — 위젯을 만들고 상태 객체를 돌려준다
  - `load(app, ctx) -> None` — 스레드에서 엔진을 부르고 결과로 `render`를 부른다
  - `render(ctx, state, data=None, **kw) -> None` — `state`는 `"initial" | "loading" | "done" | "error"`

  기존 코드의 상태 문자열 4종을 그대로 쓴다. 새 상태를 만들지 않는다.
- Produces: `analysis.TAB_SPECS -> list[module]` — 탭 표시 순서

`ctx`는 각 모듈이 정하는 상태 보관용 객체다. 최소한 다음 두 속성을 가져야 한다.
- `ctx.title_label` — 제목 줄 `CTkLabel` (`AnalysisPanel`이 회사·연도를 써 넣는다)
- `ctx.content` — 내용이 들어갈 `CTkFrame`

- [ ] **Step 1: 탭 모듈 8개 생성**

`dart_gui.py`의 load/render 쌍을 아래 표대로 옮긴다. 표의 `TITLE`·순서는 `dart_gui.py:74`의 `_ANALYSIS_TABS` 와 정확히 같다. 본문은 그대로 두고, `self._fin_content` 처럼 접근하던 위젯을 `ctx.content` 로, `self._fin_title` 을 `ctx.title_label` 로, 엔진 호출 인자는 `app.download_panel.api_key_var.get()` · `app.selected_corp` · `app.download_panel.end_year_var.get()` 으로 바꾼다. `self.after(...)` 는 `app.after(...)` 로 바꾼다.

| 순서 | 모듈 | TITLE | SCOPE | 옮길 메서드 (현재 dart_gui.py 행) |
|---|---|---|---|---|
| 1 | `analysis/fin.py` | 핵심재무 | `3y_fs` | `_render_fin` (507), `_load_financials` (694) |
| 2 | `analysis/div.py` | 배당 | `3y` | `_render_div` (735), `_load_dividends` (781) |
| 3 | `analysis/equity.py` | 타법인출자 | `1y` | `_render_equity` (848), `_load_equity` (923) |
| 4 | `analysis/ratio.py` | 재무지표 | `3y_fs` | `_render_ratio` (799) |
| 5 | `analysis/audit.py` | 감사 | `3y` | `_load_audit` (945), `_render_audit` (964) |
| 6 | `analysis/shareholder.py` | 최대주주 | `1y` | `_load_shareholder` (1027), `_render_shareholder` (1048) |
| 7 | `analysis/employee.py` | 직원 | `1y` | `_load_employee` (1117), `_render_employee` (1136) |
| 8 | `analysis/capital.py` | 자본변동 | `3y` | `_load_capital` (1220), `_render_capital` (1239) |

`SCOPE`는 현재 `_update_titles`(679행)가 탭마다 다르게 쓰던 접미사를 그대로 옮긴 것이다.
- `3y_fs` → `{name} · {yr-2}~{yr}년 · {연결(CFS)|별도(OFS)}`
- `3y` → `{name} · {yr-2}~{yr}년`
- `1y` → `{name} · {yr}년`

`analysis/ratio.py`는 별도 `load`가 없다. `_render_ratio`(799행)는 `핵심재무` 탭이 받아 둔 데이터로 계산한다. 다음 서명을 지킨다.

```python
TITLE = "재무지표"
SCOPE = "3y_fs"


def load(app, ctx):
    """핵심재무 탭이 받아 둔 데이터로 계산한다. 아직 없으면 대기 상태로 둔다."""
    if app.fin_data is None:
        render(ctx, "initial")
        return
    render(ctx, "done", calculate_financial_ratios(app.fin_data))
```

`app.fin_data`는 기존 `DartApp._fin_data`(166행)가 하던 역할이다. `analysis/fin.py`의 `load`가 성공하면 `app.fin_data = data` 로 채우고, 이어서 `ratio.load(app, app.ctx_of(ratio))` 를 부른다. 현재 코드에서 `_render_ratio` 를 부르던 자리와 같은 지점이다.

- [ ] **Step 2: `analysis/__init__.py` 생성**

```python
"""분석 탭 모듈 모음.

각 모듈은 TITLE / SCOPE / build(parent, app) / load(app, ctx) /
render(ctx, state, ...) 만 노출한다. 탭을 더하거나 뺄 때는 이 목록만 고친다.
순서는 dart_gui.py 의 _ANALYSIS_TABS 와 같다.
"""
from analysis import (
    audit,
    capital,
    div,
    employee,
    equity,
    fin,
    ratio,
    shareholder,
)

TAB_SPECS = [fin, div, equity, ratio, audit, shareholder, employee, capital]
```

- [ ] **Step 3: 임포트와 순서 확인**

Run: `python -c "import analysis; print([m.TITLE for m in analysis.TAB_SPECS])"`
Expected: `['핵심재무', '배당', '타법인출자', '재무지표', '감사', '최대주주', '직원', '자본변동']`

Run: `python -c "import analysis; print([m.SCOPE for m in analysis.TAB_SPECS])"`
Expected: `['3y_fs', '3y', '1y', '3y_fs', '3y', '1y', '1y', '3y']`

- [ ] **Step 4: 커밋**

```bash
git add analysis
git commit -m "refactor: 분석 탭 8개를 analysis/ 패키지로 분리"
```

---

### Task 10: `analysis_tab.py`와 `app.py`

**Files:**
- Create: `analysis_tab.py`
- Create: `app.py`
- Modify: `dart_gui.py` (shim만 남는다)
- Modify: `dart_downloader.spec:12`
- Modify: `DART다운로더_실행.bat:11`

**Interfaces:**
- Consumes: `analysis.TAB_SPECS`, `download_tab.DownloadPanel`
- Produces:
  - `analysis_tab.AnalysisPanel(parent, app)` — `panel.frame`, `panel.set_corp(corp)`, `panel.refresh_titles()`, `panel.ctx_of(module)`
  - `app.DartApp`, `app.main()`, `app.fin_data`, `app.ctx_of(module)`

- [ ] **Step 1: `analysis_tab.py` 생성**

`dart_gui.py`의 `_build_analysis`(340), `_on_fs_toggle`(674), `_update_titles`(679)를 옮긴다. 탭 조립은 하드코딩된 8벌 대신 `TAB_SPECS` 순회로 바꾸고, 제목 8줄을 개별로 쓰던 `_update_titles`는 `SCOPE` 기반 한 곳으로 합친다.

```python
class AnalysisPanel:
    """우측 분석 패널. 회사·연결별도 상태를 들고 탭에 뿌린다."""

    def __init__(self, parent, app):
        self.app = app
        self.frame = ctk.CTkFrame(parent)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=0)
        self.frame.grid_rowconfigure(1, weight=1)

        self._build_header(self.frame)

        self.tabview = ctk.CTkTabview(self.frame)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))

        self._ctx = {}
        for module in TAB_SPECS:
            tab_frame = self.tabview.add(module.TITLE)
            tab_frame.grid_columnconfigure(0, weight=1)
            tab_frame.grid_rowconfigure(1, weight=1)
            self._ctx[module] = module.build(tab_frame, self.app)
            module.render(self._ctx[module], "initial")

    def ctx_of(self, module):
        return self._ctx[module]

    @property
    def fs_mode(self):
        return self.fs_seg.get()          # "연결" 또는 "별도"

    def set_corp(self, corp):
        """회사가 바뀌면 제목을 고치고 탭을 전부 다시 읽는다."""
        self._analysis_label.configure(text=corp["corp_name"])
        self.refresh_titles()
        for module in TAB_SPECS:
            module.load(self.app, self._ctx[module])

    def refresh_titles(self):
        """SCOPE 규칙에 따라 각 탭 제목 줄을 다시 쓴다."""
        corp = self.app.selected_corp
        name = corp["corp_name"] if corp else ""
        yr = int(self.app.download_panel.end_year_var.get()) - 1
        rng = f"{yr-2}~{yr}년"
        fs_label = "연결(CFS)" if self.fs_mode == "연결" else "별도(OFS)"
        suffix = {
            "3y_fs": f"{rng} · {fs_label}",
            "3y": rng,
            "1y": f"{yr}년",
        }
        for module in TAB_SPECS:
            text = f"{name} · {suffix[module.SCOPE]}"
            self._ctx[module].title_label.configure(text=text)

    def _on_fs_toggle(self, _value):
        """연결/별도를 바꾸면 제목과 연결별도에 걸린 탭만 다시 읽는다."""
        if not self.app.selected_corp:
            return
        self.refresh_titles()
        fin_ctx = self._ctx[fin]
        fin.load(self.app, fin_ctx)
```

`_build_header`는 기존 `_build_analysis`의 헤더 부분(342-359행)을 그대로 쓴다. `self._analysis_label`과 `self.fs_seg`를 이 메서드가 만든다. `fs_seg`의 `command=`는 `self._on_fs_toggle`을 가리킨다.

파일 머리 임포트:

```python
import customtkinter as ctk

from analysis import TAB_SPECS, fin
```

- [ ] **Step 2: `app.py` 생성**

```python
"""DART 공시 다운로더 진입점."""
import customtkinter as ctk

import ui_theme
from analysis_tab import AnalysisPanel
from download_tab import DownloadPanel


class DartApp(ctk.CTk):
    def __init__(self):
        ui_theme.apply_theme()
        super().__init__()
        self.title("DART 공시 다운로더")
        self.geometry("1300x720")
        self.minsize(1000, 580)

        self.selected_corp = None
        self.fin_data = None          # 재무지표 탭이 받아 둔 데이터. 재무비율이 재사용

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.download_panel = DownloadPanel(self, self)
        self.download_panel.frame.grid(
            row=0, column=0, sticky="nsew", padx=(12, 4), pady=12
        )

        self.analysis_panel = AnalysisPanel(self, self)
        self.analysis_panel.frame.grid(
            row=0, column=1, sticky="nsew", padx=(4, 12), pady=12
        )

    def set_selected_corp(self, corp):
        """다운로드 패널이 회사를 고르면 분석 패널에 알린다."""
        self.selected_corp = corp
        self.fin_data = None
        self.analysis_panel.set_corp(corp)

    def ctx_of(self, module):
        """탭 모듈이 다른 탭의 상태 객체를 집어야 할 때 쓴다 (핵심재무 → 재무지표)."""
        return self.analysis_panel.ctx_of(module)


def main():
    DartApp().mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: `dart_gui.py`를 shim으로 축소**

```python
"""이전 이름 호환용 shim.

GUI는 app.py 로 옮겨 갔다. 기존 배포본의 실행 런처가 이 파일을 가리키고
있어 남아 있다. 새 코드는 app.main() 을 직접 부를 것.
"""
from app import DartApp, main  # noqa: F401

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 진입점 갱신**

`dart_downloader.spec:12`

```python
    ['app.py'],
```

`DART다운로더_실행.bat:11`

```
start "" pythonw "%~dp0app.py"
```

- [ ] **Step 5: GUI 전체 동작 확인**

Run: `python app.py`
Expected: 창이 뜬다. 회사를 검색해 고르고, 분석 탭 8개를 차례로 눌러 각 탭이 리팩터링 전과 같은 내용을 그리는지 본다. 연결/별도 토글도 눌러 본다. 확인 후 닫는다.

Run: `python dart_gui.py`
Expected: 같은 창이 뜬다(shim 확인). 확인 후 닫는다.

- [ ] **Step 6: 테스트 실행**

Run: `python -m unittest discover -s tests -v`
Expected: 두 테스트 PASS.

- [ ] **Step 7: 커밋**

```bash
git add analysis_tab.py app.py dart_gui.py dart_downloader.spec "DART다운로더_실행.bat"
git commit -m "refactor: 분석 패널과 진입점을 analysis_tab.py·app.py로 분리"
```

---

### Task 11: 목차 링크 즉시 점프

**Files:**
- Modify: `dart_viewer.py` (`_DART_CSS` 안)
- Test: `tests/test_convert_regression.py` (기준선 갱신)

**Interfaces:** 없음 (CSS만 바뀐다)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_viewer_css.py` 를 만든다.

```python
"""읽기용 HTML의 이동 동작을 지킨다."""
import os
import unittest

import dart_viewer

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
OUT = os.path.join(HERE, "_out")


class ViewerCssTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(OUT, exist_ok=True)
        out_path = os.path.join(OUT, "css_check.html")
        dart_viewer.convert_to_html(
            os.path.join(FIXTURES, "annual_report.xml"), out_path
        )
        with open(out_path, encoding="utf-8") as f:
            cls.html = f.read()

    def test_no_smooth_scroll(self):
        """긴 보고서에서 부드러운 스크롤은 수천 줄을 훑고 지나가 눈이 아프다."""
        self.assertNotIn("scroll-behavior: smooth", self.html)

    def test_headings_have_scroll_margin(self):
        """점프 후 제목이 뷰포트 최상단에 붙지 않게 여백을 둔다."""
        self.assertIn("scroll-margin-top", self.html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인**

Run: `python -m unittest tests.test_viewer_css -v`
Expected: `test_no_smooth_scroll` 이 FAIL ("scroll-behavior: smooth" 가 들어 있음). `test_headings_have_scroll_margin` 은 PASS(기존 `:target` 규칙에 이미 있음).

- [ ] **Step 3: CSS 수정**

`dart_viewer.py`의 `_DART_CSS` 안에서 다음 줄을 찾는다.

```css
html { scroll-behavior: smooth; }
```

지우고, 같은 블록의 `:target` 규칙을 찾아

```css
:target { background: #fef9c3; scroll-margin-top: 16px; }
```

다음으로 바꾼다.

```css
/* 목차·주석 링크는 애니메이션 없이 즉시 이동한다.
   긴 사업보고서에서 부드러운 스크롤은 수천 줄을 훑고 지나가 눈이 아프다. */
h1, h2, h3, h4, h5, p[id] { scroll-margin-top: 16px; }
:target { background: #fef9c3; }
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인**

Run: `python -m unittest tests.test_viewer_css -v`
Expected: 두 테스트 모두 PASS.

- [ ] **Step 5: 골든 기준선 갱신**

CSS가 의도적으로 바뀌었으므로 기준선을 다시 뜬다.

```bash
rm tests/golden/annual_report.html tests/golden/audit_report.html
python -m unittest discover -s tests -v
python -m unittest discover -s tests -v
```

Expected: 첫 실행에서 회귀 테스트가 skip, 둘째 실행에서 PASS.

- [ ] **Step 6: 브라우저에서 눈으로 확인**

Run: `python -c "import os,webbrowser;webbrowser.open('file:///'+os.path.abspath('downloads/STX/사업보고서_2025/20260323001638_읽기용.html').replace(os.sep,'/'))"`

주의: `downloads/` 아래 기존 HTML은 목차 기능 추가 이전에 생성된 구버전이라 목차가 없을 수 있다. 목차가 없으면 GUI에서 아무 회사나 사업보고서를 새로 한 건 받아 그 HTML로 확인한다.

Expected: 목차 항목을 누르면 애니메이션 없이 바로 이동하고, 대상 제목이 화면 최상단에서 조금 아래에 노란 배경으로 표시된다.

- [ ] **Step 7: 커밋**

```bash
git add dart_viewer.py tests/test_viewer_css.py tests/golden
git commit -m "fix: 목차 링크를 부드러운 스크롤 대신 즉시 점프로"
```

---

### Task 12: `note_links.py` 구현

주석 참조를 링크로 바꾸는 순수 문자열 후처리다. 이 Task는 모듈만 만들고, 변환 경로 연결은 Task 13에서 한다.

**Files:**
- Create: `note_links.py`
- Create: `tests/test_note_links.py`

**Interfaces:**
- Produces:
  - `note_links.add_note_links(body_html) -> str`
  - `note_links.NREF_CLASS -> str` (`"nref"`) — Task 13의 CSS가 이 이름을 쓴다

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_note_links.py`.

```python
"""주석 참조 링크의 동작을 지킨다.

픽스처는 실제 DART 문서에서 확인한 표기 변형을 담고 있다.
사업보고서는 연결·별도 2세트라 같은 번호가 서로 다른 곳을 가리킨다.
"""
import os
import re
import unittest
import xml.etree.ElementTree as ET

import dart_viewer
import note_links
from xml_fix import fix_xml

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
OUT = os.path.join(HERE, "_out")

LINK = re.compile(r'<a class="nref" href="#([^"]+)">(\d+)</a>')
ANY_ID = re.compile(r'id="([^"]+)"')


def _body(name):
    """링크를 붙이기 전의 순수 본문 HTML.

    변환 결과 파일을 읽지 않고 본문 생성 단계를 직접 부른다. Task 13에서
    convert_to_html이 링크를 붙이기 시작해도 이 테스트가 이중으로
    적용하지 않는다.
    """
    with open(os.path.join(FIXTURES, name + ".xml"), encoding="utf-8") as f:
        root = ET.fromstring(fix_xml(f.read()).encode("utf-8"))
    return dart_viewer.build_body_html(root, [])


class NoteLinkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.annual = note_links.add_note_links(_body("annual_report"))
        cls.audit = note_links.add_note_links(_body("audit_report"))

    def _links(self, html):
        return LINK.findall(html)

    def test_every_link_target_exists(self):
        """href가 가리키는 id가 문서에 실제로 있어야 한다."""
        for name, html in (("annual", self.annual), ("audit", self.audit)):
            with self.subTest(doc=name):
                ids = set(ANY_ID.findall(html))
                broken = [t for t, _ in self._links(html) if t not in ids]
                self.assertEqual([], broken, f"깨진 앵커: {broken}")

    def test_consolidated_and_separate_sets_differ(self):
        """연결 재무상태표의 주석3과 별도 재무상태표의 주석3은 다른 곳으로 간다."""
        rows = re.findall(r"재고자산\(주석(.*?)\)", self.annual)
        self.assertEqual(2, len(rows), "재고자산 행 2개를 찾지 못했다")
        first = LINK.findall(rows[0])
        second = LINK.findall(rows[1])
        self.assertTrue(first and second)
        self.assertNotEqual(first[0][0], second[0][0],
                            "연결·별도가 같은 앵커로 갔다")

    def test_comma_separated_numbers_each_linked(self):
        """(주석3,4)는 링크 2개가 된다."""
        m = re.search(r"현금및현금성자산\(주석(.*?)\)", self.audit)
        self.assertIsNotNone(m)
        self.assertEqual(2, len(LINK.findall(m.group(1))))

    def test_merged_title_registers_both_numbers(self):
        """'4. 종속기업의 현황 5. 관계기업…' 제목은 4번과 5번을 함께 등록한다."""
        m = re.search(r"주석(.*?)에서 설명하고", self.annual)
        self.assertIsNotNone(m)
        self.assertEqual(2, len(LINK.findall(m.group(1))))

    def test_mid_paragraph_note_is_anchored(self):
        """감사보고서의 17번은 문단 중간에서 시작하지만 앵커가 붙어야 한다."""
        m = re.search(r"급여\(주석(.*?)\)", self.audit)
        self.assertIsNotNone(m)
        self.assertEqual(1, len(LINK.findall(m.group(1))))

    def test_unknown_number_left_alone(self):
        """없는 번호는 링크하지 않고 원문 그대로 둔다."""
        self.assertIn("(주석 77 참조)", self.annual)

    def test_prose_mention_not_linked(self):
        """'주석의 2. 재무제표 작성기준'처럼 번호가 바로 붙지 않으면 건드리지 않는다."""
        self.assertIn("재무제표 주석의 2. 재무제표 작성기준", self.annual)

    def test_sub_items_not_registered_as_notes(self):
        """'(11)'·'1)'로 시작하는 하위 항목은 주석 항목이 아니다."""
        self.assertNotIn('id="nt0_11"', self.audit)

    def test_tags_not_corrupted(self):
        """링크가 태그 속성 안으로 들어가면 안 된다."""
        for name, html in (("annual", self.annual), ("audit", self.audit)):
            with self.subTest(doc=name):
                self.assertEqual([], re.findall(r"<[a-z][^>]*<a class", html))

    def test_no_note_set_returns_input_unchanged(self):
        """주석이 없는 문서는 그대로 돌려준다."""
        plain = "<p>주석이 없는 문서입니다.</p>"
        self.assertEqual(plain, note_links.add_note_links(plain))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인**

Run: `python -m unittest tests.test_note_links -v`
Expected: `ModuleNotFoundError: No module named 'note_links'`

- [ ] **Step 3: `note_links.py` 구현**

아래 내용을 그대로 쓴다. 실제 사업보고서·감사보고서 2종에 대해 검증한 코드다.

```python
"""읽기용 HTML 본문의 주석 참조(주석 12)를 해당 주석 본문으로 링크한다.

DART 문서는 주석 세트를 여러 벌 담을 수 있다. 사업보고서는 연결·별도
2벌이고 같은 내용이 서로 다른 번호를 쓴다(연결 16번 = 별도 15번). 그래서
참조가 놓인 위치가 어느 세트 안인지 보고 번호를 풀어야 한다.
"""
import re

# 주석 세트를 여는 제목. '주석'으로 끝난다.
#   3. 연결재무제표 주석 / 5. 재무제표 주석 / 주석
_SET_TITLE = re.compile(r"주석\s*$")

# 제목 안의 주석 번호. 제목 머리 또는 공백 뒤에 온다.
# DART는 두 주석을 한 제목에 합치기도 한다 — '4. 종속기업의 현황 5. 관계기업…'
_TITLE_NO = re.compile(r"(?:^|\s)(\d{1,2})(?:-\d+)?\s*\.")

# 문단 머리의 주석 번호. 여는 괄호를 허용하지 않으므로
# '(11) 자산손상'·'1) 리스제공자'는 걸리지 않는다.
_PARA_NO = re.compile(r"^\s*(\d{1,2})(?:-\d+)?\s*\.")

# 문단 중간에서 시작하는 주석. DART가 논리 문단을 한 <p>에 뭉쳐 넣는다 —
# '…희석주당손익은 동일합니다.17. 부가가치 관련자료…'
# 뒤에 숫자가 오면 '3.5배' 같은 소수라 제외한다.
_PARA_NO_MID = re.compile(r"(?<=다\.)(\d{1,2})\.\s*(?=[^\d\s])")

# 본문 참조. '주석' 바로 뒤에 숫자가 와야 한다.
#   (주석3,4) / 주석 4, 5 / 주석 17 및 28 / 주석30
_REF = re.compile(r"주석\s*(\d{1,2}(?:\s*[,및·]\s*\d{1,2})*)")
_REF_NUM = re.compile(r"\d{1,2}")

# 블록 요소. 제목은 세트 경계와 항목을, 문단은 감사보고서식 항목을 준다.
_BLOCK = re.compile(r"<(h([1-5])|p)\b([^>]*)>(.*?)</\1>", re.S)
_TAG = re.compile(r"<[^>]*>")
_TABLE = re.compile(r"<table\b.*?</table>", re.S)
_ID_ATTR = re.compile(r'\bid="([^"]*)"')

NREF_CLASS = "nref"


def _text_of(inner_html):
    """블록 안쪽 HTML에서 눈에 보이는 텍스트만 뽑아 공백을 정리한다."""
    return " ".join(_TAG.sub(" ", inner_html).split())


def _table_spans(html):
    return [m.span() for m in _TABLE.finditer(html)]


def _in_spans(pos, spans):
    return any(s <= pos < e for s, e in spans)


class _NoteSet:
    __slots__ = ("index", "title", "level", "start", "end", "items", "pending")

    def __init__(self, index, title, level, start):
        self.index = index
        self.title = title
        self.level = level
        self.start = start        # 세트를 연 제목이 끝난 위치
        self.end = None           # 세트가 닫힌 위치. None이면 문서 끝까지
        self.items = {}           # {주석번호: 앵커 id}
        self.pending = []         # 앵커를 새로 달아야 하는 [(번호, 삽입위치)]

    @property
    def is_consolidated(self):
        return "연결" in self.title

    @property
    def numbers(self):
        return set(self.items) | {no for no, _ in self.pending}

    def contains(self, pos):
        return self.start <= pos and (self.end is None or pos < self.end)


def _index_sets(html):
    """제목만 훑어 주석 세트 경계와 제목형 항목을 잡는다."""
    sets = []
    cur = None
    last_no = 0

    for m in _BLOCK.finditer(html):
        tag, level_s = m.group(1), m.group(2)
        if not level_s:                      # <p>는 여기서 다루지 않는다
            continue
        level = int(level_s)
        text = _text_of(m.group(4))
        if not text:
            continue

        if _SET_TITLE.search(text):
            cur = _NoteSet(len(sets), text, level, m.end())
            sets.append(cur)
            last_no = 0
            continue

        if cur is None:
            continue

        # 세트를 연 제목보다 상위 제목이 나오면 세트가 끝난다
        if level < cur.level:
            cur.end = m.start()
            cur = None
            continue

        nos = [int(x) for x in _TITLE_NO.findall(text)]
        if not nos:
            continue

        # 번호가 역행하면 새 장이 시작된 것이다 (…32. 다음의 '4. 재무제표')
        if nos[0] < last_no:
            cur.end = m.start()
            cur = None
            continue

        anchor = _ID_ATTR.search(m.group(3) or "")
        known = cur.numbers
        for no in nos:
            if no < last_no or no in known:
                continue
            last_no = no
            if anchor:
                cur.items[no] = anchor.group(1)
            else:
                cur.pending.append((no, m.start() + 1 + len(tag)))

    return sets


def _index_paragraph_items(html, note_set):
    """제목형 항목이 없는 세트(감사보고서)에서 문단형 항목을 잡는다."""
    tables = _table_spans(html)
    last_no = 0
    for m in _BLOCK.finditer(html):
        if m.group(2):                        # 제목은 건너뛴다
            continue
        if not note_set.contains(m.start()):
            continue
        if _in_spans(m.start(), tables):      # 표 안 문단은 항목이 아니다
            continue
        text = _text_of(m.group(4))
        nos = [int(x) for x in _PARA_NO.findall(text)]
        nos += [int(x) for x in _PARA_NO_MID.findall(text)]
        known = note_set.numbers
        for no in sorted(nos):
            if no < last_no or no in known:
                continue
            last_no = no
            note_set.pending.append((no, m.start() + 2))   # '<p' 다음


def _heading_marks(html):
    """(제목 시작위치, 제목 텍스트) 목록. 세트 밖 참조의 소속 판별에 쓴다."""
    marks = []
    for m in _BLOCK.finditer(html):
        if m.group(2):
            marks.append((m.start(), _text_of(m.group(4))))
    return marks


def _preceding_heading(marks, pos):
    lo, hi = 0, len(marks)
    while lo < hi:
        mid = (lo + hi) // 2
        if marks[mid][0] < pos:
            lo = mid + 1
        else:
            hi = mid
    return marks[lo - 1][1] if lo else ""


def _resolve_set(sets, marks, pos, before_text):
    """
    참조 위치가 속한 세트를 찾는다.

    세트 밖(감사의견·재무상태표 등)이면 '연결' 단서로 가른다. 바로 앞
    문장을 먼저 보고, 없으면 직전 제목을 본다. 표 둘째 행처럼 문장 안에
    단서가 없는 자리는 '2-1. 연결 재무상태표' 같은 제목이 잡아 준다.
    """
    for s in sets:
        if s.contains(pos):
            return s
    want_con = "연결" in before_text or "연결" in _preceding_heading(marks, pos)
    for s in sets:
        if s.is_consolidated == want_con:
            return s
    return sets[0]


def _text_segments(html):
    """태그 바깥 텍스트 구간 [(start, end), …]. 속성값은 건드리지 않는다."""
    segs = []
    prev = 0
    for m in _TAG.finditer(html):
        if m.start() > prev:
            segs.append((prev, m.start()))
        prev = m.end()
    if prev < len(html):
        segs.append((prev, len(html)))
    return segs


def _collect_ref_edits(html, sets):
    edits = []
    marks = _heading_marks(html)
    for seg_start, seg_end in _text_segments(html):
        seg = html[seg_start:seg_end]
        for m in _REF.finditer(seg):
            abs_start = seg_start + m.start()
            before = html[max(0, abs_start - 60):abs_start]
            note_set = _resolve_set(sets, marks, abs_start, before)
            nums_start = seg_start + m.start(1)
            for nm in _REF_NUM.finditer(m.group(1)):
                anchor = note_set.items.get(int(nm.group()))
                if not anchor:
                    continue
                edits.append((nums_start + nm.start(), nums_start + nm.end(),
                              f'<a class="{NREF_CLASS}" href="#{anchor}">'
                              f'{nm.group()}</a>'))
    return edits


def _apply(html, edits):
    """(시작, 끝, 대체문자열) 목록을 한 번에 적용한다. 겹치면 뒤엣것을 버린다."""
    out = []
    prev = 0
    for s, e, rep in sorted(edits):
        if s < prev:
            continue
        out.append(html[prev:s])
        out.append(rep)
        prev = e
    out.append(html[prev:])
    return "".join(out)


def add_note_links(body_html):
    """본문 HTML에 주석 앵커를 심고 참조를 링크해 돌려준다."""
    sets = _index_sets(body_html)
    if not sets:
        return body_html

    for s in sets:
        if not s.numbers:
            _index_paragraph_items(body_html, s)

    edits = []
    for s in sets:
        for no, pos in s.pending:
            anchor = f"nt{s.index}_{no}"
            s.items[no] = anchor
            edits.append((pos, pos, f' id="{anchor}"'))

    if not any(s.items for s in sets):
        return body_html

    edits.extend(_collect_ref_edits(body_html, sets))
    return _apply(body_html, edits)
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인**

Run: `python -m unittest tests.test_note_links -v`
Expected: 10개 테스트 모두 PASS.

- [ ] **Step 5: 커밋**

```bash
git add note_links.py tests/test_note_links.py
git commit -m "feat: 주석 참조를 주석 본문으로 잇는 note_links 모듈"
```

---

### Task 13: 주석 링크를 변환 경로에 연결

**Files:**
- Modify: `dart_viewer.py` (`convert_to_html`, `_DART_CSS`)
- Modify: `README.md`
- Test: `tests/test_note_links.py` (기존), `tests/test_convert_regression.py` (기준선 갱신)

**Interfaces:**
- Consumes: `note_links.add_note_links(body_html) -> str`, `note_links.NREF_CLASS`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/test_note_links.py` 끝의 `if __name__` 앞에 클래스를 하나 더 넣는다.

```python
class ConvertIntegrationTest(unittest.TestCase):
    """convert_to_html이 만든 최종 파일에 주석 링크가 들어 있어야 한다."""

    def test_converted_file_has_note_links(self):
        os.makedirs(OUT, exist_ok=True)
        out_path = os.path.join(OUT, "integration.html")
        dart_viewer.convert_to_html(
            os.path.join(FIXTURES, "audit_report.xml"), out_path
        )
        with open(out_path, encoding="utf-8") as f:
            html = f.read()
        self.assertTrue(LINK.search(html), "주석 링크가 없다")
        self.assertIn(".nref", html, "주석 링크 스타일이 없다")

    def test_toc_links_are_not_touched(self):
        """목차 사이드바의 링크는 주석 링크로 오인되면 안 된다."""
        os.makedirs(OUT, exist_ok=True)
        out_path = os.path.join(OUT, "integration_toc.html")
        dart_viewer.convert_to_html(
            os.path.join(FIXTURES, "annual_report.xml"), out_path
        )
        with open(out_path, encoding="utf-8") as f:
            html = f.read()
        nav = re.search(r"<nav class=\"toc\">.*?</nav>", html, re.S)
        self.assertIsNotNone(nav, "목차가 없다")
        self.assertNotIn('class="nref"', nav.group(0))
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인**

Run: `python -m unittest tests.test_note_links.ConvertIntegrationTest -v`
Expected: `test_converted_file_has_note_links` 가 FAIL ("주석 링크가 없다").

- [ ] **Step 3: `convert_to_html`에 후처리를 끼운다**

`dart_viewer.py` 머리에 임포트를 더한다.

```python
import note_links
```

`convert_to_html` 안의

```python
    toc = []
    body_html = build_body_html(root, toc)
```

를 다음으로 바꾼다. 후처리가 터져도 변환 자체는 살아야 한다.

```python
    toc = []
    body_html = build_body_html(root, toc)

    try:
        body_html = note_links.add_note_links(body_html)
    except Exception as e:                      # noqa: BLE001
        log(f"주석 링크 생략 (원인: {e})")
```

주석 링크는 목차 사이드바를 만들기 **전에** 본문에만 적용된다. `toc_html`은 그 뒤에 붙으므로 목차 링크가 오염되지 않는다.

- [ ] **Step 4: CSS에 주석 링크 스타일 추가**

`dart_viewer.py`의 `_DART_CSS` 안, `:target` 규칙 아래에 넣는다.

```css
/* ── 주석 참조 링크 ────────────────────────────────────────── */
a.nref { color: #2563eb; text-decoration: none;
         border-bottom: 1px dotted #93c5fd; }
a.nref:hover { background: #eff6ff; border-bottom-color: #2563eb; }
@media print { a.nref { color: inherit; border-bottom: none; } }
```

- [ ] **Step 5: 테스트를 돌려 통과를 확인**

Run: `python -m unittest tests.test_note_links -v`
Expected: 12개 테스트 모두 PASS.

- [ ] **Step 6: 골든 기준선 갱신**

```bash
rm tests/golden/annual_report.html tests/golden/audit_report.html
python -m unittest discover -s tests -v
python -m unittest discover -s tests -v
```

Expected: 첫 실행에서 회귀 테스트가 skip, 둘째 실행에서 전체 PASS.

- [ ] **Step 7: 실제 문서로 눈으로 확인**

`python app.py` 를 띄워 비상장 외감법인(예: 범한유니솔루션) 감사보고서와 상장사(예: STX) 사업보고서를 각각 한 건씩 새로 받는다. 생성된 읽기용 HTML을 브라우저로 열어 확인한다.

Expected:
- 재무상태표의 `재고자산(주석3,4)` 에서 `3`·`4` 가 각각 점선 밑줄 링크로 보인다.
- 링크를 누르면 애니메이션 없이 해당 주석으로 즉시 이동하고, 도착 지점이 노란 배경으로 표시된다.
- 사업보고서에서 연결재무제표 쪽 `주석 16` 과 별도재무제표 쪽 `주석 15` 가 서로 다른 주석으로 간다.
- 목차 사이드바의 링크에는 점선 밑줄이 생기지 않았다.

- [ ] **Step 8: README 갱신**

`README.md`에서 파일 구조를 설명하는 절을 찾아 새 모듈 트리로 바꾼다. 없으면 "설치" 절 앞에 추가한다.

```markdown
## 파일 구조

| 파일 | 역할 |
|---|---|
| `app.py` | 진입점. 창 셸과 공유 상태 |
| `settings.py` | 실행 경로·인증키 저장 |
| `ui_theme.py` | 테마·공통 위젯 스타일·표시 포맷 |
| `download_tab.py` | 좌측 다운로드 패널 (검색·조회옵션·로그) |
| `analysis_tab.py` | 우측 분석 패널 (탭 컨테이너·연결/별도 토글) |
| `analysis/` | 분석 탭 8개 (재무지표·재무비율·배당·타법인출자·감사의견·주주현황·직원현황·자본변동) |
| `dart_client.py` | CORPCODE 로드·회사 검색·공시 목록 조회 |
| `downloader.py` | 문서 다운로드·압축해제·파일명 정리 |
| `financials.py` | 재무 API 파싱·3개년 집계·비율 계산 |
| `dart_viewer.py` | DART XML → 읽기용 HTML (목차 포함) |
| `note_links.py` | 주석 참조를 주석 본문으로 잇는 링크 생성 |
| `xml_fix.py` | DART 비표준 XML 보정 |
| `dart_engine.py`, `dart_gui.py` | 이전 이름 호환용 shim |

`scripts/` 아래 단계별 도구는 `dart_engine` shim을 통해 그대로 동작한다.
```

읽기용 HTML 기능을 소개하는 부분이 있으면 다음을 덧붙인다.

```markdown
- 좌측 목차와 본문의 주석 참조(`(주석3,4)`)를 누르면 해당 위치로 즉시 이동합니다.
  사업보고서처럼 연결·별도 주석이 따로 있는 문서는 참조가 놓인 재무제표에 맞는
  주석으로 갑니다.
```

- [ ] **Step 9: 전체 테스트 실행**

Run: `python -m unittest discover -s tests -v`
Expected: 전체 PASS.

- [ ] **Step 10: 커밋**

```bash
git add dart_viewer.py tests README.md
git commit -m "feat: 읽기용 HTML의 주석 참조를 클릭 가능한 링크로"
```

---

## 완료 확인

- [ ] `python -m unittest discover -s tests -v` 전체 PASS
- [ ] `python app.py` 로 창이 뜨고 검색·다운로드·분석 탭 8개가 모두 동작
- [ ] `python dart_gui.py` 로도 같은 창이 뜬다 (shim)
- [ ] `python -c "import dart_engine as e; [getattr(e, n) for n in ['load_corp_list','convert_to_html','fix_xml','AUDIT_TYPE']]"` 무오류
- [ ] 새로 받은 사업보고서 HTML에서 목차 클릭이 즉시 이동, 주석 참조 클릭이 올바른 세트로 이동
- [ ] 줄 수를 확인한다

  Run: `python -c "import glob;[print('%5d %s'%(len(open(f,encoding='utf-8').readlines()),f)) for f in sorted(glob.glob('*.py')+glob.glob('analysis/*.py'))]"`

  기대: `dart_gui.py`·`dart_engine.py`가 각각 10줄 안팎의 shim으로 줄어 있다. GUI 쪽 파일과 탭 모듈은 300줄 안쪽이다. `financials.py`는 OpenDART 응답 파서 13개가 모여 있어 600줄대가 정상이다 — 더 쪼개려면 API 그룹별 분리가 필요한데 이번 범위 밖이다.
