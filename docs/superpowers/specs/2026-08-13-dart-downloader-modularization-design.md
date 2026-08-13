# DART 다운로더 모듈화 + 뷰어 네비게이션 개선 설계

작성일: 2026-08-13

## 배경

현재 프로젝트는 두 개의 모놀리식 파일로 되어 있다.

- `dart_gui.py` — 1,419줄. customtkinter GUI 전체(다운로드 패널 + 분석 탭 8개).
- `dart_engine.py` — 1,429줄. OpenDART API 클라이언트, 문서 다운로더, 재무 파싱, XML→HTML 변환, XML 보정.

참고 프로젝트 [coms-suite](https://github.com/dudgns0825-alt/coms-suite)는 같은 도메인(DART 공시 수집 + 재무분석)을 역할별 모듈로 나눠 두었다(`app.py`, `ui_theme.py`, `download_tab.py`, `analysis_tab.py`, `dart_client.py`, `dart_viewer.py`, `note_reader.py`, `metrics.py`, `report.py`). 이 구조를 미러링해 유지보수성과 포트폴리오 가독성을 확보한다.

동시에 생성된 읽기용 HTML의 네비게이션 문제 두 건을 고친다.

1. 목차 링크 클릭 시 부드러운 스크롤이 걸려 있어, 1.7MB짜리 사업보고서에서 수천 줄을 애니메이션으로 훑고 내려간다.
2. 재무제표 본문의 주석 참조(`(주석3,4)`, `주석 16 참조`)가 평범한 텍스트라 해당 주석까지 손으로 찾아 내려가야 한다.

## 범위

**포함**

- 두 모놀리식 파일을 역할별 모듈로 분리. 기능 변경 없음.
- 읽기용 HTML의 즉시 점프 전환.
- 읽기용 HTML의 주석 참조 → 주석 본문 링크.

**제외**

- coms-suite의 추가 기능(EDGAR 미국 공시, 비교기업 EV/EBITDA 벤치마킹, HTML 차트 리포트). 이번 작업은 구조 리팩터링만 한다.
- GUI 레이아웃 변경. 현재의 좌우 분할(좌: 다운로드·로그 / 우: 분석 탭)을 유지한다. coms-suite의 2탭 구조는 로그와 분석을 동시에 못 보게 되어 현재 방식보다 나쁘다.
- 주석 점프 부가 기능(돌아가기 버튼, 목차에 주석 목록 편입).

## 1. 모듈 구조

### 목표 트리

```
app.py               DartApp 셸 · 공유 상태(corp_list/selected_corp) · main()
settings.py          _APP_DIR · 경로 상수 · load/save_api_key
ui_theme.py          ctk 테마·폰트·Listbox 색 · 공통 위젯 팩토리 · 숫자 포맷 헬퍼
download_tab.py      DownloadPanel — 검색·옵션·로그·다운로드 (+ _report_* 헬퍼)
analysis_tab.py      AnalysisPanel — 탭뷰 · 연결/별도 토글 · 회사변경 브로드캐스트
analysis/
  __init__.py        TAB_SPECS (탭 등록표)
  fin.py             재무지표
  div.py             배당
  ratio.py           재무비율
  equity.py          타법인출자
  audit.py           감사의견
  shareholder.py     주주현황
  employee.py        직원현황
  capital.py         자본변동
dart_client.py       CORPCODE 로드 · 회사검색 · 공시목록
downloader.py        문서 받기 · 압축해제 · 리네임
financials.py        재무 API 파싱 · 3개년 집계 · 비율 계산
dart_viewer.py       DART XML → 읽기용 HTML (CSS · 태그매핑 · 목차)
note_links.py        주석 인덱싱 + 본문 참조 링크          ← 신규
xml_fix.py           DART XML 보정
dart_engine.py       호환 shim — 기존 공개 이름 재수출
dart_gui.py          호환 shim — app.main() 호출
```

### 현재 코드 → 목표 모듈 매핑

`dart_engine.py`

| 현재 위치 | 대상 |
|---|---|
| `load_corp_list`, `search_company` (26–103) | `dart_client.py` |
| `_fetch_disclosure_pages`, `list_disclosures` (104–203) | `dart_client.py` |
| `safe_filename`, `_read_document_name`, `_rename_extracted`, `download_document` (204–364) | `downloader.py` |
| `_parse_amount` ~ `get_capital_changes_3y` (365–1010) | `financials.py` |
| `_esc`, `_DART_CSS`, `_dart_*`, `_toc_*`, `convert_to_html` (1012–1296) | `dart_viewer.py` |
| `_scan_real_tags`, `fix_xml`, `_parse_tag` (1299–1429) | `xml_fix.py` |

`dart_gui.py`

| 현재 위치 | 대상 |
|---|---|
| `_APP_DIR` 판별, 경로 상수, `_CONFIG_HEADER`, `load_api_key`, `save_api_key` (29–34, 38–75) | `settings.py` |
| `ctk.set_appearance_mode`/`set_default_color_theme` (36–37) | `ui_theme.py` |
| `_fmt_val` (77), `_fmt_div_val` (95), `_fmt_ratio_val` (148) | `ui_theme.py` |
| `_report_year` (107), `_report_folder` (119), `_report_basename` (132) | `download_tab.py` |
| `DartApp.__init__`, `_build_ui` (156–195) | `app.py` |
| `_build_top`/`_build_mid`/`_build_search`/`_build_options`/`_build_log`, `_save_key`, `_browse_dir`, `_log`, `_do_search`, `_fill_listbox`, `_on_select`, `_do_download` | `download_tab.py` |
| `_build_analysis`, `_on_fs_toggle`, `_update_titles` | `analysis_tab.py` |
| `_render_fin`/`_load_financials` 외 탭별 load/render 쌍 8세트 | `analysis/*.py` |

### 탭 모듈 인터페이스

각 탭 모듈은 네 가지만 노출한다.

```python
TITLE = "재무지표"

def build(parent, app): ...      # 위젯 생성, 상태 보관용 객체 반환
def load(app, ctx): ...          # 스레드에서 엔진 호출
def render(ctx, state, data=None, **kw): ...   # 결과 그리기
```

`analysis_tab.py`는 `analysis.TAB_SPECS`를 순회하며 탭을 붙이기만 한다. 탭을 추가·수정할 때 `analysis_tab.py`는 건드리지 않는다.

### 호환 유지

`scripts/` 아래 7개 스크립트(`step1_download_corpcode.py` ~ `step6_audit_report.py`, `step_diagnose.py`, `test_engine.py`)가 `dart_engine`에서 이름을 직접 임포트한다. `dart_engine.py`를 재수출 shim으로 남겨 이들이 깨지지 않게 한다.

`DART다운로더_실행.bat`과 `dart_downloader.spec`의 진입점은 `app.py`로 갱신한다. `dart_gui.py` shim도 남겨 기존 배포본 경로가 살아 있게 한다.

## 2. 링크 이동 — 즉시 점프

`dart_engine.py:1047`의 `html { scroll-behavior: smooth; }`를 제거한다. 목차를 누르면 애니메이션 없이 바로 이동한다.

도착 지점을 놓치지 않도록 두 가지를 보완한다.

- 기존 `:target` 노란 하이라이트(`background: #fef9c3`)는 유지한다.
- `scroll-margin-top`을 `h1`~`h5`와 주석 앵커에도 적용한다. 현재는 `:target`에만 걸려 있어 이동 후 제목이 뷰포트 최상단에 붙는다.

## 3. 주석 번호 점프

`dart_viewer.py`가 본문 HTML을 만든 뒤, `note_links.py`가 문자열 후처리 2단계를 수행한다.

### 실제 문서에서 확인한 사실

두 종류의 문서를 조사했다.

**사업보고서** (`downloads/STX/사업보고서_2025/`) — 주석 항목이 `<h4>` 제목이라 이미 `sec{n}` 앵커가 있다. 결정적으로 **주석 세트가 연결·별도 2벌이고 번호 체계가 다르다**.

```
h4  3. 연결재무제표 주석
h4  1. 지배기업의 개요 (연결)  …  h4  32. 계속기업가정에 관한 중요한 불확실성 (연결)
h4  4. 재무제표
h4  5. 재무제표 주석
h4  1. 회사의 개요  …  (별도 세트)
```

같은 내용이 연결 16번 / 별도 15번으로 어긋난다. 실제 본문에도 연결 쪽엔 `(주석 16 참조)`, 별도 쪽엔 `(주석 15 참조)`가 각각 나온다.

**감사보고서** (`downloads/범한유니솔루션/감사보고서_2025/`) — 세트 시작은 `<h4>주석</h4>` 하나뿐이고, 주석 항목은 제목이 아니라 평범한 `<p>` 문단이다(`5. 유형자산`, `8. 장ㆍ단기차입금(1) 단기차입금…`). 앵커가 없어 새로 부여해야 한다.

참조 표기 변형(실측):

```
(주석3,4)      (주석8,10,13,14,15)      주석30
주석 4, 5에서   주석 17 및 28            (주석 16 참조)
주석 20 (5)에
```

### ① 주석 세트·항목 인덱싱

- **세트 시작**: 제목 텍스트가 `주석`으로 끝나는 것. `3. 연결재무제표 주석`, `5. 재무제표 주석`, `주석` 모두 걸린다.
- **항목 등록**: 세트 안에서 `^\s*(\d{1,2})(?:-\d+)?\s*\.` 로 시작하는 **제목 또는 문단**을 주석 N번으로 등록한다. 번호 뒤에 마침표를 요구하고 여는 괄호를 허용하지 않으므로 `(11) 자산손상`·`1) 리스제공자` 같은 하위 항목은 자동 배제된다. 같은 N이 두 번 나오면 처음 것만 쓴다(`2.1 연결재무제표 작성기준`이 `2. 중요한 회계처리방침` 뒤에 와도 안전하다).
- **세트 종료**: 다음 중 하나에 도달하면 끝난다.
  - 번호가 역행하는 항목 — `…32. 계속기업가정` 다음의 `4. 재무제표`
  - 세트 시작 제목보다 상위 레벨의 제목 — 감사보고서의 `<h3>외부감사 실시내용</h3>`
- **앵커**: 제목형은 이미 있는 `sec{n}` id를 재사용한다. 문단형은 `<p id="nt{set}_{N}">`를 주입한다.

### ② 참조 링크

- 태그 바깥 텍스트 노드만 골라 `주석\s*(\d+(?:\s*[,및·]\s*\d+)*)`로 매칭하고, 각 숫자를 `<a class="nref" href="#…">`로 감싼다. 태그 속성값은 건드리지 않는다.
- **스코프 해석**: 참조가 놓인 문서 오프셋이 속한 세트에서 번호를 찾는다. 어느 세트에도 속하지 않으면(감사의견처럼 세트보다 앞) 첫 세트로 보낸다. 해당 번호가 없으면 링크를 걸지 않고 원문 그대로 둔다.
- **표 셀 포함**: 재무상태표의 `재고자산(주석3,4)` 같은 표 안 텍스트도 같은 스캔에 걸린다. 감사보고서에서는 이쪽이 주 사용처다.
- **오탐 방지**: 정규식이 `주석` 바로 뒤 숫자를 요구하므로 `재무제표 주석의 2. 재무제표 작성기준`, `Ⅲ.재무에 관한 사항, 5.재무제표 주석`, 세트 제목 `3. 연결재무제표 주석`은 걸리지 않는다.
- **스타일**: `.nref { color:#2563eb; text-decoration:none; border-bottom:1px dotted #93c5fd; }`. 본문 가독성을 해치지 않게 절제한다.

## 오류 처리

- 주석 세트를 하나도 못 찾으면 후처리를 건너뛰고 기존과 동일한 HTML을 낸다. 주석이 없는 공시(주요사항보고서 등)가 여기 해당한다.
- 참조 번호가 인덱스에 없으면 그 숫자만 링크 없이 남긴다. 나머지 숫자는 정상 링크한다.
- `note_links` 후처리에서 예외가 나면 원본 `body_html`을 그대로 쓰고 로그에 남긴다. 변환 자체가 실패하지는 않게 한다.

## 검증

`tests/` 에 다음을 둔다.

1. **합성 픽스처** — 연결/별도 2세트를 가진 사업보고서형 XML, 문단형 주석을 가진 감사보고서형 XML. 실제 문서에서 확인한 참조 표기 변형을 모두 담는다.
2. **주석 링크 테스트** — 연결 본문의 `주석 16`이 연결 세트 앵커로, 별도 본문의 `주석 15`가 별도 세트 앵커로 가는지. `(주석3,4)`가 링크 2개로 쪼개지는지. `주석의 2.`가 링크되지 않는지. 없는 번호가 원문 유지되는지.
3. **리팩터링 회귀 테스트** — 리팩터링 전 `convert_to_html` 출력을 골든 파일로 떠 두고, 분리 후 출력이 (주석 링크·스크롤 CSS 변경분을 제외하고) 동일한지 비교한다.
4. **임포트 호환 테스트** — `dart_engine`에서 기존 공개 이름 전체가 여전히 임포트되는지, `scripts/` 스크립트들이 임포트 에러 없이 로드되는지.

## 작업 순서

1. 리팩터링 전 골든 HTML 확보 (회귀 기준선).
2. 엔진 분리 — `dart_client` / `downloader` / `financials` / `dart_viewer` / `xml_fix`, `dart_engine` shim.
3. GUI 분리 — `settings` / `ui_theme` / `download_tab` / `analysis_tab` / `analysis/*`, `app.py`, `dart_gui` shim.
4. 진입점 갱신 — `.spec`, 실행 bat.
5. 스크롤 CSS 수정.
6. `note_links.py` 구현 + 테스트.
7. README 구조 설명 갱신.
