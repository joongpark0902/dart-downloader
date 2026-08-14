"""GUI 공통 테마와 표시 포맷."""
import tkinter as tk

import customtkinter as ctk


# ── 글꼴 ─────────────────────────────────────────────────────────────────
#
# 이 PC에는 macOS의 SF Pro가 없다. 그렇다고 라틴/한글 글꼴을 따로 지정할
# 필요는 없었다 — Windows 글꼴 링크(font linking)가 "Segoe UI"만 지정해도
# 한글 글자를 자동으로 맑은 고딕으로 대체해 그려준다는 걸 실제 렌더링해
# 확인했다(같은 문장을 "Segoe UI"로 찍은 것과 "맑은 고딕"으로 찍은 것이
# 한글 부분은 구별이 안 될 만큼 같았고, 숫자·영문 부분은 Segoe UI 쪽이
# 더 또렷했다 — 스캐폴드 스크린샷 font-test.png 기준). 그래서 라틴/한글을
# 나눠 관리하지 않고 이 한 글꼴만 쓴다. 이 상수를 바꾸면 apply_theme()의
# 전역 기본값과, 아래 표 셀 글꼴들이 한 번에 같이 바뀐다.
FONT_FAMILY = "Segoe UI"

# 로그 타임스탬프·회사코드처럼 자릿수를 맞춰야 하는 곳에 쓰는 고정폭 글꼴.
# 일반 UI 글꼴과는 성격이 달라 FONT_FAMILY와 분리해 둔다.
FONT_FAMILY_MONO = "Consolas"


def apply_theme():
    """앱 시작 때 한 번 부른다."""
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    # CTkFont()를 family 없이 부르는 모든 곳(위젯 기본 글꼴 대부분이 이렇게
    # 만들어진다)이 이 한 줄로 FONT_FAMILY를 쓰게 된다. 위젯 생성부마다
    # font=를 일일이 넘기지 않아도 되는 단일 지점 — 다음에 글꼴을 바꿀 때도
    # 여기와 FONT_FAMILY 상수만 고치면 된다.
    ctk.ThemeManager.theme["CTkFont"]["family"] = FONT_FAMILY


# ── 라이트 팔레트 ────────────────────────────────────────────────────────
#
# macOS 라이트 모드(Activity Monitor 참고 이미지의 라이트 버전) 값에서
# 출발해, 실제로 이 윈도우 PC 화면에 찍어 보고 눈으로 맞춘 값이다.
# 이론적인 macOS 값을 그대로 베끼지 않은 이유: Segoe UI/맑은 고딕은 SF Pro
# 보다 굵어 보여서 같은 명도 대비를 쓰면 더 진하게 느껴진다 — 그래서
# 보조 텍스트·구분선 쪽은 macOS 원본보다 살짝 연하게 조정했다.
WINDOW_BG = "#ECECEC"        # 창 바깥 배경(타이틀바 바로 아래 바탕)
PANEL_BG = "#F6F6F6"         # 패널 표면 — 좌측 패널 바탕, 표 헤더 바탕
SURFACE = "#FFFFFF"          # 콘텐츠/표 표면 — 카드형 박스, 로그창, 목록창
BORDER = "#D8D8D8"           # 헤어라인 테두리·구분선
TEXT_PRIMARY = "#1D1D1F"     # 본문 텍스트
TEXT_SECONDARY = "#6E6E73"   # 보조·설명 텍스트, "N/A" 같은 빈 값
ACCENT = "#0A6CFF"           # 강조색(선택 표시 등)
SELECTION_FILL = ACCENT      # 선택된 행/항목의 배경(진한 파랑, 단색)
SELECTION_TEXT = "#FFFFFF"   # 선택된 행 위에 얹히는 텍스트
ROW_STRIPE = "#F5F5F7"       # 표 줄무늬(zebra)의 홀수 행 배경
NEGATIVE = "#FF3B30"         # 음수·마이너스 값 강조색(라이트 배경용 red)


# tk.Listbox는 customtkinter가 감싸주지 않아 색을 직접 맞춘다. highlightthickness
# 로 얇은 테두리를 둘러 흰 바탕 카드 위에서도 목록 영역 경계가 보이게 한다
# (카드와 목록이 둘 다 SURFACE 흰색이라 테두리가 없으면 서로 묻힌다).
LISTBOX_STYLE = {
    "bg": SURFACE,
    "fg": TEXT_PRIMARY,
    "selectbackground": SELECTION_FILL,
    "selectforeground": SELECTION_TEXT,
    "activestyle": "none",
    "relief": "flat",
    "borderwidth": 0,
    "highlightthickness": 1,
    "highlightbackground": BORDER,
    "highlightcolor": BORDER,
    "font": (FONT_FAMILY_MONO, 10),
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
# scaling을 건드리지 않는다)일 때와 글자 그대로 같다. apply_theme()에서
# 기본 글꼴 family를 FONT_FAMILY로 바꿔치기했으므로, 라이트 팔레트로
# 옮기며 다시 실측해 family만 "Segoe UI"로 갱신했다(크기·스타일은 그대로).
TABLE_CELL_FONT = ("Segoe UI", -13, "normal roman  ")

# CTkLabel 기본 text_color 테마값(라이트/다크 튜플)의 라이트 쪽. 명시적으로
# text_color를 지정하지 않는 셀(예: capital.py의 발행일·발행형태 칸)은
# TEXT_PRIMARY 같은 임의값이 아니라 이 tk 색이름이어야 CTkLabel과 색이
# 정확히 같아진다(cget()으로 실측).
TABLE_CELL_DEFAULT_FG = "gray10"

# CTkScrollableFrame(fg_color="transparent")로 만든 스크롤 영역 안은 상위
# 프레임 색이 그대로 비쳐 보인다 — analysis/audit.py, analysis/capital.py,
# analysis/shareholder.py가 이 경우다(스크롤 프레임 자체와 그 안에 얹은
# 투명 서브프레임 모두 동일하게 이 색으로 귀결된다). 이 상위 프레임은
# analysis_tab.py가 CTkTabview(fg_color=SURFACE)로 명시한 탭 내용 배경이라
# SURFACE와 정확히 같다(cget()으로 실측).
TABLE_CELL_BG_TRANSPARENT_SCROLL = SURFACE

# CTkScrollableFrame을 fg_color 지정 없이(테마 기본값) 만들면 스스로 색을
# 칠한다 — analysis/equity.py의 스크롤 표가 이 경우다. 라이트 모드 실측값은
# "gray86"(CTkFrame 기본 fg_color의 라이트 쪽)이다.
TABLE_CELL_BG_DEFAULT_SCROLL = "gray86"

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


# ── 표 헤더 셀 / 줄무늬 / 구분선 ────────────────────────────────────────────
#
# 데이터 셀과 달리 헤더 셀은 표 하나에 열 개수만큼(보통 4~7개)만 만들어져
# 반복 렌더링 비용이 없다 — 그래서 여기는 tk.Label로 내리지 않고 그대로
# CTkLabel을 쓴다. Activity Monitor의 헤더 바("App Name", "Energy Impact"
# 같은 열 이름 줄)처럼 데이터보다 한 톤 옅고 작게 잡아, 굵은 헤더가 데이터를
# 누르지 않게 한다.
TABLE_HEADER_BG = PANEL_BG
# (family, size) 2-튜플까지만 쓴다. TABLE_CELL_FONT처럼 스타일까지 넣은
# 3-튜플을 CTkLabel에 넘기면 customtkinter의 _apply_font_scaling()이
# 3번째 원소를 font[2:]로 슬라이스해 통째로 다시 튜플에 담아버려
# ("normal roman  ",)처럼 중첩 튜플이 되고, 그걸 그대로 tkinter.Label에
# 넘기면 "unknown font style" 예외가 난다(tk.Label에 직접 넘길 때는
# 이 스케일링 단계를 안 거치므로 문제없다 — table_cell이 3-튜플을 쓰는
# 이유). 헤더는 볼드가 필요 없으니 2-튜플로 그 버그를 원천적으로 피한다.
TABLE_HEADER_FONT = ("Segoe UI", -11)


def table_header(parent, text, *, anchor="w", **grid_kwargs):
    """표 열 헤더 한 칸을 CTkLabel로 만들어 grid까지 배치하고 돌려준다."""
    lbl = ctk.CTkLabel(
        parent, text=text, fg_color=TABLE_HEADER_BG, text_color=TEXT_SECONDARY,
        font=TABLE_HEADER_FONT, anchor=anchor, corner_radius=0,
    )
    lbl.grid(sticky=anchor, **grid_kwargs)
    return lbl


def zebra_bg(row_index, base=SURFACE, stripe=ROW_STRIPE):
    """표 행 배경을 얼룩무늬(zebra)로 돌려준다. 짝수 행은 표 바탕색(base),
    홀수 행은 한 단계 어두운 줄무늬색(stripe)이다. table_cell(bg=...)에
    그대로 넘기면 된다.
    """
    return base if row_index % 2 == 0 else stripe


def table_separator(parent, **grid_kwargs):
    """표 안 헤어라인 구분선 한 칸을 만들어 grid까지 배치하고 돌려준다.

    가로선(헤더 밑줄 등)은 sticky="ew", 세로선(열 사이 구분)은 sticky="ns"로
    호출측에서 지정한다 — 방향에 맞춰 두께 1px을 폭/높이 중 알맞은 쪽에
    준다. sticky를 안 넘기면 가로선("ew")으로 취급한다(grid_kwargs.
    setdefault로 실제 grid() 호출에도 같은 기본값이 들어가게 한다 —
    두께 판단에만 쓰고 grid에는 안 넘기면 sticky 없이 배치돼 선이 안
    늘어나는 버그가 난다).
    """
    grid_kwargs.setdefault("sticky", "ew")
    sticky = grid_kwargs["sticky"]
    sep = ctk.CTkFrame(parent, fg_color=BORDER, corner_radius=0)
    if "n" in sticky or "s" in sticky:
        sep.configure(width=1)
    else:
        sep.configure(height=1)
    sep.grid(**grid_kwargs)
    return sep


def fmt_val(val):
    """금액 포맷 + 색상. (표시문자열, 텍스트 색상) 반환."""
    if val is None:
        return "N/A", TEXT_SECONDARY
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
        return f"-{s}", NEGATIVE
    return s, TEXT_PRIMARY


def fmt_div_val(val, key):
    """배당 항목별 포맷 + 색상. (표시문자열, 텍스트 색상) 반환."""
    if val is None:
        return "N/A", TEXT_SECONDARY
    if "%" in key:
        color = NEGATIVE if val < 0 else TEXT_PRIMARY
        return f"{val:.2f}%", color
    if "백만원" in key:
        return fmt_val(int(val) * 1_000_000)   # 백만원→원 변환 후 조/억 표시
    return f"{int(val):,}원", TEXT_PRIMARY


def fmt_ratio_val(val):
    """재무비율 포맷 + 색상. (표시문자열, 텍스트 색상) 반환."""
    if val is None:
        return "N/A", TEXT_SECONDARY
    color = NEGATIVE if val < 0 else TEXT_PRIMARY
    return f"{val:.2f}%", color
