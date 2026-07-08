# -*- coding: utf-8 -*-
"""우측 미리보기 패널 컴포넌트."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, List

from .. import constants as C
from .. import record as R
from ..widgets import ACCENT
from ..app_state import AppState

TITLE_FONT = ("맑은 고딕", 12, "bold")
PREVIEW_FONT = ("맑은 고딕", 13)
BOLD_FONT = ("맑은 고딕", 11, "bold")

class PreviewPanel(ttk.Frame):
    def __init__(self, parent, state: AppState, status_callback: Callable[[str, str, bool], None], reset_callback: Callable, copy_callback: Callable, settings_callback: Callable, **kwargs):
        super().__init__(parent, **kwargs)
        self.state = state
        self.show_status = status_callback
        self.reset_callback = reset_callback
        self.copy_callback = copy_callback
        self.settings_callback = settings_callback

        self.preview_mode = "auto"
        self._left_changed_in_edit = False

        self._build_ui()

    def _build_ui(self):
        self.configure(padding=12)

        head_row = ttk.Frame(self)
        head_row.pack(fill="x")
        ttk.Label(head_row, text="진료 기록 미리보기", font=TITLE_FONT, foreground=ACCENT).pack(side="left")

        self.edit_btn = ttk.Button(head_row, text="✏ 직접 수정", command=self.toggle_edit_mode)
        self.edit_btn.pack(side="right")

        self.regen_btn = ttk.Button(head_row, text="🔄 자동 생성 내용으로 갱신", command=self.regenerate_preview)

        # 창이 낮아도 버튼/상태 표시가 잘리지 않도록 아래쪽부터 먼저 배치
        bottom = ttk.Frame(self)
        bottom.pack(side="bottom", fill="x", pady=(6, 0))

        self.status_lbl = ttk.Label(self, text="", font=BOLD_FONT)
        self.status_lbl.pack(side="bottom", fill="x")

        self.output = tk.Text(
            self, font=PREVIEW_FONT, wrap="word", relief="solid",
            borderwidth=1, padx=14, pady=14, spacing3=10,
        )
        self.output.pack(fill="both", expand=True, pady=(8, 6))
        self.output.configure(state="disabled")

        ttk.Button(bottom, text="초기화 (Ctrl+R)", command=self.reset_callback).pack(side="left")
        ttk.Button(bottom, text="⚙ 설정", command=self.settings_callback).pack(side="left", padx=(6, 0))

        tk.Button(
            bottom, text="📋 전체 복사 (Ctrl+Shift+C)", font=("맑은 고딕", 13, "bold"),
            bg=ACCENT, fg="white", activebackground="#1d4fc4", activeforeground="white",
            relief="flat", padx=20, pady=8, cursor="hand2", command=self.copy_callback,
        ).pack(side="right")

    def update_preview(self, record: R.TherapyRecord) -> None:
        """AppState 변경 시 호출되어 미리보기를 갱신합니다."""
        if self.preview_mode != "auto":
            if not self._left_changed_in_edit:
                self._left_changed_in_edit = True
                self.show_status(
                    "왼쪽 항목이 변경되었습니다. [자동 생성 내용으로 갱신]을 누르면 반영됩니다.",
                    "#856404", True
                )
            return

        text = record.build_text()
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def toggle_edit_mode(self) -> None:
        if self.preview_mode == "auto" or self.preview_mode == "manual":
            self.preview_mode = "editing"
            self._left_changed_in_edit = False
            self.output.configure(state="normal")
            self.output.focus_set()
            self.edit_btn.config(text="✔ 편집 종료")
            self.regen_btn.pack(side="right", padx=(0, 6))
            self.show_status("직접 수정 중입니다. 편집이 끝나면 [편집 종료]를 누르세요.", "#856404", True)
        else:
            self.preview_mode = "manual"
            self.output.configure(state="disabled")
            self.edit_btn.config(text="✏ 직접 수정")
            self.show_status("직접 수정한 내용이 유지됩니다. (자동 갱신 일시 중지)", "#856404", True)

    def regenerate_preview(self) -> None:
        if self.preview_mode != "auto":
            current = self.output.get("1.0", "end-1c")
            if current != self.state.current_record().build_text() and not messagebox.askyesno(
                "갱신 확인", "직접 수정한 내용이 사라지고 왼쪽 입력값으로 다시 생성됩니다.\n계속할까요?"
            ):
                return

        self.preview_mode = "auto"
        self.edit_btn.config(text="✏ 직접 수정")
        self.regen_btn.pack_forget()
        self.output.configure(state="disabled")
        self.show_status("", "", False)  # clear status
        self.update_preview(self.state.current_record())

    def get_current_text(self) -> str:
        return self.output.get("1.0", "end-1c")

    def reset_mode(self) -> None:
        self.preview_mode = "auto"
        self.edit_btn.config(text="✏ 직접 수정")
        self.regen_btn.pack_forget()
        self.output.configure(state="disabled")
