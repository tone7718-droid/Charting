# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict

from .list_editor import ListEditor
BASE_FONT = ("맑은 고딕", 11)

class TherapistTab(ttk.Frame):
    def __init__(self, master, settings: Dict, apply_cb: Callable, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.settings = settings
        self.apply_cb = apply_cb

        self.pack(fill="both", expand=True, padx=12, pady=12)

        ttk.Label(self, text="치료사 목록 (등록/수정/삭제)", font=("맑은 고딕", 11, "bold")).pack(anchor="w")

        self.editor = ListEditor(
            self, self.settings["therapists"],
            self._on_list_change
        )
        self.editor.pack(fill="both", expand=True, pady=(6, 12))

        bottom_row = ttk.Frame(self)
        bottom_row.pack(fill="x")
        ttk.Label(bottom_row, text="기본 치료사:").pack(side="left")

        self.default_combo = ttk.Combobox(bottom_row, state="readonly", font=BASE_FONT)
        self.default_combo.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.default_combo.bind("<<ComboboxSelected>>", self._on_default_change)

        self._refresh_combo()

    def _on_list_change(self, new_list: list) -> None:
        self.settings["therapists"] = new_list
        # 기본 치료사가 목록에서 삭제된 경우
        if self.settings.get("default_therapist") not in new_list:
            self.settings["default_therapist"] = ""
        self._refresh_combo()
        self.apply_cb()

    def _refresh_combo(self) -> None:
        therapists = self.settings["therapists"]
        self.default_combo.configure(values=["(선택 안함)"] + therapists)
        default = self.settings.get("default_therapist")
        if default in therapists:
            self.default_combo.set(default)
        else:
            self.default_combo.set("(선택 안함)")

    def _on_default_change(self, _e=None) -> None:
        val = self.default_combo.get()
        self.settings["default_therapist"] = "" if val == "(선택 안함)" else val
        self.apply_cb()
