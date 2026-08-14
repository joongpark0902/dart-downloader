"""분석 탭: 직원.

dart_gui.py의 _render_employee / _load_employee 를 그대로 옮긴 모듈이다.
위젯 접근은 self._emp_content → ctx.content, self._emp_title → ctx.title_label 로,
엔진 호출 인자는 app.download_panel.* / app.selected_corp 로 바꿨다.
"""
import threading

import customtkinter as ctk

import ui_theme
from financials import get_employee_status
from ui_theme import NEGATIVE, TEXT_PRIMARY, TEXT_SECONDARY, table_header, table_separator

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

    # div.py와 같은 이유로 ui_theme.ScrollFrame을 쓴다 — 성별 2열+합계
    # 열은 매우 좁은 창에서 최소 폭에 닿을 수 있어, 그때 가로 스크롤바가
    # 조용히 잘리는 대신 옆으로 밀어 보게 해 준다.
    content = ui_theme.ScrollFrame(parent)
    content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
    content.grid_columnconfigure(0, weight=1)

    return Ctx(title_label, content)


def render(ctx, state, data=None, year=None):
    """직원 탭 컨텐츠를 갱신한다. state: 'initial'|'loading'|'done'|'error'"""
    for w in ctx.content.winfo_children():
        w.destroy()

    msgs = {
        "initial": ("회사를 선택하면 직원 정보가 표시됩니다.", TEXT_SECONDARY),
        "loading": ("불러오는 중...", TEXT_SECONDARY),
        "error":   ("데이터를 가져오지 못했습니다.", NEGATIVE),
    }
    if state in msgs:
        text, color = msgs[state]
        ctk.CTkLabel(ctx.content, text=text, text_color=color).grid(
            row=0, column=0, padx=8, pady=8
        )
        return

    f = ctk.CTkFrame(ctx.content, fg_color="transparent")
    # sticky="new": div.py와 같은 이유 — content가 물려준 폭을 채운다.
    f.grid(row=0, column=0, sticky="new", padx=8, pady=8)

    gender_names = [g["성별"] for g in data["성별"]]
    n_val_cols = len(gender_names) + 1   # 성별 열 + 합계 열

    # 항목(레이블) 열만 weight를 받아 늘고 준다("1인평균급여(연간)"처럼 긴
    # 레이블이 있다). 성별·합계 값 열은 원래도 오른쪽 정렬 고정폭이었으므로
    # weight=0으로 유지한다(같은 정렬 의도).
    f.grid_columnconfigure(0, weight=1, minsize=150)
    for ci in range(n_val_cols):
        f.grid_columnconfigure(ci + 1, weight=0, minsize=110)

    def _row(parent, r, label, *vals):
        ctk.CTkLabel(parent, text=label, anchor="w").grid(
            row=r, column=0, padx=(0, 12), pady=6, sticky="w"
        )
        for ci, (txt, color) in enumerate(vals):
            ctk.CTkLabel(parent, text=txt, text_color=color,
                         anchor="e").grid(
                row=r, column=ci + 1, padx=4, pady=6, sticky="e"
            )

    # 성별 헤더
    table_header(f, "항목", row=0, column=0, padx=(0, 12), pady=4)
    for ci, g in enumerate(gender_names):
        table_header(f, g, anchor="e", row=0, column=ci + 1, padx=4, pady=4)
    table_header(f, "합계", anchor="e",
                 row=0, column=len(gender_names) + 1, padx=4, pady=4)

    table_separator(f, row=1, column=0, columnspan=len(gender_names) + 2, pady=2)

    def _fmt_int(v):
        return (f"{v:,}명", TEXT_PRIMARY) if v is not None else ("-", TEXT_SECONDARY)

    def _fmt_tenure(v):
        return (f"{v}년", TEXT_PRIMARY) if v is not None else ("-", TEXT_SECONDARY)

    def _fmt_salary(v):
        if v is None: return ("-", TEXT_SECONDARY)
        if v >= 100_000_000: return (f"{v/100_000_000:.1f}억원", TEXT_PRIMARY)
        return (f"{v:,}원", TEXT_PRIMARY)

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

    table_separator(f, row=5, column=0, columnspan=len(gd) + 2, pady=2)

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
