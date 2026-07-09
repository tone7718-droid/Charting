# -*- coding: utf-8 -*-
"""공통 위젯 동작 테스트."""

import tkinter as tk
import unittest

from therapy_chart.widgets import ScrollableFrame


class TestScrollableFrame(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk를 시작할 수 없습니다: {exc}")
        self.root.withdraw()

    def tearDown(self):
        if hasattr(self, "root"):
            self.root.destroy()

    def test_new_children_get_mousewheel_binding_after_layout_change(self):
        frame = ScrollableFrame(self.root)
        frame.pack(fill="both", expand=True)
        self.root.update_idletasks()

        button = tk.Button(frame.inner, text="새 칩")
        button.pack()
        self.root.update_idletasks()

        self.assertTrue(button.bind("<MouseWheel>"))


if __name__ == "__main__":
    unittest.main()
