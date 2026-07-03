# -*- coding: utf-8 -*-
"""공통 위젯: 달력, 토글 버튼, 스크롤 프레임."""

from __future__ import annotations

import calendar
import datetime
import tkinter as tk
from tkinter import ttk
from typing import Callable, List

WEEKDAYS_KR = ["일", "월", "화", "수", "목", "금", "토"]

ACCENT = "#2f6fed"          # 주 강조색
ACCENT_DARK = "#1d4fc4"
CHIP_OFF_BG = "#f7f7f7"
CHIP_OFF_FG = "#333333"


class CalendarWidget(ttk.Frame):
    """순수 tkinter 달력 위젯. 날짜 클릭 시 on_select(date)를 호출한다."""

    def __init__(self, master, on_select: Callable[[datetime.date], None],
                 font=("맑은 고딕", 10)):
        super().__init__(master)
        self.on_select = on_select
        self.font = font
        today = datetime.date.today()
        self.year = today.year
        self.month = today.month
        self.selected = today

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 2))
        ttk.Button(header, text="◀", width=3, command=self.prev_month).pack(side="left")
        self.title_lbl = ttk.Label(header, font=(font[0], font[1], "bold"), anchor="center")
        self.title_lbl.pack(side="left", expand=True, fill="x")
        ttk.Button(header, text="▶", width=3, command=self.next_month).pack(side="right")

        self.grid_frame = ttk.Frame(self)
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
            color = "#d9534f" if col == 0 else ("#428bca" if col == 6 else "#333333")
            tk.Label(self.grid_frame, text=name, font=self.font, fg=color, width=2).grid(
                row=0, column=col, padx=1, pady=1
            )

        cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
        today = datetime.date.today()
        for row, week in enumerate(cal.monthdayscalendar(self.year, self.month), start=1):
            for col, day in enumerate(week):
                if day == 0:
                    tk.Label(self.grid_frame, text="", width=2).grid(row=row, column=col)
                    continue
                date = datetime.date(self.year, self.month, day)
                is_selected = date == self.selected
                bg = ACCENT if is_selected else ("#e8f0fe" if date == today else "#f0f0f0")
                fg = "white" if is_selected else (
                    "#d9534f" if col == 0 else ("#428bca" if col == 6 else "black")
                )
                tk.Button(
                    self.grid_frame,
                    text=str(day),
                    width=2,
                    relief="flat",
                    font=self.font,
                    bg=bg,
                    fg=fg,
                    activebackground=ACCENT,
                    activeforeground="white",
                    command=lambda d=day: self.pick(d),
                ).grid(row=row, column=col, padx=1, pady=1)


class ToggleChip(tk.Button):
    """다중 선택용 토글 버튼.

    선택 상태는 색상 + 체크 표시(✓) + 테두리로 구분한다.
    클릭 시 on_toggle(label, selected)를 호출한다.
    """

    def __init__(self, master, label: str, on_toggle: Callable[[str, bool], None],
                 font=("맑은 고딕", 11)):
        self.label = label
        self._selected = False
        self._on_toggle = on_toggle
        super().__init__(
            master,
            text=label,
            font=font,
            relief="solid",
            borderwidth=1,
            bg=CHIP_OFF_BG,
            fg=CHIP_OFF_FG,
            activebackground="#e8f0fe",
            activeforeground=CHIP_OFF_FG,
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
            self.config(text=f"✓ {self.label}", bg=ACCENT, fg="white",
                        activebackground=ACCENT_DARK, activeforeground="white")
        else:
            self.config(text=self.label, bg=CHIP_OFF_BG, fg=CHIP_OFF_FG,
                        activebackground="#e8f0fe", activeforeground=CHIP_OFF_FG)


class ChipGroup(ttk.Frame):
    """토글 버튼 묶음. 클릭한 순서를 유지한 선택 목록을 제공한다."""

    def __init__(self, master, items: List[str], per_row: int = 3,
                 on_change: Callable[[], None] = lambda: None,
                 font=("맑은 고딕", 11)):
        super().__init__(master)
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
        super().__init__(master)
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.inner = ttk.Frame(canvas, padding=12)
        inner_id = canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind(
            "<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(inner_id, width=e.width))

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # 마우스가 이 영역 위에 있을 때만 휠 스크롤 동작
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
