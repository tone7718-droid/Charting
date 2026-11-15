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
    def test_csv_import_reports_save_failure_instead_of_success(self):
        for reason in ("io", "conflict"):
            with self.subTest(reason=reason):
                dialog = self.make_dialog()
                dialog.changed = Mock(return_value=False)
                with patch("therapy_chart.settings_dialog.filedialog.askopenfilename", return_value="test.csv"), \
                     patch.object(storage, "import_diagnoses_csv", return_value=([{"code": "TEST", "name": "test"}], 0)), \
                     patch.object(storage, "get_last_save_error", return_value=reason), \
                     patch("therapy_chart.settings_dialog.messagebox.showinfo") as info, \
                     patch("therapy_chart.settings_dialog.messagebox.showerror") as error:
                    SettingsDialog.diag_import_csv(dialog)
                info.assert_not_called()
                error.assert_called_once()
                self.assertIn("저장하지 못했습니다", error.call_args.args[1])
                self.assertTrue(any(d["code"] == "TEST" for d in self.settings["diagnoses"]))

    def test_csv_import_reports_success_after_persisting(self):
        dialog = self.make_dialog()
        with patch("therapy_chart.settings_dialog.filedialog.askopenfilename", return_value="test.csv"), \
             patch.object(storage, "import_diagnoses_csv", return_value=([{"code": "TEST", "name": "test"}], 0)), \
             patch("therapy_chart.settings_dialog.messagebox.showinfo") as info, \
             patch("therapy_chart.settings_dialog.messagebox.showerror") as error:
            SettingsDialog.diag_import_csv(dialog)
        error.assert_not_called()
        info.assert_called_once()
        self.assertTrue(any(d["code"] == "TEST" for d in storage.load_settings()["diagnoses"]))

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
                                 diag_search_var=Mock(), diag_listbox=Mock(), master=Mock(), destroy=Mock(),
                                 _diag_view=[])
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


class TestSettingsDialogWindow(unittest.TestCase):
    """실제 설정 창을 띄워 목록 선택 동작을 검증한다."""

    def setUp(self):
        import tkinter as tk

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        environment = patch.dict(os.environ, {"APPDATA": self.tmp.name})
        environment.start()
        self.addCleanup(environment.stop)
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk를 시작할 수 없습니다: {exc}")
        self.addCleanup(self.root.destroy)
        self.settings = storage.load_settings()
        self.settings["therapists"][:] = ["홍길동", "김철수"]
        self.dialog = SettingsDialog(
            self.root, self.settings, on_change=lambda replacement=None: storage.save_settings(self.settings, replacement)
        )
        self.dialog.update()

    def test_list_selection_survives_selecting_text_in_entry(self):
        import tkinter as tk
        from tkinter import ttk

        editor = self.dialog.therapist_editor
        editor.refresh()
        editor.listbox.selection_set(1)
        editor._on_select()
        entry = next(w for w in editor.winfo_children()[1].winfo_children() if isinstance(w, ttk.Entry))
        entry.focus_force()
        entry.selection_range(0, tk.END)  # 이름을 고치려고 입력란 글자를 선택
        self.dialog.update()
        self.assertEqual(editor.selected_index(), 1)
        for listbox in (editor.listbox, self.dialog.diag_listbox, self.dialog.recent_region_listbox):
            self.assertEqual(int(listbox.cget("exportselection")), 0)

    def test_renaming_default_therapist_keeps_it_as_default(self):
        self.settings["default_therapist"] = self.settings["last_therapist"] = "홍길동"
        self.assertTrue(storage.save_settings(self.settings))
        editor = self.dialog.therapist_editor
        editor.refresh()
        editor.listbox.selection_set(0)
        editor.entry_var.set("홍길순")
        editor.rename()
        saved = storage.load_settings()
        self.assertEqual(saved["therapists"], ["홍길순", "김철수"])
        self.assertEqual(saved["default_therapist"], "홍길순")
        self.assertEqual(saved["last_therapist"], "홍길순")

    def test_deleting_default_therapist_clears_default(self):
        self.settings["default_therapist"] = "홍길동"
        self.assertTrue(storage.save_settings(self.settings))
        editor = self.dialog.therapist_editor
        editor.refresh()
        editor.listbox.selection_set(0)
        with patch("therapy_chart.settings_dialog.messagebox.askyesno", return_value=True):
            editor.delete()
        saved = storage.load_settings()
        self.assertEqual(saved["therapists"], ["김철수"])
        self.assertEqual(saved["default_therapist"], "")

    def test_diagnosis_stays_selected_after_favorite_and_update(self):
        dialog = self.dialog
        dialog.diag_listbox.selection_set(3)
        chosen = dict(dialog._selected_diag())
        dialog.diag_toggle_favorite()
        selected = dialog._selected_diag()
        self.assertEqual((selected["code"], selected["name"]), (chosen["code"], chosen["name"]))
        self.assertTrue(selected["favorite"])
        dialog.diag_code_var.set(chosen["code"])
        dialog.diag_name_var.set("바꾼 이름")
        dialog.diag_update()
        self.assertEqual(dialog._selected_diag()["name"], "바꾼 이름")

    def test_search_finds_code_typed_with_dot(self):
        self.dialog.diag_search_var.set("m75.1")
        self.assertEqual([d["code"] for d in self.dialog._diag_view], ["M751"])


if __name__ == "__main__":
    unittest.main()
