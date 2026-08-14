"""분석 패널.

dart_gui.py의 _build_analysis, _on_fs_toggle, _update_titles를 옮긴 모듈이다.
탭 조립은 analysis.TAB_SPECS 순회로 바꿨고, 제목 8줄을 개별로 쓰던
_update_titles는 각 모듈의 SCOPE 기반 한 곳으로 합쳤다. 연결/별도
토글(fs_seg)도 이 패널로 옮겨 왔다.

지연 로딩: 회사가 바뀌어도 화면에 보이는 탭 하나만 즉시 불러온다. 나머지는
"stale" 표시만 해 두고, 탭뷰의 command 콜백(탭 전환 시 호출)이 처음 그
탭을 볼 때 불러온다. 핵심재무(fin)와 재무지표(ratio)는 SCOPE가 둘 다
"3y_fs"이고 fin.load() 하나가 두 탭을 함께 채우는 구조라, stale 판정과
로딩 모두 이 두 모듈을 한 쌍으로 묶어 처리한다(_load_tab 참고).
"""
import customtkinter as ctk

import ui_theme
from analysis import TAB_SPECS, fin, ratio


class AnalysisPanel:
    """우측 분석 패널. 회사·연결별도 상태를 들고 탭에 뿌린다."""

    def __init__(self, parent, app):
        self.app = app
        self.frame = ctk.CTkFrame(
            parent, fg_color=ui_theme.PANEL_BG, border_width=1, border_color=ui_theme.BORDER
        )
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=0)
        self.frame.grid_rowconfigure(1, weight=1)

        self._build_header(self.frame)

        # CTkTabview에 fg_color를 명시한다 — 안 주면 "이 프레임 색이 CTkFrame
        # 기본값과 같은가"를 보고 탭 안쪽 톤을 자동으로 고르는데, 위에서
        # self.frame의 fg_color를 이미 PANEL_BG로 직접 지정했으므로 그 자동
        # 판단이 깨진다. 명시적으로 SURFACE(흰색)를 줘서 각 탭 내용 영역이
        # macOS 표 배경처럼 흰 바탕이 되게 하고, ui_theme.ScrollFrame(
        # analysis/audit.py 등이 만드는 스크롤 컨테이너)의 기본 배경도
        # 이 SURFACE와 맞춰 둔다.
        self.tabview = ctk.CTkTabview(
            self.frame, fg_color=ui_theme.SURFACE, command=self._on_tab_change
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))

        self._ctx = {}
        self._stale = {}
        self._by_title = {}
        for module in TAB_SPECS:
            tab_frame = self.tabview.add(module.TITLE)
            tab_frame.grid_columnconfigure(0, weight=1)
            tab_frame.grid_rowconfigure(1, weight=1)
            self._ctx[module] = module.build(tab_frame, self.app)
            module.render(self._ctx[module], "initial")
            self._stale[module] = False
            self._by_title[module.TITLE] = module

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
        """회사가 바뀌면 제목을 고치고 탭을 전부 stale로 표시한 뒤,
        지금 보이는 탭 하나만 즉시 읽는다. 나머지는 탭을 열 때 읽는다.
        """
        self._analysis_label.configure(text=corp["corp_name"])
        self.refresh_titles()
        for module in TAB_SPECS:
            module.render(self._ctx[module], "initial")
            self._stale[module] = True
        self._load_if_stale(self._visible_module())

    def _visible_module(self):
        """지금 보이는 탭에 대응하는 모듈. 탭이 하나도 없으면 None."""
        return self._by_title.get(self.tabview.get())

    def _load_tab(self, module):
        """module 을 실제로 불러오고 stale 표시를 지운다.

        재무지표(ratio)는 자체 로더가 없는 no-op이다 — 핵심재무(fin)의
        load() 가 두 탭을 함께 채우므로, ratio 를 불러야 할 때도 실제로는
        fin.load() 를 돌리고 두 모듈의 stale 표시를 함께 지운다.
        """
        driver = fin if module is ratio else module
        driver.load(self.app, self._ctx[driver])
        self._stale[driver] = False
        if driver is fin:
            self._stale[ratio] = False

    def _load_if_stale(self, module):
        if module is not None and self._stale.get(module):
            self._load_tab(module)

    def _on_tab_change(self):
        """탭 전환 콜백. 회사가 선택되지 않았으면 아무 것도 하지 않는다."""
        if not self.app.selected_corp:
            return
        self._load_if_stale(self._visible_module())

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
        """연결/별도를 바꾸면 제목과, 연결/별도에 실제로 걸린 탭만 stale로
        표시한다. SCOPE가 "3y_fs"인 탭(핵심재무·재무지표)만 fs_mode를 인자로
        받아 조회하므로 — 이 두 탭만 stale이 된다. 지금 그 중 하나가 보이는
        중이면 바로 다시 읽고, 아니면 다음에 그 탭을 열 때 읽는다.
        """
        if not self.app.selected_corp:
            return
        self.refresh_titles()
        for module in TAB_SPECS:
            if module.SCOPE == "3y_fs":
                self._stale[module] = True
        self._load_if_stale(self._visible_module())
