import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import qt_mock
import main


class TestCategoryFeature(unittest.TestCase):
    def setUp(self):
        self.doc = main.Document()

    def test_backward_compatibility_4_columns(self):
        # 4-column CSV without category
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write("site1,user1,pass1,comm1\n")
            tmp.write("site2,user2,pass2,comm2\n")
            tmp_path = tmp.name

        try:
            self.doc.importCSV(tmp_path, delim=",", quote='"')
            data = self.doc.getData()
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0], ["site1", "", "user1", "pass1", "comm1"])
            self.assertEqual(data[1], ["site2", "", "user2", "pass2", "comm2"])
            self.assertEqual(self.doc.getCategories(), [])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_save_and_load_5_columns(self):
        entries = [
            ["site1", "Work", "user1", "pass1", "comm1"],
            ["site2", "Personal", "user2", "pass2", "comm2"],
            ["site3", "", "user3", "pass3", "comm3"],
        ]
        self.doc.setData(entries)
        self.assertEqual(self.doc.getCategories(), ["Personal", "Work"])

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as tmp:
            tmp_path = tmp.name

        try:
            # Test direct importCSV on 5-column CSV
            with open(tmp_path, "w", newline="", encoding="utf-8") as f:
                f.write("site1,Work,user1,pass1,comm1\n")
                f.write("site2,Personal,user2,pass2,comm2\n")

            new_doc = main.Document()
            new_doc.importCSV(tmp_path, delim=",", quote='"')
            self.assertEqual(
                new_doc.getData(),
                [
                    ["site1", "Work", "user1", "pass1", "comm1"],
                    ["site2", "Personal", "user2", "pass2", "comm2"],
                ],
            )
            self.assertEqual(new_doc.getCategories(), ["Personal", "Work"])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_main_table_model_category_filtering(self):
        entries = [
            ["site1", "Work", "user1", "pass1", "comm1"],
            ["site2", "Personal", "user2", "pass2", "comm2"],
            ["site3", "Work", "user3", "pass3", "comm3"],
            ["site4", "Finance", "user4", "pass4", "comm4"],
        ]
        self.doc.setData(entries)
        mock_main = MagicMock()
        mock_main.viewPasswords.isChecked.return_value = False
        model = main.MainTableModel(self.doc, mock_main)

        # "All Categories" (default)
        self.assertEqual(model.rowCount(), 4)
        self.assertEqual(model.columnCount(), 5)

        # Filter by "Work"
        model.setCategoryFilter("Work")
        self.assertEqual(model.rowCount(), 2)
        # Verify visible rows map to doc rows with "Work"
        self.assertEqual(self.doc.getData()[model.getDocRow(0)][1], "Work")
        self.assertEqual(self.doc.getData()[model.getDocRow(1)][1], "Work")

        # Filter by "Finance"
        model.setCategoryFilter("Finance")
        self.assertEqual(model.rowCount(), 1)
        self.assertEqual(self.doc.getData()[model.getDocRow(0)][1], "Finance")

        # Filter back to "All Categories"
        model.setCategoryFilter("All Categories")
        self.assertEqual(model.rowCount(), 4)

    def test_table_model_password_masking(self):
        self.doc.setData(
            [
                ["site1", "Work", "user1", "secret_pass", "comm1"],
            ]
        )
        mock_main = MagicMock()
        mock_main.viewPasswords.isChecked.return_value = False
        model = main.MainTableModel(self.doc, mock_main)

        # With show passwords unchecked, password column (col 3) is masked
        index_pass = MagicMock()
        index_pass.row.return_value = 0
        index_pass.column.return_value = 3
        self.assertEqual(model.data(index_pass, 0), "****")

        # With show passwords checked, password column (col 3) is visible
        mock_main.viewPasswords.isChecked.return_value = True
        self.assertEqual(model.data(index_pass, 0), "secret_pass")

    def test_table_model_sorting(self):
        self.doc.setData(
            [
                ["zebra", "Z-Cat", "user1", "p1", "c1"],
                ["apple", "A-Cat", "user2", "p2", "c2"],
                ["mango", "M-Cat", "user3", "p3", "c3"],
            ]
        )
        mock_main = MagicMock()
        mock_main.viewPasswords.isChecked.return_value = False
        model = main.MainTableModel(self.doc, mock_main)

        # Sort by Name (col 0) ascending
        model.sort(0, 0)
        self.assertEqual(self.doc.getData()[0][0], "apple")
        self.assertEqual(self.doc.getData()[1][0], "mango")
        self.assertEqual(self.doc.getData()[2][0], "zebra")

        # Sort by Category (col 1) ascending
        model.sort(1, 0)
        self.assertEqual(self.doc.getData()[0][1], "A-Cat")
        self.assertEqual(self.doc.getData()[1][1], "M-Cat")
        self.assertEqual(self.doc.getData()[2][1], "Z-Cat")

    def test_find_dialog_with_category_filtering(self):
        entries = [
            ["alpha.com", "Work", "alice", "p1", "note"],
            ["beta.com", "Personal", "alice", "p2", "note"],
            ["gamma.com", "Work", "charlie", "p3", "note"],
        ]
        self.doc.setData(entries)
        mock_main = MagicMock()
        mock_main.viewPasswords.isChecked.return_value = False
        model = main.MainTableModel(self.doc, mock_main)
        table = MagicMock()
        table.model.return_value = model

        find_dialog = main.FindDialog(None, table, self.doc)
        find_dialog.findText.setText("alice")
        find_dialog.caseCheck.setChecked(False)

        # Search in "All Categories": should find row 0 (alpha.com) then row 1 (beta.com)
        table.reset_mock()
        find_dialog.slotNext(forwardSearch=True)
        table.selectRow.assert_called_once_with(0)

        table.reset_mock()
        find_dialog.slotNext(forwardSearch=True)
        table.selectRow.assert_called_once_with(1)

        # Now filter by "Personal": only beta.com is visible (table row index 0)
        model.setCategoryFilter("Personal")
        find_dialog.lastText = None  # Reset search state

        table.reset_mock()
        find_dialog.slotNext(forwardSearch=True)
        # Should select visible row 0 in table, which corresponds to beta.com (doc row 1)
        table.selectRow.assert_called_once_with(0)
        self.assertEqual(self.doc.getData()[model.getDocRow(0)][0], "beta.com")

        # Search for "gamma" while filtered by "Personal" should NOT match (gamma is in "Work")
        find_dialog.lastText = None
        find_dialog.findText.setText("gamma")
        table.reset_mock()
        with patch("main.OKDialog") as mock_ok:
            find_dialog.slotNext(forwardSearch=True)
            table.selectRow.assert_not_called()
            mock_ok.assert_called_once()

    def test_edit_dialog_add_and_edit_category(self):
        self.doc.setData(
            [
                ["site1", "Work", "user1", "pass1", "comm1"],
                ["site2", "Personal", "user2", "pass2", "comm2"],
            ]
        )
        mock_main = MagicMock()
        mock_main.viewPasswords.isChecked.return_value = False
        model = main.MainTableModel(self.doc, mock_main)

        edit_dialog = main.EditDialog(mock_main, self.doc, model)

        # New entry with new category
        edit_dialog.clear(defaultCategory="Work")
        edit_dialog.name.setText("site3")
        edit_dialog.category.setCurrentText("Finance")
        edit_dialog.username.setText("user3")
        edit_dialog.password.setText("pass3")
        edit_dialog.comment.setText("comm3")
        edit_dialog.slotOk()

        self.assertEqual(len(self.doc.getData()), 3)
        self.assertIn(
            ["site3", "Finance", "user3", "pass3", "comm3"], self.doc.getData()
        )
        self.assertIn("Finance", self.doc.getCategories())

        # Edit existing entry category
        edit_dialog.setRow(0)
        edit_dialog.category.setCurrentText("Banking")
        edit_dialog.slotOk()

        self.assertEqual(self.doc.getData()[0][1], "Banking")
        self.assertIn("Banking", self.doc.getCategories())

    def test_main_window_initial_sort_ascending(self):
        mock_app = MagicMock()
        win = main.MainWindow(mock_app)
        win.document.setData(
            [
                ["zebra", "Z", "u1", "p1", "c1"],
                ["apple", "A", "u2", "p2", "c2"],
                ["mango", "M", "u3", "p3", "c3"],
            ]
        )
        win.mymodel.resort()

        # Should sort Ascending (A at top, Z at bottom)
        self.assertEqual(win.document.getData()[0][0], "apple")
        self.assertEqual(win.document.getData()[1][0], "mango")
        self.assertEqual(win.document.getData()[2][0], "zebra")
        # Header indicator should be column 0, AscendingOrder (0)
        self.assertEqual(win.table.horizontalHeader().sortIndicatorSection(), 0)
        self.assertEqual(win.table.horizontalHeader().sortIndicatorOrder(), 0)


if __name__ == "__main__":
    unittest.main()
