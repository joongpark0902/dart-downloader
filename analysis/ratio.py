"""분석 탭: 재무지표.

dart_gui.py의 _render_ratio 를 그대로 옮긴 모듈이다. 이 탭은 별도의 API 호출이
없다 — 핵심재무(fin.py) 탭이 조회해 둔 원본 데이터로 비율을 계산한다.
위젯 접근은 self._ratio_content → ctx.content, self._ratio_title → ctx.title_label 로 바꿨다.
"""
import customtkinter as ctk

from financials import calculate_financial_ratios
from ui_theme import fmt_ratio_val

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

    content = ctk.CTkFrame(parent, fg_color="transparent")
    content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
    content.grid_columnconfigure(0, weight=1)
    content.grid_rowconfigure(0, weight=1)

    return Ctx(title_label, content)


def render(ctx, state, data=None, years=None):
    """재무지표 탭 컨텐츠를 갱신한다. state: 'initial'|'loading'|'done'|'error'|'no_ofs'"""
    for w in ctx.content.winfo_children():
        w.destroy()

    msgs = {
        "initial": ("회사를 선택하면 재무지표가 표시됩니다.", "gray"),
        "loading": ("불러오는 중...",                     "gray"),
        "error":   ("데이터를 불러오지 못했습니다.",         "#FF6B6B"),
        "no_ofs":  ("별도 재무제표 데이터가 없어 재무지표를 계산할 수 없습니다.", "orange"),
    }
    if state in msgs:
        text, color = msgs[state]
        ctk.CTkLabel(ctx.content, text=text, text_color=color).grid(
            row=0, column=0, padx=12, pady=12)
        return

    f = ctk.CTkFrame(ctx.content, fg_color="transparent")
    f.grid(row=0, column=0, sticky="n", padx=8, pady=8)
    col_w = 110

    # 헤더
    ctk.CTkLabel(f, text="항목", font=ctk.CTkFont(weight="bold"),
                 width=120, anchor="w").grid(row=0, column=0, padx=(0, 8), pady=4, sticky="w")
    for ci, yr in enumerate(years):
        ctk.CTkLabel(f, text=f"{yr}년", font=ctk.CTkFont(weight="bold"),
                     width=col_w, anchor="e").grid(row=0, column=ci+1, padx=4, pady=4)

    sep = ctk.CTkFrame(f, height=1, fg_color="gray40")
    sep.grid(row=1, column=0, columnspan=len(years)+1, sticky="ew", pady=2)

    # 구분선: 부채비율 위(수익성↔안정성), 매출총이익률 위(기본↔확장)
    for ri, label in enumerate(_RATIO_LABELS):
        if label in ("부채비율", "매출총이익률"):
            ctk.CTkFrame(f, height=1, fg_color="gray30").grid(
                row=ri+2, column=0, columnspan=len(years)+1, sticky="ew", pady=2
            )

        ctk.CTkLabel(f, text=label, width=120, anchor="w").grid(
            row=ri+2, column=0, padx=(0, 8), pady=6, sticky="w"
        )
        for ci, row_data in enumerate(data):
            val = row_data.get(label)
            text, color = fmt_ratio_val(val)
            ctk.CTkLabel(f, text=text, text_color=color,
                         width=col_w, anchor="e").grid(
                row=ri+2, column=ci+1, padx=4, pady=6
            )


def load(app, ctx):
    """핵심재무 탭이 받아 둔 데이터로 계산한다. 아직 없으면 대기 상태로 둔다.

    브리프가 제시한 예시(render(ctx, "done", calculate_financial_ratios(app.fin_data)))는
    연도 헤더에 쓰이는 years 인자가 빠져 있어 _render_ratio 의 실제 시그니처와
    맞지 않는다. calculate_financial_ratios 의 반환 행마다 "year" 키가 있으므로
    여기서 years 를 뽑아 함께 넘긴다.
    """
    if app.fin_data is None:
        render(ctx, "initial")
        return
    ratios = calculate_financial_ratios(app.fin_data)
    years = [r["year"] for r in ratios]
    render(ctx, "done", data=ratios, years=years)
