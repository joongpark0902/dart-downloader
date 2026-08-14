import os
import re
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

import settings
import ui_theme
from dart_client import list_disclosures, load_corp_list, search_company
from dart_viewer import convert_to_html
from downloader import download_document
from settings import load_api_key, save_api_key


def _report_year(report_nm):
    """
    report_nm 끝의 결산기 표기에서 사업연도를 뽑는다.
    '사업보고서 (2024.12)' → '2024',  '연결감사보고서 (2025.12)' → '2025'
    """
    if "(" in report_nm:
        tail = report_nm.split("(")[-1][:4]
        if tail.isdigit():
            return tail
    return "unknown"


def _report_folder(report_nm, report_types):
    """
    저장 폴더에 쓸 보고서 유형명. 연결감사보고서는 별도 폴더로 분리해
    같은 해 별도·연결 감사보고서가 한 폴더에 섞이지 않게 한다.
    """
    if "연결감사보고서" in report_nm:
        return "연결감사보고서"
    return next((rt for rt in report_types if rt in report_nm), "기타")


_QUARTER_BY_MONTH = {"03": "1분기", "06": "2분기", "09": "3분기", "12": "4분기"}


def _report_basename(report_nm, rtype, year):
    """
    저장 파일명의 앞부분. 기본은 '보고서유형_연도'.
    분기보고서만 한 해에 두 번(1·3분기) 나오므로 분기를 덧붙여 구분한다.
      '분기보고서 (2025.03)' → '분기보고서_2025_1분기'
    """
    base = f"{rtype}_{year}"
    if rtype != "분기보고서":
        return base
    m = re.search(r"\((\d{4})\.(\d{2})", report_nm)
    if not m:
        return base
    month = m.group(2)
    return f"{base}_{_QUARTER_BY_MONTH.get(month, month + '월')}"


class DownloadPanel:
    """좌측 다운로드 패널. 검색·조회옵션·로그·다운로드를 담는다."""

    def __init__(self, parent, app):
        self.app = app
        self.frame = ctk.CTkFrame(parent, fg_color=ui_theme.PANEL_BG)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(2, weight=1)

        self.corp_list = None
        self._search_results = []

        self._build_top(self.frame)
        self._build_mid(self.frame)
        self._build_log(self.frame)

    def log(self, msg):
        """로그 상자에 한 줄 붙인다. 작업 스레드에서 불러도 안전하다."""
        def _upd():
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"[{ts}] {msg}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.app.after(0, _upd)

    # ── 좌측 패널 조립 ────────────────────────────────────────────────────────

    def _build_top(self, parent):
        f = ctk.CTkFrame(parent, fg_color=ui_theme.SURFACE, border_width=1, border_color=ui_theme.BORDER)
        f.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        f.grid_columnconfigure(1, weight=1)
        f.grid_columnconfigure(4, weight=2)

        ctk.CTkLabel(f, text="인증키").grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")
        self.api_key_var = tk.StringVar(value=load_api_key())
        ctk.CTkEntry(f, textvariable=self.api_key_var, placeholder_text="DART Open API 인증키 입력").grid(
            row=0, column=1, padx=4, pady=8, sticky="ew"
        )
        ctk.CTkButton(f, text="저장", width=56, command=self._save_key).grid(
            row=0, column=2, padx=(4, 0), pady=8
        )
        ctk.CTkLabel(f, text="저장폴더").grid(row=0, column=3, padx=(12, 6), pady=8, sticky="w")
        self.save_dir_var = tk.StringVar(value=settings.DEFAULT_DOWNLOADS)
        ctk.CTkEntry(f, textvariable=self.save_dir_var).grid(
            row=0, column=4, padx=4, pady=8, sticky="ew"
        )
        ctk.CTkButton(f, text="찾아보기", width=80, command=self._browse_dir).grid(
            row=0, column=5, padx=(4, 10), pady=8
        )

    def _build_mid(self, parent):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        f.grid_columnconfigure(0, weight=1)

        self._build_search(f)
        self._build_options(f)

    def _build_search(self, parent):
        f = ctk.CTkFrame(parent, fg_color=ui_theme.SURFACE, border_width=1, border_color=ui_theme.BORDER)
        f.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(f, text="회사 검색", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=10, pady=(10, 6), sticky="w"
        )

        row = ctk.CTkFrame(f, fg_color="transparent")
        row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10)
        row.grid_columnconfigure(0, weight=1)

        self.search_var = tk.StringVar()
        entry = ctk.CTkEntry(row, textvariable=self.search_var, placeholder_text="회사명 입력 후 엔터")
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        entry.bind("<Return>", lambda _: self._do_search())
        ctk.CTkButton(row, text="검색", width=64, command=self._do_search).grid(row=0, column=1)

        lb_wrap = ctk.CTkFrame(f, fg_color="transparent")
        lb_wrap.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(8, 0))

        self.listbox = tk.Listbox(
            lb_wrap, height=6, selectmode=tk.SINGLE, **ui_theme.LISTBOX_STYLE
        )
        sb = tk.Scrollbar(lb_wrap, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        self.selected_label = ctk.CTkLabel(f, text="선택된 회사: 없음", text_color=ui_theme.TEXT_SECONDARY)
        self.selected_label.grid(row=3, column=0, columnspan=2, padx=10, pady=(6, 10), sticky="w")

    def _build_options(self, parent):
        f = ctk.CTkFrame(parent, fg_color=ui_theme.SURFACE, border_width=1, border_color=ui_theme.BORDER)
        f.grid(row=0, column=1, sticky="ns", padx=(4, 8), pady=8)

        ctk.CTkLabel(f, text="조회 옵션", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(10, 8), sticky="w"
        )

        ctk.CTkLabel(f, text="시작연도").grid(row=1, column=0, padx=(12, 6), pady=4, sticky="w")
        self.bgn_year_var = tk.StringVar(value="2021")
        ctk.CTkEntry(f, textvariable=self.bgn_year_var, width=78).grid(
            row=1, column=1, padx=(0, 12), pady=4, sticky="w"
        )

        ctk.CTkLabel(f, text="종료연도").grid(row=2, column=0, padx=(12, 6), pady=4, sticky="w")
        self.end_year_var = tk.StringVar(value="2026")
        ctk.CTkEntry(f, textvariable=self.end_year_var, width=78).grid(
            row=2, column=1, padx=(0, 12), pady=4, sticky="w"
        )

        ctk.CTkLabel(f, text="보고서 유형").grid(
            row=3, column=0, columnspan=2, padx=12, pady=(10, 4), sticky="w"
        )

        self.chk_annual  = tk.BooleanVar(value=True)
        self.chk_semi    = tk.BooleanVar(value=True)
        self.chk_quarter = tk.BooleanVar(value=True)
        self.chk_audit   = tk.BooleanVar(value=False)

        for i, (text, var) in enumerate([
            ("사업보고서", self.chk_annual),
            ("반기보고서", self.chk_semi),
            ("분기보고서", self.chk_quarter),
            ("감사보고서", self.chk_audit),
        ], start=4):
            ctk.CTkCheckBox(f, text=text, variable=var).grid(
                row=i, column=0, columnspan=2, padx=12, pady=3, sticky="w"
            )

        ctk.CTkLabel(
            f, text="※ 감사보고서 = 단독공시(별도·연결)\n     비상장 외감법인은 이것만 있습니다",
            text_color=ui_theme.TEXT_SECONDARY, justify="left", anchor="w",
            font=ctk.CTkFont(size=11),
        ).grid(row=8, column=0, columnspan=2, padx=(12, 12), pady=(0, 2), sticky="w")

        ctk.CTkLabel(f, text="저장 형식").grid(
            row=9, column=0, padx=(12, 6), pady=(10, 4), sticky="w"
        )
        self.fmt_var = tk.StringVar(value="읽기용 HTML만")
        ctk.CTkOptionMenu(
            f, variable=self.fmt_var,
            values=["원본 XML만", "원본 + 읽기용 HTML", "읽기용 HTML만"],
            width=160,
        ).grid(row=9, column=1, padx=(0, 12), pady=(10, 4), sticky="w")

        self.download_btn = ctk.CTkButton(
            f, text="다운로드", height=38, command=self._do_download
        )
        self.download_btn.grid(row=10, column=0, columnspan=2, padx=12, pady=(6, 12), sticky="ew")

    def _build_log(self, parent):
        f = ctk.CTkFrame(parent, fg_color=ui_theme.SURFACE, border_width=1, border_color=ui_theme.BORDER)
        f.grid(row=2, column=0, sticky="nsew", padx=8, pady=(4, 8))
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(f, text="로그", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(8, 0), sticky="w"
        )
        self.log_box = ctk.CTkTextbox(
            f, state="disabled", font=(ui_theme.FONT_FAMILY_MONO, 10), wrap="word",
            fg_color=ui_theme.SURFACE, border_width=1, border_color=ui_theme.BORDER,
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 10))

    # ── 이벤트 핸들러 ──────────────────────────────────────────────────────────

    def _save_key(self):
        key = self.api_key_var.get().strip()
        if not key:
            self.log("저장할 인증키가 비어 있습니다.")
            return
        try:
            path = save_api_key(key)
        except OSError as e:
            self.log(f"인증키 저장 실패: {e}")
            return
        self.log(f"인증키를 저장했습니다 → {path}")
        self.log("※ config.txt에는 본인 키가 들어 있습니다. 폴더째 남에게 전달하지 마세요.")

    def _browse_dir(self):
        path = filedialog.askdirectory(initialdir=self.save_dir_var.get())
        if path:
            self.save_dir_var.set(path)

    def _do_search(self):
        keyword = self.search_var.get().strip()
        if not keyword:
            return

        def run():
            api_key = self.api_key_var.get().strip()
            if self.corp_list is None:
                try:
                    self.corp_list = load_corp_list(
                        api_key, cache_path=settings.CORPCODE_PATH, log_fn=self.log
                    )
                except Exception as e:
                    self.log(f"오류: {e}")
                    return
            results = search_company(self.corp_list, keyword)
            self.log(f"'{keyword}' 검색 결과: {len(results)}건")
            self.app.after(0, lambda: self._fill_listbox(results))

        threading.Thread(target=run, daemon=True).start()

    def _fill_listbox(self, results):
        self._search_results = results
        self.listbox.delete(0, tk.END)
        for r in results:
            mark = "     " if r.get("stock_code") else " [비상장]"
            self.listbox.insert(tk.END, f"  {r['corp_code']}{mark} {r['corp_name']}")

    def _on_select(self, _event):
        sel = self.listbox.curselection()
        if not sel:
            return
        corp = self._search_results[sel[0]]
        name = corp["corp_name"]
        code = corp["corp_code"]
        self.selected_label.configure(
            text=f"선택된 회사: {name}  ({code})", text_color=ui_theme.TEXT_PRIMARY
        )

        if not corp.get("stock_code"):
            self.log(
                f"{name}: 비상장 회사입니다. 사업보고서를 제출하지 않는 외감법인이면 "
                "'감사보고서'를 체크해야 원문을 받을 수 있고, "
                "우측 분석 탭은 값이 비어 있을 수 있습니다."
            )

        self.app.set_selected_corp(corp)

    def _do_download(self):
        if not self.app.selected_corp:
            self.log("회사를 먼저 선택하세요.")
            return

        report_types = [
            rt for rt, var in [
                ("사업보고서", self.chk_annual),
                ("반기보고서", self.chk_semi),
                ("분기보고서", self.chk_quarter),
                ("감사보고서", self.chk_audit),
            ] if var.get()
        ]
        if not report_types:
            self.log("보고서 유형을 하나 이상 선택하세요.")
            return

        api_key     = self.api_key_var.get().strip()
        corp        = self.app.selected_corp
        bgn_de      = self.bgn_year_var.get().strip() + "0101"
        end_de      = self.end_year_var.get().strip() + "1231"
        base_dir    = self.save_dir_var.get()
        fmt         = self.fmt_var.get()
        make_html   = fmt in ("원본 + 읽기용 HTML", "읽기용 HTML만")
        html_only   = fmt == "읽기용 HTML만"

        def run():
            self.app.after(0, lambda: self.download_btn.configure(
                state="disabled", text="다운로드 중..."
            ))
            try:
                self.log(f"[{corp['corp_name']}] 공시 목록 조회 중...")
                disclosures = list_disclosures(
                    api_key, corp["corp_code"], bgn_de, end_de,
                    report_types=report_types, log_fn=self.log,
                )
                if not disclosures:
                    self.log("해당 조건의 공시가 없습니다.")
                    return

                ok = fail = skip = html_ok = html_fail = 0
                for d in disclosures:
                    year  = _report_year(d["report_nm"])
                    rtype = _report_folder(d["report_nm"], report_types)
                    base_name = _report_basename(d["report_nm"], rtype, year)
                    save_dir  = os.path.join(base_dir, corp["corp_name"], f"{rtype}_{year}")
                    self.log(f"→ {d['report_nm']}  ({d['rcept_dt']})")
                    result = download_document(
                        api_key, d["rcept_no"], save_dir, log_fn=self.log,
                        base_name=base_name,
                    )
                    if result["status"] == "성공":     ok += 1
                    elif result["status"] == "건너뜀": skip += 1
                    else:                              fail += 1

                    if make_html and result["status"] in ("성공", "건너뜀"):
                        xml_files = [f for f in result.get("files", [])
                                     if f.lower().endswith(".xml")]
                        for fname in xml_files:
                            xml_full  = os.path.join(save_dir, fname)
                            html_full = xml_full[:-4] + ".html"
                            try:
                                convert_to_html(xml_full, html_full, log_fn=self.log)
                                html_ok += 1
                                if html_only:
                                    os.remove(xml_full)
                            except Exception as he:
                                self.log(f"HTML 변환 실패 ({fname}): {he}")
                                html_fail += 1
                        if html_only and not xml_files:
                            pass  # XML 없으면 건너뜀

                msg = f"완료 — 성공 {ok}건 / 건너뜀 {skip}건 / 실패 {fail}건"
                if make_html:
                    msg += f" | HTML {html_ok}건 변환"
                    if html_fail: msg += f" / 실패 {html_fail}건"
                self.log(msg)
            except Exception as e:
                self.log(f"오류: {e}")
            finally:
                self.app.after(0, lambda: self.download_btn.configure(
                    state="normal", text="다운로드"
                ))

        threading.Thread(target=run, daemon=True).start()
