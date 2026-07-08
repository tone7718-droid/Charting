# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict

from .list_editor import ListEditor
from .. import constants as C

class ListTab(ttk.Frame):
    """치료 목적 / 시행 기법 탭 (간단한 목록 편집만 제공)"""
    def __init__(self, master, settings: Dict, apply_cb: Callable, setting_key: str, default_items: list, title: str, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.settings = settings
        self.apply_cb = apply_cb
        self.setting_key = setting_key

        self.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(self, text=title, font=("맑은 고딕", 11, "bold")).pack(anchor="w")

        editor = ListEditor(
            self, self.settings[setting_key],
            self._on_change,
            protected_items=default_items,
            height=12
        )
        editor.pack(fill="both", expand=True, pady=(6, 0))

    def _on_change(self, new_list: list) -> None:
        self.settings[self.setting_key] = new_list
        self.apply_cb()
