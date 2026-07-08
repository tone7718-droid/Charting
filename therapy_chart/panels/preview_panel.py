# -*- coding: utf-8 -*-
"""메인 화면 오른쪽 미리보기 패널."""

import tkinter as tk
from tkinter import ttk

from .. import theme as T


class PreviewPanel(ttk.Frame):
    """진료 기록 미리보기, 상태 메시지, 주요 액션 버튼을 묶은 패널.

    버튼 command는 App 인스턴스에서 전달받는다. 생성된 핵심 위젯은
    기존 App 로직과 호환되도록 app 속성에도 연결한다.
    """

    def __init__(self, master, app):
        super().__init__(master, padding=16, style="App.TFrame")
        self.app = app
        self._build()

    def _build(self) -> None:
        # 상단 헤더 카드 -------------------------------------------------
        header = tk.Frame(self, bg=T.CARD_BG, highlightbackground=T.BORDER, highlightthickness=1)
        header.pack(fill="x", pady=(0, 10))
        header.grid_columnconfigure(0, weight=1)

        title_block = tk.Frame(header, bg=T.CARD_BG)
        title_block.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 10))
        tk.Label(
            title_block,
            text="진료 기록 미리보기",
            font=T.TITLE_FONT,
            bg=T.CARD_BG,
            fg=T.TEXT,
        ).pack(anchor="w")
        tk.Label(
            title_block,
            text="복사 전 필수 항목과 범위 오류를 확인합니다.",
            font=T.SMALL_FONT,
            bg=T.CARD_BG,
            fg=T.TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        self.completion_lbl = tk.Label(
            header,
            text="필수 항목 확인 중",
            font=T.SMALL_BOLD_FONT,
            bg=T.WARNING_SOFT,
            fg=T.WARNING,
            padx=10,
            pady=5,
        )
        self.completion_lbl.grid(row=0, column=1, sticky="ne", padx=14, pady=14)

        edit_row = tk.Frame(header, bg=T.CARD_BG)
        edit_row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))
        self.regen_btn = ttk.Button(edit_row, text="🔄 자동 생성으로 갱신", command=self.app.regenerate_preview)
        self.edit_btn = ttk.Button(edit_row, text="✏ 직접 수정", command=self.app.toggle_edit_mode)
        self.edit_btn.pack(side="right")

        # 미리보기 카드 --------------------------------------------------
        preview_card = tk.Frame(self, bg=T.CARD_BG, highlightbackground=T.BORDER, highlightthickness=1)
        preview_card.pack(fill="both", expand=True)

        self.output = tk.Text(
            preview_card,
            font=T.PREVIEW_FONT,
            wrap="word",
            relief="flat",
            borderwidth=0,
            padx=18,
            pady=18,
            spacing3=10,
            bg=T.PREVIEW_BG,
            fg=T.TEXT,
            insertbackground=T.TEXT,
            selectbackground=T.ACCENT_SOFT,
            selectforeground=T.TEXT,
        )
        self.output.pack(fill="both", expand=True, padx=12, pady=12)
        self.output.configure(state="disabled")

        # 하단 상태/버튼 -------------------------------------------------
        bottom = ttk.Frame(self, style="App.TFrame")
        bottom.pack(fill="x", pady=(10, 0))

        left_buttons = ttk.Frame(bottom, style="App.TFrame")
        left_buttons.pack(side="left")
        ttk.Button(left_buttons, text="초기화", command=self.app.reset_inputs).pack(side="left")
        ttk.Button(left_buttons, text="⚙ 설정", command=self.app.open_settings).pack(side="left", padx=(6, 0))

        self.copy_btn = tk.Button(
            bottom,
            text="📋 전체 복사",
            font=T.PRIMARY_BUTTON_FONT,
            bg=T.ACCENT,
            fg=T.TEXT_LIGHT,
            activebackground=T.ACCENT_DARK,
            activeforeground=T.TEXT_LIGHT,
            relief="flat",
            padx=24,
            pady=10,
            cursor="hand2",
            command=self.app.copy_output,
        )
        self.copy_btn.pack(side="right")

        self.status_lbl = ttk.Label(self, text="", style="Status.TLabel")
        self.status_lbl.pack(fill="x", pady=(8, 0))

        # 기존 App 메서드가 참조하는 이름을 유지한다.
        self.app.edit_btn = self.edit_btn
        self.app.regen_btn = self.regen_btn
        self.app.status_lbl = self.status_lbl
        self.app.output = self.output
        self.app.preview_panel = self

    def set_completion(self, completed: int, total: int, missing=None, invalid=None) -> None:
        """필수 항목 완료 상태를 상단 배지로 표시한다."""
        missing = missing or []
        invalid = invalid or []
        if invalid:
            self.completion_lbl.config(
                text="⚠ 범위 오류 확인",
                bg=T.DANGER_SOFT,
                fg=T.DANGER,
            )
        elif missing:
            self.completion_lbl.config(
                text=f"필수 항목 {completed}/{total} 완료",
                bg=T.WARNING_SOFT,
                fg=T.WARNING,
            )
        else:
            self.completion_lbl.config(
                text="✅ 복사 가능",
                bg=T.SUCCESS_SOFT,
                fg=T.SUCCESS,
            )
