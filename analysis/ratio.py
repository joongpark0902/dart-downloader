"""분석 탭: 재무지표.

dart_gui.py의 _render_ratio 를 그대로 옮긴 모듈이다. 이 탭은 독립된 API 호출이나
계산을 갖지 않는다 — 핵심재무(analysis/fin.py)의 load() 가 데이터를 조회하고
calculate_financial_ratios 로 비율까지 계산한 뒤, 이 모듈의 render() 를 직접
호출해 화면을 갱신한다. 위젯 접근은 self._ratio_content → ctx.content,
self._ratio_title → ctx.title_label 로 바꿨다.
"""
import customtkinter as ctk

import ui_theme
from ui_theme import NEGATIVE, TEXT_SECONDARY, fmt_ratio_val, table_header, table_separator

# 라이트 팔레트에는 표준 warning색이 없어(NEGATIVE는 오류/음수 전용) 이
# 탭 특유의 "계산 불가" 안내에만 쓰는 호박색을 따로 둔다(fin.py의 _WARNING과
# 같은 값 — 재무지표는 핵심재무와 짝을 이루는 탭이라 안내 색도 맞춘다).
_WARNING = "#B8720A"

TITLE = "재무지표"
SCOPE = "3y_fs"

_RATIO_LABELS = ["영업이익률", "순이익률", "부채비율", "ROE", "ROA",
                 "매출총이익률", "매출원가율", "총포괄이익률"]


class Ctx:
    """탭 위젯을 담아 두는 상태 객체."""

    def __init__(self, title_label, content):
        self.title_label = title_label
        self.content = content


def build(parent, app):
    """재무지표 탭 위젯을 만든다. (dart_gui.py _build_analysis 의 재무지표 절 이식)"""
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    title_label = ctk.CTkLabel(
        parent, text="기업분석 — 재무지표",
        font=ctk.CTkFont(size=13, weight="bold")
    )
    title_label.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

    # div.py와 같은 이유로 ui_theme.ScrollFrame을 쓴다 — 3개년 열이 아주
    # 좁은 창에서 최소 폭에 닿으면 가로 스크롤바가 조용히 잘리는 대신
    # 옆으로 밀어 보게 해 준다.
    content = ui_theme.ScrollFrame(parent)
    content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
    content.grid_columnconfigure(0, weight=1)

    return Ctx(title_label, content)


def render(ctx, state, data=None, years=None):
    """재무지표 탭 컨텐츠를 갱신한다. state: 'initial'|'loading'|'done'|'error'|'no_ofs'"""
    for w in ctx.content.winfo_children():
        w.destroy()

    msgs = {
        "initial": ("회사를 선택하면 재무지표가 표시됩니다.", TEXT_SECONDARY),
        "loading": ("불러오는 중...",                     TEXT_SECONDARY),
        "error":   ("데이터를 불러오지 못했습니다.",         NEGATIVE),
        "no_ofs":  ("별도 재무제표 데이터가 없어 재무지표를 계산할 수 없습니다.", _WARNING),
    }
    if state in msgs:
        text, color = msgs[state]
        ctk.CTkLabel(ctx.content, text=text, text_color=color).grid(
            row=0, column=0, padx=12, pady=12)
        return

    f = ctk.CTkFrame(ctx.content, fg_color="transparent")
    # sticky="new": fin.py와 같은 이유 — content가 물려준 폭을 채운다.
    f.grid(row=0, column=0, sticky="new", padx=8, pady=8)

    # 항목(레이블) 열만 weight를 받아 늘고 준다. 연도 값 열은 원래도
    # 오른쪽 정렬 고정폭이었으므로 weight=0으로 유지한다(같은 정렬 의도).
    f.grid_columnconfigure(0, weight=1, minsize=110)
    for ci in range(len(years)):
        f.grid_columnconfigure(ci + 1, weight=0, minsize=90)

    # 헤더
    table_header(f, "항목", row=0, column=0, padx=(0, 8), pady=4)
    for ci, yr in enumerate(years):
        table_header(f, f"{yr}년", anchor="e", row=0, column=ci+1, padx=4, pady=4)

    table_separator(f, row=1, column=0, columnspan=len(years)+1, pady=2)

    # 구분선: 부채비율 위(수익성↔안정성), 매출총이익률 위(기본↔확장)
    for ri, label in enumerate(_RATIO_LABELS):
        if label in ("부채비율", "매출총이익률"):
            table_separator(f, row=ri+2, column=0, columnspan=len(years)+1, pady=2)

        ctk.CTkLabel(f, text=label, anchor="w").grid(
            row=ri+2, column=0, padx=(0, 8), pady=6, sticky="w"
        )
        for ci, row_data in enumerate(data):
            val = row_data.get(label)
            text, color = fmt_ratio_val(val)
            ctk.CTkLabel(f, text=text, text_color=color,
                         anchor="e").grid(
                row=ri+2, column=ci+1, padx=4, pady=6, sticky="e"
            )


def load(app, ctx):
    """재무지표 탭은 독립된 로더를 갖지 않는다 — 아무 것도 하지 않는다.

    dart_gui.py 원본에서 재무지표(_render_ratio)는 핵심재무의 _load_financials
    가 조회한 데이터로부터 계산되어 함께 렌더링될 뿐, 자신만의 조회/계산 로직이
    없다. 이 탭의 실제 갱신은 analysis/fin.py 의 load() 가
    app.ctx_of(ratio) 를 통해 render() 를 직접 호출하며 이뤄진다.

    그럼에도 load(app, ctx) 를 정의해 두는 이유는, 분석 패널이 모든 탭 모듈의
    load 를 동일한 방식으로 호출할 수 있게 하기 위해서다(균일 인터페이스).
    """
    pass
