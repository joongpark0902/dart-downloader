"""분석 탭: 타법인출자.

dart_gui.py의 _render_equity / _load_equity 를 그대로 옮긴 모듈이다.
위젯 접근은 self._eqt_content → ctx.content, self._eqt_title → ctx.title_label 로,
엔진 호출 인자는 app.download_panel.* / app.selected_corp 로 바꿨다.
"""
import threading

import customtkinter as ctk

import ui_theme
from financials import get_equity_investments
from ui_theme import (
    ACCENT,
    NEGATIVE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    fmt_val,
    table_cell,
    table_header,
    table_separator,
    zebra_bg,
)

# 지분율 구간별 강조색. 자회사(50%↑)는 앱 강조색(ACCENT)을, 관계사(20%↑)는
# 흰 배경에서도 또렷이 읽히는 초록을 쓴다 — 다크 테마 때의 파스텔
# "#63B3ED"/"#68D391"은 흰 배경 위에서는 대비가 부족해 그대로 못 쓴다.
_AFFILIATE_GREEN = "#1E9E58"

TITLE = "타법인출자"
SCOPE = "1y"


class Ctx:
    """탭 위젯을 담아 두는 상태 객체."""

    def __init__(self, title_label, content):
        self.title_label = title_label
        self.content = content


def build(parent, app):
    """타법인출자 탭 위젯을 만든다. (dart_gui.py _build_analysis 의 타법인출자 절 이식)"""
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    title_label = ctk.CTkLabel(
        parent, text="기업분석 — 타법인출자",
        font=ctk.CTkFont(size=13, weight="bold")
    )
    title_label.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

    content = ctk.CTkFrame(parent, fg_color="transparent")
    content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
    content.grid_columnconfigure(0, weight=1)
    content.grid_rowconfigure(0, weight=1)

    return Ctx(title_label, content)


def render(ctx, state, data=None, year=None, corp_name=""):
    """타법인출자 탭 컨텐츠를 갱신한다. state: 'initial'|'loading'|'done'|'error'"""
    for w in ctx.content.winfo_children():
        w.destroy()

    if state == "initial":
        ctk.CTkLabel(ctx.content,
                     text="회사를 선택하면 출자 현황이 표시됩니다.",
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
    if not data:
        ctk.CTkLabel(ctx.content,
                     text="출자 내역이 없습니다.", text_color=TEXT_SECONDARY).grid(row=0, column=0)
        return

    # ── 정보 헤더 ──
    info_frame = ctk.CTkFrame(ctx.content, fg_color="transparent")
    info_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 0))
    ctk.CTkLabel(info_frame,
                 text=f"총 {len(data)}건  ({year}년 기준)",
                 text_color=TEXT_SECONDARY).pack(side="left")

    # ── 스크롤 테이블 ──
    # (다른 세 스크롤 탭과 배경 톤을 맞춘다 — ui_theme.ScrollFrame은 기본
    # SURFACE로 칠해져 CTkScrollableFrame 기본값("gray86")과 달리 이 탭만
    # 배경이 살짝 어두워 보이던 문제가 사라진다.)
    scroll = ui_theme.ScrollFrame(ctx.content)
    scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
    ctx.content.grid_rowconfigure(1, weight=1)

    HEADERS = ["법인명", "최초취득일", "지분율", "기말장부가액"]
    # (weight, minsize). 법인명만 weight를 받아 늘고 준다 — 긴 법인명이
    # 흔한 열이라 창이 넓어지면 여기로 여유 폭이 간다. 나머지 셋(취득일·
    # 지분율·장부가액)은 원래도 오른쪽 정렬 고정폭이었으므로 weight=0으로
    # 그 정렬 의도를 그대로 지킨다.
    COLS = [(1, 110), (0, 90), (0, 55), (0, 85)]

    # 헤더 행
    for ci, (h, (weight, minsize)) in enumerate(zip(HEADERS, COLS)):
        anchor = "w" if ci == 0 else "e"
        scroll.grid_columnconfigure(ci, weight=weight, minsize=minsize)
        table_header(scroll, h, anchor=anchor,
                     row=0, column=ci, padx=(0 if ci else 4, 4), pady=4)

    table_separator(scroll, row=1, column=0, columnspan=4, pady=2)

    def _pct_color(pct):
        if pct is None:  return TEXT_SECONDARY
        if pct >= 50:    return ACCENT            # 자회사
        if pct >= 20:    return _AFFILIATE_GREEN   # 관계사
        return TEXT_SECONDARY                      # 기타

    for ri, row in enumerate(data):
        pct   = row["지분율"]
        bv    = row["기말장부가액"]
        pct_s = f"{pct:.1f}%" if pct is not None else "N/A"
        bv_s, bv_c = fmt_val(bv) if bv is not None else ("N/A", TEXT_SECONDARY)
        row_idx = ri + 2
        bg = zebra_bg(ri)

        cells = [
            (row["법인명"],   "w", TEXT_PRIMARY),
            (row["최초취득일"], "e", TEXT_SECONDARY),
            (pct_s,          "e", _pct_color(pct)),
            (bv_s,           "e", bv_c),
        ]
        for ci, (text, anchor, color) in enumerate(cells):
            # 표 데이터 셀 → tk.Label (열 폭은 위 헤더가 이미 잡아 둔다)
            table_cell(
                scroll, text, bg=bg, fg=color, anchor=anchor,
                row=row_idx, column=ci, padx=(0 if ci else 4, 4), pady=2,
            )


def load(app, ctx):
    """엔진을 스레드에서 불러 결과로 render 를 부른다."""
    corp     = app.selected_corp
    api_key  = app.download_panel.api_key_var.get().strip()
    end_year = str(int(app.download_panel.end_year_var.get()) - 1)

    app.after(0, lambda: render(ctx, "loading"))

    def run():
        try:
            data = get_equity_investments(
                api_key, corp["corp_code"], end_year, log_fn=app.download_panel.log
            )
            app.after(0, lambda: render(
                ctx, "done", data=data, year=end_year, corp_name=corp["corp_name"]
            ))
        except Exception as e:
            app.download_panel.log(f"타법인출자 오류: {e}")
            app.after(0, lambda: render(ctx, "error"))

    threading.Thread(target=run, daemon=True).start()
