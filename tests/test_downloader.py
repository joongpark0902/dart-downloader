"""downloader._read_document_name가 첨부문서 제목을 제대로 읽어내는지 지킨다.

_DART_BR_ENTITY 참조 누락으로 인한 NameError 회귀를 막는 테스트.
(모든 호출에서 죽었으므로 &cr;가 없는 평범한 파일에서도 재현된다)
"""
import os
import tempfile
import unittest

import downloader


class ReadDocumentNameTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def _write(self, content):
        path = os.path.join(self._tmpdir.name, "doc.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_plain_document_name(self):
        """&cr; 등의 특수 엔티티가 없는 평범한 문서명도 정상적으로 읽혀야 한다."""
        path = self._write("<DOCUMENT-NAME>사업보고서</DOCUMENT-NAME>")
        self.assertEqual("사업보고서", downloader._read_document_name(path))

    def test_cr_entity_becomes_space_and_collapses(self):
        """비표준 엔티티 &cr;는 공백으로 바뀌고, 연속 공백은 하나로 합쳐져야 한다."""
        path = self._write(
            "<DOCUMENT-NAME>사업보고서&cr;&cr;   2024</DOCUMENT-NAME>"
        )
        self.assertEqual("사업보고서 2024", downloader._read_document_name(path))

    def test_missing_tag_returns_empty_string(self):
        """<DOCUMENT-NAME> 태그 자체가 없으면 빈 문자열을 돌려줘야 한다."""
        path = self._write("<DOCUMENT>내용만 있고 이름 태그는 없음</DOCUMENT>")
        self.assertEqual("", downloader._read_document_name(path))


if __name__ == "__main__":
    unittest.main()
