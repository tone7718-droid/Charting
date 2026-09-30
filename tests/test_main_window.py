# -*- coding: utf-8 -*-
"""기록 복사와 종료 시 저장 실패를 검증한다."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from therapy_chart.main_window import App
from tests.test_record import sample_record


class TestCopyAndClose(unittest.TestCase):
    def make_app(self):
        return SimpleNamespace(
            preview_mode="auto", settings={"auto_reset_after_copy": False},
            current_record=sample_record, _update_completion=Mock(), _mark_missing=Mock(),
            clipboard_clear=Mock(), clipboard_append=Mock(), update=Mock(),
            _remember_recents=Mock(return_value=True), show_status=Mock(), reset_inputs=Mock(),
        )

    def test_failed_clipboard_does_not_update_recent_list(self):
        app = self.make_app()
        app.clipboard_append.side_effect = RuntimeError("clipboard unavailable")
        App.copy_output(app)
        app._remember_recents.assert_not_called()

    def test_copy_retains_save_failure_warning_even_with_auto_reset(self):
        app = self.make_app()
        app.settings["auto_reset_after_copy"] = True
        app._remember_recents.return_value = False
        App.copy_output(app)
        app.clipboard_append.assert_called_once()
        app.reset_inputs.assert_called_once_with(confirm=False)
        self.assertIn("최근 목록은 저장하지 못했습니다", app.show_status.call_args.args[0])
        self.assertTrue(app.show_status.call_args.kwargs["sticky"])

    def test_close_can_be_cancelled_after_save_failure(self):
        app = SimpleNamespace(settings={}, state=Mock(return_value="zoomed"), therapist_var=Mock(), save_settings=Mock(return_value=False),
                              destroy=Mock(), show_status=Mock())
        with patch("therapy_chart.main_window.messagebox.askyesno", return_value=False):
            App.on_close(app)
        app.destroy.assert_not_called()

    def test_close_can_discard_unsaved_settings(self):
        app = SimpleNamespace(settings={}, state=Mock(return_value="zoomed"), therapist_var=Mock(), save_settings=Mock(return_value=False),
                              destroy=Mock(), show_status=Mock())
        with patch("therapy_chart.main_window.messagebox.askyesno", return_value=True):
            App.on_close(app)
        app.destroy.assert_called_once()


class TestGeometry(unittest.TestCase):
    def test_oversized_offscreen_and_tiny_geometry_stay_inside_screen(self):
        import re

        for screen in ((1920, 1080), (1280, 720), (800, 600)):
            for geometry in ("3000x2000+4000+2000", "1280x800-1400-900", "10x10+1200+700"):
                with self.subTest(screen=screen, geometry=geometry):
                    result = App._clamp_geometry(geometry, *screen)
                    width, height, x, y = map(int, re.fullmatch(r"(\d+)x(\d+)\+(\d+)\+(\d+)", result).groups())
                    self.assertLessEqual(x + width, screen[0])
                    self.assertLessEqual(y + height, screen[1] - 40)

    def test_invalid_geometry_is_ignored(self):
        self.assertIsNone(App._clamp_geometry("invalid", 1920, 1080))


if __name__ == "__main__":
    unittest.main()
