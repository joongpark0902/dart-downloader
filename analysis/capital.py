"""분석 탭: 자본변동.

dart_gui.py의 _render_capital / _load_capital 를 그대로 옮긴 모듈이다.
위젯 접근은 self._cap_content → ctx.content, self._cap_title → ctx.title_label 로,
엔진 호출 인자는 app.download_panel.* / app.selected_corp 로 바꿨다.
"""
import threading

import customtkinter as ctk

import ui_theme
from financials import get_capital_changes_3y
from ui_theme import (
    NEGATIVE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    table_cell,
    table_header,
    table_separator,
)

TITLE = "자본변동"
SCOPE = "3y"


class Ctx:
    """탭 위젯을 담아 두는 상태 객체."""

    def __init__(self, title_label, content):
        self.title_label = title_label
        self.content = content


def build(parent, app):
    """자본변동 탭 위젯을 만든다. (dart_gui.py _build_analysis 의 자본변동 절 이식)"""
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    title_label = ctk.CTkLabel(
        parent, text="기업분석 — 자본변동",
        font=ctk.CTkFont(size=13, weight="bold")
    )
    title_label.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

    content = ui_theme.ScrollFrame(parent)
    content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
    content.grid_columnconfigure(0, weight=1)

    return Ctx(title_label, content)


def render(ctx, state, data=None):
    """자본변동 탭 컨텐츠를 갱신한다. state: 'initial'|'loading'|'done'|'error'"""
    for w in ctx.content.winfo_children():
        w.destroy()

    msgs = {
        "initial": ("회사를 선택하면 자본변동 정보가 표시됩니다.", TEXT_SECONDARY),
        "loading": ("불러오는 중...", TEXT_SECONDARY),
        "error":   ("데이터를 가져오지 못했습니다.", NEGATIVE),
    }
    if state in msgs:
        text, color = msgs[state]
        ctk.CTkLabel(ctx.content, text=text, text_color=color).grid(
            row=0, column=0, padx=8, pady=8, sticky="w"
        )
        return

    bold = ctk.CTkFont(weight="bold")
    row_idx = 0

    hdrs  = ["발행일", "발행형태", "주식종류", "수량", "액면가(원)", "발행가(원)"]
    keys  = ["발행일", "발행형태", "주식종류", "수량", "액면가", "발행가"]
    wids  = [100, 120, 90, 110, 110, 110]
    hdrs2 = ["주식종류", "기초수량", "취득", "처분", "소각", "기말수량"]
    keys2 = ["주식종류", "기초수량", "취득", "처분", "소각", "기말수량"]
    wids2 = [90, 130, 100, 100, 100, 130]

    for yi, year_data in enumerate(data):
        yr    = year_data["year"]
        issu  = year_data.get("증자감자", [])
        treas = year_data.get("자기주식", [])

        # 연도 헤더
        ctk.CTkLabel(ctx.content, text=f"■ {yr}년도", font=bold, text_color=TEXT_PRIMARY).grid(
            row=row_idx, column=0, padx=8, pady=(12 if yi else 4, 4), sticky="w"
        )
        row_idx += 1

        # ▸ 증자(감자)
        ctk.CTkLabel(ctx.content, text="▸ 증자(감자) 현황",
                     text_color=TEXT_SECONDARY).grid(row=row_idx, column=0, padx=16, pady=(2, 0), sticky="w")
        row_idx += 1
        if not issu:
            ctk.CTkLabel(ctx.content, text="  해당사항 없음",
                         text_color=TEXT_SECONDARY).grid(row=row_idx, column=0, padx=28, pady=2, sticky="w")
            row_idx += 1
        else:
            sub = ctk.CTkFrame(ctx.content, fg_color="transparent")
            sub.grid(row=row_idx, column=0, padx=24, pady=4, sticky="nw")
            row_idx += 1
            for ci, (h, w) in enumerate(zip(hdrs, wids)):
                table_header(sub, h, width=w, row=0, column=ci, padx=4, pady=2)
            table_separator(sub, row=1, column=0, columnspan=len(hdrs), pady=1)
            for ri, item in enumerate(issu):
                for ci, key in enumerate(keys):
                    # 표 데이터 셀 → tk.Label (열 폭은 위 헤더가 이미 잡아 둔다)
                    table_cell(
                        sub, item.get(key, "-"),
                        bg=ui_theme.zebra_bg(ri), anchor="w",
                        row=ri + 2, column=ci, padx=4, pady=3,
                    )

        # ▸ 자기주식
        ctk.CTkLabel(ctx.content, text="▸ 자기주식 취득·처분",
                     text_color=TEXT_SECONDARY).grid(row=row_idx, column=0, padx=16, pady=(6, 0), sticky="w")
        row_idx += 1
        if not treas:
            ctk.CTkLabel(ctx.content, text="  해당사항 없음",
                         text_color=TEXT_SECONDARY).grid(row=row_idx, column=0, padx=28, pady=2, sticky="w")
            row_idx += 1
        else:
            sub2 = ctk.CTkFrame(ctx.content, fg_color="transparent")
            sub2.grid(row=row_idx, column=0, padx=24, pady=4, sticky="nw")
            row_idx += 1
            for ci, (h, w) in enumerate(zip(hdrs2, wids2)):
                anchor = "w" if ci == 0 else "e"
                table_header(sub2, h, width=w, anchor=anchor, row=0, column=ci, padx=4, pady=2)
            table_separator(sub2, row=1, column=0, columnspan=len(hdrs2), pady=1)
            for ri, item in enumerate(treas):
                for ci, key in enumerate(keys2):
                    anchor = "w" if ci == 0 else "e"
                    # 표 데이터 셀 → tk.Label (열 폭은 위 헤더가 이미 잡아 둔다)
                    table_cell(
                        sub2, item.get(key, "-"),
                        bg=ui_theme.zebra_bg(ri), anchor=anchor,
                        row=ri + 2, column=ci, padx=4, pady=3,
                    )

        # 연도 사이 구분선
        if yi < len(data) - 1:
            table_separator(ctx.content, row=row_idx, column=0, padx=8, pady=8)
            row_idx += 1

    ctx.content.grid_columnconfigure(0, weight=1)


def load(app, ctx):
    """엔진을 스레드에서 불러 결과로 render 를 부른다."""
    corp     = app.selected_corp
    api_key  = app.download_panel.api_key_var.get().strip()
    end_year = str(int(app.download_panel.end_year_var.get()) - 1)

    app.after(0, lambda: render(ctx, "loading"))

    def run():
        try:
            data = get_capital_changes_3y(
                api_key, corp["corp_code"], end_year, log_fn=app.download_panel.log
            )
            app.after(0, lambda: render(ctx, "done", data=data))
        except Exception as e:
            app.download_panel.log(f"자본변동 오류: {e}")
            app.after(0, lambda: render(ctx, "error"))

    threading.Thread(target=run, daemon=True).start()
