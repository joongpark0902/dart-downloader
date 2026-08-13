"""convert_to_html 출력이 리팩터링 전후로 같은지 지킨다.

골든 파일이 없으면 현재 출력을 기준선으로 저장한다. 기준선을 일부러
바꿔야 할 때는 tests/golden/ 의 해당 파일을 지우고 다시 돌린다.
"""
import os
import unittest

import dart_engine

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
GOLDEN = os.path.join(HERE, "golden")
OUT = os.path.join(HERE, "_out")

FIXTURE_NAMES = ["annual_report", "audit_report"]


class ConvertRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(GOLDEN, exist_ok=True)
        os.makedirs(OUT, exist_ok=True)

    def _convert(self, name):
        xml_path = os.path.join(FIXTURES, name + ".xml")
        out_path = os.path.join(OUT, name + ".html")
        dart_engine.convert_to_html(xml_path, out_path)
        with open(out_path, encoding="utf-8") as f:
            return f.read()

    def test_output_matches_golden(self):
        for name in FIXTURE_NAMES:
            with self.subTest(fixture=name):
                actual = self._convert(name)
                golden_path = os.path.join(GOLDEN, name + ".html")
                if not os.path.exists(golden_path):
                    with open(golden_path, "w", encoding="utf-8") as f:
                        f.write(actual)
                    self.skipTest(f"기준선 생성: {name}.html")
                with open(golden_path, encoding="utf-8") as f:
                    expected = f.read()
                self.assertEqual(expected, actual, f"{name} 출력이 기준선과 다르다")


if __name__ == "__main__":
    unittest.main()
