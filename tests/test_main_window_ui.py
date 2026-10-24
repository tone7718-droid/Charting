# -*- coding: utf-8 -*-
"""실제 메인 창을 생성해 화면 구성과 입력 연결을 검증한다."""

import os
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from therapy_chart import constants as C
from therapy_chart.main_window import App


class TestMainWindowBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"APPDATA": self.tmp.name})
        self.environment.start()
        # 첫 실행 등록 창이 테스트 중 뜨지 않도록 막는다.
        self.first_run = patch.object(App, "first_run_check")
        self.first_run.start()
        try:
            self.app = App()
        except tk.TclError as exc:
            self.first_run.stop()
            self.environment.stop()
            self.tmp.cleanup()
            self.skipTest(f"Tk를 시작할 수 없습니다: {exc}")
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()
        self.first_run.stop()
        self.environment.stop()
        self.tmp.cleanup()

    def test_input_widgets_are_created(self):
        for name in (
            "recent_diag_combo", "diag_search_var", "diag_list", "purpose_chips", "therapist_combo",
            "calendar", "region_combo", "region_fav_btn", "minutes_lbl", "tech_chips",
            "improvement_chips", "preview_panel", "output", "banner",
        ):
            with self.subTest(name=name):
                self.assertTrue(hasattr(self.app, name))

    def test_required_field_titles_are_registered(self):
        expected = {
            C.LABEL_DIAGNOSIS, C.LABEL_PURPOSE, C.LABEL_THERAPIST, C.LABEL_DATE,
            C.LABEL_COUNT, C.LABEL_REGION, C.LABEL_TECHNIQUE,
        }
        self.assertEqual(set(self.app._field_titles), expected)
        for label, widget in self.app._field_titles.items():
            with self.subTest(label=label):
                self.assertTrue(getattr(widget, "_normal_text", ""))

    def test_diagnosis_search_is_traced_once(self):
        self.assertEqual(len(self.app.diag_search_var.trace_info()), 1)

    def test_banner_is_shown_above_inputs_only_without_therapists(self):
        self.app.settings["therapists"] = []
        self.app.refresh_from_settings()
        slaves = self.app.pack_slaves()
        self.assertIn(self.app.banner, slaves)
        self.assertLess(slaves.index(self.app.banner), slaves.index(self.app.main_paned))

        self.app.settings["therapists"] = ["홍길동"]
        self.app.refresh_from_settings()
        self.assertNotIn(self.app.banner, self.app.pack_slaves())

    def test_input_changes_reach_preview(self):
        self.app.diag_name_var.set("요추 염좌")
        self.app.count_var.set("3")
        text = self.app.output.get("1.0", "end")
        self.assertIn("요추 염좌", text)
        self.assertIn("3회차", text)


if __name__ == "__main__":
    unittest.main()
