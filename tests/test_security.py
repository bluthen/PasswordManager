import os
import stat
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import qt_mock
import main
import misc
import passwordGenerator


class TestSecurityFixes(unittest.TestCase):
    def test_password_generator_entropy_and_character_classes(self):
        # Test across 50 consecutive calls to ensure no global state bug
        for _ in range(50):
            pwd = passwordGenerator.generate_password(length=16)
            self.assertGreaterEqual(len(pwd), 16)
            has_lower = any(c.islower() for c in pwd)
            has_upper = any(c.isupper() for c in pwd)
            has_digit = any(c.isdigit() for c in pwd)
            has_special = any(c in passwordGenerator.SPECIAL_CHARS for c in pwd)

            self.assertTrue(has_lower, f"Missing lowercase in {pwd}")
            self.assertTrue(has_upper, f"Missing uppercase in {pwd}")
            self.assertTrue(has_digit, f"Missing digit in {pwd}")
            self.assertTrue(has_special, f"Missing special character in {pwd}")

    def test_password_generator_custom_length(self):
        pwd = passwordGenerator.generate_password(length=24)
        self.assertEqual(len(pwd), 24)

        # Minimum length enforcement
        pwd_short = passwordGenerator.generate_password(length=4)
        self.assertGreaterEqual(len(pwd_short), 8)

    def test_save_atomic_and_permissions(self):
        doc = main.Document()
        doc.setData([["site", "cat", "user", "pass", "comment"]])

        with tempfile.TemporaryDirectory() as tmp_dir:
            vault_file = os.path.join(tmp_dir, "test_vault.gcsv")

            def mock_popen(*args, **kwargs):
                proc = MagicMock()
                proc.communicate.return_value = (b"ENCRYPTED_VAULT_BYTES", b"")
                proc.returncode = 0
                return proc

            with (
                patch("main.Config") as mock_cfg,
                patch("main.subprocess.Popen", side_effect=mock_popen),
            ):
                cfg = mock_cfg.return_value
                cfg.getPreOpenCommand.return_value = ""
                cfg.getPostSaveCommand.return_value = ""
                cfg.getEncCommand.return_value = "$g --encrypt -r $k"
                cfg.getGPGKey.return_value = "MYKEYID"
                cfg.getOpenLast.return_value = False
                cfg.getCSVDelimiterTab.return_value = True
                cfg.getCSVQuoteCheck.return_value = False
                cfg.getCSVQuote.return_value = ""

                doc.save(vault_file)

            self.assertTrue(os.path.exists(vault_file))
            with open(vault_file, "rb") as f:
                self.assertEqual(f.read(), b"ENCRYPTED_VAULT_BYTES")

            # Verify permissions on POSIX systems (0600)
            if os.name == "posix":
                file_mode = stat.S_IMODE(os.stat(vault_file).st_mode)
                self.assertEqual(file_mode, 0o600)

    def test_save_cleans_up_on_failure(self):
        doc = main.Document()
        doc.setData([["site", "cat", "user", "pass", "comment"]])

        with tempfile.TemporaryDirectory() as tmp_dir:
            vault_file = os.path.join(tmp_dir, "test_vault.gcsv")

            def mock_popen_fail(*args, **kwargs):
                proc = MagicMock()
                proc.communicate.return_value = (b"", b"GPG encryption error")
                proc.returncode = 2
                return proc

            with (
                patch("main.Config") as mock_cfg,
                patch("main.subprocess.Popen", side_effect=mock_popen_fail),
            ):
                cfg = mock_cfg.return_value
                cfg.getPreOpenCommand.return_value = ""
                cfg.getPostSaveCommand.return_value = ""
                cfg.getEncCommand.return_value = "$g --encrypt -r $k"
                cfg.getGPGKey.return_value = "MYKEYID"
                cfg.getOpenLast.return_value = False
                cfg.getCSVDelimiterTab.return_value = True
                cfg.getCSVQuoteCheck.return_value = False
                cfg.getCSVQuote.return_value = ""

                with self.assertRaises(Exception) as ctx:
                    doc.save(vault_file)
                self.assertIn("Failed to encrypt data", str(ctx.exception))

            # Ensure no orphaned temp files remain
            remaining_files = os.listdir(tmp_dir)
            self.assertEqual(remaining_files, [])

    def test_save_validates_gpg_key(self):
        doc = main.Document()
        doc.setData([["site", "cat", "user", "pass", "comment"]])

        with tempfile.TemporaryDirectory() as tmp_dir:
            vault_file = os.path.join(tmp_dir, "test_vault.gcsv")

            with patch("main.Config") as mock_cfg:
                cfg = mock_cfg.return_value
                cfg.getEncCommand.return_value = "$g --encrypt -r $k"
                cfg.getGPGKey.return_value = ""

                with self.assertRaises(Exception) as ctx:
                    doc.save(vault_file)
                self.assertIn("GPG Key is not configured", str(ctx.exception))

    def test_parse_colon_delimited_gpg_keys(self):
        colon_output = """
sec:u:2048:1:D833441B88B270C0:1580000000:::u:::scESC:::
fpr:::::::::E7B8749202D3A5D4C3A9B2E8D833441B88B270C0:
uid:u::::1580000000::...::Alice User <alice@example.com>:
sec:u:4096:1:1234567890ABCDEF:1600000000:::u:::scESC:::
uid:u::::1600000000::...::Bob User <bob@example.com>:
"""
        keys = main.KeyTableModel._parse_keys(colon_output)
        self.assertEqual(len(keys), 2)
        self.assertEqual(keys[0][1], "D833441B88B270C0")
        self.assertIn("Alice User", keys[0][0])
        self.assertEqual(keys[1][1], "1234567890ABCDEF")
        self.assertIn("Bob User", keys[1][0])

    def test_parse_legacy_human_readable_gpg_keys(self):
        legacy_output = """
sec   rsa2048/A1B2C3D4 2020-01-01 [SC]
uid           [ultimate] Legacy User <legacy@example.com>

sec   rsa4096/E5F6A7B8 2021-05-01 [SC]
uid           [ultimate] Another User <another@example.com>
"""
        keys = main.KeyTableModel._parse_keys(legacy_output)
        self.assertEqual(len(keys), 2)
        self.assertEqual(keys[0][1], "A1B2C3D4")
        self.assertEqual(keys[1][1], "E5F6A7B8")

    def test_command_symbol_replacement(self):
        with patch("misc.Config") as mock_cfg:
            cfg = mock_cfg.return_value
            cfg.getGPGPath.return_value = "/usr/bin/gpg2"
            cfg.getGPGKey.return_value = "KEY123"

            gpg_cmd = ["$g", "--no-tty", "-r", "$k", "-d", "$f"]
            misc.replace_gpg_symbols(gpg_cmd, "/path/to/my vault.gcsv")
            self.assertEqual(
                gpg_cmd,
                [
                    "/usr/bin/gpg2",
                    "--no-tty",
                    "-r",
                    "KEY123",
                    "-d",
                    "/path/to/my vault.gcsv",
                ],
            )

            save_cmd = ["git", "--work-tree=$d", "add", "$f"]
            misc.replace_open_save_symbols(save_cmd, "/path/to/vault.gcsv")
            self.assertEqual(
                save_cmd,
                ["git", "--work-tree=/path/to", "add", "/path/to/vault.gcsv"],
            )

    def test_edit_dialog_password_masking(self):
        doc = main.Document()
        mock_main = MagicMock()
        mock_main.viewPasswords.isChecked.return_value = False
        model = main.MainTableModel(doc, mock_main)
        edit_dialog = main.EditDialog(mock_main, doc, model)

        # Ensure password field uses Password echo mode (masked) initially
        self.assertEqual(
            edit_dialog.password.echoMode(),
            main.QtWidgets.QLineEdit.Password,
        )
        # Ensure show checkbox widget has been removed
        self.assertNotIn("showCheck", edit_dialog.__dict__)

        # Ensure trailing toggle password action is present
        self.assertTrue(hasattr(edit_dialog, "togglePasswordAction"))

        # Test toggling password visibility
        edit_dialog.slotTogglePassword()
        self.assertEqual(
            edit_dialog.password.echoMode(),
            main.QtWidgets.QLineEdit.Normal,
        )

        edit_dialog.slotTogglePassword()
        self.assertEqual(
            edit_dialog.password.echoMode(),
            main.QtWidgets.QLineEdit.Password,
        )

        # Test clear resets echo mode back to Password
        edit_dialog.slotTogglePassword()  # now Normal
        edit_dialog.clear()
        self.assertEqual(
            edit_dialog.password.echoMode(),
            main.QtWidgets.QLineEdit.Password,
        )

    def test_create_eye_icon(self):
        icon_hidden = main.create_eye_icon(visible=False)
        icon_visible = main.create_eye_icon(visible=True)
        self.assertIsNotNone(icon_hidden)
        self.assertIsNotNone(icon_visible)


if __name__ == "__main__":
    unittest.main()
