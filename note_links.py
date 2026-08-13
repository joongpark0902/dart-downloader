"""읽기용 HTML 본문의 주석 참조(주석 12)를 해당 주석 본문으로 링크한다.

DART 문서는 주석 세트를 여러 벌 담을 수 있다. 사업보고서는 연결·별도
2벌이고 같은 내용이 서로 다른 번호를 쓴다(연결 16번 = 별도 15번). 그래서
참조가 놓인 위치가 어느 세트 안인지 보고 번호를 풀어야 한다.
"""
import re

# 주석 세트를 여는 제목. '주석'으로 끝난다.
#   3. 연결재무제표 주석 / 5. 재무제표 주석 / 주석
_SET_TITLE = re.compile(r"주석\s*$")

# 제목 안의 주석 번호. 제목 머리 또는 공백 뒤에 온다.
# DART는 두 주석을 한 제목에 합치기도 한다 — '4. 종속기업의 현황 5. 관계기업…'
_TITLE_NO = re.compile(r"(?:^|\s)(\d{1,2})(?:-\d+)?\s*\.")

# 제목이 번호처럼 '보이는지'만 헐겁게 본다 — 실 문서엔 '7-2 사용이 제한된
# 금융자산'처럼 마침표를 빠뜨린 항목이 섞여 있어(같은 문서의 '7-1.'엔
# 마침표가 있다) _TITLE_NO가 못 잡는다. 이런 항목은 세트를 닫으면 안 되므로
# — 정말 번호가 없는 구분 제목과 가려내는 용도로만 쓴다.
#
# _TITLE_NO(엄격)는 항목 등록에, _TITLE_NO_LIKE(헐거움)는 세트를 닫을지
# 판단하는 데만 쓴다 — 번호를 확정 못 해도 "번호가 있어 보이면" 닫지
# 않는다. 실 문서(STX 사업보고서)에서 확인한 두 모양만 받아준다: 마침표
# 붙은 번호('13.') 또는 하이픈 붙은 하위번호(마침표는 있어도 되고 없어도
# 되는 '7-2'·'7-3.'). 숫자로 시작하지만 이 두 모양이 아닌 제목
# ('6 대 매 출 처 현 황'처럼 letter-spacing한 구분 제목이 우연히 숫자로
# 시작하는 경우)은 일부러 거부한다 — 안 그러면 \b만 보던 옛 패턴처럼 그런
# 제목도 "번호 항목"으로 오판해 세트를 안 닫고, 그 뒤 참조가 엉뚱한
# 세트로 새 버린다.
_TITLE_NO_LIKE = re.compile(r"^\d{1,2}(?:-\d+\.?|\.)")

# 문단 머리의 주석 번호. 여는 괄호를 허용하지 않으므로
# '(11) 자산손상'·'1) 리스제공자'는 걸리지 않는다.
_PARA_NO = re.compile(r"^\s*(\d{1,2})(?:-\d+)?\s*\.")

# 문단 중간에서 시작하는 주석. DART가 논리 문단을 한 <p>에 뭉쳐 넣는다 —
# '…희석주당손익은 동일합니다.17. 부가가치 관련자료…'
# 뒤에 숫자가 오면 '3.5배' 같은 소수라 제외한다.
_PARA_NO_MID = re.compile(r"(?<=다\.)(\d{1,2})\.\s*(?=[^\d\s])")

# 본문 참조. '주석' 바로 뒤에 숫자가 와야 한다.
#   (주석3,4) / 주석 4, 5 / 주석 17 및 28 / 주석30
# 숫자는 최대 3자리. 그 뒤에 숫자가 더 이어지면(네 자리 이상) 아예
# 매치하지 않는다 — '주석 100'을 '10'+'0'으로 잘라 삼키지 않기 위해서다.
_REF = re.compile(r"주석\s*(\d{1,3}(?!\d)(?:\s*[,및·]\s*\d{1,3}(?!\d))*)")
_REF_NUM = re.compile(r"\d{1,3}(?!\d)")

# 블록 요소. 제목은 세트 경계와 항목을, 문단은 감사보고서식 항목을 준다.
_BLOCK = re.compile(r"<(h([1-5])|p)\b([^>]*)>(.*?)</\1>", re.S)
_TAG = re.compile(r"<[^>]*>")
_TABLE = re.compile(r"<table\b.*?</table>", re.S)
_ID_ATTR = re.compile(r'\bid="([^"]*)"')

NREF_CLASS = "nref"


def _text_of(inner_html):
    """블록 안쪽 HTML에서 눈에 보이는 텍스트만 뽑아 공백을 정리한다."""
    return " ".join(_TAG.sub(" ", inner_html).split())


def _table_spans(html):
    return [m.span() for m in _TABLE.finditer(html)]


def _in_spans(pos, spans):
    return any(s <= pos < e for s, e in spans)


class _NoteSet:
    __slots__ = ("index", "title", "level", "start", "end", "items", "pending")

    def __init__(self, index, title, level, start):
        self.index = index
        self.title = title
        self.level = level
        self.start = start        # 세트를 연 제목이 끝난 위치
        self.end = None           # 세트가 닫힌 위치. None이면 문서 끝까지
        self.items = {}           # {주석번호: 앵커 id}
        self.pending = []         # 앵커를 새로 달아야 하는 [(번호, 삽입위치)]

    @property
    def is_consolidated(self):
        return "연결" in self.title

    @property
    def numbers(self):
        return set(self.items) | {no for no, _ in self.pending}

    def contains(self, pos):
        return self.start <= pos and (self.end is None or pos < self.end)


def _index_sets(html):
    """제목만 훑어 주석 세트 경계와 제목형 항목을 잡는다.

    세트는 다음 세 가지로만 닫힌다.
      1) 세트를 연 제목보다 상위(수) 제목이 나올 때.
      2) 세트와 같은 급 제목인데 번호가 없을 때 — '재 무 제 표'처럼 장을
         구분만 하는 제목이 섞여 있어도 세트가 뒤 내용을 삼키지 않는다.
      3) 세트와 같은 급 제목인데 번호가 역행할 때 (…32. 다음의 '4. 재무제표').
    세트보다 하위(깊은) 제목은 세트를 닫지도, 항목으로 등록하지도 않는다 —
    주석 안의 소제목일 뿐이다.
    """
    sets = []
    cur = None
    last_no = 0

    for m in _BLOCK.finditer(html):
        tag, level_s = m.group(1), m.group(2)
        if not level_s:                      # <p>는 여기서 다루지 않는다
            continue
        level = int(level_s)
        text = _text_of(m.group(4))
        if not text:
            continue

        if _SET_TITLE.search(text):
            if cur is not None and cur.end is None:
                cur.end = m.start()          # 이전 세트가 열려 있으면 여기서 닫는다
            cur = _NoteSet(len(sets), text, level, m.end())
            sets.append(cur)
            last_no = 0
            continue

        if cur is None:
            continue

        # 세트를 연 제목보다 상위 제목이 나오면 세트가 끝난다
        if level < cur.level:
            cur.end = m.start()
            cur = None
            continue

        # 세트보다 하위(더 깊은) 제목은 주석 안의 소제목이다 — 무시한다
        if level > cur.level:
            continue

        nos = [int(x) for x in _TITLE_NO.findall(text)]
        if not nos:
            if _TITLE_NO_LIKE.match(text):
                # 마침표만 빠졌을 뿐 번호 항목으로 보인다 — 세트를 닫지 않는다
                continue
            # 같은 급인데 번호처럼 보이지도 않는다 — 장을 구분하는 제목이니
            # 세트가 끝난다
            cur.end = m.start()
            cur = None
            continue

        # 번호가 역행하면 새 장이 시작된 것이다 (…32. 다음의 '4. 재무제표')
        if nos[0] < last_no:
            cur.end = m.start()
            cur = None
            continue

        anchor = _ID_ATTR.search(m.group(3) or "")
        known = cur.numbers
        for no in nos:
            if no < last_no or no in known:
                continue
            last_no = no
            if anchor:
                cur.items[no] = anchor.group(1)
            else:
                cur.pending.append((no, m.start() + 1 + len(tag)))

    return sets


def _index_paragraph_items(html, note_set):
    """제목형 항목이 없는 세트(감사보고서)에서 문단형 항목을 잡는다."""
    tables = _table_spans(html)
    last_no = 0
    for m in _BLOCK.finditer(html):
        if m.group(2):                        # 제목은 건너뛴다
            continue
        if not note_set.contains(m.start()):
            continue
        if _in_spans(m.start(), tables):      # 표 안 문단은 항목이 아니다
            continue
        text = _text_of(m.group(4))
        nos = [int(x) for x in _PARA_NO.findall(text)]
        nos += [int(x) for x in _PARA_NO_MID.findall(text)]
        known = note_set.numbers
        for no in sorted(nos):
            if no < last_no or no in known:
                continue
            last_no = no
            note_set.pending.append((no, m.start() + 2))   # '<p' 다음


def _heading_marks(html):
    """(제목 시작위치, 제목 텍스트) 목록. 세트 밖 참조의 소속 판별에 쓴다."""
    marks = []
    for m in _BLOCK.finditer(html):
        if m.group(2):
            marks.append((m.start(), _text_of(m.group(4))))
    return marks


def _preceding_heading(marks, pos):
    lo, hi = 0, len(marks)
    while lo < hi:
        mid = (lo + hi) // 2
        if marks[mid][0] < pos:
            lo = mid + 1
        else:
            hi = mid
    return marks[lo - 1][1] if lo else ""


def _resolve_set(sets, marks, pos, before_text):
    """
    참조 위치가 속한 세트를 찾는다.

    세트 밖(감사의견·재무상태표 등)이면 '연결' 단서로 가른다. 바로 앞
    문장을 먼저 보고, 없으면 직전 제목을 본다. 표 둘째 행처럼 문장 안에
    단서가 없는 자리는 '2-1. 연결 재무상태표' 같은 제목이 잡아 준다.

    한계(알고 갈 것 — 지금은 고치지 않는다):
      - 세트가 3개 이상이면 '연결' 단서와 처음으로 일치하는 세트를
        고른다. 세트가 둘일 때만 신뢰할 수 있는 이분법이다.
      - 두 세트 제목 다 '연결'을 담지 않으면(감사보고서에서 흔한
        '주석' vs '주석' 같은 경우) 세트 밖 참조는 전부 sets[0]로
        간다 — 근거 없이 첫 세트를 고르는 것과 같다.
      - before_text는 참조와 같은 텍스트 세그먼트(태그로 안 끊긴 같은
        구간 — 보통 같은 문장·같은 칸) 안에서, 그 세그먼트 안 마지막
        쉼표(,) 뒤 — 즉 참조가 속한 절(clause)만 본다. 세그먼트 안에
        쉼표가 없으면 세그먼트 전체를 본다. 그래서 이전 제목이나 옆
        칸의 '연결'은 물론, 같은 문장 안 앞선 절의 '연결'도 더 이상
        단서로 새지 않는다 — "…3. 연결재무제표 주석 > "주석 25",
        …5. 재무제표 주석 > "주석 23" 등을 참조" 처럼 한 문장이 연결·
        별도 두 세트를 다 인용하는 특수관계자 주석 안내문에서 흔하다.
        쉼표로만 자르고 세미콜론으로는 안 자른다 — &gt;·&quot; 같은
        HTML 개체가 세미콜론으로 끝난 채 텍스트 세그먼트에 그대로
        남아 있어서, 세미콜론까지 자르면 개체 경계를 절 경계로 오인해
        옆 참조(주석 25)를 오히려 엉뚱한 세트로 튕겨 낸다. 다만 같은
        문장이라도 참조 앞에 인라인 태그(<b>·<br> 등)가 끼어 있으면 그
        앞은 별도 세그먼트라 못 본다 — 그런 자리는 직전 제목
        휴리스틱으로 넘어간다.
    """
    for s in sets:
        if s.contains(pos):
            return s
    want_con = "연결" in before_text or "연결" in _preceding_heading(marks, pos)
    for s in sets:
        if s.is_consolidated == want_con:
            return s
    return sets[0]


def _clause_before(before):
    """before 텍스트를 참조가 속한 절로 좁힌다 — 세그먼트 안 마지막
    쉼표(,) 뒤만 남긴다. 쉼표가 없으면 세그먼트 전체를 그대로 둔다.

    쉼표로만 자른다. 세미콜론으로 자르지 않는 이유는 _resolve_set
    독스트링에 있다 — &gt;·&quot; 같은 HTML 개체가 세미콜론으로 끝난
    채 텍스트 세그먼트에 남아 있어서다.
    """
    idx = before.rfind(",")
    return before[idx + 1:] if idx != -1 else before


def _text_segments(html):
    """태그 바깥 텍스트 구간 [(start, end), …]. 속성값은 건드리지 않는다."""
    segs = []
    prev = 0
    for m in _TAG.finditer(html):
        if m.start() > prev:
            segs.append((prev, m.start()))
        prev = m.end()
    if prev < len(html):
        segs.append((prev, len(html)))
    return segs


def _collect_ref_edits(html, sets):
    edits = []
    marks = _heading_marks(html)
    for seg_start, seg_end in _text_segments(html):
        seg = html[seg_start:seg_end]
        for m in _REF.finditer(seg):
            abs_start = seg_start + m.start()
            before = _clause_before(seg[:m.start()])
            note_set = _resolve_set(sets, marks, abs_start, before)
            nums_start = seg_start + m.start(1)
            for nm in _REF_NUM.finditer(m.group(1)):
                anchor = note_set.items.get(int(nm.group()))
                if not anchor:
                    continue
                edits.append((nums_start + nm.start(), nums_start + nm.end(),
                              f'<a class="{NREF_CLASS}" href="#{anchor}">'
                              f'{nm.group()}</a>'))
    return edits


def _apply(html, edits):
    """(시작, 끝, 대체문자열) 목록을 한 번에 적용한다. 겹치면 뒤엣것을 버린다."""
    out = []
    prev = 0
    for s, e, rep in sorted(edits):
        if s < prev:
            continue
        out.append(html[prev:s])
        out.append(rep)
        prev = e
    out.append(html[prev:])
    return "".join(out)


def add_note_links(body_html):
    """본문 HTML에 주석 앵커를 심고 참조를 링크해 돌려준다."""
    sets = _index_sets(body_html)
    if not sets:
        return body_html

    for s in sets:
        if not s.numbers:
            _index_paragraph_items(body_html, s)

    edits = []
    for s in sets:
        for no, pos in s.pending:
            anchor = f"nt{s.index}_{no}"
            s.items[no] = anchor
            edits.append((pos, pos, f' id="{anchor}"'))

    if not any(s.items for s in sets):
        return body_html

    edits.extend(_collect_ref_edits(body_html, sets))
    return _apply(body_html, edits)
