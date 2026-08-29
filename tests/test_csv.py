import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import qt_mock
import main


class TestCSVSerialization(unittest.TestCase):
    def setUp(self):
        self.doc = main.Document()
        self.test_entries = [
            ["Site 1", "user1", "simple_password", "simple comment"],
            ["Site 2", "user2", "p@ss\tword", "comment\twith\ttab"],
            ["Site 3", "user3", "p@ss\nword", "comment\nwith\nnewline"],
            ["Site 4", "user4", "p@ss\r\nword", "comment\r\nwith\rcrlf"],
            ["Site 5", "user5", 'p@ss"word"', 'comment"with"quotes'],
            ["Site 6", "user6", "p@ss'word'", "comment'with'quotes"],
            ["Site 7", "user7", "p@ss\\word", "comment\\with\\backslash"],
            ["Site 8", "user8", "p@ss\\\\double", "comment\\\\double"],
            ["Site 9", "user9", "p@ss,with,comma", "comment,with,comma"],
            ["Site 10", "user10", "p@ss;with;semi", "comment;with;semi"],
            ["Site 11", "user11", "p@ss|with|pipe", "comment|with|pipe"],
            [
                "Site 12",
                "user12",
                "🔐 🔑 中文 日本語 Русский €£¥",
                "unicode & emojis 🚀",
            ],
            [
                "Site 13",
                "user13",
                "pass ~!@#$%^&*()-_=+[{]}\\|;:'\",<.>/?",
                "all ascii specials",
            ],
        ]

    def _mock_gpg_encrypt_decrypt(self, saved_storage):
        def mock_encrypt_popen(*args, **kwargs):
            mock_proc = MagicMock()

            def communicate(input_bytes=None):
                saved_storage["content"] = input_bytes
                return (input_bytes, b"")

            mock_proc.communicate = communicate
            mock_proc.returncode = 0
            return mock_proc

        def mock_decrypt_popen(*args, **kwargs):
            mock_proc = MagicMock()

            def communicate(input_bytes=None):
                return (saved_storage.get("content", b""), b"")

            mock_proc.communicate = communicate
            mock_proc.returncode = 0
            return mock_proc

        return mock_encrypt_popen, mock_decrypt_popen

    def test_save_and_load_special_chars_quote_none_tab(self):
        saved_storage = {}
        mock_enc, mock_dec = self._mock_gpg_encrypt_decrypt(saved_storage)

        with tempfile.NamedTemporaryFile(suffix=".gcsv", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with (
                patch("main.Config") as mock_cfg,
                patch("main.subprocess.Popen", side_effect=mock_enc),
            ):
                cfg = mock_cfg.return_value
                cfg.getPreOpenCommand.return_value = ""
                cfg.getPostSaveCommand.return_value = ""
                cfg.getEncCommand.return_value = "$g --encrypt"
                cfg.getOpenLast.return_value = False
                cfg.getCSVDelimiterTab.return_value = True
                cfg.getCSVQuoteCheck.return_value = False
                cfg.getCSVQuote.return_value = ""

                self.doc.setData(self.test_entries)
                self.doc.save(tmp_path)

            load_doc = main.Document()
            with (
                patch("main.Config") as mock_cfg,
                patch("main.subprocess.Popen", side_effect=mock_dec),
            ):
                cfg = mock_cfg.return_value
                cfg.getPreOpenCommand.return_value = ""
                cfg.getPostSaveCommand.return_value = ""
                cfg.getDecCommand.return_value = "$g -d $f"
                cfg.getCSVDelimiterTab.return_value = True
                cfg.getCSVQuoteCheck.return_value = False
                cfg.getCSVQuote.return_value = ""

                load_doc.load(tmp_path)

            self.assertEqual(load_doc.getData(), self.test_entries)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_save_and_load_special_chars_quoted(self):
        saved_storage = {}
        mock_enc, mock_dec = self._mock_gpg_encrypt_decrypt(saved_storage)

        with tempfile.NamedTemporaryFile(suffix=".gcsv", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with (
                patch("main.Config") as mock_cfg,
                patch("main.subprocess.Popen", side_effect=mock_enc),
            ):
                cfg = mock_cfg.return_value
                cfg.getPreOpenCommand.return_value = ""
                cfg.getPostSaveCommand.return_value = ""
                cfg.getEncCommand.return_value = "$g --encrypt"
                cfg.getOpenLast.return_value = False
                cfg.getCSVDelimiterTab.return_value = True
                cfg.getCSVQuoteCheck.return_value = True
                cfg.getCSVQuote.return_value = '"'

                self.doc.setData(self.test_entries)
                self.doc.save(tmp_path)

            load_doc = main.Document()
            with (
                patch("main.Config") as mock_cfg,
                patch("main.subprocess.Popen", side_effect=mock_dec),
            ):
                cfg = mock_cfg.return_value
                cfg.getPreOpenCommand.return_value = ""
                cfg.getPostSaveCommand.return_value = ""
                cfg.getDecCommand.return_value = "$g -d $f"
                cfg.getCSVDelimiterTab.return_value = True
                cfg.getCSVQuoteCheck.return_value = True
                cfg.getCSVQuote.return_value = '"'

                load_doc.load(tmp_path)

            self.assertEqual(load_doc.getData(), self.test_entries)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_save_and_load_custom_delimiter(self):
        saved_storage = {}
        mock_enc, mock_dec = self._mock_gpg_encrypt_decrypt(saved_storage)

        with tempfile.NamedTemporaryFile(suffix=".gcsv", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with (
                patch("main.Config") as mock_cfg,
                patch("main.subprocess.Popen", side_effect=mock_enc),
            ):
                cfg = mock_cfg.return_value
                cfg.getPreOpenCommand.return_value = ""
                cfg.getPostSaveCommand.return_value = ""
                cfg.getEncCommand.return_value = "$g --encrypt"
                cfg.getOpenLast.return_value = False
                cfg.getCSVDelimiterTab.return_value = False
                cfg.getCSVDelimiter.return_value = ","
                cfg.getCSVQuoteCheck.return_value = False
                cfg.getCSVQuote.return_value = ""

                self.doc.setData(self.test_entries)
                self.doc.save(tmp_path)

            load_doc = main.Document()
            with (
                patch("main.Config") as mock_cfg,
                patch("main.subprocess.Popen", side_effect=mock_dec),
            ):
                cfg = mock_cfg.return_value
                cfg.getPreOpenCommand.return_value = ""
                cfg.getPostSaveCommand.return_value = ""
                cfg.getDecCommand.return_value = "$g -d $f"
                cfg.getCSVDelimiterTab.return_value = False
                cfg.getCSVDelimiter.return_value = ","
                cfg.getCSVQuoteCheck.return_value = False
                cfg.getCSVQuote.return_value = ""

                load_doc.load(tmp_path)

            self.assertEqual(load_doc.getData(), self.test_entries)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_save_with_empty_quote_char(self):
        saved_storage = {}
        mock_enc, mock_dec = self._mock_gpg_encrypt_decrypt(saved_storage)

        with tempfile.NamedTemporaryFile(suffix=".gcsv", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with (
                patch("main.Config") as mock_cfg,
                patch("main.subprocess.Popen", side_effect=mock_enc),
            ):
                cfg = mock_cfg.return_value
                cfg.getPreOpenCommand.return_value = ""
                cfg.getPostSaveCommand.return_value = ""
                cfg.getEncCommand.return_value = "$g --encrypt"
                cfg.getOpenLast.return_value = False
                cfg.getCSVDelimiterTab.return_value = True
                cfg.getCSVQuoteCheck.return_value = True
                cfg.getCSVQuote.return_value = ""  # Empty quote string shouldn't crash

                self.doc.setData(self.test_entries)
                self.doc.save(tmp_path)

            load_doc = main.Document()
            with (
                patch("main.Config") as mock_cfg,
                patch("main.subprocess.Popen", side_effect=mock_dec),
            ):
                cfg = mock_cfg.return_value
                cfg.getPreOpenCommand.return_value = ""
                cfg.getPostSaveCommand.return_value = ""
                cfg.getDecCommand.return_value = "$g -d $f"
                cfg.getCSVDelimiterTab.return_value = True
                cfg.getCSVQuoteCheck.return_value = True
                cfg.getCSVQuote.return_value = ""

                load_doc.load(tmp_path)

            self.assertEqual(load_doc.getData(), self.test_entries)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_import_csv(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write("site1,user1,pass1,comm1\n")
            tmp.write('site2,user2,"pass,2","comm\n2"\n')
            tmp_path = tmp.name

        try:
            import_doc = main.Document()
            import_doc.importCSV(tmp_path, delim=",", quote='"')
            expected = [
                ["site1", "user1", "pass1", "comm1"],
                ["site2", "user2", "pass,2", "comm\n2"],
            ]
            self.assertEqual(import_doc.getData(), expected)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_import_csv_quote_none(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write("site1\tuser1\tpass1\tcomm1\n")
            tmp.write("site2\tuser2\tpass\\\t2\tcomm\\\n2\n")
            tmp_path = tmp.name

        try:
            import_doc = main.Document()
            import_doc.importCSV(tmp_path, delim="\t", quote=None)
            expected = [
                ["site1", "user1", "pass1", "comm1"],
                ["site2", "user2", "pass\t2", "comm\n2"],
            ]
            self.assertEqual(import_doc.getData(), expected)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_import_csv_padding(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write("site1,user1\n")
            tmp.write("site2\n")
            tmp_path = tmp.name

        try:
            import_doc = main.Document()
            import_doc.importCSV(tmp_path, delim=",", quote=None)
            expected = [
                ["site1", "user1", "", ""],
                ["site2", "", "", ""],
            ]
            self.assertEqual(import_doc.getData(), expected)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
