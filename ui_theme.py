"""GUI 공통 테마와 표시 포맷."""
import tkinter as tk

import customtkinter as ctk


def apply_theme():
    """앱 시작 때 한 번 부른다."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")


# tk.Listbox는 customtkinter가 감싸주지 않아 색을 직접 맞춘다
LISTBOX_STYLE = {
    "bg": "#2b2b2b",
    "fg": "white",
    "selectbackground": "#1f6aa5",
    "activestyle": "none",
    "relief": "flat",
    "borderwidth": 0,
    "font": ("Consolas", 10),
    "exportselection": False,
}


# ── 표 데이터 셀: 왜 CTkLabel이 아니라 tk.Label인가 ────────────────────────
#
# 실측(이 PC 기준):
#   순수 tk.Label     200개:      21 ms
#   CTkLabel(일반 프레임 안)  200개:    100 ms
#   CTkLabel(CTkScrollableFrame 안) 200개: 1,645 ms   ← 개당 8ms
#
# CTkLabel 하나는 내부적으로 캔버스 1개 + tkinter.Label 1개를 만들고
# 매번 둥근 사각형을 다시 그린다. 일반 프레임 안에서도 순수 tk.Label보다
# 5배 느리지만(200개=100ms), CTkScrollableFrame 안에서는 스크롤 영역 재계산이
# 겹쳐 개당 8ms까지 치솟는다 — 최대주주처럼 20행×6열=120개짜리 표면
# 화면 갱신 한 번에 메인 스레드가 거의 1초 멈춘다.
#
# 그래서 반복되는 행/열 루프로 찍어내는 "표 셀"만 tk.Label로 내린다.
# 제목·상태 메시지·표 헤더처럼 화면에 몇 개 안 되고 반복 렌더링되지
# 않는 위젯은 그대로 CTkLabel을 쓴다 — 비용이 무의미하기 때문이다.
#
# 문제는 tk.Label이 CTkLabel과 색·글꼴 지정 방식이 달라서(fg_color vs bg,
# text_color vs fg, CTkFont 객체 vs tk 폰트 튜플) 그냥 옮기면 어긋난다는
# 것. 아래 상수들은 이론(테마 JSON)이 아니라, 실제로 만들어진 CTkLabel의
# 내부 tkinter.Label에서 cget()으로 읽어낸 값을 그대로 박아 넣은 것이다
# (자세한 측정 과정은 .superpowers/sdd/gui-perf-report.md "표 셀 위젯
# 교체" 절 참고). 다음에 이 파일을 고치는 사람은 "tk.Label을 왜 안
# CTkLabel로 통일하지?"라고 묻기 전에 위 숫자부터 다시 재보길 바란다.

# CTkFont() 기본값(볼드 아님, 13px)이 customtkinter 내부에서
# _apply_font_scaling()을 거쳐 최종적으로 tkinter.Label에 넘어가는
# (family, size, style) 3-튜플 그대로다. widget_scaling=1.0(이 앱은
# scaling을 건드리지 않는다)일 때와 글자 그대로 같다.
TABLE_CELL_FONT = ("Roboto", -13, "normal roman  ")

# CTkLabel 기본 text_color 테마값(라이트/다크 튜플)의 다크 쪽. 명시적으로
# text_color를 지정하지 않는 셀(예: capital.py의 발행일·발행형태 칸)은
# "white"가 아니라 이 미묘하게 다른 회백색이어야 CTkLabel과 색이 같아진다.
TABLE_CELL_DEFAULT_FG = "#DCE4EE"

# CTkScrollableFrame(fg_color="transparent")로 만든 스크롤 영역 안은 상위
# 프레임 색이 그대로 비쳐 "gray20"으로 보인다 — analysis/audit.py,
# analysis/capital.py, analysis/shareholder.py가 이 경우다(스크롤 프레임
# 자체와 그 안에 얹은 투명 서브프레임 모두 동일하게 이 색으로 귀결된다).
TABLE_CELL_BG_TRANSPARENT_SCROLL = "gray20"

# CTkScrollableFrame을 fg_color 지정 없이(테마 기본값) 만들면 스스로 색을
# 칠해 "gray17"로 보인다 — analysis/equity.py의 스크롤 표가 이 경우다.
TABLE_CELL_BG_DEFAULT_SCROLL = "gray17"

# CTkLabel의 기본 height(모든 셀 호출부가 height= 를 안 주므로 실제로 쓰인
# 값). tk.Label은 같은 텍스트라도 자기 폰트 높이만큼만 차지해 그대로 두면
# 행이 눌린 것처럼 얇아진다 — grid_rowconfigure(minsize=...)로 행 높이를
# 강제해 세로 간격을 그대로 유지한다.
TABLE_ROW_MINSIZE = 28


def table_cell(parent, text, *, bg, fg=TABLE_CELL_DEFAULT_FG, anchor="w", **grid_kwargs):
    """표 데이터 셀 하나를 tk.Label로 만들어 grid까지 배치하고 돌려준다.

    CTkLabel(width=..., anchor=...)은 위젯 자체를 고정 픽셀 폭·28px 높이로
    그려 anchor로 그 안에서 글자 위치를 잡았다. tk.Label의 width/height는
    문자·줄 단위라 그대로 옮기면 어긋난다 — 대신 폭 지정은 같은 열의 헤더
    CTkLabel(그대로 유지)에 맡기고, 여기서는 sticky=anchor로 헤더가 잡아준
    열 폭 안에서 같은 가장자리에 붙이고, 행 높이는 grid_rowconfigure로
    직접 고정한다.
    """
    row = grid_kwargs.get("row")
    if row is not None:
        # CTkLabel은 pady와 별개로 그 자체가 28px였다 — 행 전체 높이는
        # 28 + pady*2 였다는 뜻이다. tk.Label은 폰트 높이만큼만 차지하므로
        # 같은 pady를 줘도 행이 얇아진다. minsize에 그 pady를 더해 보정한다.
        pady = grid_kwargs.get("pady", 0)
        pady = pady if isinstance(pady, int) else max(pady)
        parent.grid_rowconfigure(row, minsize=TABLE_ROW_MINSIZE + 2 * pady)
    lbl = tk.Label(
        parent, text=text, bg=bg, fg=fg, font=TABLE_CELL_FONT,
        anchor=anchor, bd=0, highlightthickness=0, padx=0, pady=0,
    )
    lbl.grid(sticky=anchor, **grid_kwargs)
    return lbl


def fmt_val(val):
    """금액 포맷 + 색상. (표시문자열, 텍스트 색상) 반환."""
    if val is None:
        return "N/A", "gray50"
    trillion = 1_000_000_000_000
    billion  = 100_000_000
    abs_val  = abs(val)
    if abs_val >= trillion:
        s = f"{abs_val / trillion:.2f}조"
    elif abs_val >= billion:
        s = f"{abs_val / billion:.0f}억"
    else:
        s = f"{abs_val:,}원"
    if val < 0:
        return f"-{s}", "#FF6B6B"
    return s, "white"


def fmt_div_val(val, key):
    """배당 항목별 포맷 + 색상. (표시문자열, 텍스트 색상) 반환."""
    if val is None:
        return "N/A", "gray50"
    if "%" in key:
        color = "#FF6B6B" if val < 0 else "white"
        return f"{val:.2f}%", color
    if "백만원" in key:
        return fmt_val(int(val) * 1_000_000)   # 백만원→원 변환 후 조/억 표시
    return f"{int(val):,}원", "white"


def fmt_ratio_val(val):
    """재무비율 포맷 + 색상. (표시문자열, 텍스트 색상) 반환."""
    if val is None:
        return "N/A", "gray50"
    color = "#FF6B6B" if val < 0 else "white"
    return f"{val:.2f}%", color
