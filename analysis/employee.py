"""분석 탭: 직원.

dart_gui.py의 _render_employee / _load_employee 를 그대로 옮긴 모듈이다.
위젯 접근은 self._emp_content → ctx.content, self._emp_title → ctx.title_label 로,
엔진 호출 인자는 app.download_panel.* / app.selected_corp 로 바꿨다.
"""
import threading

import customtkinter as ctk

from financials import get_employee_status

TITLE = "직원"
SCOPE = "1y"


class Ctx:
    """탭 위젯을 담아 두는 상태 객체."""

    def __init__(self, title_label, content):
        self.title_label = title_label
        self.content = content


def build(parent, app):
    """직원 탭 위젯을 만든다. (dart_gui.py _build_analysis 의 직원 절 이식)"""
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    title_label = ctk.CTkLabel(
        parent, text="기업분석 — 직원",
        font=ctk.CTkFont(size=13, weight="bold")
    )
    title_label.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

    content = ctk.CTkFrame(parent, fg_color="transparent")
    content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
    content.grid_columnconfigure(0, weight=1)
    content.grid_rowconfigure(0, weight=1)

    return Ctx(title_label, content)


def render(ctx, state, data=None, year=None):
    """직원 탭 컨텐츠를 갱신한다. state: 'initial'|'loading'|'done'|'error'"""
    for w in ctx.content.winfo_children():
        w.destroy()

    msgs = {
        "initial": ("회사를 선택하면 직원 정보가 표시됩니다.", "gray"),
        "loading": ("불러오는 중...", "gray"),
        "error":   ("데이터를 가져오지 못했습니다.", "#e05252"),
    }
    if state in msgs:
        text, color = msgs[state]
        ctk.CTkLabel(ctx.content, text=text, text_color=color).grid(
            row=0, column=0, padx=8, pady=8
        )
        return

    f = ctk.CTkFrame(ctx.content, fg_color="transparent")
    f.grid(row=0, column=0, sticky="n", padx=8, pady=8)

    bold  = ctk.CTkFont(weight="bold")
    label_w, val_w = 160, 140

    def _row(parent, r, label, *vals):
        ctk.CTkLabel(parent, text=label, width=label_w, anchor="w").grid(
            row=r, column=0, padx=(0, 12), pady=6, sticky="w"
        )
        for ci, (txt, color) in enumerate(vals):
            ctk.CTkLabel(parent, text=txt, text_color=color,
                         width=val_w, anchor="e").grid(
                row=r, column=ci + 1, padx=4, pady=6
            )

    # 성별 헤더
    ctk.CTkLabel(f, text="항목", font=bold, width=label_w, anchor="w").grid(
        row=0, column=0, padx=(0, 12), pady=4
    )
    gender_names = [g["성별"] for g in data["성별"]]
    for ci, g in enumerate(gender_names):
        ctk.CTkLabel(f, text=g, font=bold, width=val_w, anchor="e").grid(
            row=0, column=ci + 1, padx=4, pady=4
        )
    ctk.CTkLabel(f, text="합계", font=bold, width=val_w, anchor="e").grid(
        row=0, column=len(gender_names) + 1, padx=4, pady=4
    )

    ctk.CTkFrame(f, height=1, fg_color="gray40").grid(
        row=1, column=0, columnspan=len(gender_names) + 2, sticky="ew", pady=2
    )

    def _fmt_int(v):
        return (f"{v:,}명", "white") if v is not None else ("-", "gray50")

    def _fmt_tenure(v):
        return (f"{v}년", "white") if v is not None else ("-", "gray50")

    def _fmt_salary(v):
        if v is None: return ("-", "gray50")
        if v >= 100_000_000: return (f"{v/100_000_000:.1f}억원", "white")
        return (f"{v:,}원", "white")

    gd = data["성별"]

    _row(f, 2, "총직원수",
         *[_fmt_int(g["직원수"]) for g in gd],
         _fmt_int(data["총직원"]))
    _row(f, 3, "정규직",
         *[_fmt_int(g["정규직"]) for g in gd],
         _fmt_int(data["정규직"]))
    _row(f, 4, "계약직",
         *[_fmt_int(g["계약직"]) for g in gd],
         _fmt_int(data["계약직"]))

    ctk.CTkFrame(f, height=1, fg_color="gray30").grid(
        row=5, column=0, columnspan=len(gd) + 2, sticky="ew", pady=2
    )

    _row(f, 6, "평균근속연수",
         *[_fmt_tenure(g["평균근속연수"]) for g in gd],
         _fmt_tenure(data["평균근속연수"]))
    _row(f, 7, "1인평균급여(연간)",
         *[_fmt_salary(g["1인평균급여"]) for g in gd],
         _fmt_salary(data["1인평균급여"]))


def load(app, ctx):
    """엔진을 스레드에서 불러 결과로 render 를 부른다."""
    corp     = app.selected_corp
    api_key  = app.download_panel.api_key_var.get().strip()
    end_year = str(int(app.download_panel.end_year_var.get()) - 1)

    app.after(0, lambda: render(ctx, "loading"))

    def run():
        try:
            data = get_employee_status(
                api_key, corp["corp_code"], end_year, log_fn=app.download_panel.log
            )
            app.after(0, lambda: render(ctx, "done", data=data, year=end_year))
        except Exception as e:
            app.download_panel.log(f"직원 현황 오류: {e}")
            app.after(0, lambda: render(ctx, "error"))

    threading.Thread(target=run, daemon=True).start()
