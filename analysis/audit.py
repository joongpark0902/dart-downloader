"""분석 탭: 감사.

dart_gui.py의 _render_audit / _load_audit 를 그대로 옮긴 모듈이다.
위젯 접근은 self._adt_content → ctx.content, self._adt_title → ctx.title_label 로,
엔진 호출 인자는 app.download_panel.* / app.selected_corp 로 바꿨다.
"""
import threading

import customtkinter as ctk

import ui_theme
from financials import get_audit_opinion_3y
from ui_theme import NEGATIVE, SURFACE, TEXT_PRIMARY, TEXT_SECONDARY, table_cell

TITLE = "감사"
SCOPE = "3y"


class Ctx:
    """탭 위젯을 담아 두는 상태 객체."""

    def __init__(self, title_label, content):
        self.title_label = title_label
        self.content = content


def build(parent, app):
    """감사 탭 위젯을 만든다. (dart_gui.py _build_analysis 의 감사 절 이식)"""
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    title_label = ctk.CTkLabel(
        parent, text="기업분석 — 감사",
        font=ctk.CTkFont(size=13, weight="bold")
    )
    title_label.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

    content = ui_theme.ScrollFrame(parent)
    content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
    content.grid_columnconfigure(0, weight=1)

    return Ctx(title_label, content)


def render(ctx, state, data=None):
    """감사 탭 컨텐츠를 갱신한다. state: 'initial'|'loading'|'done'|'error'"""
    for w in ctx.content.winfo_children():
        w.destroy()

    msgs = {
        "initial": ("회사를 선택하면 감사 정보가 표시됩니다.", TEXT_SECONDARY),
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
    for ri, row in enumerate(data):
        yr = row["year"]
        # 연도 헤더
        ctk.CTkLabel(
            ctx.content,
            text=f"■ {yr}년도",
            font=bold, text_color=TEXT_PRIMARY
        ).grid(row=ri * 6, column=0, padx=8, pady=(12 if ri else 4, 2), sticky="w")

        # 감사인·의견 한 줄 (표 데이터 셀 → tk.Label; ui_theme.table_cell 참고)
        opinion_color = TEXT_PRIMARY if "적정" in row["감사의견"] else NEGATIVE
        table_cell(
            ctx.content,
            f"감사인: {row['감사인']}   |   감사의견: {row['감사의견']}",
            bg=SURFACE, fg=opinion_color, anchor="w",
            row=ri * 6 + 1, column=0, padx=16, pady=2,
        )

        # 강조사항
        ctk.CTkLabel(ctx.content, text="▸ 강조사항",
                     text_color=TEXT_SECONDARY).grid(
            row=ri * 6 + 2, column=0, padx=16, pady=(6, 0), sticky="w"
        )
        ctk.CTkTextbox(
            ctx.content, height=50, wrap="word",
            fg_color=ui_theme.PANEL_BG, text_color=TEXT_PRIMARY, border_width=0,
        ).grid(row=ri * 6 + 3, column=0, padx=24, pady=(0, 4), sticky="ew")
        tb_emp = ctx.content.grid_slaves(row=ri * 6 + 3, column=0)[0]
        tb_emp.insert("end", row["강조사항"])
        tb_emp.configure(state="disabled")

        # 핵심감사사항
        ctk.CTkLabel(ctx.content, text="▸ 핵심감사사항",
                     text_color=TEXT_SECONDARY).grid(
            row=ri * 6 + 4, column=0, padx=16, pady=(6, 0), sticky="w"
        )
        tb_core = ctk.CTkTextbox(
            ctx.content, height=110, wrap="word",
            fg_color=ui_theme.PANEL_BG, text_color=TEXT_PRIMARY, border_width=0,
        )
        tb_core.grid(row=ri * 6 + 5, column=0, padx=24, pady=(0, 4), sticky="ew")
        tb_core.insert("end", row["핵심감사사항"])
        tb_core.configure(state="disabled")

    ctx.content.grid_columnconfigure(0, weight=1)


def load(app, ctx):
    """엔진을 스레드에서 불러 결과로 render 를 부른다."""
    corp     = app.selected_corp
    api_key  = app.download_panel.api_key_var.get().strip()
    end_year = str(int(app.download_panel.end_year_var.get()) - 1)

    app.after(0, lambda: render(ctx, "loading"))

    def run():
        try:
            data = get_audit_opinion_3y(
                api_key, corp["corp_code"], end_year, log_fn=app.download_panel.log
            )
            app.after(0, lambda: render(ctx, "done", data=data))
        except Exception as e:
            app.download_panel.log(f"감사의견 오류: {e}")
            app.after(0, lambda: render(ctx, "error"))

    threading.Thread(target=run, daemon=True).start()
