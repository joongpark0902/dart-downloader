import threading

import customtkinter as ctk

import ui_theme
from dart_engine import (
    calculate_financial_ratios,
    get_audit_opinion_3y,
    get_capital_changes,
    get_capital_changes_3y,
    get_dividend_info_3y,
    get_employee_status,
    get_equity_investments,
    get_extended_financials_3y,
    get_key_financials_3y,
    get_major_shareholder,
)
from download_tab import DownloadPanel
from ui_theme import fmt_div_val, fmt_ratio_val, fmt_val

_FIN_LABELS    = ["매출액", "영업이익", "당기순이익", "자산총계", "부채총계", "자본총계"]
_DIV_LABELS    = ["주당배당금(원)", "배당성향(%)", "시가배당률(%)", "현금배당총액(백만원)"]
_RATIO_LABELS  = ["영업이익률", "순이익률", "부채비율", "ROE", "ROA",
                  "매출총이익률", "매출원가율", "총포괄이익률"]
_ANALYSIS_TABS = ["핵심재무", "배당", "타법인출자", "재무지표", "감사", "최대주주", "직원", "자본변동"]


class DartApp(ctk.CTk):
    def __init__(self):
        ui_theme.apply_theme()
        super().__init__()
        self.title("DART 공시 다운로더")
        self.geometry("1300x720")
        self.minsize(1000, 580)

        self.selected_corp  = None
        self._fin_data      = None   # 재무지표 탭에서 재사용

        self._build_ui()

    # ── UI 최상위 ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 좌측: 다운로드 패널
        self.download_panel = DownloadPanel(self, self)
        self.download_panel.frame.grid(
            row=0, column=0, sticky="nsew", padx=(12, 4), pady=12
        )

        # 우측: 분석 패널
        right = ctk.CTkFrame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 12), pady=12)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=0)  # 헤더
        right.grid_rowconfigure(1, weight=1)  # 탭뷰

        self._build_analysis(right)

    # ── 우측 패널 (분석 탭) ────────────────────────────────────────────────────

    def _build_analysis(self, parent):
        # ── 헤더: 회사명 + 연결/별도 토글
        hdr = ctk.CTkFrame(parent, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 0))
        hdr.grid_columnconfigure(0, weight=1)

        self._analysis_label = ctk.CTkLabel(
            hdr, text="기업분석",
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        )
        self._analysis_label.grid(row=0, column=0, sticky="w")

        self.fs_seg = ctk.CTkSegmentedButton(
            hdr, values=["연결", "별도"], width=120,
            command=self._on_fs_toggle,
        )
        self.fs_seg.set("연결")
        self.fs_seg.grid(row=0, column=1, sticky="e", padx=(8, 0))

        # ── 탭뷰 (row=1)
        tabview = ctk.CTkTabview(parent)
        tabview.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))

        for name in _ANALYSIS_TABS:
            tabview.add(name)

        # 핵심재무 탭
        fin_tab = tabview.tab("핵심재무")
        fin_tab.grid_columnconfigure(0, weight=1)
        fin_tab.grid_rowconfigure(1, weight=1)

        self._fin_title = ctk.CTkLabel(
            fin_tab, text="기업분석 — 핵심재무",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self._fin_title.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self._fin_content = ctk.CTkFrame(fin_tab, fg_color="transparent")
        self._fin_content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._fin_content.grid_columnconfigure(0, weight=1)
        self._fin_content.grid_rowconfigure(0, weight=1)

        self._render_fin("initial")

        # 배당 탭
        div_tab = tabview.tab("배당")
        div_tab.grid_columnconfigure(0, weight=1)
        div_tab.grid_rowconfigure(1, weight=1)

        self._div_title = ctk.CTkLabel(
            div_tab, text="기업분석 — 배당",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self._div_title.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self._div_content = ctk.CTkFrame(div_tab, fg_color="transparent")
        self._div_content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._div_content.grid_columnconfigure(0, weight=1)
        self._div_content.grid_rowconfigure(0, weight=1)

        self._render_div("initial")

        # 타법인출자 탭
        eqt_tab = tabview.tab("타법인출자")
        eqt_tab.grid_columnconfigure(0, weight=1)
        eqt_tab.grid_rowconfigure(1, weight=1)

        self._eqt_title = ctk.CTkLabel(
            eqt_tab, text="기업분석 — 타법인출자",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self._eqt_title.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self._eqt_content = ctk.CTkFrame(eqt_tab, fg_color="transparent")
        self._eqt_content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._eqt_content.grid_columnconfigure(0, weight=1)
        self._eqt_content.grid_rowconfigure(0, weight=1)

        self._render_equity("initial")

        # 재무지표 탭
        ratio_tab = tabview.tab("재무지표")
        ratio_tab.grid_columnconfigure(0, weight=1)
        ratio_tab.grid_rowconfigure(1, weight=1)

        self._ratio_title = ctk.CTkLabel(
            ratio_tab, text="기업분석 — 재무지표",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self._ratio_title.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self._ratio_content = ctk.CTkFrame(ratio_tab, fg_color="transparent")
        self._ratio_content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._ratio_content.grid_columnconfigure(0, weight=1)
        self._ratio_content.grid_rowconfigure(0, weight=1)

        self._render_ratio("initial")

        # 감사 탭
        adt_tab = tabview.tab("감사")
        adt_tab.grid_columnconfigure(0, weight=1)
        adt_tab.grid_rowconfigure(1, weight=1)

        self._adt_title = ctk.CTkLabel(
            adt_tab, text="기업분석 — 감사",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self._adt_title.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self._adt_content = ctk.CTkScrollableFrame(adt_tab, fg_color="transparent")
        self._adt_content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._adt_content.grid_columnconfigure(0, weight=1)

        self._render_audit("initial")

        # 최대주주 탭
        shr_tab = tabview.tab("최대주주")
        shr_tab.grid_columnconfigure(0, weight=1)
        shr_tab.grid_rowconfigure(1, weight=1)

        self._shr_title = ctk.CTkLabel(
            shr_tab, text="기업분석 — 최대주주",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self._shr_title.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self._shr_content = ctk.CTkScrollableFrame(shr_tab, fg_color="transparent")
        self._shr_content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._shr_content.grid_columnconfigure(0, weight=1)

        self._render_shareholder("initial")

        # 직원 탭
        emp_tab = tabview.tab("직원")
        emp_tab.grid_columnconfigure(0, weight=1)
        emp_tab.grid_rowconfigure(1, weight=1)

        self._emp_title = ctk.CTkLabel(
            emp_tab, text="기업분석 — 직원",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self._emp_title.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self._emp_content = ctk.CTkFrame(emp_tab, fg_color="transparent")
        self._emp_content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._emp_content.grid_columnconfigure(0, weight=1)
        self._emp_content.grid_rowconfigure(0, weight=1)

        self._render_employee("initial")

        # 자본변동 탭
        cap_tab = tabview.tab("자본변동")
        cap_tab.grid_columnconfigure(0, weight=1)
        cap_tab.grid_rowconfigure(1, weight=1)

        self._cap_title = ctk.CTkLabel(
            cap_tab, text="기업분석 — 자본변동",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self._cap_title.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self._cap_content = ctk.CTkScrollableFrame(cap_tab, fg_color="transparent")
        self._cap_content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._cap_content.grid_columnconfigure(0, weight=1)

        self._render_capital("initial")

    def _render_fin(self, state, data=None, corp_name="", years=None):
        """핵심재무 탭 컨텐츠를 갱신한다. state: 'initial'|'loading'|'done'|'error'"""
        for w in self._fin_content.winfo_children():
            w.destroy()

        if state == "initial":
            ctk.CTkLabel(self._fin_content,
                         text="회사를 선택하면 재무 데이터가 표시됩니다.",
                         text_color="gray").grid(row=0, column=0)
            return

        if state == "loading":
            ctk.CTkLabel(self._fin_content,
                         text="불러오는 중...", text_color="gray").grid(row=0, column=0)
            return

        if state == "no_ofs":
            ctk.CTkLabel(self._fin_content,
                         text="해당 회사는 별도 재무제표를 별도로 공시하지 않습니다.",
                         text_color="orange").grid(row=0, column=0, padx=12, pady=12)
            return

        if state == "error":
            ctk.CTkLabel(self._fin_content,
                         text="데이터를 불러오지 못했습니다.", text_color="#FF6B6B").grid(row=0, column=0)
            return

        # ── 전체 N/A 감지 → 비지원 안내 ──
        all_none = all(
            row.get(label) is None
            for row in data
            for label in _FIN_LABELS
        )
        outer = ctk.CTkFrame(self._fin_content, fg_color="transparent")
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

    # ── 이벤트 핸들러 ──────────────────────────────────────────────────────────

    def set_selected_corp(self, corp):
        """다운로드 패널이 회사를 고르면 분석 쪽을 갱신한다. (Task 10에서 정리)"""
        self.selected_corp = corp
        self._analysis_label.configure(text=corp["corp_name"])
        self._update_titles(corp["corp_name"])
        self._load_financials()
        self._load_dividends()
        self._load_equity()
        self._load_audit()
        self._load_shareholder()
        self._load_employee()
        self._load_capital()

    def _on_fs_toggle(self, _value):
        if self.selected_corp:
            self._update_titles()
            self._load_financials()

    def _update_titles(self, name=None):
        if name is None:
            name = self.selected_corp["corp_name"] if self.selected_corp else ""
        yr = int(self.download_panel.end_year_var.get()) - 1
        fs_label = "연결(CFS)" if self.fs_seg.get() == "연결" else "별도(OFS)"
        rng = f"{yr-2}~{yr}년"
        self._fin_title.configure(text=f"{name} · {rng} · {fs_label}")
        self._div_title.configure(text=f"{name} · {rng}")
        self._eqt_title.configure(text=f"{name} · {yr}년")
        self._ratio_title.configure(text=f"{name} · {rng} · {fs_label}")
        self._adt_title.configure(text=f"{name} · {rng}")
        self._shr_title.configure(text=f"{name} · {yr}년")
        self._emp_title.configure(text=f"{name} · {yr}년")
        self._cap_title.configure(text=f"{name} · {rng}")

    def _load_financials(self):
        corp     = self.selected_corp
        api_key  = self.download_panel.api_key_var.get().strip()
        end_year = str(int(self.download_panel.end_year_var.get()) - 1)
        fs_div   = "CFS" if self.fs_seg.get() == "연결" else "OFS"

        self.after(0, lambda: self._render_fin("loading"))
        self.after(0, lambda: self._render_ratio("loading"))

        def run():
            try:
                data  = get_key_financials_3y(
                    api_key, corp["corp_code"], end_year,
                    fs_div=fs_div, log_fn=self.download_panel.log
                )
                # OFS 데이터가 전 연도 없으면 안내
                if fs_div == "OFS" and all(not r.get("available") for r in data):
                    self.after(0, lambda: self._render_fin("no_ofs"))
                    self.after(0, lambda: self._render_ratio("no_ofs"))
                    return
                years  = [r["year"] for r in data]
                try:
                    ext = get_extended_financials_3y(
                        api_key, corp["corp_code"], end_year, log_fn=self.download_panel.log
                    )
                except Exception as e:
                    self.download_panel.log(f"확장재무 조회 실패 (무시): {e}")
                    ext = None
                ratios = calculate_financial_ratios(data, extended_3y=ext)
                self._fin_data = data
                self.after(0, lambda: self._render_fin("done", data=data,
                                                        corp_name=corp["corp_name"],
                                                        years=years))
                self.after(0, lambda: self._render_ratio("done", data=ratios, years=years))
            except Exception as e:
                self.download_panel.log(f"재무 데이터 오류: {e}")
                self.after(0, lambda: self._render_fin("error"))
                self.after(0, lambda: self._render_ratio("error"))

        threading.Thread(target=run, daemon=True).start()

    def _render_div(self, state, data=None, years=None):
        """배당 탭 컨텐츠를 갱신한다. state: 'initial'|'loading'|'done'|'error'"""
        for w in self._div_content.winfo_children():
            w.destroy()

        if state == "initial":
            ctk.CTkLabel(self._div_content,
                         text="회사를 선택하면 배당 데이터가 표시됩니다.",
                         text_color="gray").grid(row=0, column=0)
            return
        if state == "loading":
            ctk.CTkLabel(self._div_content,
                         text="불러오는 중...", text_color="gray").grid(row=0, column=0)
            return
        if state == "error":
            ctk.CTkLabel(self._div_content,
                         text="데이터를 불러오지 못했습니다.", text_color="#FF6B6B").grid(row=0, column=0)
            return

        f = ctk.CTkFrame(self._div_content, fg_color="transparent")
        f.grid(row=0, column=0, sticky="n", padx=8, pady=8)

        col_w = 130

        # 헤더
        ctk.CTkLabel(f, text="항목", font=ctk.CTkFont(weight="bold"),
                     width=160, anchor="w").grid(row=0, column=0, padx=(0, 8), pady=4, sticky="w")
        for ci, yr in enumerate(years):
            ctk.CTkLabel(f, text=f"{yr}년", font=ctk.CTkFont(weight="bold"),
                         width=col_w, anchor="e").grid(row=0, column=ci+1, padx=4, pady=4)

        sep = ctk.CTkFrame(f, height=1, fg_color="gray40")
        sep.grid(row=1, column=0, columnspan=len(years)+1, sticky="ew", pady=2)

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

    def _load_dividends(self):
        corp     = self.selected_corp
        api_key  = self.download_panel.api_key_var.get().strip()
        end_year = str(int(self.download_panel.end_year_var.get()) - 1)

        self.after(0, lambda: self._render_div("loading"))

        def run():
            try:
                data  = get_dividend_info_3y(api_key, corp["corp_code"], end_year, log_fn=self.download_panel.log)
                years = [r["year"] for r in data]
                self.after(0, lambda: self._render_div("done", data=data, years=years))
            except Exception as e:
                self.download_panel.log(f"배당 데이터 오류: {e}")
                self.after(0, lambda: self._render_div("error"))

        threading.Thread(target=run, daemon=True).start()

    def _render_ratio(self, state, data=None, years=None):
        """재무지표 탭 컨텐츠 갱신. state: 'initial'|'loading'|'done'|'error'"""
        for w in self._ratio_content.winfo_children():
            w.destroy()

        msgs = {
            "initial": ("회사를 선택하면 재무지표가 표시됩니다.", "gray"),
            "loading": ("불러오는 중...",                     "gray"),
            "error":   ("데이터를 불러오지 못했습니다.",         "#FF6B6B"),
            "no_ofs":  ("별도 재무제표 데이터가 없어 재무지표를 계산할 수 없습니다.", "orange"),
        }
        if state in msgs:
            text, color = msgs[state]
            ctk.CTkLabel(self._ratio_content, text=text, text_color=color).grid(
                row=0, column=0, padx=12, pady=12)
            return

        f = ctk.CTkFrame(self._ratio_content, fg_color="transparent")
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

    def _render_equity(self, state, data=None, year=None, corp_name=""):
        """타법인출자 탭 컨텐츠 갱신. state: 'initial'|'loading'|'done'|'error'"""
        for w in self._eqt_content.winfo_children():
            w.destroy()

        if state == "initial":
            ctk.CTkLabel(self._eqt_content,
                         text="회사를 선택하면 출자 현황이 표시됩니다.",
                         text_color="gray").grid(row=0, column=0)
            return
        if state == "loading":
            ctk.CTkLabel(self._eqt_content,
                         text="불러오는 중...", text_color="gray").grid(row=0, column=0)
            return
        if state == "error":
            ctk.CTkLabel(self._eqt_content,
                         text="데이터를 불러오지 못했습니다.", text_color="#FF6B6B").grid(row=0, column=0)
            return
        if not data:
            ctk.CTkLabel(self._eqt_content,
                         text="출자 내역이 없습니다.", text_color="gray").grid(row=0, column=0)
            return

        # ── 정보 헤더 ──
        info_frame = ctk.CTkFrame(self._eqt_content, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 0))
        ctk.CTkLabel(info_frame,
                     text=f"총 {len(data)}건  ({year}년 기준)",
                     text_color="gray70").pack(side="left")

        # ── 스크롤 테이블 ──
        scroll = ctk.CTkScrollableFrame(self._eqt_content)
        scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._eqt_content.grid_rowconfigure(1, weight=1)

        COL_W = [200, 105, 72, 115]   # 법인명, 최초취득일, 지분율, 기말장부가액
        HEADERS = ["법인명", "최초취득일", "지분율", "기말장부가액"]

        # 헤더 행
        for ci, (h, w) in enumerate(zip(HEADERS, COL_W)):
            anchor = "w" if ci == 0 else "e"
            ctk.CTkLabel(scroll, text=h, font=ctk.CTkFont(weight="bold"),
                         width=w, anchor=anchor).grid(
                row=0, column=ci, padx=(0 if ci else 4, 4), pady=4, sticky=anchor
            )

        sep = ctk.CTkFrame(scroll, height=1, fg_color="gray40")
        sep.grid(row=1, column=0, columnspan=4, sticky="ew", pady=2)

        def _pct_color(pct):
            if pct is None:  return "gray50"
            if pct >= 50:    return "#63B3ED"   # 자회사 — 파랑
            if pct >= 20:    return "#68D391"   # 관계사 — 초록
            return "gray70"                      # 기타

        for ri, row in enumerate(data):
            pct   = row["지분율"]
            bv    = row["기말장부가액"]
            pct_s = f"{pct:.1f}%" if pct is not None else "N/A"
            bv_s, bv_c = fmt_val(bv) if bv is not None else ("N/A", "gray50")
            row_idx = ri + 2

            cells = [
                (row["법인명"],   "w", "white"),
                (row["최초취득일"], "e", "gray70"),
                (pct_s,          "e", _pct_color(pct)),
                (bv_s,           "e", bv_c),
            ]
            for ci, (text, anchor, color) in enumerate(cells):
                ctk.CTkLabel(scroll, text=text, text_color=color,
                             width=COL_W[ci], anchor=anchor).grid(
                    row=row_idx, column=ci,
                    padx=(0 if ci else 4, 4), pady=2, sticky=anchor
                )

    def _load_equity(self):
        corp     = self.selected_corp
        api_key  = self.download_panel.api_key_var.get().strip()
        end_year = str(int(self.download_panel.end_year_var.get()) - 1)

        self.after(0, lambda: self._render_equity("loading"))

        def run():
            try:
                data = get_equity_investments(
                    api_key, corp["corp_code"], end_year, log_fn=self.download_panel.log
                )
                self.after(0, lambda: self._render_equity(
                    "done", data=data, year=end_year, corp_name=corp["corp_name"]
                ))
            except Exception as e:
                self.download_panel.log(f"타법인출자 오류: {e}")
                self.after(0, lambda: self._render_equity("error"))

        threading.Thread(target=run, daemon=True).start()

    # ── 감사 탭 ──────────────────────────────────────────────────────────────
    def _load_audit(self):
        corp     = self.selected_corp
        api_key  = self.download_panel.api_key_var.get().strip()
        end_year = str(int(self.download_panel.end_year_var.get()) - 1)

        self.after(0, lambda: self._render_audit("loading"))

        def run():
            try:
                data = get_audit_opinion_3y(
                    api_key, corp["corp_code"], end_year, log_fn=self.download_panel.log
                )
                self.after(0, lambda: self._render_audit("done", data=data))
            except Exception as e:
                self.download_panel.log(f"감사의견 오류: {e}")
                self.after(0, lambda: self._render_audit("error"))

        threading.Thread(target=run, daemon=True).start()

    def _render_audit(self, state, data=None):
        for w in self._adt_content.winfo_children():
            w.destroy()

        msgs = {
            "initial": ("회사를 선택하면 감사 정보가 표시됩니다.", "gray"),
            "loading": ("불러오는 중...", "gray"),
            "error":   ("데이터를 가져오지 못했습니다.", "#e05252"),
        }
        if state in msgs:
            text, color = msgs[state]
            ctk.CTkLabel(self._adt_content, text=text, text_color=color).grid(
                row=0, column=0, padx=8, pady=8, sticky="w"
            )
            return

        bold = ctk.CTkFont(weight="bold")
        for ri, row in enumerate(data):
            yr = row["year"]
            # 연도 헤더
            ctk.CTkLabel(
                self._adt_content,
                text=f"■ {yr}년도",
                font=bold, text_color="white"
            ).grid(row=ri * 6, column=0, padx=8, pady=(12 if ri else 4, 2), sticky="w")

            # 감사인·의견 한 줄
            opinion_color = "white" if "적정" in row["감사의견"] else "#e05252"
            ctk.CTkLabel(
                self._adt_content,
                text=f"감사인: {row['감사인']}   |   감사의견: {row['감사의견']}",
                text_color=opinion_color,
            ).grid(row=ri * 6 + 1, column=0, padx=16, pady=2, sticky="w")

            # 강조사항
            ctk.CTkLabel(self._adt_content, text="▸ 강조사항",
                         text_color="gray70").grid(
                row=ri * 6 + 2, column=0, padx=16, pady=(6, 0), sticky="w"
            )
            ctk.CTkTextbox(
                self._adt_content, height=50, wrap="word",
                fg_color="#2a2a2a", border_width=0,
            ).grid(row=ri * 6 + 3, column=0, padx=24, pady=(0, 4), sticky="ew")
            tb_emp = self._adt_content.grid_slaves(row=ri * 6 + 3, column=0)[0]
            tb_emp.insert("end", row["강조사항"])
            tb_emp.configure(state="disabled")

            # 핵심감사사항
            ctk.CTkLabel(self._adt_content, text="▸ 핵심감사사항",
                         text_color="gray70").grid(
                row=ri * 6 + 4, column=0, padx=16, pady=(6, 0), sticky="w"
            )
            tb_core = ctk.CTkTextbox(
                self._adt_content, height=110, wrap="word",
                fg_color="#2a2a2a", border_width=0,
            )
            tb_core.grid(row=ri * 6 + 5, column=0, padx=24, pady=(0, 4), sticky="ew")
            tb_core.insert("end", row["핵심감사사항"])
            tb_core.configure(state="disabled")

        self._adt_content.grid_columnconfigure(0, weight=1)

    # ── 최대주주 탭 ───────────────────────────────────────────────────────────
    def _load_shareholder(self):
        corp     = self.selected_corp
        api_key  = self.download_panel.api_key_var.get().strip()
        end_year = str(int(self.download_panel.end_year_var.get()) - 1)

        self.after(0, lambda: self._render_shareholder("loading"))

        def run():
            try:
                data = get_major_shareholder(
                    api_key, corp["corp_code"], end_year, log_fn=self.download_panel.log
                )
                self.after(0, lambda: self._render_shareholder(
                    "done", data=data, year=end_year
                ))
            except Exception as e:
                self.download_panel.log(f"최대주주 오류: {e}")
                self.after(0, lambda: self._render_shareholder("error"))

        threading.Thread(target=run, daemon=True).start()

    def _render_shareholder(self, state, data=None, year=None):
        for w in self._shr_content.winfo_children():
            w.destroy()

        msgs = {
            "initial": ("회사를 선택하면 최대주주 정보가 표시됩니다.", "gray"),
            "loading": ("불러오는 중...", "gray"),
            "error":   ("데이터를 가져오지 못했습니다.", "#e05252"),
        }
        if state in msgs:
            text, color = msgs[state]
            ctk.CTkLabel(self._shr_content, text=text, text_color=color).grid(
                row=0, column=0, padx=8, pady=8, sticky="w"
            )
            return

        if not data:
            ctk.CTkLabel(self._shr_content,
                         text="최대주주 정보 없음", text_color="gray").grid(
                row=0, column=0, padx=8, pady=8
            )
            return

        f = ctk.CTkFrame(self._shr_content, fg_color="transparent")
        f.grid(row=0, column=0, sticky="nw", padx=8, pady=8)

        bold = ctk.CTkFont(weight="bold")
        headers = [("주주명", 180, "w"), ("관계", 100, "w"),
                   ("주식종류", 90, "w"), ("기말주식수", 130, "e"), ("지분율(%)", 90, "e")]
        for ci, (h, w, anchor) in enumerate(headers):
            ctk.CTkLabel(f, text=h, font=bold, width=w, anchor=anchor).grid(
                row=0, column=ci, padx=4, pady=4
            )

        ctk.CTkFrame(f, height=1, fg_color="gray40").grid(
            row=1, column=0, columnspan=len(headers), sticky="ew", pady=2
        )

        anchors = ["w", "w", "w", "e", "e"]
        widths  = [180, 100, 90, 130, 90]
        grid_row = 2
        prev_is_detail = False
        for row in data:
            is_total = row["주주명"] == "계"
            # 합계 행 앞에 구분선
            if is_total and prev_is_detail:
                ctk.CTkFrame(f, height=1, fg_color="gray30").grid(
                    row=grid_row, column=0, columnspan=len(headers),
                    sticky="ew", pady=2
                )
                grid_row += 1
            color = ("white" if row["관계"] == "최대주주"
                     else "gray50" if is_total else "gray80")
            vals = [
                row["주주명"],
                row["관계"],
                row["주식종류"],
                f"{row['기말주식수']:,}" if row["기말주식수"] is not None else "-",
                f"{row['지분율']:.2f}%" if row["지분율"] is not None else "-",
            ]
            for ci, (val, anc, wd) in enumerate(zip(vals, anchors, widths)):
                ctk.CTkLabel(f, text=val, text_color=color,
                             width=wd, anchor=anc).grid(
                    row=grid_row, column=ci, padx=4, pady=3
                )
            prev_is_detail = not is_total
            grid_row += 1

    # ── 직원 탭 ──────────────────────────────────────────────────────────────
    def _load_employee(self):
        corp     = self.selected_corp
        api_key  = self.download_panel.api_key_var.get().strip()
        end_year = str(int(self.download_panel.end_year_var.get()) - 1)

        self.after(0, lambda: self._render_employee("loading"))

        def run():
            try:
                data = get_employee_status(
                    api_key, corp["corp_code"], end_year, log_fn=self.download_panel.log
                )
                self.after(0, lambda: self._render_employee("done", data=data, year=end_year))
            except Exception as e:
                self.download_panel.log(f"직원 현황 오류: {e}")
                self.after(0, lambda: self._render_employee("error"))

        threading.Thread(target=run, daemon=True).start()

    def _render_employee(self, state, data=None, year=None):
        for w in self._emp_content.winfo_children():
            w.destroy()

        msgs = {
            "initial": ("회사를 선택하면 직원 정보가 표시됩니다.", "gray"),
            "loading": ("불러오는 중...", "gray"),
            "error":   ("데이터를 가져오지 못했습니다.", "#e05252"),
        }
        if state in msgs:
            text, color = msgs[state]
            ctk.CTkLabel(self._emp_content, text=text, text_color=color).grid(
                row=0, column=0, padx=8, pady=8
            )
            return

        f = ctk.CTkFrame(self._emp_content, fg_color="transparent")
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

    # ── 자본변동 탭 ───────────────────────────────────────────────────────────
    def _load_capital(self):
        corp     = self.selected_corp
        api_key  = self.download_panel.api_key_var.get().strip()
        end_year = str(int(self.download_panel.end_year_var.get()) - 1)

        self.after(0, lambda: self._render_capital("loading"))

        def run():
            try:
                data = get_capital_changes_3y(
                    api_key, corp["corp_code"], end_year, log_fn=self.download_panel.log
                )
                self.after(0, lambda: self._render_capital("done", data=data))
            except Exception as e:
                self.download_panel.log(f"자본변동 오류: {e}")
                self.after(0, lambda: self._render_capital("error"))

        threading.Thread(target=run, daemon=True).start()

    def _render_capital(self, state, data=None):
        for w in self._cap_content.winfo_children():
            w.destroy()

        msgs = {
            "initial": ("회사를 선택하면 자본변동 정보가 표시됩니다.", "gray"),
            "loading": ("불러오는 중...", "gray"),
            "error":   ("데이터를 가져오지 못했습니다.", "#e05252"),
        }
        if state in msgs:
            text, color = msgs[state]
            ctk.CTkLabel(self._cap_content, text=text, text_color=color).grid(
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
            ctk.CTkLabel(self._cap_content, text=f"■ {yr}년도", font=bold).grid(
                row=row_idx, column=0, padx=8, pady=(12 if yi else 4, 4), sticky="w"
            )
            row_idx += 1

            # ▸ 증자(감자)
            ctk.CTkLabel(self._cap_content, text="▸ 증자(감자) 현황",
                         text_color="gray60").grid(row=row_idx, column=0, padx=16, pady=(2, 0), sticky="w")
            row_idx += 1
            if not issu:
                ctk.CTkLabel(self._cap_content, text="  해당사항 없음",
                             text_color="gray60").grid(row=row_idx, column=0, padx=28, pady=2, sticky="w")
                row_idx += 1
            else:
                sub = ctk.CTkFrame(self._cap_content, fg_color="transparent")
                sub.grid(row=row_idx, column=0, padx=24, pady=4, sticky="nw")
                row_idx += 1
                for ci, (h, w) in enumerate(zip(hdrs, wids)):
                    ctk.CTkLabel(sub, text=h, font=bold, width=w, anchor="w").grid(
                        row=0, column=ci, padx=4, pady=2)
                ctk.CTkFrame(sub, height=1, fg_color="gray40").grid(
                    row=1, column=0, columnspan=len(hdrs), sticky="ew", pady=1)
                for ri, item in enumerate(issu):
                    for ci, (key, w) in enumerate(zip(keys, wids)):
                        ctk.CTkLabel(sub, text=item.get(key, "-"), width=w,
                                     anchor="w").grid(row=ri + 2, column=ci, padx=4, pady=3)

            # ▸ 자기주식
            ctk.CTkLabel(self._cap_content, text="▸ 자기주식 취득·처분",
                         text_color="gray60").grid(row=row_idx, column=0, padx=16, pady=(6, 0), sticky="w")
            row_idx += 1
            if not treas:
                ctk.CTkLabel(self._cap_content, text="  해당사항 없음",
                             text_color="gray60").grid(row=row_idx, column=0, padx=28, pady=2, sticky="w")
                row_idx += 1
            else:
                sub2 = ctk.CTkFrame(self._cap_content, fg_color="transparent")
                sub2.grid(row=row_idx, column=0, padx=24, pady=4, sticky="nw")
                row_idx += 1
                for ci, (h, w) in enumerate(zip(hdrs2, wids2)):
                    ctk.CTkLabel(sub2, text=h, font=bold, width=w,
                                 anchor=("w" if ci == 0 else "e")).grid(
                        row=0, column=ci, padx=4, pady=2)
                ctk.CTkFrame(sub2, height=1, fg_color="gray40").grid(
                    row=1, column=0, columnspan=len(hdrs2), sticky="ew", pady=1)
                for ri, item in enumerate(treas):
                    for ci, (key, w) in enumerate(zip(keys2, wids2)):
                        anchor = "w" if ci == 0 else "e"
                        ctk.CTkLabel(sub2, text=item.get(key, "-"), width=w,
                                     anchor=anchor).grid(row=ri + 2, column=ci, padx=4, pady=3)

            # 연도 사이 구분선
            if yi < len(data) - 1:
                ctk.CTkFrame(self._cap_content, height=1, fg_color="gray30").grid(
                    row=row_idx, column=0, sticky="ew", padx=8, pady=8)
                row_idx += 1

        self._cap_content.grid_columnconfigure(0, weight=1)


if __name__ == "__main__":
    app = DartApp()
    app.mainloop()
