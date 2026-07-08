# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict

from .list_editor import ListEditor

class RegionTab(ttk.Frame):
    def __init__(self, master, settings: Dict, apply_cb: Callable, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.settings = settings
        self.apply_cb = apply_cb

        self.pack(fill="both", expand=True, padx=12, pady=12)

        ttk.Label(self, text="시행 부위 즐겨찾기", font=("맑은 고딕", 11, "bold")).pack(anchor="w")
        editor = ListEditor(
            self, self.settings["region_favorites"],
            self._on_fav_change, height=6
        )
        editor.pack(fill="both", expand=True, pady=(6, 12))

        ttk.Button(self, text="최근 사용 목록 비우기", command=self._clear_recent).pack(anchor="e")

    def _on_fav_change(self, new_list: list) -> None:
        self.settings["region_favorites"] = new_list
        self.apply_cb()

    def _clear_recent(self) -> None:
        if not self.settings["recent_regions"]:
            return
        if messagebox.askyesno("확인", "시행 부위 최근 사용 목록을 모두 지우시겠습니까?", parent=self):
            self.settings["recent_regions"] = []
            self.apply_cb()
            messagebox.showinfo("완료", "지워졌습니다.", parent=self)
