"""dart_engine이 내보내던 이름이 리팩터링 후에도 살아 있는지 지킨다."""
import ast
import importlib
import os
import unittest

PUBLIC_NAMES = [
    "load_corp_list", "search_company", "list_disclosures",
    "safe_filename", "download_document",
    "get_key_financials", "get_key_financials_3y",
    "get_dividend_info", "get_dividend_info_3y",
    "calculate_financial_ratios",
    "get_extended_financials", "get_extended_financials_3y",
    "get_equity_investments", "get_audit_opinion_3y",
    "get_major_shareholder", "get_employee_status",
    "get_capital_changes", "get_capital_changes_3y",
    "convert_to_html", "fix_xml", "AUDIT_TYPE",
]

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")


class PublicApiTest(unittest.TestCase):
    def test_dart_engine_exports(self):
        engine = importlib.import_module("dart_engine")
        missing = [n for n in PUBLIC_NAMES if not hasattr(engine, n)]
        self.assertEqual([], missing, f"dart_engine에서 사라진 이름: {missing}")

    def test_scripts_imports_resolve(self):
        """scripts/ 도구가 dart_engine에서 끌어 쓰는 이름이 전부 살아 있어야 한다.

        스크립트를 실제로 임포트하면 네트워크를 타므로 AST로만 확인한다.
        """
        engine = importlib.import_module("dart_engine")
        for fname in sorted(os.listdir(SCRIPTS)):
            if not fname.endswith(".py"):
                continue
            path = os.path.join(SCRIPTS, fname)
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
            wanted = [
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module == "dart_engine"
                for alias in node.names
            ]
            with self.subTest(script=fname):
                missing = [n for n in wanted if not hasattr(engine, n)]
                self.assertEqual([], missing, f"{fname}가 못 찾는 이름: {missing}")


if __name__ == "__main__":
    unittest.main()
