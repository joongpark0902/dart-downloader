"""읽기용 HTML의 이동 동작을 지킨다."""
import os
import re
import unittest

import dart_viewer

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
OUT = os.path.join(HERE, "_out")


class ViewerCssTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(OUT, exist_ok=True)
        out_path = os.path.join(OUT, "css_check.html")
        dart_viewer.convert_to_html(
            os.path.join(FIXTURES, "annual_report.xml"), out_path
        )
        with open(out_path, encoding="utf-8") as f:
            cls.html = f.read()

    def test_no_smooth_scroll(self):
        """긴 보고서에서 부드러운 스크롤은 수천 줄을 훑고 지나가 눈이 아프다."""
        self.assertNotIn("scroll-behavior: smooth", self.html)

    def test_headings_have_scroll_margin(self):
        """점프 후 제목이 뷰포트 최상단에 붙지 않게 여백을 둔다.

        단순히 문자열이 어딘가에 있는지가 아니라, 제목 선택자 규칙 안에
        있고 :target 규칙 안에는 없는지까지 확인한다.
        """
        headings_rule = re.search(
            r"h1,\s*h2,\s*h3,\s*h4,\s*h5,\s*p\[id\]\s*\{([^}]*)\}", self.html
        )
        self.assertIsNotNone(headings_rule, "제목 선택자 규칙을 찾지 못했다")
        self.assertIn("scroll-margin-top", headings_rule.group(1))

        target_rule = re.search(r":target\s*\{([^}]*)\}", self.html)
        self.assertIsNotNone(target_rule, ":target 규칙을 찾지 못했다")
        self.assertNotIn("scroll-margin-top", target_rule.group(1))


if __name__ == "__main__":
    unittest.main()
