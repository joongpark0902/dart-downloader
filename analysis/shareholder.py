"""분석 탭: 최대주주.

dart_gui.py의 _render_shareholder / _load_shareholder 를 그대로 옮긴 모듈이다.
위젯 접근은 self._shr_content → ctx.content, self._shr_title → ctx.title_label 로,
엔진 호출 인자는 app.download_panel.* / app.selected_corp 로 바꿨다.
"""
import threading

import customtkinter as ctk

import ui_theme
from financials import get_major_shareholder
from ui_theme import (
    NEGATIVE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    table_cell,
    table_header,
    table_separator,
    zebra_bg,
)

TITLE = "최대주주"
SCOPE = "1y"


class Ctx:
    """탭 위젯을 담아 두는 상태 객체."""

    def __init__(self, title_label, content):
        self.title_label = title_label
        self.content = content


def build(parent, app):
    """최대주주 탭 위젯을 만든다. (dart_gui.py _build_analysis 의 최대주주 절 이식)"""
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    title_label = ctk.CTkLabel(
        parent, text="기업분석 — 최대주주",
        font=ctk.CTkFont(size=13, weight="bold")
    )
    title_label.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

    content = ui_theme.ScrollFrame(parent)
    content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
    content.grid_columnconfigure(0, weight=1)

    return Ctx(title_label, content)


def render(ctx, state, data=None, year=None):
    """최대주주 탭 컨텐츠를 갱신한다. state: 'initial'|'loading'|'done'|'error'"""
    for w in ctx.content.winfo_children():
        w.destroy()

    msgs = {
        "initial": ("회사를 선택하면 최대주주 정보가 표시됩니다.", TEXT_SECONDARY),
        "loading": ("불러오는 중...", TEXT_SECONDARY),
        "error":   ("데이터를 가져오지 못했습니다.", NEGATIVE),
    }
    if state in msgs:
        text, color = msgs[state]
        ctk.CTkLabel(ctx.content, text=text, text_color=color).grid(
            row=0, column=0, padx=8, pady=8, sticky="w"
        )
        return

    if not data:
        ctk.CTkLabel(ctx.content,
                     text="최대주주 정보 없음", text_color=TEXT_SECONDARY).grid(
            row=0, column=0, padx=8, pady=8
        )
        return

    f = ctk.CTkFrame(ctx.content, fg_color="transparent")
    f.grid(row=0, column=0, sticky="nw", padx=8, pady=8)

    headers = [("주주명", 180, "w"), ("관계", 100, "w"),
               ("주식종류", 90, "w"), ("기말주식수", 130, "e"), ("지분율(%)", 90, "e")]
    for ci, (h, w, anchor) in enumerate(headers):
        table_header(f, h, width=w, anchor=anchor, row=0, column=ci, padx=4, pady=4)

    table_separator(f, row=1, column=0, columnspan=len(headers), pady=2)

    anchors = ["w", "w", "w", "e", "e"]
    grid_row = 2
    prev_is_detail = False
    data_row_idx = 0   # 줄무늬는 실제 데이터 행 기준으로만 센다(구분선은 안 셈)
    for row in data:
        is_total = row["주주명"] == "계"
        # 합계 행 앞에 구분선
        if is_total and prev_is_detail:
            table_separator(f, row=grid_row, column=0, columnspan=len(headers), pady=2)
            grid_row += 1
        # 합계 행은 흐리게, 그 외(최대주주 포함 모든 상세 행)는 본문 진하기로.
        color = TEXT_SECONDARY if is_total else TEXT_PRIMARY
        bg = zebra_bg(data_row_idx)
        vals = [
            row["주주명"],
            row["관계"],
            row["주식종류"],
            f"{row['기말주식수']:,}" if row["기말주식수"] is not None else "-",
            f"{row['지분율']:.2f}%" if row["지분율"] is not None else "-",
        ]
        for ci, (val, anc) in enumerate(zip(vals, anchors)):
            # 표 데이터 셀 → tk.Label (열 폭은 위 헤더가 이미 잡아 둔다)
            table_cell(
                f, val, bg=bg, fg=color, anchor=anc,
                row=grid_row, column=ci, padx=4, pady=3,
            )
        prev_is_detail = not is_total
        grid_row += 1
        data_row_idx += 1


def load(app, ctx):
    """엔진을 스레드에서 불러 결과로 render 를 부른다."""
    corp     = app.selected_corp
    api_key  = app.download_panel.api_key_var.get().strip()
    end_year = str(int(app.download_panel.end_year_var.get()) - 1)

    app.after(0, lambda: render(ctx, "loading"))

    def run():
        try:
            data = get_major_shareholder(
                api_key, corp["corp_code"], end_year, log_fn=app.download_panel.log
            )
            app.after(0, lambda: render(
                ctx, "done", data=data, year=end_year
            ))
        except Exception as e:
            app.download_panel.log(f"최대주주 오류: {e}")
            app.after(0, lambda: render(ctx, "error"))

    threading.Thread(target=run, daemon=True).start()
