"""읽기용 HTML의 이동 동작을 지킨다."""
import os
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
        """점프 후 제목이 뷰포트 최상단에 붙지 않게 여백을 둔다."""
        self.assertIn("scroll-margin-top", self.html)


if __name__ == "__main__":
    unittest.main()
