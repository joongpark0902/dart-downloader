"""GUI 공통 테마와 표시 포맷."""
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
