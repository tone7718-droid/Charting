# -*- coding: utf-8 -*-
"""메인 화면 오른쪽 미리보기 패널."""

import tkinter as tk
from tkinter import ttk

from ..widgets import ACCENT

BASE_FONT = ("맑은 고딕", 11)
BOLD_FONT = ("맑은 고딕", 11, "bold")
TITLE_FONT = ("맑은 고딕", 12, "bold")
PREVIEW_FONT = ("맑은 고딕", 13)


class PreviewPanel(ttk.Frame):
    """진료 기록 미리보기, 상태 메시지, 주요 액션 버튼을 묶은 패널.

    버튼 command는 App 인스턴스에서 전달받는다. 생성된 핵심 위젯은
    기존 App 로직과 호환되도록 app 속성에도 연결한다.
    """

    def __init__(self, master, app):
        super().__init__(master, padding=12)
        self.app = app
        self._build()

    def _build(self) -> None:
        head_row = ttk.Frame(self)
        head_row.pack(fill="x")
        ttk.Label(head_row, text="진료 기록 미리보기", font=TITLE_FONT, foreground=ACCENT).pack(side="left")

        self.edit_btn = ttk.Button(head_row, text="✏ 직접 수정", command=self.app.toggle_edit_mode)
        self.edit_btn.pack(side="right")
        self.regen_btn = ttk.Button(head_row, text="🔄 자동 생성 내용으로 갱신", command=self.app.regenerate_preview)

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

        ttk.Button(bottom, text="초기화 (Ctrl+R)", command=self.app.reset_inputs).pack(side="left")
        ttk.Button(bottom, text="⚙ 설정", command=self.app.open_settings).pack(side="left", padx=(6, 0))
        tk.Button(
            bottom, text="📋 전체 복사 (Ctrl+Shift+C)", font=("맑은 고딕", 13, "bold"),
            bg=ACCENT, fg="white", activebackground="#1d4fc4", activeforeground="white",
            relief="flat", padx=20, pady=8, cursor="hand2", command=self.app.copy_output,
        ).pack(side="right")

        # 기존 App 메서드가 참조하는 이름을 유지한다.
        self.app.edit_btn = self.edit_btn
        self.app.regen_btn = self.regen_btn
        self.app.status_lbl = self.status_lbl
        self.app.output = self.output
