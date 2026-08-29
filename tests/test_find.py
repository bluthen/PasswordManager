import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import qt_mock
import main


class TestFindDialog(unittest.TestCase):
    def setUp(self):
        self.parent = MagicMock()
        self.table = MagicMock()
        self.doc = main.Document()
        self.doc.setData(
            [
                ["google.com", "Alice", "secret1", "Work email"],
                ["GITHUB.COM", "bob", "secret2", "Personal code"],
                ["amazon.com", "Charlie", "secret3", "Shopping"],
            ]
        )
        self.find_dialog = main.FindDialog(self.parent, self.table, self.doc)

    def test_case_insensitive_search_uppercase_query(self):
        # Searching for "GOOGLE" with case sensitivity unchecked should find row 0 ("google.com")
        self.find_dialog.findText.setText("GOOGLE")
        self.find_dialog.caseCheck.setChecked(False)

        self.table.reset_mock()
        self.find_dialog.slotNext(forwardSearch=True)
        self.table.selectRow.assert_called_once_with(0)

    def test_case_insensitive_search_lowercase_query(self):
        # Searching for "github" with case sensitivity unchecked should find row 1 ("GITHUB.COM")
        self.find_dialog.findText.setText("github")
        self.find_dialog.caseCheck.setChecked(False)

        self.table.reset_mock()
        self.find_dialog.slotNext(forwardSearch=True)
        self.table.selectRow.assert_called_once_with(1)

    def test_case_insensitive_search_mixed_case_query(self):
        # Searching for "cHaRlIe" with case sensitivity unchecked should find row 2 ("amazon.com", "Charlie", ...)
        self.find_dialog.findText.setText("cHaRlIe")
        self.find_dialog.caseCheck.setChecked(False)

        self.table.reset_mock()
        self.find_dialog.slotNext(forwardSearch=True)
        self.table.selectRow.assert_called_once_with(2)

    def test_case_sensitive_search_exact_match(self):
        # Searching for "GITHUB" with case sensitivity checked should find row 1
        self.find_dialog.findText.setText("GITHUB")
        self.find_dialog.caseCheck.setChecked(True)

        self.table.reset_mock()
        self.find_dialog.slotNext(forwardSearch=True)
        self.table.selectRow.assert_called_once_with(1)

    def test_case_sensitive_search_mismatch(self):
        # Searching for "github" (lowercase) with case sensitivity checked should not match "GITHUB.COM"
        self.find_dialog.findText.setText("github")
        self.find_dialog.caseCheck.setChecked(True)

        self.table.reset_mock()
        with patch("main.OKDialog") as mock_ok_dialog:
            self.find_dialog.slotNext(forwardSearch=True)
            self.table.selectRow.assert_not_called()
            mock_ok_dialog.assert_called_once()

    def test_search_navigation_next_and_previous(self):
        self.doc.setData(
            [
                ["example1.com", "user1", "pass1", "test"],
                ["example2.com", "user2", "pass2", "test"],
                ["example3.com", "user3", "pass3", "test"],
            ]
        )
        self.find_dialog.findText.setText("EXAMPLE")
        self.find_dialog.caseCheck.setChecked(False)

        # Next -> row 0
        self.table.reset_mock()
        self.find_dialog.slotNext(forwardSearch=True)
        self.table.selectRow.assert_called_once_with(0)

        # Next again -> row 1
        self.table.reset_mock()
        self.find_dialog.slotNext(forwardSearch=True)
        self.table.selectRow.assert_called_once_with(1)

        # Next again -> row 2
        self.table.reset_mock()
        self.find_dialog.slotNext(forwardSearch=True)
        self.table.selectRow.assert_called_once_with(2)

        # Previous -> row 1
        self.table.reset_mock()
        self.find_dialog.slotPrevious()
        self.table.selectRow.assert_called_once_with(1)

    def test_empty_search_string(self):
        self.find_dialog.findText.setText("")
        self.table.reset_mock()
        self.find_dialog.slotNext(forwardSearch=True)
        self.table.selectRow.assert_not_called()

    def test_search_across_different_columns_case_insensitive(self):
        self.doc.setData(
            [
                ["mysite.org", "admin", "pAssWord123", "Important Notes"],
            ]
        )
        self.find_dialog.caseCheck.setChecked(False)

        # Match in column 1 (username)
        self.find_dialog.findText.setText("ADMIN")
        self.table.reset_mock()
        self.find_dialog.slotNext(forwardSearch=True)
        self.table.selectRow.assert_called_once_with(0)

        # Match in column 2 (password)
        self.find_dialog.findText.setText("PASSWORD123")
        self.table.reset_mock()
        self.find_dialog.slotNext(forwardSearch=True)
        self.table.selectRow.assert_called_once_with(0)

        # Match in column 3 (comment)
        self.find_dialog.findText.setText("notes")
        self.table.reset_mock()
        self.find_dialog.slotNext(forwardSearch=True)
        self.table.selectRow.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
