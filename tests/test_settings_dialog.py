# -*- coding: utf-8 -*-
"""화면 대역과 실제 저장 함수를 연결한 설정 편집 회귀 테스트."""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from therapy_chart import storage
from therapy_chart.settings_dialog import ListEditor, SettingsDialog


class TestSettingsEditing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"APPDATA": self.tmp.name})
        self.environment.start()
        self.settings = storage.load_settings()

    def tearDown(self):
        self.environment.stop()
        self.tmp.cleanup()

    def test_list_edit_after_saving_another_tab_and_consecutive_changes(self):
        editor = SimpleNamespace(items=self.settings["purposes"], entry_var=Mock(), refresh=Mock(),
                                 selected_index=lambda: 0, protected=set(), on_rename=Mock(), on_delete=Mock())
        editor.on_change = lambda _: storage.save_settings(self.settings)
        editor._changed = lambda: ListEditor._changed(editor)
        self.settings["treatment_minutes"] = 45
        self.assertTrue(storage.save_settings(self.settings))
        for name in ("first", "second"):
            editor.entry_var.get.return_value = name
            ListEditor.add(editor)
        editor.entry_var.get.return_value = "renamed"
        ListEditor.rename(editor)
        with patch("therapy_chart.settings_dialog.messagebox.askyesno", return_value=True):
            ListEditor.delete(editor)
        persisted = storage.load_settings()["purposes"]
        self.assertEqual(persisted, editor.items)
        self.assertIn("first", persisted)
        self.assertIn("second", persisted)
        self.assertNotIn("renamed", persisted)

    def make_dialog(self):
        dialog = SimpleNamespace(settings=self.settings, diag_code_var=Mock(), diag_name_var=Mock(),
                                 diag_search_var=Mock(), diag_listbox=Mock(), master=Mock(), destroy=Mock())
        dialog.diag_search_var.get.return_value = ""
        dialog.diag_listbox.curselection.return_value = (0,)
        dialog.refresh_diag_list = lambda: SettingsDialog.refresh_diag_list(dialog)
        dialog._selected_diag = lambda: SettingsDialog._selected_diag(dialog)
        dialog.on_change = lambda replacement=None: storage.save_settings(self.settings, replacement=replacement)
        dialog.changed = lambda replacement=None: SettingsDialog.changed(dialog, replacement)
        dialog.refresh_diag_list()
        return dialog

    def test_consecutive_diagnosis_updates_favorite_and_delete(self):
        dialog = self.make_dialog()
        dialog.diag_code_var.get.return_value = "m75.1"
        for name in ("first", "second"):
            dialog.diag_name_var.get.return_value = name
            SettingsDialog.diag_update(dialog)
        SettingsDialog.diag_toggle_favorite(dialog)
        persisted = storage.load_settings()["diagnoses"][0]
        self.assertEqual(persisted["name"], "second")
        self.assertTrue(persisted["favorite"])
        with patch("therapy_chart.settings_dialog.messagebox.askyesno", return_value=True):
            SettingsDialog.diag_delete(dialog)
        self.assertFalse(any(d["name"] == "second" for d in storage.load_settings()["diagnoses"]))

    def test_restore_failure_preserves_existing_settings(self):
        dialog = self.make_dialog()
        self.settings["therapists"] = ["original"]
        self.assertTrue(storage.save_settings(self.settings))
        path = os.path.join(self.tmp.name, "backup.json")
        storage.backup_to(path, {"therapists": ["restored"]})
        with patch("therapy_chart.settings_dialog.filedialog.askopenfilename", return_value=path), \
             patch("therapy_chart.settings_dialog.messagebox.askyesno", return_value=True), \
             patch("therapy_chart.settings_dialog.messagebox.showerror") as error, \
             patch.object(storage.os, "replace", side_effect=OSError("disk error")):
            SettingsDialog.restore(dialog)
        error.assert_called_once()
        self.assertEqual(self.settings["therapists"], ["original"])
        self.assertEqual(storage.load_settings()["therapists"], ["original"])
        dialog.destroy.assert_not_called()

    def test_restore_success_applies_and_closes(self):
        dialog = self.make_dialog()
        path = os.path.join(self.tmp.name, "backup.json")
        storage.backup_to(path, {"therapists": ["restored"]})
        with patch("therapy_chart.settings_dialog.filedialog.askopenfilename", return_value=path), \
             patch("therapy_chart.settings_dialog.messagebox.askyesno", return_value=True), \
             patch("therapy_chart.settings_dialog.messagebox.showinfo"):
            SettingsDialog.restore(dialog)
        self.assertEqual(self.settings["therapists"], ["restored"])
        dialog.destroy.assert_called_once()

    def test_reload_action_recovers_conflicted_dialog(self):
        dialog = self.make_dialog()
        external = storage.load_settings()
        external["therapists"] = ["external"]
        self.assertTrue(storage.save_settings(external))
        self.assertFalse(storage.save_settings(self.settings))
        with patch("therapy_chart.settings_dialog.messagebox.askyesno", return_value=True):
            SettingsDialog.reload_settings(dialog)
        self.assertEqual(self.settings["therapists"], ["external"])
        self.assertTrue(storage.save_settings(self.settings))
        dialog.master.refresh_from_settings.assert_called_once()
        dialog.destroy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
