"""분석 탭: 핵심재무.

dart_gui.py의 _render_fin / _load_financials 를 그대로 옮긴 모듈이다.
위젯 접근은 self._fin_content → ctx.content, self._fin_title → ctx.title_label 로,
엔진 호출 인자는 app.download_panel.* / app.selected_corp 로 바꿨다.

_load_financials 는 원본에서 핵심재무·재무지표 두 탭을 함께 구동하는 단일 로더다.
재무지표(analysis/ratio.py)는 독립된 API 호출이나 계산을 갖지 않으므로, 이 모듈의
load() 가 두 탭 모두를 갱신한다.
"""
import threading

import customtkinter as ctk

from financials import (
    calculate_financial_ratios,
    get_extended_financials_3y,
    get_key_financials_3y,
)
from ui_theme import fmt_val

# 재무지표 탭 컨텍스트를 얻기 위해 모듈 자체를 import 한다.
# app.ctx_of(module) 접근자는 다음 작업(Task 10)에서 도입된다.
from analysis import ratio

TITLE = "핵심재무"
SCOPE = "3y_fs"

_FIN_LABELS = ["매출액", "영업이익", "당기순이익", "자산총계", "부채총계", "자본총계"]


class Ctx:
    """탭 위젯을 담아 두는 상태 객체."""

    def __init__(self, title_label, content):
        self.title_label = title_label
        self.content = content


def build(parent, app):
    """핵심재무 탭 위젯을 만든다. (dart_gui.py _build_analysis 의 핵심재무 절 이식)"""
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    title_label = ctk.CTkLabel(
        parent, text="기업분석 — 핵심재무",
        font=ctk.CTkFont(size=13, weight="bold")
    )
    title_label.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

    content = ctk.CTkFrame(parent, fg_color="transparent")
    content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
    content.grid_columnconfigure(0, weight=1)
    content.grid_rowconfigure(0, weight=1)

    return Ctx(title_label, content)


def render(ctx, state, data=None, corp_name="", years=None):
    """핵심재무 탭 컨텐츠를 갱신한다. state: 'initial'|'loading'|'done'|'error'|'no_ofs'"""
    for w in ctx.content.winfo_children():
        w.destroy()

    if state == "initial":
        ctk.CTkLabel(ctx.content,
                     text="회사를 선택하면 재무 데이터가 표시됩니다.",
                     text_color="gray").grid(row=0, column=0)
        return

    if state == "loading":
        ctk.CTkLabel(ctx.content,
                     text="불러오는 중...", text_color="gray").grid(row=0, column=0)
        return

    if state == "no_ofs":
        ctk.CTkLabel(ctx.content,
                     text="해당 회사는 별도 재무제표를 별도로 공시하지 않습니다.",
                     text_color="orange").grid(row=0, column=0, padx=12, pady=12)
        return

    if state == "error":
        ctk.CTkLabel(ctx.content,
                     text="데이터를 불러오지 못했습니다.", text_color="#FF6B6B").grid(row=0, column=0)
        return

    # ── 전체 N/A 감지 → 비지원 안내 ──
    all_none = all(
        row.get(label) is None
        for row in data
        for label in _FIN_LABELS
    )
    outer = ctk.CTkFrame(ctx.content, fg_color="transparent")
    outer.grid(row=0, column=0, sticky="n", padx=8, pady=8)

    if all_none:
        ctk.CTkLabel(
            outer,
            text="이 회사는 XBRL 재무데이터를 지원하지 않습니다 (비상장 외감법인 등)",
            text_color="#FFA040",
        ).grid(row=0, column=0, pady=(0, 10), sticky="w")

    # ── 표 그리기 ──
    f = ctk.CTkFrame(outer, fg_color="transparent")
    f.grid(row=1, column=0, sticky="n")

    col_w = 110
    row_h = 32

    # 헤더
    ctk.CTkLabel(f, text="항목", font=ctk.CTkFont(weight="bold"),
                 width=120, anchor="w").grid(row=0, column=0, padx=(0, 8), pady=4, sticky="w")
    for ci, yr in enumerate(years):
        ctk.CTkLabel(f, text=f"{yr}년", font=ctk.CTkFont(weight="bold"),
                     width=col_w, anchor="e").grid(row=0, column=ci+1, padx=4, pady=4)

    # 구분선
    sep = ctk.CTkFrame(f, height=1, fg_color="gray40")
    sep.grid(row=1, column=0, columnspan=len(years)+1, sticky="ew", pady=2)

    # 데이터 행
    for ri, label in enumerate(_FIN_LABELS):
        # 구분선: 자산총계 위
        if label == "자산총계":
            sep2 = ctk.CTkFrame(f, height=1, fg_color="gray30")
            sep2.grid(row=ri*2+2, column=0, columnspan=len(years)+1,
                      sticky="ew", pady=2)

        row_idx = ri * 2 + 3 if label != "매출액" else ri * 2 + 2

        ctk.CTkLabel(f, text=label, width=120, anchor="w").grid(
            row=ri+2, column=0, padx=(0, 8), pady=6, sticky="w"
        )
        for ci, row_data in enumerate(data):
            val = row_data.get(label)
            text, color = fmt_val(val)
            ctk.CTkLabel(f, text=text, text_color=color,
                         width=col_w, anchor="e").grid(
                row=ri+2, column=ci+1, padx=4, pady=6
            )


def load(app, ctx):
    """엔진을 스레드에서 불러 결과로 render 를 부른다.

    dart_gui.py 의 _load_financials 를 그대로 이식했다 — 핵심재무 탭(ctx)과
    재무지표 탭(app.ctx_of(ratio))을 함께 갱신하는 단일 로더다.
    """
    corp     = app.selected_corp
    api_key  = app.download_panel.api_key_var.get().strip()
    end_year = str(int(app.download_panel.end_year_var.get()) - 1)
    # TODO(Task10): fs_seg(연결/별도 토글)는 분석 패널로 옮겨질 예정. 지금은 app.fs_seg 로 읽는다.
    fs_div   = "CFS" if app.fs_seg.get() == "연결" else "OFS"

    ratio_ctx = app.ctx_of(ratio)  # ctx_of 는 Task 10에서 도입 예정

    app.after(0, lambda: render(ctx, "loading"))
    app.after(0, lambda: ratio.render(ratio_ctx, "loading"))

    def run():
        try:
            data = get_key_financials_3y(
                api_key, corp["corp_code"], end_year,
                fs_div=fs_div, log_fn=app.download_panel.log
            )
            # OFS 데이터가 전 연도 없으면 안내
            if fs_div == "OFS" and all(not r.get("available") for r in data):
                app.after(0, lambda: render(ctx, "no_ofs"))
                app.after(0, lambda: ratio.render(ratio_ctx, "no_ofs"))
                return
            years = [r["year"] for r in data]
            try:
                ext = get_extended_financials_3y(
                    api_key, corp["corp_code"], end_year, log_fn=app.download_panel.log
                )
            except Exception as e:
                app.download_panel.log(f"확장재무 조회 실패 (무시): {e}")
                ext = None
            ratios = calculate_financial_ratios(data, extended_3y=ext)
            app.after(0, lambda: render(ctx, "done", data=data,
                                         corp_name=corp["corp_name"],
                                         years=years))
            app.after(0, lambda: ratio.render(ratio_ctx, "done", data=ratios, years=years))
        except Exception as e:
            app.download_panel.log(f"재무 데이터 오류: {e}")
            app.after(0, lambda: render(ctx, "error"))
            app.after(0, lambda: ratio.render(ratio_ctx, "error"))

    threading.Thread(target=run, daemon=True).start()
