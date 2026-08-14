"""분석 탭: 배당.

dart_gui.py의 _render_div / _load_dividends 를 그대로 옮긴 모듈이다.
위젯 접근은 self._div_content → ctx.content, self._div_title → ctx.title_label 로,
엔진 호출 인자는 app.download_panel.* / app.selected_corp 로 바꿨다.
"""
import threading

import customtkinter as ctk

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

    content = ctk.CTkFrame(parent, fg_color="transparent")
    content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
    content.grid_columnconfigure(0, weight=1)
    content.grid_rowconfigure(0, weight=1)

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
    f.grid(row=0, column=0, sticky="n", padx=8, pady=8)

    col_w = 130

    # 헤더
    table_header(f, "항목", width=160, row=0, column=0, padx=(0, 8), pady=4)
    for ci, yr in enumerate(years):
        table_header(f, f"{yr}년", width=col_w, anchor="e", row=0, column=ci+1, padx=4, pady=4)

    table_separator(f, row=1, column=0, columnspan=len(years)+1, pady=2)

    for ri, label in enumerate(_DIV_LABELS):
        ctk.CTkLabel(f, text=label, width=160, anchor="w").grid(
            row=ri+2, column=0, padx=(0, 8), pady=6, sticky="w"
        )
        for ci, row_data in enumerate(data):
            val = row_data.get(label)
            text, color = fmt_div_val(val, label)
            ctk.CTkLabel(f, text=text, text_color=color,
                         width=col_w, anchor="e").grid(
                row=ri+2, column=ci+1, padx=4, pady=6
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
