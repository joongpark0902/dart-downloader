"""분석 패널.

dart_gui.py의 _build_analysis, _on_fs_toggle, _update_titles를 옮긴 모듈이다.
탭 조립은 analysis.TAB_SPECS 순회로 바꿨고, 제목 8줄을 개별로 쓰던
_update_titles는 각 모듈의 SCOPE 기반 한 곳으로 합쳤다. 연결/별도
토글(fs_seg)도 이 패널로 옮겨 왔다.
"""
import customtkinter as ctk

from analysis import TAB_SPECS, fin


class AnalysisPanel:
    """우측 분석 패널. 회사·연결별도 상태를 들고 탭에 뿌린다."""

    def __init__(self, parent, app):
        self.app = app
        self.frame = ctk.CTkFrame(parent)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=0)
        self.frame.grid_rowconfigure(1, weight=1)

        self._build_header(self.frame)

        self.tabview = ctk.CTkTabview(self.frame)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))

        self._ctx = {}
        for module in TAB_SPECS:
            tab_frame = self.tabview.add(module.TITLE)
            tab_frame.grid_columnconfigure(0, weight=1)
            tab_frame.grid_rowconfigure(1, weight=1)
            self._ctx[module] = module.build(tab_frame, self.app)
            module.render(self._ctx[module], "initial")

    def _build_header(self, parent):
        """헤더: 회사명 + 연결/별도 토글. (dart_gui.py _build_analysis 342-359행 이식)"""
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

    def ctx_of(self, module):
        return self._ctx[module]

    @property
    def fs_mode(self):
        return self.fs_seg.get()          # "연결" 또는 "별도"

    def set_corp(self, corp):
        """회사가 바뀌면 제목을 고치고 탭을 전부 다시 읽는다."""
        self._analysis_label.configure(text=corp["corp_name"])
        self.refresh_titles()
        for module in TAB_SPECS:
            module.load(self.app, self._ctx[module])

    def refresh_titles(self):
        """SCOPE 규칙에 따라 각 탭 제목 줄을 다시 쓴다."""
        corp = self.app.selected_corp
        name = corp["corp_name"] if corp else ""
        yr = int(self.app.download_panel.end_year_var.get()) - 1
        rng = f"{yr-2}~{yr}년"
        fs_label = "연결(CFS)" if self.fs_mode == "연결" else "별도(OFS)"
        suffix = {
            "3y_fs": f"{rng} · {fs_label}",
            "3y": rng,
            "1y": f"{yr}년",
        }
        for module in TAB_SPECS:
            text = f"{name} · {suffix[module.SCOPE]}"
            self._ctx[module].title_label.configure(text=text)

    def _on_fs_toggle(self, _value):
        """연결/별도를 바꾸면 제목과 연결별도에 걸린 탭만 다시 읽는다."""
        if not self.app.selected_corp:
            return
        self.refresh_titles()
        fin_ctx = self._ctx[fin]
        fin.load(self.app, fin_ctx)
