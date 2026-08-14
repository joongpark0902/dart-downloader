"""주석 참조 링크의 동작을 지킨다.

픽스처는 실제 DART 문서에서 확인한 표기 변형을 담고 있다.
사업보고서는 연결·별도 2세트라 같은 번호가 서로 다른 곳을 가리킨다.
"""
import os
import re
import unittest
import xml.etree.ElementTree as ET

import dart_viewer
import note_links
from xml_fix import fix_xml

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
OUT = os.path.join(HERE, "_out")

LINK = re.compile(r'<a class="nref" href="#([^"]+)">(\d+)</a>')
_TAG = re.compile(r"<[a-zA-Z][^>]*>")
_FIRST_ID = re.compile(r'\bid="([^"]*)"')


def _reachable_ids(html):
    """실제로 닿을 수 있는 id만 모은다 — 태그 하나에 id="" 속성이 두 번
    박혀도(중복 삽입 버그) 브라우저는 첫 id만 인정하므로, 태그별 첫
    id="..."만 진짜로 친다. 문서 전체를 훑는 나이브한 정규식이면 중복
    속성의 두 번째 id도 "있다"고 잘못 세어 죽은 앵커를 놓친다."""
    ids = set()
    for m in _TAG.finditer(html):
        idm = _FIRST_ID.search(m.group())
        if idm:
            ids.add(idm.group(1))
    return ids


def _heading_text(html, anchor):
    """앵커 id를 단 제목(hN) 태그의 안쪽 텍스트를 돌려준다."""
    m = re.search(r'<h\d[^>]*\bid="%s"[^>]*>(.*?)</h\d>' % re.escape(anchor),
                  html, re.S)
    return m.group(1) if m else None


def _body(name):
    """링크를 붙이기 전의 순수 본문 HTML.

    변환 결과 파일을 읽지 않고 본문 생성 단계를 직접 부른다. Task 13에서
    convert_to_html이 링크를 붙이기 시작해도 이 테스트가 이중으로
    적용하지 않는다.
    """
    with open(os.path.join(FIXTURES, name + ".xml"), encoding="utf-8") as f:
        root = ET.fromstring(fix_xml(f.read()).encode("utf-8"))
    return dart_viewer.build_body_html(root, [])


class NoteLinkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.annual = note_links.add_note_links(_body("annual_report"))
        cls.audit = note_links.add_note_links(_body("audit_report"))

    def _links(self, html):
        return LINK.findall(html)

    def test_every_link_target_exists(self):
        """href가 가리키는 id가 문서에 실제로 있어야 한다.

        링크가 0개여도 이 검사는 통과해 버린다 — 기능이 통째로 죽어도
        못 잡는다. annual_report·audit_report 픽스처는 각각 9개·5개를
        내므로, 절반에도 못 미치는 3개를 바닥으로 잡아 총체적 파손을
        걸러낸다.
        """
        MIN_LINKS = 3
        for name, html in (("annual", self.annual), ("audit", self.audit)):
            with self.subTest(doc=name):
                links = self._links(html)
                self.assertGreaterEqual(len(links), MIN_LINKS,
                                         f"링크가 너무 적다: {len(links)}개")
                ids = _reachable_ids(html)
                broken = [t for t, _ in links if t not in ids]
                self.assertEqual([], broken, f"깨진 앵커: {broken}")

    def test_consolidated_and_separate_sets_differ(self):
        """연결 재무상태표의 주석3과 별도 재무상태표의 주석3은 다른 곳으로 간다.

        앵커가 다르다는 것만으로는 부족하다 — 각 앵커가 실제로 옳은
        세트(연결/별도)의 제목을 가리키는지까지 확인한다.
        """
        rows = re.findall(r"재고자산\(주석(.*?)\)", self.annual)
        self.assertEqual(2, len(rows), "재고자산 행 2개를 찾지 못했다")
        first = LINK.findall(rows[0])
        second = LINK.findall(rows[1])
        self.assertTrue(first and second)
        self.assertNotEqual(first[0][0], second[0][0],
                            "연결·별도가 같은 앵커로 갔다")

        first_heading = _heading_text(self.annual, first[0][0])
        second_heading = _heading_text(self.annual, second[0][0])
        self.assertIsNotNone(first_heading)
        self.assertIsNotNone(second_heading)
        self.assertIn("(연결)", first_heading,
                       "연결 재무상태표의 주석이 연결 주석 항목을 가리키지 않는다")
        self.assertNotIn("(연결)", second_heading,
                          "별도 재무상태표의 주석이 연결 주석 항목으로 샜다")

    def test_comma_separated_numbers_each_linked(self):
        """(주석3,4)는 링크 2개가 된다."""
        m = re.search(r"현금및현금성자산\(주석(.*?)\)", self.audit)
        self.assertIsNotNone(m)
        self.assertEqual(2, len(LINK.findall(m.group(1))))

    def test_merged_title_registers_both_numbers(self):
        """'4. 종속기업의 현황 5. 관계기업…' 제목은 4번과 5번을 함께 등록한다."""
        m = re.search(r"주석(.*?)에서 설명하고", self.annual)
        self.assertIsNotNone(m)
        self.assertEqual(2, len(LINK.findall(m.group(1))))

    def test_mid_paragraph_note_is_anchored(self):
        """감사보고서의 17번은 문단 중간에서 시작하지만 앵커가 붙어야 한다."""
        m = re.search(r"급여\(주석(.*?)\)", self.audit)
        self.assertIsNotNone(m)
        self.assertEqual(1, len(LINK.findall(m.group(1))))

    def test_unknown_number_left_alone(self):
        """없는 번호는 링크하지 않고 원문 그대로 둔다."""
        self.assertIn("(주석 77 참조)", self.annual)

    def test_prose_mention_not_linked(self):
        """'주석의 2. 재무제표 작성기준'처럼 번호가 바로 붙지 않으면 건드리지 않는다."""
        self.assertIn("재무제표 주석의 2. 재무제표 작성기준", self.annual)

    def test_sub_items_not_registered_as_notes(self):
        """'(11)'·'1)'로 시작하는 하위 항목은 주석 항목이 아니다."""
        self.assertNotIn('id="nt0_11"', self.audit)

    def test_tags_not_corrupted(self):
        """링크가 태그 속성 안으로 들어가면 안 된다."""
        for name, html in (("annual", self.annual), ("audit", self.audit)):
            with self.subTest(doc=name):
                self.assertEqual([], re.findall(r"<[a-z][^>]*<a class", html))

    def test_no_note_set_returns_input_unchanged(self):
        """주석이 없는 문서는 그대로 돌려준다."""
        plain = "<p>주석이 없는 문서입니다.</p>"
        self.assertEqual(plain, note_links.add_note_links(plain))


class UnnumberedSeparatorTest(unittest.TestCase):
    """세트 사이에 번호 없는 구분 제목('재 무 제 표')이 끼는 경우를 지킨다.

    번호 역행이 아니라 '번호 없는 같은 급 제목'으로 세트가 끝나는 경우라
    이전 세트가 닫히지 않고 뒤 내용을 통째로 삼킬 수 있었다. 세 참조의
    앵커를 정확히 못박아 그 회귀를 막는다. annual_report.xml에서
    '4. 재무제표' 제목 하나만 '재 무 제 표'로 바꾼 픽스처를 쓴다.
    """

    @classmethod
    def setUpClass(cls):
        cls.html = note_links.add_note_links(_body("annual_report_unnumbered"))

    def test_consolidated_row_still_correct(self):
        """연결 재무상태표 행은 이 변경과 무관하게 그대로다."""
        rows = re.findall(r"재고자산\(주석(.*?)\)", self.html)
        self.assertEqual(2, len(rows), "재고자산 행 2개를 찾지 못했다")
        self.assertEqual([("sec6", "3"), ("sec7", "4")], LINK.findall(rows[0]))

    def test_separate_row_no_longer_leaks_to_consolidated(self):
        """별도 재무상태표의 주석3은 별도 세트로 가야 한다(수정 전엔 연결로 샜다).

        별도 세트에는 4번 항목이 없으므로 3만 링크되고 4는 그대로 남는다.
        """
        rows = re.findall(r"재고자산\(주석(.*?)\)", self.html)
        second = rows[1]
        self.assertEqual([("sec18", "3")], LINK.findall(second))
        self.assertTrue(second.endswith(",4"),
                         "항목이 없는 4는 링크 없이 그대로 남아야 한다")
        self.assertNotIn("sec6", second, "연결 주석 항목(sec6)으로 새면 안 된다")
        self.assertNotIn("sec7", second, "연결 주석 항목(sec7)으로 새면 안 된다")

    def test_separate_body_reference_is_linked(self):
        """별도 본문의 '주석 15'는 링크되어야 한다(수정 전엔 세트 밖으로 밀려나
        전혀 링크되지 않았다)."""
        m = re.search(r"분류되어 있습니다\(주석(.*?)\)", self.html)
        self.assertIsNotNone(m)
        self.assertEqual([("sec19", "15")], LINK.findall(m.group(1)))


class ReferenceNumberWidthTest(unittest.TestCase):
    """세 자리 주석 번호까지 다루고, 네 자리는 아예 손대지 않는다."""

    HTML = (
        '<h3>주석</h3>'
        '<h3 id="n10">10. 열 번째 항목</h3><p>내용.</p>'
        '<p>참조A: 주석 10 은 링크되어야 한다.</p>'
        '<p>참조B: 주석 100 은 항목이 없어 링크되지 않아야 하고 100이 잘리면 안 된다.</p>'
        '<p>참조C: 주석 1000 은 통째로 손대지 않아야 한다.</p>'
    )

    @classmethod
    def setUpClass(cls):
        cls.html = note_links.add_note_links(cls.HTML)

    def test_two_digit_still_links(self):
        """기존 두 자리 번호 동작은 그대로여야 한다."""
        self.assertIn('<a class="nref" href="#n10">10</a>', self.html)

    def test_three_digit_without_item_not_linked_and_not_truncated(self):
        """항목이 없는 세 자리 번호는 링크되지 않고, '10'+'0'으로 잘리지도
        않아야 한다."""
        self.assertIn("주석 100 은 항목이 없어", self.html)
        self.assertNotIn('href="#n10">10</a>0', self.html)

    def test_four_digit_left_alone_entirely(self):
        """네 자리 이상은 매치 자체를 포기하고 원문 그대로 둔다."""
        self.assertIn("주석 1000 은 통째로 손대지 않아야 한다", self.html)


class TitleNumberMissingPeriodTest(unittest.TestCase):
    """실 DART 문서엔 '7-1.'엔 마침표가 있는데 '7-2'엔 빠진 경우가 섞여 있다
    (STX 사업보고서_2025에서 실제로 확인). 번호처럼 보이는 제목은 마침표가
    없다는 이유만으로 세트를 닫으면 안 된다 — 닫으면 그 뒤의 모든 항목이
    통째로 미등록 상태가 된다.
    """

    HTML = (
        '<h3>주석</h3>'
        '<h3 id="n7">7-1. 범주별 금융상품</h3><p>내용.</p>'
        '<h3>7-2 사용이 제한된 금융자산</h3><p>내용.</p>'
        '<h3 id="n8">8. 매출채권</h3><p>내용.</p>'
        '<p>참조: 주석 8 참고.</p>'
    )

    @classmethod
    def setUpClass(cls):
        cls.html = note_links.add_note_links(cls.HTML)

    def test_item_after_missing_period_heading_still_registers(self):
        """'7-2' 제목 뒤에도 세트가 열려 있어야 8번 항목이 계속 등록된다."""
        self.assertIn('<a class="nref" href="#n8">8</a>', self.html)


class ParagraphNumberSpaceBeforePeriodTest(unittest.TestCase):
    """문단 중간 항목 번호가 '다.' 뒤에 공백을 두고 이어지는 경우도 등록
    해야 한다. STX 사업보고서_2022(00760 원문)에서 실제로 확인했다 —
    '…산정하지 않았습니다. 25. 특수관계자…'. 붙여 쓴 경우('…동일합니다.
    17. 부가가치…')만 받던 예전 _PARA_NO_MID는 이 공백 있는 모양을
    통째로 놓쳐, 그 문서의 '25'를 참조하는 모든 칸이 이 번호 하나
    때문에(§전부 아니면 전무 규칙) 아예 링크를 잃었다.
    """

    HTML = (
        '<h3>주석</h3>'
        '<p>24. 주당손익 당기와 전기 기본주당이익의 계산내역은 다음과'
        ' 같습니다. 희석효과가 존재하지 않아 산정하지 않았습니다.'
        ' 25. 특수관계자 (1) 당기말 현재 당사와 특수관계에 있는 회사의'
        ' 내역은 다음과 같습니다.</p>'
        '<p>내용은 주석 25 을 참고.</p>'
    )

    @classmethod
    def setUpClass(cls):
        cls.html = note_links.add_note_links(cls.HTML)

    def test_space_before_period_item_registers_and_resolves(self):
        m = re.search(r"내용은 주석(.*?)을 참고", self.html)
        self.assertIsNotNone(m)
        self.assertEqual(1, len(LINK.findall(m.group(1))),
                          "'다. 25.'처럼 공백을 두고 이어지는 항목이 등록되지 않았다")


class DigitLedSeparatorTest(unittest.TestCase):
    """숫자로 시작하지만 번호 항목이 아닌 구분 제목('6 대 매 출 처 현황'처럼
    letter-spacing된 제목)도 세트를 닫아야 한다.

    _TITLE_NO_LIKE가 '\\b'만 보던 시절엔 이런 제목도 번호 항목처럼 보여
    세트를 안 닫았고, 그 뒤에 나오는 '주석 2' 같은 참조가 (전혀 다른
    맥락인데도) 앞 세트에 남아 있던 항목으로 잘못 링크됐다. 세트가
    둘이라 별도 세트 쪽에 같은 번호 항목이 없으므로, 고쳐진 뒤엔
    아예 링크되지 않아야 한다.
    """

    HTML = (
        '<h3>3. 연결재무제표 주석</h3>'
        '<h3 id="n2">2. 회계정책 (연결)</h3><p>내용.</p>'
        '<h3>6 대 매 출 처 현 황</h3>'
        '<p>최근 5개년 동안의 매출 상위 거래처 현황은 다음 표와 같으며'
        ' 재무제표 주석과는 무관한 별도 안내 사항입니다.</p>'
        '<p>주석 2 참고 바랍니다.</p>'
        '<h3>5. 재무제표 주석</h3>'
        '<h3 id="n2b">2. 회계정책</h3><p>내용.</p>'
    )

    @classmethod
    def setUpClass(cls):
        cls.html = note_links.add_note_links(cls.HTML)

    def test_reference_after_separator_does_not_leak_into_preceding_set(self):
        """구분 제목 뒤의 '주석 2'는 앞(연결) 세트의 n2가 아니라 뒤(별도)
        세트의 n2b로 가야 한다.

        '재 무 제 표'처럼 앞 헤딩 텍스트엔 '연결' 단서가 없지만, 그
        헤딩보다 앞선 60자 원본 HTML 안에는 '(연결)'이 남아 있을 수
        있어 필러 문단으로 거리를 벌렸다(그 경우까지 걸리면 이 테스트가
        아니라 _resolve_set의 알려진 60자 한계를 건드리는 것이라 별개
        문제다).
        """
        m = re.search(r"주석(.*?)참고 바랍니다\.", self.html)
        self.assertIsNotNone(m)
        self.assertEqual([("n2b", "2")], LINK.findall(m.group(1)))


class BeforeTextRawHtmlLeakTest(unittest.TestCase):
    """before_text가 원본 HTML 60자 창이면 이웃 태그의 '연결'까지 단서로
    잡힌다 — DigitLedSeparatorTest와 같은 구조지만 필러 문단 없이 붙여서,
    직전 제목('2. 회계정책 (연결)')의 '(연결)'이 60자 창에 그대로
    들어오는 자리를 만든다. 참조가 놓인 문장 자체('주석 2 참고
    바랍니다.')에는 '연결' 단서가 없고, 가장 가까운 앞 제목('6 대 매
    출 처 현 황')에도 없으므로, 단서를 참조와 같은 텍스트 세그먼트로
    한정하면 별도 세트로 가야 한다.
    """

    HTML = (
        '<h3 id="s1">1. 연결재무제표 주석</h3>'
        '<h3 id="n2">2. 회계정책 (연결)</h3><p>내용.</p>'
        '<h3>6 대 매 출 처 현 황</h3>'
        '<p>주석 2 참고 바랍니다.</p>'
        '<h3 id="s2">2. 별도재무제표 주석</h3>'
        '<h3 id="n2b">2. 회계정책</h3><p>별도 내용.</p>'
    )

    @classmethod
    def setUpClass(cls):
        cls.html = note_links.add_note_links(cls.HTML)

    def test_reference_resolves_to_separate_set_not_neighbouring_heading(self):
        """'주석 2'는 별도 세트의 n2b로 가야 한다(수정 전엔 이웃 제목의
        '(연결)'이 60자 창에 걸려 연결 세트의 n2로 샜다)."""
        m = re.search(r"주석(.*?)참고 바랍니다\.", self.html)
        self.assertIsNotNone(m)
        self.assertEqual([("n2b", "2")], LINK.findall(m.group(1)))


class ClauseScopedEvidenceTest(unittest.TestCase):
    """분기보고서 특수관계자 주석 안내문처럼 한 문장(=한 텍스트 세그먼트)
    안에서 연결·별도 두 세트를 순서대로 인용하는 경우.

    앞 절의 '3. 연결재무제표 주석 > "주석 25"'에 남은 '연결'이 뒤 절의
    '5. 재무제표 주석 > "주석 23"'까지 오염시키면 안 된다 — before_text가
    세그먼트 전체면(수정 전) 오염되고, 참조가 속한 절(마지막 쉼표 뒤)로
    좁히면(수정 후) 오염되지 않는다. STX 분기보고서_2026에서 실제로
    확인한 문구 구조를 그대로 옮겼다.
    """

    HTML = (
        '<h3>3. 연결재무제표 주석</h3>'
        '<h3 id="c23">23. 법인세 (연결)</h3><p>내용.</p>'
        '<h3 id="c25">25. 특수관계자 (연결)</h3><p>내용.</p>'
        '<h3>5. 재무제표 주석</h3>'
        '<h3 id="s23">23. 특수관계자</h3><p>내용.</p>'
        '<h2>Ⅲ. 재무에관한사항</h2>'
        '<p>기타 특수관계자와의 거래 등은 Ⅲ. 재무에관한사항 &gt; 3. 연결재무제표 주석 &gt;'
        ' &quot;주석 25. 특수관계자&quot;, Ⅲ. 재무에관한사항 &gt;5. 재무제표 주석 &gt;'
        ' &quot;주석 23. 특수관계자&quot; 등을 참조하시기 바랍니다.</p>'
    )

    @classmethod
    def setUpClass(cls):
        cls.html = note_links.add_note_links(cls.HTML)

    def test_second_reference_resolves_to_separate_set(self):
        m = re.search(r"등을 참조하시기 바랍니다", self.html)
        self.assertIsNotNone(m)
        para = self.html[max(0, m.start() - 400):m.start()]
        links = LINK.findall(para)
        self.assertEqual([("c25", "25"), ("s23", "23")], links,
                          "뒤 절의 주석23이 앞 절의 '연결'에 오염돼 c23으로 새면 안 된다")


class SharedOffsetAnchorTest(unittest.TestCase):
    """합쳐진 제목('4. 종속기업의 현황 5. 관계기업…')처럼 한 블록이 번호
    둘을 같은 삽입 위치에 동시에 등록하면, id="" 속성을 두 번 넣는 대신
    (브라우저가 첫 id만 인정해 뒤 앵커가 죽는다) 두 번호가 같은 앵커를
    공유해야 한다 — 어차피 같은 블록을 가리키므로 의미상으로도 맞다.
    한강버스 감사보고서_2025에서 실제로 확인한 구조(합쳐진 제목)를 옮겼다.
    """

    HTML = (
        '<h3>주석</h3>'
        '<h3>18. 기타지분상품 19. 배당금 지급제한</h3><p>내용.</p>'
        '<p>기타지분상품은 주석18, 배당금 지급제한은 주석19를 참고.</p>'
    )

    @classmethod
    def setUpClass(cls):
        cls.html = note_links.add_note_links(cls.HTML)

    def test_no_duplicate_id_attribute_on_one_tag(self):
        """한 태그 안에 id="" 속성이 두 번 들어가면 안 된다."""
        self.assertNotRegex(self.html, r'<[a-zA-Z][^>]*\bid="[^"]*"[^>]*\bid="')

    def test_both_note_numbers_stay_reachable(self):
        """18과 19 둘 다 링크되고, 그 링크가 가리키는 앵커가 실제로 있어야
        한다(first-id-wins 기준)."""
        links = LINK.findall(self.html)
        nums = {n for _, n in links}
        self.assertEqual({"18", "19"}, nums)
        ids = _reachable_ids(self.html)
        broken = [t for t, _ in links if t not in ids]
        self.assertEqual([], broken, f"깨진 앵커: {broken}")


class NoteColumnTest(unittest.TestCase):
    """전용 '주석' 열(모양 ②) — 삼성전자 감사보고서에서 실제로 확인한
    구조를 재현한다. 헤더가 '과목·주석·기간(colspan2)·기간(colspan2)'인
    표에서, 계정명이 아니라 '주석' 열의 칸에 번호만 홀로 든다.
    """

    @classmethod
    def setUpClass(cls):
        cls.html = note_links.add_note_links(_body("note_column"))

    def _row(self, account):
        m = re.search(r"<tr><td[^>]*>%s</td>(.*?)</tr>" % re.escape(account),
                      self.html)
        self.assertIsNotNone(m, f"'{account}' 행을 찾지 못했다")
        return m.group(1)

    def test_single_number_cell_linked(self):
        """'27' 하나뿐인 칸은 그 번호 하나만 링크된다."""
        row = self._row("2. 매출채권")
        self.assertEqual([("sec7", "27")], LINK.findall(row))

    def test_multiple_numbers_in_one_cell_each_linked_separately(self):
        """'4, 28'은 두 번호가 각각 따로 링크된다."""
        row = self._row("1. 현금및현금성자산")
        self.assertEqual([("sec4", "4"), ("sec8", "28")], LINK.findall(row))

    def test_blank_cell_untouched(self):
        """주석 칸이 빈 행은 손대지 않는다."""
        row = self._row("3. 재고자산")
        self.assertEqual([], LINK.findall(row))
        self.assertNotIn('<a class="nref"', row)

    def test_number_without_matching_note_left_alone(self):
        """항목이 없는 번호(99)는 원문 그대로 남아야 한다."""
        row = self._row("4. 없는주석계정")
        self.assertEqual([], LINK.findall(row))
        self.assertIn("<td>99</td>", row)

    def test_row_after_rowspan_shift_is_skipped_not_guessed(self):
        """앞 행의 rowspan이 이 행의 칸을 한 칸씩 밀었다 — 이 행 자신의
        colspan 합이 헤더 전체 열 수(6)와 안 맞으므로, 항목 8이 실제로
        있어도(sec6) 링크하지 않고 건너뛴다."""
        row = self._row("8")
        self.assertEqual([], LINK.findall(row))
        self.assertTrue(row.startswith("<td>20</td>"))

    def test_aligned_row_before_the_rowspan_still_links(self):
        """rowspan을 낸 행 자신은 여전히 정렬이 맞으므로 정상 링크된다."""
        row = self._row("동일계정그룹")
        self.assertEqual([("sec5", "7")], LINK.findall(row))

    def test_header_row_itself_not_linked(self):
        """헤더의 '주석' 칸과 기간 칸('제 10(당) 기'의 숫자 등)은 링크되면
        안 된다."""
        m = re.search(r"<thead>.*?</thead>", self.html, re.S)
        self.assertIsNotNone(m)
        self.assertNotIn('class="nref"', m.group(0))

    def test_every_link_target_exists(self):
        ids = _reachable_ids(self.html)
        links = LINK.findall(self.html)
        broken = [t for t, _ in links if t not in ids]
        self.assertEqual([], broken, f"깨진 앵커: {broken}")

    def test_full_width_label_row_not_linked(self):
        """D1 — 자본변동표류 라벨 행('1. 총포괄손익'처럼 한 칸이 표 전체
        열을 가로지르는 행)은 그 칸이 주석 열을 덮어도 링크되면 안 된다.
        메가존클라우드 실 공시에서 확인한 모양이다. 라벨 번호는 이
        픽스처에 이미 있는 항목 27을 재사용한다 — 수정 전 코드가 라벨을
        '27'로 오인해 실제로 존재하는 항목에 잘못 링크하는 것까지
        보여주기 위해서다(항목이 아예 없는 번호였다면 우연히 안 걸릴
        수도 있었다)."""
        m = re.search(r'<tr><td colspan="6"[^>]*>27\. 총포괄손익</td></tr>',
                      self.html)
        self.assertIsNotNone(m, "라벨 행을 찾지 못했다")
        self.assertNotIn('class="nref"', m.group(0))

    def test_junk_cell_year_not_linked(self):
        """D3 — '2027'은 '027'로 잘려 주석 27로 링크되면 안 된다(27은
        이 픽스처에 실제로 있는 항목이라 수정 전엔 실제로 걸렸다)."""
        row = self._row("A. 연도값")
        self.assertEqual([], LINK.findall(row))
        self.assertIn("<td>2027</td>", row)

    def test_junk_cell_hyphenated_not_linked(self):
        """D3 — '4-1'은 4와 1로 쪼개져 각각 링크되면 안 된다(4는 실제
        항목이라 수정 전엔 걸렸다)."""
        row = self._row("B. 하이픈값")
        self.assertEqual([], LINK.findall(row))
        self.assertIn("<td>4-1</td>", row)

    def test_junk_cell_asterisk_not_linked(self):
        """D3 — '*27'의 27이 주석으로 링크되면 안 된다(27은 실제 항목이라
        수정 전엔 걸렸다)."""
        row = self._row("C. 별표값")
        self.assertEqual([], LINK.findall(row))
        self.assertIn("<td>*27</td>", row)

    def test_junk_cell_thousands_separated_not_linked(self):
        """D3 — '27,4567'에서 어느 숫자도 잘못 링크되면 안 된다(수정 전엔
        앞의 '27'이 실제 항목에 걸렸다). 전체 텍스트가 순수 번호 목록
        모양이 아니므로(뒤 조각이 네 자리) 칸째 버려져야 한다."""
        row = self._row("D. 콤마천단위")
        self.assertEqual([], LINK.findall(row))
        self.assertIn("<td>27,4567</td>", row)

    def test_junk_cell_dash_not_linked(self):
        """D3 — 값 없음을 뜻하는 '-'는 링크되면 안 된다. 숫자가 아예
        없어 수정 전 코드도 이 칸만은 잘못 걸 수 없었다 — 방어적
        회귀 테스트로 남긴다."""
        row = self._row("E. 빈값표시")
        self.assertEqual([], LINK.findall(row))
        self.assertIn("<td>-</td>", row)

    def test_doubled_separator_still_links_all_numbers(self):
        """구분자가 겹쳐도('7,,27') 명백한 주석 번호 목록이면 번호를 모두
        링크해야 한다 — STX 사업보고서_2023 실 공시의 '6,,13,14,15,16,
        27,29'(DART 원문 오탈자)가 정확히 이 모양이다. 구분자를 하나만
        허용하던 수정 전엔 이 칸 전체가 버려져 7과 27 둘 다 링크를
        잃었다."""
        row = self._row("F. 겹쉼표값")
        self.assertEqual([("sec5", "7"), ("sec7", "27")], LINK.findall(row))

    def test_cell_with_one_unresolvable_number_links_nothing(self):
        """전부 아니면 전무 — '27,234,567'은 문법상 순수 번호 목록이지만
        (구분자가 느슨해진 뒤로 '1,234,567' 같은 천단위 금액도 문법은
        통과한다) 234와 567엔 항목이 없다. 번호별로 있으면 걸고 없으면
        두는 식이었다면 27만(우연히 존재하는 항목이라) 잘못 링크됐을
        것이다 — 전부 아니면 전무 규칙은 27도 함께 버려야 한다."""
        row = self._row("G. 부분항목금액")
        self.assertEqual([], LINK.findall(row))
        self.assertIn("<td>27,234,567</td>", row)


class NoteColumnHeaderRowspanTest(unittest.TestCase):
    """D2 — 둘째 헤더 행에 '주석'이 있고 그 위 행에 rowspan이 있으면,
    그 rowspan이 아래 행의 열 위치를 밀었을 수 있어 열 인덱스를 확신할
    수 없다. 짐작해서 잘못 링크하느니 표 전체를 링크하지 않아야 한다
    (실 공시엔 아직 이 모양이 없다 — latent 결함).
    """

    HTML = (
        '<h3>주석</h3>'
        '<h3 id="n1">1. 회사의 개요</h3><p>내용.</p>'
        '<table><thead>'
        '<tr><th rowspan="2">과 목</th><th colspan="3">제10기</th></tr>'
        '<tr><th>주 석</th><th>당기</th><th>전기</th></tr>'
        '</thead><tbody>'
        '<tr><td>1</td><td>100</td><td>90</td></tr>'
        '</tbody></table>'
    )

    @classmethod
    def setUpClass(cls):
        cls.html = note_links.add_note_links(cls.HTML)

    def test_table_links_nothing(self):
        """위 행의 rowspan 때문에 열 인덱스를 못 믿으므로 표 전체를
        링크하지 않아야 한다(수정 전엔 잘못 계산된 열 인덱스로 첫 칸을
        링크했다)."""
        self.assertEqual([], LINK.findall(self.html))


class NoteColumnTwoSetTest(unittest.TestCase):
    """전용 '주석' 열(모양 ②)을 연결·별도 두 세트가 함께 쓰는 경우.

    두 재무상태표 모두 열 방식으로 '주석 3'을 표시하지만, 각자 다른
    세트(연결/별도)의 3번 항목을 가리켜야 한다 — 기존 note_column.xml은
    단일 세트뿐이라 이 경로(연결/별도 분기 + 열 방식)를 전혀 검증하지
    못했다.
    """

    @classmethod
    def setUpClass(cls):
        cls.html = note_links.add_note_links(_body("note_column_two_sets"))

    def _row(self):
        return re.findall(r"<tr><td[^>]*>재고자산</td>(.*?)</tr>", self.html)

    def test_each_table_resolves_to_its_own_set(self):
        """연결 재무상태표의 주석3은 연결 세트의 '3. 재고자산 (연결)'
        제목(sec6)으로, 별도 재무상태표의 주석3은 별도 세트의
        '3. 재고자산' 제목(sec12)으로 가야 한다 — 같은 번호 3이 표
        방식(모양 ②)으로도 세트별로 정확히 갈라져야 한다."""
        rows = self._row()
        self.assertEqual(2, len(rows), "재고자산 행 2개를 찾지 못했다")
        consolidated, separate = rows
        self.assertEqual([("sec6", "3")], LINK.findall(consolidated),
                          "연결 재무상태표의 주석3이 연결 세트로 가지 않았다")
        self.assertEqual([("sec12", "3")], LINK.findall(separate),
                          "별도 재무상태표의 주석3이 별도 세트로 가지 않았다")
        heading_c = _heading_text(self.html, "sec6")
        heading_s = _heading_text(self.html, "sec12")
        self.assertIn("(연결)", heading_c)
        self.assertNotIn("(연결)", heading_s)

    def test_every_link_target_exists(self):
        ids = _reachable_ids(self.html)
        links = LINK.findall(self.html)
        broken = [t for t, _ in links if t not in ids]
        self.assertEqual([], broken, f"깨진 앵커: {broken}")


class ConvertIntegrationTest(unittest.TestCase):
    """convert_to_html이 만든 최종 파일에 주석 링크가 들어 있어야 한다."""

    def test_converted_file_has_note_links(self):
        os.makedirs(OUT, exist_ok=True)
        out_path = os.path.join(OUT, "integration.html")
        dart_viewer.convert_to_html(
            os.path.join(FIXTURES, "audit_report.xml"), out_path
        )
        with open(out_path, encoding="utf-8") as f:
            html = f.read()
        self.assertTrue(LINK.search(html), "주석 링크가 없다")
        self.assertIn(".nref", html, "주석 링크 스타일이 없다")

    def test_toc_links_are_not_touched(self):
        """목차 사이드바의 링크는 주석 링크로 오인되면 안 된다."""
        os.makedirs(OUT, exist_ok=True)
        out_path = os.path.join(OUT, "integration_toc.html")
        dart_viewer.convert_to_html(
            os.path.join(FIXTURES, "annual_report.xml"), out_path
        )
        with open(out_path, encoding="utf-8") as f:
            html = f.read()
        nav = re.search(r"<nav class=\"toc\">.*?</nav>", html, re.S)
        self.assertIsNotNone(nav, "목차가 없다")
        self.assertNotIn('class="nref"', nav.group(0))


if __name__ == "__main__":
    unittest.main()
