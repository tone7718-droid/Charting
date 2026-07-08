# -*- coding: utf-8 -*-
"""설정 다이얼로그.

치료사 / 치료 목적 / 시행 기법 / 진단명 / 시행 부위 / 데이터(백업·복원) 관리.
설정 dict를 직접 수정하며, 변경이 있을 때마다 on_change() 콜백을 호출한다
(메인 창이 저장과 화면 갱신을 담당).
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict

from . import constants as C
from .settings_tabs import TherapistTab, ListTab, DiagnosisTab, RegionTab, DataTab

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, settings: Dict, on_change: Callable[[], bool]):
        super().__init__(parent)
        self.parent = parent
        self.settings = settings
        self.on_change = on_change

        self.title("설정")
        self.geometry("600x600")
        self.minsize(500, 500)
        self.transient(parent)
        self.grab_set()

        try:
            self.iconbitmap(parent.iconbitmap())
        except tk.TclError:
            pass

        self._build_ui()
        self._center_window()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab_therapist = TherapistTab(notebook, self.settings, self.on_change)
        notebook.add(tab_therapist, text=" 👤 치료사 ")

        tab_purpose = ListTab(
            notebook, self.settings, self.on_change,
            setting_key="purposes", default_items=list(C.DEFAULT_PURPOSES), title="치료 목적 (기본 항목 외 자유롭게 추가/수정)"
        )
        notebook.add(tab_purpose, text=" 🎯 치료 목적 ")

        tab_tech = ListTab(
            notebook, self.settings, self.on_change,
            setting_key="techniques", default_items=list(C.DEFAULT_TECHNIQUES), title="시행 기법 (기본 항목 외 자유롭게 추가/수정)"
        )
        notebook.add(tab_tech, text=" 👐 시행 기법 ")

        tab_diag = DiagnosisTab(notebook, self.settings, self.on_change)
        notebook.add(tab_diag, text=" 🩺 진단명 ")

        tab_region = RegionTab(notebook, self.settings, self.on_change)
        notebook.add(tab_region, text=" 🦴 시행 부위 ")

        tab_data = DataTab(notebook, self.settings, self.on_change)
        notebook.add(tab_data, text=" 💾 데이터/기타 ")

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btn_frame, text="닫기", command=self.destroy).pack(side="right")

    def _center_window(self) -> None:
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()

        x = px + (pw // 2) - (w // 2)
        y = py + (ph // 2) - (h // 2)

        self.geometry(f"+{x}+{y}")
