"""분석 탭: 배당.

dart_gui.py의 _render_div / _load_dividends 를 그대로 옮긴 모듈이다.
위젯 접근은 self._div_content → ctx.content, self._div_title → ctx.title_label 로,
엔진 호출 인자는 app.download_panel.* / app.selected_corp 로 바꿨다.
"""
import threading

import customtkinter as ctk

import ui_theme
from financials import get_dividend_info_3y
from ui_theme import NEGATIVE, TEXT_SECONDARY, fmt_div_val, table_header, table_separator

TITLE = "배당"
SCOPE = "3y"

_DIV_LABELS = ["주당배당금(원)", "배당성향(%)", "시가배당률(%)", "현금배당총액(백만원)"]


class Ctx:
    """탭 위젯을 담아 두는 상태 객체."""

    def __init__(self, title_label, content):
        self.title_label = title_label
        self.content = content


def build(parent, app):
    """배당 탭 위젯을 만든다. (dart_gui.py _build_analysis 의 배당 절 이식)"""
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    title_label = ctk.CTkLabel(
        parent, text="기업분석 — 배당",
        font=ctk.CTkFont(size=13, weight="bold")
    )
    title_label.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

    # 일반 CTkFrame 대신 ui_theme.ScrollFrame을 쓴다 — 표 데이터 자체는
    # 짧아 세로 스크롤은 거의 안 쓰이지만, 아주 좁은 창에서 열 폭이 최소
    # 아래로 못 줄어드는 지점에 닿으면 이 컨테이너의 가로 스크롤바가
    # (ui_theme.ScrollFrame._sync_hscrollbar) 조용히 잘리는 대신 옆으로
    # 밀어 보게 해 준다.
    content = ui_theme.ScrollFrame(parent)
    content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
    content.grid_columnconfigure(0, weight=1)

    return Ctx(title_label, content)


def render(ctx, state, data=None, years=None):
    """배당 탭 컨텐츠를 갱신한다. state: 'initial'|'loading'|'done'|'error'"""
    for w in ctx.content.winfo_children():
        w.destroy()

    if state == "initial":
        ctk.CTkLabel(ctx.content,
                     text="회사를 선택하면 배당 데이터가 표시됩니다.",
                     text_color=TEXT_SECONDARY).grid(row=0, column=0)
        return
    if state == "loading":
        ctk.CTkLabel(ctx.content,
                     text="불러오는 중...", text_color=TEXT_SECONDARY).grid(row=0, column=0)
        return
    if state == "error":
        ctk.CTkLabel(ctx.content,
                     text="데이터를 불러오지 못했습니다.", text_color=NEGATIVE).grid(row=0, column=0)
        return

    f = ctk.CTkFrame(ctx.content, fg_color="transparent")
    # sticky="new": 옛 "n"(자연폭·가운데 배치)은 창을 좁혀도 표 폭이 안
    # 줄어 오른쪽이 그대로 잘렸다. content가 이미 폭을 물려주므로 "new"로
    # 왼/오른쪽까지 붙여 그 폭을 받는다.
    f.grid(row=0, column=0, sticky="new", padx=8, pady=8)

    # 항목(레이블) 열만 weight를 받아 창 폭에 맞춰 늘고 준다 — "현금배당
    # 총액(백만원)"처럼 긴 레이블이 있는 열이라 여유 폭이 여기로 가는 게
    # 자연스럽다. 연도 값 열은 원래도 오른쪽 정렬 고정폭이었으므로
    # weight=0으로 유지한다(같은 정렬 의도).
    f.grid_columnconfigure(0, weight=1, minsize=150)
    for ci in range(len(years)):
        f.grid_columnconfigure(ci + 1, weight=0, minsize=90)

    # 헤더
    table_header(f, "항목", row=0, column=0, padx=(0, 8), pady=4)
    for ci, yr in enumerate(years):
        table_header(f, f"{yr}년", anchor="e", row=0, column=ci+1, padx=4, pady=4)

    table_separator(f, row=1, column=0, columnspan=len(years)+1, pady=2)

    for ri, label in enumerate(_DIV_LABELS):
        ctk.CTkLabel(f, text=label, anchor="w").grid(
            row=ri+2, column=0, padx=(0, 8), pady=6, sticky="w"
        )
        for ci, row_data in enumerate(data):
            val = row_data.get(label)
            text, color = fmt_div_val(val, label)
            ctk.CTkLabel(f, text=text, text_color=color,
                         anchor="e").grid(
                row=ri+2, column=ci+1, padx=4, pady=6, sticky="e"
            )


def load(app, ctx):
    """엔진을 스레드에서 불러 결과로 render 를 부른다."""
    corp     = app.selected_corp
    api_key  = app.download_panel.api_key_var.get().strip()
    end_year = str(int(app.download_panel.end_year_var.get()) - 1)

    app.after(0, lambda: render(ctx, "loading"))

    def run():
        try:
            data  = get_dividend_info_3y(api_key, corp["corp_code"], end_year, log_fn=app.download_panel.log)
            years = [r["year"] for r in data]
            app.after(0, lambda: render(ctx, "done", data=data, years=years))
        except Exception as e:
            app.download_panel.log(f"배당 데이터 오류: {e}")
            app.after(0, lambda: render(ctx, "error"))

    threading.Thread(target=run, daemon=True).start()
