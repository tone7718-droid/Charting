# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List, Optional

BASE_FONT = ("맑은 고딕", 11)

class ListEditor(ttk.Frame):
    """문자열 목록 편집 공통 위젯 (추가/수정/삭제).

    protected_items에 포함된 항목을 삭제할 때는 확인 창을 표시한다.
    """

    def __init__(self, master, items: List[str], on_change: Callable[[List[str]], None],
                 protected_items: Optional[List[str]] = None, height: int = 8):
        super().__init__(master)
        self.items = items
        self.on_change = on_change
        self.protected = set(protected_items or [])

        list_row = ttk.Frame(self)
        list_row.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_row, height=height, font=BASE_FONT, activestyle="none")
        sb = ttk.Scrollbar(list_row, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        entry_row = ttk.Frame(self)
        entry_row.pack(fill="x", pady=(6, 0))
        self.entry_var = tk.StringVar()
        entry = ttk.Entry(entry_row, textvariable=self.entry_var, font=BASE_FONT)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_row = ttk.Frame(self)
        btn_row.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_row, text="추가", command=self._add).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(btn_row, text="수정", command=self._update).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_row, text="삭제", command=self._delete).pack(side="left", expand=True, fill="x", padx=(2, 0))

        self.listbox.bind("<Double-1>", lambda e: self._update())
        entry.bind("<Return>", lambda e: self._add())

        self._refresh()

    def _refresh(self) -> None:
        self.listbox.delete(0, "end")
        for item in self.items:
            self.listbox.insert("end", item)

    def _on_select(self, _e=None) -> None:
        sel = self.listbox.curselection()
        if sel:
            self.entry_var.set(self.items[sel[0]])

    def _add(self) -> None:
        val = self.entry_var.get().strip()
        if val and val not in self.items:
            self.items.append(val)
            self._refresh()
            self.entry_var.set("")
            self.on_change(self.items)

    def _update(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        val = self.entry_var.get().strip()
        if val and val != self.items[idx]:
            if val in self.items:
                messagebox.showwarning("중복", "이미 존재하는 항목입니다.", parent=self)
                return
            self.items[idx] = val
            self._refresh()
            self.listbox.selection_set(idx)
            self.on_change(self.items)

    def _delete(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        val = self.items[idx]
        if val in self.protected:
            if not messagebox.askyesno(
                "삭제 확인",
                f"기본 항목 '{val}'을(를) 삭제하시겠습니까?\n(설정을 초기화하면 다시 생성됩니다)",
                parent=self
            ):
                return
        del self.items[idx]
        self._refresh()
        self.entry_var.set("")
        self.on_change(self.items)
