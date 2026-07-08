# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, List
import traceback

from .. import storage

BASE_FONT = ("맑은 고딕", 11)

class DiagnosisTab(ttk.Frame):
    def __init__(self, master, settings: Dict, apply_cb: Callable, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.settings = settings
        self.apply_cb = apply_cb
        self._view_data: List[Dict] = []

        self.pack(fill="both", expand=True, padx=12, pady=12)

        search_row = ttk.Frame(self)
        search_row.pack(fill="x", pady=(0, 6))
        ttk.Label(search_row, text="검색:").pack(side="left")
        self.search_var = tk.StringVar()
        ttk.Entry(search_row, textvariable=self.search_var, font=BASE_FONT).pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )
        self.search_var.trace_add("write", lambda *_: self._refresh_list())

        list_row = ttk.Frame(self)
        list_row.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_row, height=8, font=BASE_FONT, activestyle="none")
        sb = ttk.Scrollbar(list_row, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        entry_row = ttk.Frame(self)
        entry_row.pack(fill="x", pady=(6, 0))
        ttk.Label(entry_row, text="코드:").pack(side="left")
        self.code_var = tk.StringVar()
        ttk.Entry(entry_row, textvariable=self.code_var, width=8, font=BASE_FONT).pack(side="left", padx=(2, 8))
        ttk.Label(entry_row, text="명칭:").pack(side="left")
        self.name_var = tk.StringVar()
        entry_name = ttk.Entry(entry_row, textvariable=self.name_var, font=BASE_FONT)
        entry_name.pack(side="left", fill="x", expand=True)

        btn_row = ttk.Frame(self)
        btn_row.pack(fill="x", pady=(6, 12))
        ttk.Button(btn_row, text="추가", command=self._add).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(btn_row, text="수정", command=self._update).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_row, text="삭제", command=self._delete).pack(side="left", expand=True, fill="x", padx=2)
        self.fav_btn = ttk.Button(btn_row, text="☆ 즐겨찾기", command=self._toggle_fav)
        self.fav_btn.pack(side="left", expand=True, fill="x", padx=(2, 0))

        entry_name.bind("<Return>", lambda e: self._add())

        csv_frame = ttk.LabelFrame(self, text="일괄 관리 (CSV)", padding=10)
        csv_frame.pack(fill="x", side="bottom")
        ttk.Button(csv_frame, text="CSV 가져오기...", command=self._import_csv).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(csv_frame, text="CSV 내보내기...", command=self._export_csv).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(csv_frame, text="최근 사용 비우기", command=self._clear_recent).pack(side="left", expand=True, fill="x", padx=(2, 0))

        self._refresh_list()

    def _refresh_list(self) -> None:
        query = self.search_var.get().strip().lower()
        self.listbox.delete(0, "end")
        self._view_data = []
        diagnoses = self.settings["diagnoses"]
        ordered = [d for d in diagnoses if d.get("favorite")] + [d for d in diagnoses if not d.get("favorite")]
        for d in ordered:
            code, name = d.get("code", ""), d.get("name", "")
            if query and query not in code.lower() and query not in name.lower():
                continue
            star = "★ " if d.get("favorite") else "    "
            self.listbox.insert("end", f"{star}{code} {name}".strip())
            self._view_data.append(d)

    def _on_select(self, _e=None) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        d = self._view_data[sel[0]]
        self.code_var.set(d.get("code", ""))
        self.name_var.set(d.get("name", ""))
        self.fav_btn.config(text="★ 즐겨찾기 해제" if d.get("favorite") else "☆ 즐겨찾기 등록")

    def _add(self) -> None:
        code = self.code_var.get().strip().upper()
        name = self.name_var.get().strip()
        if not (code or name):
            return
        diagnoses = self.settings["diagnoses"]
        for d in diagnoses:
            if d.get("code") == code and d.get("name") == name:
                messagebox.showwarning("중복", "이미 동일한 진단명이 있습니다.", parent=self)
                return
        diagnoses.insert(0, {"code": code, "name": name, "favorite": False})
        self.search_var.set("")
        self._refresh_list()
        self.apply_cb()

    def _update(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        code = self.code_var.get().strip().upper()
        name = self.name_var.get().strip()
        if not (code or name):
            return
        d = self._view_data[sel[0]]
        d["code"] = code
        d["name"] = name
        self._refresh_list()
        self.apply_cb()

    def _delete(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        d = self._view_data[sel[0]]
        self.settings["diagnoses"].remove(d)
        self.code_var.set("")
        self.name_var.set("")
        self._refresh_list()
        self.apply_cb()

    def _toggle_fav(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        d = self._view_data[sel[0]]
        d["favorite"] = not d.get("favorite")
        self._refresh_list()
        self.apply_cb()

    def _import_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="CSV 파일 선택",
            filetypes=[("CSV 파일", "*.csv"), ("모든 파일", "*.*")],
            parent=self
        )
        if not path:
            return
        try:
            items, skipped = storage.import_diagnoses_csv(path)
        except Exception as e:
            messagebox.showerror("오류", f"가져오기 실패:\n{str(e)}", parent=self)
            return

        msg = f"{len(items)}개의 진단명을 읽었습니다."
        if skipped:
            msg += f"\n(빈 줄이나 내용이 없는 {skipped}줄 건너뜀)"
        msg += "\n\n기존 목록에 추가하시겠습니까?\n(아니오를 누르면 기존 목록을 대체합니다)"

        reply = messagebox.askyesnocancel("확인", msg, parent=self)
        if reply is None:
            return
        if reply:  # Yes = append
            existing = {(d.get("code", ""), d.get("name", "")) for d in self.settings["diagnoses"]}
            added = 0
            for item in items:
                if (item["code"], item["name"]) not in existing:
                    self.settings["diagnoses"].append(item)
                    added += 1
            messagebox.showinfo("완료", f"{added}개 항목 추가 완료.", parent=self)
        else:  # No = replace
            self.settings["diagnoses"] = items
            messagebox.showinfo("완료", "목록 교체 완료.", parent=self)

        self.search_var.set("")
        self._refresh_list()
        self.apply_cb()

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title="CSV 파일 저장",
            defaultextension=".csv",
            filetypes=[("CSV 파일", "*.csv")],
            initialfile="diagnoses.csv",
            parent=self
        )
        if not path:
            return
        try:
            storage.export_diagnoses_csv(path, self.settings["diagnoses"])
            messagebox.showinfo("완료", "저장되었습니다.", parent=self)
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패:\n{str(e)}", parent=self)

    def _clear_recent(self) -> None:
        if not self.settings["recent_diagnoses"]:
            return
        if messagebox.askyesno("확인", "진단명 최근 사용 목록을 모두 지우시겠습니까?", parent=self):
            self.settings["recent_diagnoses"] = []
            self.apply_cb()
            messagebox.showinfo("완료", "지워졌습니다.", parent=self)
