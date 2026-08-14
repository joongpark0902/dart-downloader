"""읽기용 HTML 본문의 주석 참조(주석 12)를 해당 주석 본문으로 링크한다.

DART 문서는 주석 세트를 여러 벌 담을 수 있다. 사업보고서는 연결·별도
2벌이고 같은 내용이 서로 다른 번호를 쓴다(연결 16번 = 별도 15번). 그래서
참조가 놓인 위치가 어느 세트 안인지 보고 번호를 풀어야 한다.

DART는 재무제표에 주석 번호를 두 가지 모양으로 단다.
  ① 인라인 — 계정명 텍스트 안에 '주석'이라는 글자와 함께 번호가 붙는다.
     '현금및현금성자산(주석3,4)'. 비상장 외감법인 K-GAAP 재무제표에 흔하다.
     _REF가 이 모양을 담당한다.
  ② 전용 열 — 표 헤더에 '주석'이라는 열이 따로 있고, 그 열의 각 칸에
     '주석'이라는 글자 없이 번호만 홀로 들어간다('4, 28'·'27'). 상장사
     IFRS 재무제표(삼성전자 등)의 표준 모양이다. _collect_column_ref_edits가
     이 모양을 담당한다 — 헤더 행에서 '주석'(공백 허용) 칸을 찾아 그
     앞 칸들의 colspan을 더해 열 번호를 구하고, 본문 각 행에서 같은 방식
     으로 그 열을 짚어 번호를 뽑는다. 두 모양 모두 번호를 찾은 뒤엔 같은
     _resolve_set으로 연결·별도를 가른다.

후속 과제(지금 하지 않음) — 전용 열(모양 ②)의 열 인덱스 산수는 colspan을
누적하는 위치 계산일 뿐, rowspan을 정말로 풀어내는 HTML 표 그리드 알고리즘이
아니다. 그래서 "이 행 자신의 colspan 합이 헤더 전체 열 수와 맞는지"와
"헤더 위쪽 행에 rowspan이 있는지"라는 가드에 기대어 안전한 쪽(=링크하지
않는 쪽)으로만 실패한다. 제대로 고치려면 표 전체를 rowspan/colspan을 모두
해석하는 진짜 그리드로 풀어 셀 좌표를 구하는 알고리즘으로 갈아엎어야 한다.
지금 방식은 실 공시 32건에서는 문제없이 동작하므로, 그런 사례가 실제로
나타나기 전까지는 미룬다.
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
# 붙여서('…희석주당손익은 동일합니다.17. 부가가치 관련자료…')도, 띄어서
# ('…산정하지 않았습니다. 25. 특수관계자…')도 나온다. 두 모양 다 받도록
# '다.'와 번호 사이의 공백은 있어도 없어도 되게 한다(lookbehind는 고정
# 폭이라 '다\.' 뒤에 별도로 \s*를 둔다). 뒤에 숫자가 오면 '3.5배'·
# '2024. 12. 31' 같은 소수·날짜라 제외한다.
_PARA_NO_MID = re.compile(r"(?<=다\.)\s*(\d{1,2})\.\s*(?=[^\d\s])")

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

# 전용 '주석' 열(모양 ②) 파싱에 쓰는 태그 조각들.
_TABLE_TAG = re.compile(r"<table\b[^>]*>|</table>")
_THEAD = re.compile(r"<thead>(.*?)</thead>", re.S)
_TR = re.compile(r"<tr>(.*?)</tr>", re.S)
# th/td 짝만 맞춘다 — <th>로 열었으면 </th>로만, <td>는 </td>로만 닫힌다고
# 본다(\1 역참조). DART 변환기는 늘 짝을 맞춰 내므로 안전하다.
_CELL = re.compile(r"<t([hd])\b([^>]*)>(.*?)</t\1>", re.S)
_COLSPAN_ATTR = re.compile(r'colspan="(\d+)"')
_ROWSPAN_ATTR = re.compile(r'rowspan="(\d+)"')
_WS = re.compile(r"\s+")

# 전용 '주석' 열 칸이 '진짜 순수한 주석 번호 목록'인지 검사한다. 칸의
# 눈에 보이는 텍스트 전체(공백 정리 후)가 이 모양이어야만 그 칸을 받아
# 준다 — 하나라도 안 맞으면(라벨 행·연도·'4-1'·'*1'·값) 칸 전체를
# 버린다. 일부만 긁어내는 예전 방식(_REF_NUM을 칸 텍스트에 바로 돌리기)은
# '2024'에서 '024'를 주석 24로, '4-1'에서 4와 1을 각각, '*1'에서 1을
# 주석으로 잘못 읽어냈다.
#
# 구분자는 하나 이상 연속돼도 받아준다([,및·]+) — STX 사업보고서_2023
# 실 공시에 'DART 원문 자체의 오탈자로 '6,,13,14,15,16,27,29'처럼 쉼표가
# 두 번 연달아 나오는 칸이 실제로 있었다. 명백히 주석 번호 목록인데
# 쉼표가 겹쳤다는 이유만으로 7개 링크를 통째로 잃을 이유가 없다.
_NOTE_CELL_TEXT = re.compile(r"^\d{1,3}(?:\s*[,및·]+\s*\d{1,3})*$")

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
      - 절을 쉼표로만 가르는 대가로 두 가지를 못 본다. 첫째, 절 구분이
        쉼표가 아니면(및··(가운뎃점)·~·전각 쉼표(，)) 앞 절의 '연결'이
        그대로 새어 뒤 절 참조를 끌어간다. 둘째, 반대로 '…연결재무제표에
        대한 사항은, 주석 25 참조'처럼 쉼표가 유효한 단서를 잘라 버리면
        연결 참조가 별도로 튄다. 보유 공시 22건을 훑어 참조 2개 이상과
        '연결'이 함께 든 텍스트 세그먼트 35개를 전수 확인했더니 35개
        모두 쉼표 구분이라 지금은 실제로 걸리는 자리가 없다. 이 모양이
        실물에서 나오면 쉼표 자르기를 버리고, 세그먼트 전체에서 단서
        위치를 모아('연결'=연결, '별도'·'개별'·'연결'이 앞에 없는
        '재무제표 주석'=별도) 참조 왼쪽에 가장 가까운 단서를 택하는
        방식으로 바꿀 것. 단순히 '마지막 연결 vs 마지막 별도'로는 안
        된다 — 별도 단서가 아예 없는 STX 문장이 다시 깨진다.
      - 전용 '주석' 열(모양 ②) 칸에는 번호만 있고 앞뒤로 문장이 없다.
        그래서 이 칸에서 온 참조는 before_text가 사실상 항상 비어 있고,
        늘 위 문단·쉼표 절 단서가 아니라 직전 제목 휴리스틱만으로
        연결·별도를 가른다 — 표가 '2-1. 연결 재무상태표'처럼 소속을
        밝히는 제목 바로 아래 있어야 정확하다는 뜻이다. 실 공시에서는
        재무제표 표가 늘 그런 제목 아래 있어 지금까지 문제가 없었다.
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


def _collect_ref_edits(html, sets, marks):
    """모양 ① — '주석' 글자가 붙은 인라인 참조를 링크한다."""
    edits = []
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


def _colspan(attrs):
    m = _COLSPAN_ATTR.search(attrs)
    return int(m.group(1)) if m else 1


def _cell_text_matches_note(inner_html):
    return _WS.sub("", _text_of(inner_html)) == "주석"


def _table_elements(html):
    """문서 안 모든 <table>…</table> 요소의 (시작, 끝)을 돌려준다. 중첩된
    테이블도 각각 독립된 요소로 담긴다 — 바깥 테이블을 볼 때는
    _mask_nested_tables로 그 안쪽을 지워 직계 자식 행만 보고, 중첩 테이블은
    이 목록의 별도 항목으로서 자기 자신의 프레임 안에서 다시 처리된다."""
    stack = []
    tables = []
    for m in _TABLE_TAG.finditer(html):
        if m.group(0).startswith("</"):
            if stack:
                tables.append((stack.pop(), m.end()))
        else:
            stack.append(m.start())
    return tables


def _mask_nested_tables(segment):
    """segment(<table>…</table> 전체) 안에 중첩된 테이블이 있으면 그 내용을
    같은 길이의 공백으로 지운 사본을 돌려준다 — 오프셋은 그대로 유지하면서
    바깥 테이블의 직계 자식 행·칸만 정규식으로 안전하게 훑기 위해서다."""
    out = list(segment)
    depth = 0
    nest_start = None
    for m in _TABLE_TAG.finditer(segment):
        if m.group(0).startswith("</"):
            depth -= 1
            if depth == 1 and nest_start is not None:
                for i in range(nest_start, m.end()):
                    if out[i] != "\n":
                        out[i] = " "
                nest_start = None
        else:
            depth += 1
            if depth == 2:
                nest_start = m.start()
    return "".join(out)


def _note_column_index(masked_table_html):
    """헤더 행에서 '주석'(공백 허용) 칸을 찾아 (열 인덱스, 그 행의 전체
    열 수)를 돌려준다. <thead>가 없거나 '주석' 칸이 없으면 None — thead
    없는 표는 아예 다루지 않는다(실 공시 26건 중 그런 사례가 없었다).

    다중행 헤더 대비: '주석' 칸을 찾은 행보다 위쪽 행에 rowspan이 있으면
    그 rowspan이 아래 행의 칸들을 밀었을 수 있다 — 지금은 각 행 자신의
    colspan만 누적하는 위치 산수라 그렇게 밀린 열 인덱스를 제대로 못
    구한다(rowspan을 실제로 해석하는 그리드 알고리즘이 진짜 고침이지만
    지금은 하지 않는다 — 모듈 docstring 참고). 그래서 위쪽 행에
    rowspan이 있으면 짐작하지 않고 None을 돌려 그 표 전체를 링크하지
    않는다 — 링크가 없는 편이 잘못된 열을 짚는 것보다 낫다.
    """
    thead_m = _THEAD.search(masked_table_html)
    if not thead_m:
        return None
    for tr_m in _TR.finditer(thead_m.group(1)):
        col = 0
        note_col = None
        for cell_m in _CELL.finditer(tr_m.group(1)):
            cs = _colspan(cell_m.group(2))
            if note_col is None and _cell_text_matches_note(cell_m.group(3)):
                note_col = col
            col += cs
        if note_col is not None:
            return note_col, col
        if _ROWSPAN_ATTR.search(tr_m.group(1)):
            return None            # 이 행의 rowspan이 아래 행 열을 밀었을 수 있다
    return None


def _collect_column_ref_edits(html, sets, marks, inline_spans):
    """모양 ② — 전용 '주석' 열의 칸에 홀로 든 번호를 링크한다.

    칸 하나에 번호가 여럿이면('4, 28') 인라인 경로와 똑같이 하나씩 각자
    링크한다. 빈 칸·숫자가 아닌 칸·항목이 없는 번호는 손대지 않는다(뒤
    _resolve_set.items.get이 항목 없는 번호를 그냥 걸러 준다).

    행 정렬 안전장치: 앞 칸의 rowspan이 뒤 행의 칸을 밀 수 있다. 이 행
    자신의 <td>들이 낸 colspan 합이 헤더의 전체 열 수와 안 맞으면, 그
    칸이 실제로 몇 번째 열인지 추측하지 않고 행 전체를 건너뛴다 — 잘못
    링크하느니 안 거는 쪽이 낫다.

    칸 전체 채택 안전장치: 자본변동표류엔 표 전체 너비를 가로지르는
    라벨 행이 있다('<td colspan="8">1. 총포괄손익</td>'). 이 한 칸이
    표 전체 열을 덮으므로 colspan 합은 헤더와 맞아떨어지고, 주석 열도
    당연히 이 칸에 걸린다 — 행 정렬 안전장치로는 절대 걸러지지 않는
    부류다. 그래서 칸을 찾은 뒤 두 가지를 더 요구한다: (1) 그 칸
    자신의 colspan이 1(또는 없음)이어야 한다 — 라벨 행처럼 여러 열을
    가로지르는 칸은 애초에 후보에서 뺀다. (2) 칸의 눈에 보이는 텍스트
    전체가 순수한 주석 번호 목록 모양(_NOTE_CELL_TEXT)이어야 한다 —
    하나라도 아니면 칸을 통째로 버리고, 숫자만 긁어내는 부분 채택은
    하지 않는다('2024'에서 '024'만, '4-1'에서 4와 1을 따로, '*1'에서
    1을 주석으로 읽는 예전 버그를 막는다).

    전부 아니면 전무(all-or-nothing) 안전장치: _NOTE_CELL_TEXT는 구분자가
    겹쳐도('6,,13' 같은 DART 원문 오탈자) 받아주도록 느슨하다. 그런데
    그 느슨함 때문에 '1,234,567'처럼 세 자리씩 끊어 쓴 금액도 문법상으로는
    똑같이 '순수한 번호 목록'처럼 보인다. 이런 칸에서 번호별로 있으면
    걸고 없으면 두는 식(인라인 경로와 같은 방식)으로 하면, 우연히
    항목이 있는 '1'만 링크되고 '234'·'567'은 조용히 버려져 결과적으로
    링크 하나가 잘못 걸린 것과 같은 효과를 낸다. 그래서 이 칸의 번호는
    전부 아니면 전무로 다룬다 — 칸 안의 모든 번호가 각자 항목을 찾아야
    (하나라도 항목이 없으면 그 칸은 통째로 버리고) 그제서야 전부 링크한다.
    진짜 주석 칸이라면 적힌 번호 모두가 실재하는 주석을 가리켜야
    자연스럽다 — 하나라도 항목이 없다면 애초에 이 칸을 주석 열로 잘못
    짚었을 가능성이 높다는 뜻이므로, 그 칸은 아무것도 믿지 않는다.

    인라인 경로(_collect_ref_edits)는 이와 반대로 항목이 있는 번호만
    골라 걸고 없는 번호는 그냥 둔다 — 일부러 다르게 짠 것이니 "일관성
    없다"며 나중에 고치지 말 것. 인라인 경로엔 '주석'이라는 글자 자체가
    그 자리가 진짜 주석 참조라는 확증이 있지만, 이 열 경로는 확증이
    위치(열 인덱스) 하나뿐이다 — 확증이 약한 만큼 항목 불일치 하나에도
    칸 전체를 더 보수적으로 버려야 한다.

    표 칸에는 '주석'이라는 글자가 없으므로 인라인 경로(_REF)와 겹칠 일이
    실제로는 없지만, inline_spans로 이미 링크된 자리를 한 번 더 걸러
    이중 링크를 막는다.
    """
    edits = []
    for start, end in _table_elements(html):
        seg = html[start:end]
        masked = _mask_nested_tables(seg)
        info = _note_column_index(masked)
        if info is None:
            continue
        note_col, header_total = info
        thead_end = _THEAD.search(masked).end()
        for tr_m in _TR.finditer(masked, thead_end):
            row = tr_m.group(1)
            col = 0
            note_span = None
            note_cs = None
            for cell_m in _CELL.finditer(row):
                cs = _colspan(cell_m.group(2))
                if col <= note_col < col + cs:
                    note_span = (tr_m.start(1) + cell_m.start(3),
                                 tr_m.start(1) + cell_m.end(3))
                    note_cs = cs
                col += cs
            if col != header_total or note_span is None:
                continue          # 정렬이 안 맞는 행 — 짐작하지 않고 건너뛴다
            if note_cs != 1:
                continue          # 여러 열을 가로지르는 칸 — 라벨 행일 수 있다
            abs_start = start + note_span[0]
            abs_end = start + note_span[1]
            cell_html = html[abs_start:abs_end]
            if not _NOTE_CELL_TEXT.match(_text_of(cell_html)):
                continue          # 순수 주석 번호 목록이 아니다 — 칸째 버린다
            # 전부 아니면 전무: 이 칸의 번호를 모두 모아본 뒤, 하나라도
            # 항목을 못 찾으면 칸 전체를 포기한다(이미 인라인으로 링크된
            # 번호만 후보에서 뺀다 — 그건 이 칸의 판단과 무관하다).
            candidates = []
            cell_ok = True
            for seg_start, seg_end in _text_segments(cell_html):
                text_seg = cell_html[seg_start:seg_end]
                for nm in _REF_NUM.finditer(text_seg):
                    num_start = abs_start + seg_start + nm.start()
                    num_end = abs_start + seg_start + nm.end()
                    if _in_spans(num_start, inline_spans):
                        continue
                    before = _clause_before(text_seg[:nm.start()])
                    note_set = _resolve_set(sets, marks, num_start, before)
                    anchor = note_set.items.get(int(nm.group()))
                    if not anchor:
                        cell_ok = False
                        break
                    candidates.append((num_start, num_end, anchor, nm.group()))
                if not cell_ok:
                    break
            if not cell_ok:
                continue          # 번호 하나라도 항목이 없다 — 칸째 버린다
            for num_start, num_end, anchor, numtext in candidates:
                edits.append((num_start, num_end,
                              f'<a class="{NREF_CLASS}" href="#{anchor}">'
                              f'{numtext}</a>'))
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
        anchor_at = {}                    # {삽입위치: 그 자리에 먼저 붙인 앵커}
        for no, pos in s.pending:
            anchor = anchor_at.get(pos)
            if anchor is None:
                # 같은 위치에 처음 등록되는 번호만 진짜 id="" 삽입을 받는다.
                # 합쳐진 제목('4. … 5. …')이나 한 문단 안 여러 항목처럼
                # 같은 자리에 번호가 둘 이상 몰리면, 같은 요소에 id 속성을
                # 두 번 넣을 수는 없으니(브라우저가 첫 id만 인정해 뒤 앵커가
                # 죽는다) 뒤 번호들은 이 앵커를 같이 쓴다 — 어차피 같은
                # 블록을 가리키므로 의미상으로도 맞다.
                anchor = f"nt{s.index}_{no}"
                anchor_at[pos] = anchor
                edits.append((pos, pos, f' id="{anchor}"'))
            s.items[no] = anchor

    if not any(s.items for s in sets):
        return body_html

    marks = _heading_marks(body_html)
    ref_edits = _collect_ref_edits(body_html, sets, marks)
    edits.extend(ref_edits)
    inline_spans = [(s, e) for s, e, _ in ref_edits]
    edits.extend(_collect_column_ref_edits(body_html, sets, marks, inline_spans))
    return _apply(body_html, edits)
