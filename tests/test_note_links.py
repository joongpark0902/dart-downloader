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
ANY_ID = re.compile(r'id="([^"]+)"')


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
                ids = set(ANY_ID.findall(html))
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
