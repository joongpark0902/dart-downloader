"""DART 공시 다운로더 진입점."""
import customtkinter as ctk

import ui_theme
from analysis_tab import AnalysisPanel
from download_tab import DownloadPanel


class DartApp(ctk.CTk):
    def __init__(self):
        ui_theme.apply_theme()
        super().__init__()
        self.configure(fg_color=ui_theme.WINDOW_BG)
        self.title("DART 공시 다운로더")
        self.geometry("1300x720")
        self.minsize(1000, 580)

        self.selected_corp = None

        self._build_ui()
        ui_theme.apply_titlebar_theme(self)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.download_panel = DownloadPanel(self, self)
        self.download_panel.frame.grid(
            row=0, column=0, sticky="nsew", padx=(12, 4), pady=12
        )

        self.analysis_panel = AnalysisPanel(self, self)
        self.analysis_panel.frame.grid(
            row=0, column=1, sticky="nsew", padx=(4, 12), pady=12
        )

    def set_selected_corp(self, corp):
        """다운로드 패널이 회사를 고르면 분석 패널에 알린다."""
        self.selected_corp = corp
        self.analysis_panel.set_corp(corp)

    def ctx_of(self, module):
        """탭 모듈이 다른 탭의 상태 객체를 집어야 할 때 쓴다 (핵심재무 → 재무지표)."""
        return self.analysis_panel.ctx_of(module)


def main():
    DartApp().mainloop()


if __name__ == "__main__":
    main()
