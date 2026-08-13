"""분석 탭 모듈 모음.

각 모듈은 TITLE / SCOPE / build(parent, app) / load(app, ctx) /
render(ctx, state, ...) 만 노출한다. 탭을 더하거나 뺄 때는 이 목록만 고친다.
순서는 dart_gui.py 의 _ANALYSIS_TABS 와 같다.
"""
from analysis import (
    audit,
    capital,
    div,
    employee,
    equity,
    fin,
    ratio,
    shareholder,
)

TAB_SPECS = [fin, div, equity, ratio, audit, shareholder, employee, capital]
