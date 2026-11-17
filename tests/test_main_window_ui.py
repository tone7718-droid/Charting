# -*- coding: utf-8 -*-
"""실제 메인 창을 생성해 화면 구성과 입력 연결을 검증한다."""

import os
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from therapy_chart import constants as C
from therapy_chart.main_window import App


class AppTestCase(unittest.TestCase):
    """임시 데이터 폴더에서 실제 메인 창을 만들어 주는 공통 준비."""

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
        if self.app is not None:
            self.app.destroy()
        self.first_run.stop()
        self.environment.stop()
        self.tmp.cleanup()


class TestMainWindowBuild(AppTestCase):
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

    def test_preview_does_not_force_its_own_size(self):
        # 글상자가 기본 80×24글자를 요구하면 왼쪽 입력 영역이 좁아져 달력이 잘린다.
        self.assertEqual(int(self.app.output.cget("width")), 1)
        self.assertEqual(int(self.app.output.cget("height")), 1)

    def test_record_values_are_cleaned_for_one_line_output(self):
        self.app.diag_name_var.set("요추\n염좌 ")
        self.app.count_var.set("007")
        text = self.app.output.get("1.0", "end")
        self.assertIn("진단명 : 요추 염좌\n", text)
        self.assertIn("7회차", text)
        self.assertNotIn("007", text)


class TestMainWindowBehavior(AppTestCase):
    """날짜·검색·직접 수정 등 입력 보조 동작."""

    def test_untouched_date_follows_today_when_day_changes(self):
        import datetime

        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        # 어제 프로그램을 켜고 날짜를 건드리지 않은 상태를 만든다.
        self.app.date_selected = yesterday
        self.app._today_seen = yesterday
        self.assertTrue(self.app._sync_today())
        self.assertEqual(self.app.date_selected, today)
        self.assertEqual(self.app.calendar.selected, today)
        self.assertIn(f"{today.year}년 {today.month:02d}월 {today.day:02d}일", self.app.output.get("1.0", "end"))
        self.assertFalse(self.app._sync_today())  # 같은 날에는 다시 바꾸지 않는다

    def test_date_picked_by_user_is_kept_when_day_changes(self):
        import datetime

        today = datetime.date.today()
        picked = today - datetime.timedelta(days=3)
        self.app.calendar.set_date(picked)
        self.app.on_date_selected(picked)
        self.app._today_seen = today - datetime.timedelta(days=1)
        self.assertFalse(self.app._sync_today())
        self.assertEqual(self.app.date_selected, picked)

    def test_date_hint_and_today_button(self):
        import datetime

        today = datetime.date.today()
        self.assertEqual(self.app.date_hint_lbl.cget("text"), "")
        self.app.on_date_selected(today - datetime.timedelta(days=2))
        self.assertIn("2일 전", self.app.date_hint_lbl.cget("text"))
        self.app.on_date_selected(today + datetime.timedelta(days=1))
        self.assertIn("미래", self.app.date_hint_lbl.cget("text"))
        self.app.select_today()
        self.assertEqual(self.app.date_selected, today)
        self.assertEqual(self.app.calendar.selected, today)
        self.assertEqual(self.app.date_hint_lbl.cget("text"), "")
        self.assertTrue(self.app._date_follows_today)

    def test_reset_returns_date_to_today_and_clears_recent_selection(self):
        import datetime

        self.app.settings["recent_diagnoses"] = [{"code": "M545", "name": "요통"}]
        self.app.refresh_from_settings()
        self.app.recent_diag_combo.current(0)
        self.app.on_date_selected(datetime.date.today() - datetime.timedelta(days=5))
        self.app.reset_inputs(confirm=False)
        self.assertEqual(self.app.recent_diag_combo.get(), "")
        self.assertEqual(self.app.date_selected, datetime.date.today())
        self.assertEqual(self.app.date_hint_lbl.cget("text"), "")
        self.assertTrue(self.app._date_follows_today)

    def test_search_matches_dotted_code_and_enter_picks_first(self):
        self.app.diag_search_var.set("m54.5")
        self.assertEqual([d["code"] for d in self.app._diag_view], ["M545"])
        self.app._pick_first_diag()
        self.assertEqual(self.app.diag_code_var.get(), "M545")
        self.assertEqual(self.app.diag_name_var.get(), "요통")

    def test_enter_in_empty_search_does_not_pick_anything(self):
        self.app._pick_first_diag()
        self.assertEqual(self.app.diag_code_var.get(), "")

    def test_code_fills_name_only_when_name_is_empty_and_code_is_unique(self):
        self.app.diag_code_var.set("m54.5")
        self.app._autofill_diag_name()
        self.assertEqual(self.app.diag_name_var.get(), "요통")

        self.app.diag_name_var.set("직접 적은 진단명")
        self.app.diag_code_var.set("M751")
        self.app._autofill_diag_name()
        self.assertEqual(self.app.diag_name_var.get(), "직접 적은 진단명")

        self.app.settings["diagnoses"].append({"code": "M751", "name": "다른 이름", "favorite": False})
        self.app.diag_name_var.set("")
        self.app._autofill_diag_name()
        self.assertEqual(self.app.diag_name_var.get(), "")  # 같은 코드가 둘이면 고르지 않는다

    def test_autofilled_name_is_cleared_when_code_changes(self):
        self.app.diag_code_var.set("M545")
        self.app._autofill_diag_name()
        self.assertEqual(self.app.diag_name_var.get(), "요통")
        self.app.diag_code_var.set("M751")  # 코드를 고치는 순간 예전 진단명이 남으면 안 된다
        self.assertEqual(self.app.diag_name_var.get(), "")
        self.assertNotIn("요통", self.app.output.get("1.0", "end"))
        self.app._autofill_diag_name()
        self.assertEqual(self.app.diag_name_var.get(), "회전근개증후군")

    def test_name_typed_or_picked_by_user_survives_code_change(self):
        self.app.diag_code_var.set("M545")
        self.app._autofill_diag_name()
        self.app.diag_name_var.set("요통(만성)")  # 자동 입력 후 직접 고친 진단명
        self.app.diag_code_var.set("M5450")
        self.assertEqual(self.app.diag_name_var.get(), "요통(만성)")

        self.app.diag_search_var.set("M751")
        self.app._pick_first_diag()  # 목록에서 고른 진단명
        self.app.diag_search_var.set("")
        self.app.diag_code_var.set("M7510")
        self.assertEqual(self.app.diag_name_var.get(), "회전근개증후군")

    def test_reset_keeps_current_therapist(self):
        self.app.settings["therapists"][:] = ["홍길동", "김철수"]
        self.app.settings["default_therapist"] = ""
        self.app.refresh_from_settings()
        self.app.therapist_var.set("김철수")
        self.app.reset_inputs(confirm=False)
        self.assertEqual(self.app.therapist_var.get(), "김철수")
        self.app.settings["default_therapist"] = "홍길동"  # 기본 치료사가 있어도 지금 작업자를 유지한다
        self.app.reset_inputs(confirm=False)
        self.assertEqual(self.app.therapist_var.get(), "김철수")
        self.app.therapist_var.set("")
        self.app.reset_inputs(confirm=False)
        self.assertEqual(self.app.therapist_var.get(), "홍길동")

    def test_clear_status_cancels_pending_clear(self):
        import time

        self.app.show_status("짧은 안내", "black")
        self.app.clear_status()
        self.assertIsNone(self.app._status_after)
        self.app.show_status("고정 경고", "red", sticky=True)
        deadline = time.time() + 3.0
        while time.time() < deadline:
            self.app.update()
            time.sleep(0.05)
        self.assertEqual(self.app.status_lbl.cget("text"), "고정 경고")

    def test_small_wheel_steps_still_scroll(self):
        self.app.deiconify()
        self.app.geometry("1200x500+0+0")
        self.app.update()
        left = self.app.nametowidget(self.app.main_paned.panes()[0])
        canvas = next(w for w in left.winfo_children() if isinstance(w, tk.Canvas))
        canvas.yview_moveto(0)
        self.app.update()
        top = canvas.yview()[0]
        canvas.event_generate("<MouseWheel>", delta=-30)  # 터치패드처럼 작은 값
        self.app.update()
        self.assertGreater(canvas.yview()[0], top)
        self.app.withdraw()

    def test_diagnosis_list_scrolls_itself_and_keeps_selection(self):
        self.app.update_idletasks()
        self.assertEqual(self.app.diag_list.bind("<MouseWheel>"), "")
        self.assertEqual(int(self.app.diag_list.cget("exportselection")), 0)
        self.assertNotEqual(self.app.therapist_combo.bind("<MouseWheel>"), "")  # 휠로 값이 바뀌지 않게 유지

    def test_edit_mode_enables_undo_and_remembers_starting_text(self):
        self.app.diag_name_var.set("요통")
        self.app.toggle_edit_mode()
        self.assertTrue(self.app.output.cget("undo"))
        self.assertIn("요통", self.app._edit_base_text)
        self.app.toggle_edit_mode()  # 편집 종료
        self.assertFalse(self.app.output.cget("undo"))
        self.assertEqual(self.app.preview_mode, "manual")
        self.app.toggle_edit_mode()  # 다시 편집해도 처음 기준을 유지한다
        self.assertIn("요통", self.app._edit_base_text)
        with patch("therapy_chart.main_window.messagebox.askyesno", return_value=True):
            self.app.regenerate_preview()
        self.assertIsNone(self.app._edit_base_text)

    def test_shortcut_is_ignored_while_another_window_has_focus(self):
        from unittest.mock import Mock

        other = tk.Toplevel(self.app)
        entry = tk.Entry(other)
        action = Mock()
        with patch.object(self.app, "focus_get", return_value=entry):
            self.app._run_shortcut(action)
        action.assert_not_called()
        with patch.object(self.app, "focus_get", return_value=self.app.diag_list):
            self.app._run_shortcut(action)
        action.assert_called_once()

    def test_closing_cancels_scheduled_callbacks(self):
        pending = list(self.app._pending_after.values())
        self.assertTrue(pending)
        scheduled = self.app.tk.call("after", "info")
        self.assertTrue(all(after_id in scheduled for after_id in pending))
        self.app.show_status("잠깐 보이는 안내", "black")
        pending.append(self.app._status_after)
        # 닫힌 창의 예약 작업이 남아 있으면 다른 창의 update() 때 오류로 실행된다.
        with patch.object(self.app, "after_cancel", wraps=self.app.after_cancel) as cancel:
            self.app.destroy()
        self.assertEqual(sorted(call.args[0] for call in cancel.call_args_list), sorted(pending))
        self.app = None


if __name__ == "__main__":
    unittest.main()
