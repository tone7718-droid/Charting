# -*- coding: utf-8 -*-
"""공통 위젯: 달력, 토글 버튼, 스크롤 프레임."""

from __future__ import annotations

import calendar
import datetime
import tkinter as tk
from tkinter import ttk
from typing import Callable, List

from . import theme as T

WEEKDAYS_KR = ["일", "월", "화", "수", "목", "금", "토"]

# 기존 모듈 import 호환성을 위해 유지
ACCENT = T.ACCENT
ACCENT_DARK = T.ACCENT_DARK
CHIP_OFF_BG = T.CHIP_OFF_BG
CHIP_OFF_FG = T.CHIP_OFF_FG


class CalendarWidget(ttk.Frame):
    """순수 tkinter 달력 위젯. 날짜 클릭 시 on_select(date)를 호출한다."""

    def __init__(self, master, on_select: Callable[[datetime.date], None],
                 font=T.SMALL_FONT):
        super().__init__(master, style="Card.TFrame")
        self.on_select = on_select
        self.font = font
        today = datetime.date.today()
        self.year = today.year
        self.month = today.month
        self.selected = today

        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x", pady=(0, 4))
        ttk.Button(header, text="◀", width=3, command=self.prev_month).pack(side="left")
        self.title_lbl = ttk.Label(header, font=(font[0], font[1], "bold"), anchor="center", style="Card.TLabel")
        self.title_lbl.pack(side="left", expand=True, fill="x")
        ttk.Button(header, text="▶", width=3, command=self.next_month).pack(side="right")

        self.grid_frame = tk.Frame(self, bg=T.CARD_BG)
        self.grid_frame.pack()
        self.draw()

    def prev_month(self) -> None:
        self.month -= 1
        if self.month == 0:
            self.month = 12
            self.year -= 1
        self.draw()

    def next_month(self) -> None:
        self.month += 1
        if self.month == 13:
            self.month = 1
            self.year += 1
        self.draw()

    def set_date(self, date: datetime.date) -> None:
        """프로그램에서 날짜를 지정한다 (예: 초기화 시 오늘로)."""
        self.selected = date
        self.year, self.month = date.year, date.month
        self.draw()

    def pick(self, day: int) -> None:
        self.selected = datetime.date(self.year, self.month, day)
        self.draw()
        self.on_select(self.selected)

    def draw(self) -> None:
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self.title_lbl.config(text=f"{self.year}년 {self.month}월")

        for col, name in enumerate(WEEKDAYS_KR):
            color = T.DANGER if col == 0 else (T.ACCENT if col == 6 else T.TEXT_MUTED)
            tk.Label(
                self.grid_frame, text=name, font=self.font, fg=color, width=2,
                bg=T.CARD_BG,
            ).grid(row=0, column=col, padx=2, pady=2)

        cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
        today = datetime.date.today()
        for row, week in enumerate(cal.monthdayscalendar(self.year, self.month), start=1):
            for col, day in enumerate(week):
                if day == 0:
                    tk.Label(self.grid_frame, text="", width=2, bg=T.CARD_BG).grid(row=row, column=col)
                    continue
                date = datetime.date(self.year, self.month, day)
                is_selected = date == self.selected
                bg = T.ACCENT if is_selected else (T.ACCENT_SOFT if date == today else T.SUBTLE_BG)
                fg = T.TEXT_LIGHT if is_selected else (
                    T.DANGER if col == 0 else (T.ACCENT if col == 6 else T.TEXT)
                )
                tk.Button(
                    self.grid_frame,
                    text=str(day),
                    width=2,
                    relief="flat",
                    borderwidth=0,
                    font=self.font,
                    bg=bg,
                    fg=fg,
                    activebackground=T.ACCENT,
                    activeforeground=T.TEXT_LIGHT,
                    cursor="hand2",
                    command=lambda d=day: self.pick(d),
                ).grid(row=row, column=col, padx=2, pady=2)


class ToggleChip(tk.Button):
    """다중 선택용 토글 버튼.

    선택 상태는 색상 + 체크 표시(✓) + 테두리로 구분한다.
    클릭 시 on_toggle(label, selected)를 호출한다.
    """

    def __init__(self, master, label: str, on_toggle: Callable[[str, bool], None],
                 font=T.BASE_FONT):
        self.label = label
        self._selected = False
        self._on_toggle = on_toggle
        super().__init__(
            master,
            text=label,
            font=font,
            relief="solid",
            borderwidth=1,
            bg=T.CHIP_OFF_BG,
            fg=T.CHIP_OFF_FG,
            activebackground=T.ACCENT_SOFT,
            activeforeground=T.CHIP_OFF_FG,
            highlightbackground=T.CHIP_BORDER,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._click,
        )

    @property
    def selected(self) -> bool:
        return self._selected

    def _click(self) -> None:
        self.set_selected(not self._selected)
        self._on_toggle(self.label, self._selected)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        if selected:
            self.config(
                text=f"✓ {self.label}", bg=T.ACCENT, fg=T.TEXT_LIGHT,
                activebackground=T.ACCENT_DARK, activeforeground=T.TEXT_LIGHT,
            )
        else:
            self.config(
                text=self.label, bg=T.CHIP_OFF_BG, fg=T.CHIP_OFF_FG,
                activebackground=T.ACCENT_SOFT, activeforeground=T.CHIP_OFF_FG,
            )


class ChipGroup(ttk.Frame):
    """토글 버튼 묶음. 클릭한 순서를 유지한 선택 목록을 제공한다."""

    def __init__(self, master, items: List[str], per_row: int = 3,
                 on_change: Callable[[], None] = lambda: None,
                 font=T.BASE_FONT):
        super().__init__(master, style="Card.TFrame")
        self.per_row = per_row
        self.on_change = on_change
        self.font = font
        self.selection_order: List[str] = []  # 클릭한 순서
        self.chips: List[ToggleChip] = []
        self.set_items(items)

    def set_items(self, items: List[str]) -> None:
        """항목 목록을 다시 그린다. 여전히 존재하는 선택은 유지한다."""
        for chip in self.chips:
            chip.destroy()
        self.chips = []
        self.selection_order = [s for s in self.selection_order if s in items]
        for i, label in enumerate(items):
            chip = ToggleChip(self, label, self._on_toggle, font=self.font)
            chip.grid(row=i // self.per_row, column=i % self.per_row,
                      sticky="w", padx=(0, 6), pady=3)
            if label in self.selection_order:
                chip.set_selected(True)
            self.chips.append(chip)

    def _on_toggle(self, label: str, selected: bool) -> None:
        if selected:
            if label not in self.selection_order:
                self.selection_order.append(label)
        else:
            self.selection_order = [s for s in self.selection_order if s != label]
        self.on_change()

    def get_selected(self) -> List[str]:
        """클릭한 순서대로 선택된 항목을 반환한다."""
        return list(self.selection_order)

    def clear_selection(self) -> None:
        self.selection_order = []
        for chip in self.chips:
            chip.set_selected(False)
        self.on_change()


class ScrollableFrame(ttk.Frame):
    """세로 스크롤이 가능한 컨테이너. .inner 프레임에 내용을 배치한다."""

    def __init__(self, master):
        super().__init__(master, style="App.TFrame")
        canvas = tk.Canvas(self, highlightthickness=0, bg=T.APP_BG)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.inner = ttk.Frame(canvas, padding=16, style="App.TFrame")
        inner_id = canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind(
            "<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(inner_id, width=e.width))

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        # 이 캔버스와 내부 위젯에만 휠 바인딩 (bind_all/unbind_all은
        # 앱 전역 바인딩을 건드리므로 위젯 스코프로 한정한다)
        def bind_wheel(widget):
            widget.bind("<MouseWheel>", on_mousewheel)
            for child in widget.winfo_children():
                bind_wheel(child)

        canvas.bind("<MouseWheel>", on_mousewheel)
        # 칩/버튼이 설정 변경으로 다시 생성될 때도 새 자식까지 휠 바인딩을 갱신한다.
        self.inner.bind("<Configure>", lambda _e: bind_wheel(self.inner), add="+")
        self.inner.bind("<Map>", lambda _e: bind_wheel(self.inner), add="+")
