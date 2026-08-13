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
        """href가 가리키는 id가 문서에 실제로 있어야 한다."""
        for name, html in (("annual", self.annual), ("audit", self.audit)):
            with self.subTest(doc=name):
                ids = set(ANY_ID.findall(html))
                broken = [t for t, _ in self._links(html) if t not in ids]
                self.assertEqual([], broken, f"깨진 앵커: {broken}")

    def test_consolidated_and_separate_sets_differ(self):
        """연결 재무상태표의 주석3과 별도 재무상태표의 주석3은 다른 곳으로 간다."""
        rows = re.findall(r"재고자산\(주석(.*?)\)", self.annual)
        self.assertEqual(2, len(rows), "재고자산 행 2개를 찾지 못했다")
        first = LINK.findall(rows[0])
        second = LINK.findall(rows[1])
        self.assertTrue(first and second)
        self.assertNotEqual(first[0][0], second[0][0],
                            "연결·별도가 같은 앵커로 갔다")

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


if __name__ == "__main__":
    unittest.main()
