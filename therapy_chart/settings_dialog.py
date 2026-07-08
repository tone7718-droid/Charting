# -*- coding: utf-8 -*-
"""설정 다이얼로그.

치료사 / 치료 목적 / 시행 기법 / 진단명 / 시행 부위 / 데이터(백업·복원) 관리.
설정 dict를 직접 수정하며, 변경이 있을 때마다 on_change() 콜백을 호출한다
(메인 창이 저장과 화면 갱신을 담당).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, List, Optional

from . import constants as C
from . import record as R
from . import storage
from . import ui_validation as V

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
        entry.bind("<Return>", lambda _e: self.add())
        ttk.Button(entry_row, text="추가", command=self.add).pack(side="left")
        ttk.Button(entry_row, text="수정", command=self.rename).pack(side="left", padx=(4, 0))
        ttk.Button(entry_row, text="삭제", command=self.delete).pack(side="left", padx=(4, 0))

        self.refresh()

    def refresh(self) -> None:
        self.listbox.delete(0, "end")
        for item in self.items:
            self.listbox.insert("end", item)

    def selected_index(self) -> Optional[int]:
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def _on_select(self, _e=None) -> None:
        idx = self.selected_index()
        if idx is not None:
            self.entry_var.set(self.items[idx])

    def _changed(self) -> None:
        self.refresh()
        self.on_change(self.items)

    def add(self) -> None:
        value = self.entry_var.get().strip()
        if not value:
            return
        if value in self.items:
            messagebox.showinfo("안내", "이미 등록된 항목입니다.", parent=self)
            return
        self.items.append(value)
        self.entry_var.set("")
        self._changed()

    def rename(self) -> None:
        idx = self.selected_index()
        value = self.entry_var.get().strip()
        if idx is None:
            messagebox.showinfo("안내", "수정할 항목을 목록에서 먼저 선택하세요.", parent=self)
            return
        if not value:
            return
        if value != self.items[idx] and value in self.items:
            messagebox.showinfo("안내", "이미 등록된 항목입니다.", parent=self)
            return
        old = self.items[idx]
        self.items[idx] = value
        self._changed()
        self.on_rename(old, value)

    def delete(self) -> None:
        idx = self.selected_index()
        if idx is None:
            messagebox.showinfo("안내", "삭제할 항목을 목록에서 먼저 선택하세요.", parent=self)
            return
        item = self.items[idx]
        if item in self.protected:
            if not messagebox.askyesno(
                "삭제 확인", f"'{item}'은(는) 기본 제공 항목입니다.\n정말 삭제할까요?", parent=self
            ):
                return
        elif not messagebox.askyesno("삭제 확인", f"'{item}'을(를) 삭제할까요?", parent=self):
            return
        del self.items[idx]
        self.entry_var.set("")
        self._changed()
        self.on_delete(item)

    def on_rename(self, old: str, new: str) -> None:
        pass

    def on_delete(self, item: str) -> None:
        pass


class SettingsDialog(tk.Toplevel):
    """설정 창. settings dict를 직접 수정한다."""

    def __init__(self, master, settings: Dict, on_change: Callable[[], None]):
        super().__init__(master)
        self.title("설정")
        self.settings = settings
        self.on_change = on_change
        self.geometry("620x560")
        self.minsize(560, 480)
        self.transient(master)
        self.grab_set()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_therapists(notebook)
        self.tab_purposes(notebook)
        self.tab_techniques(notebook)
        self.tab_diagnoses(notebook)
        self.tab_regions(notebook)
        self.tab_data(notebook)

        ttk.Button(self, text="닫기", command=self.destroy).pack(pady=(0, 10))

    def changed(self):
        """설정이 바뀔 때마다 호출 — 메인 창이 저장/갱신한다. 저장 성공 여부 반환."""
        return self.on_change()

    # ------------------------------------------------------------------
    # 치료사
    # ------------------------------------------------------------------
    def tab_therapists(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text=" 치료사 ")

        ttk.Label(tab, text="치료사 이름만 등록하세요. 출력 시 '물리치료사'가 자동으로 붙습니다.").pack(anchor="w")

        editor = ListEditor(tab, self.settings["therapists"], lambda _items: self._therapists_changed())
        editor.pack(fill="both", expand=True, pady=(6, 0))
        self.therapist_editor = editor

        def on_rename(old: str, new: str) -> None:
            if self.settings.get("default_therapist") == old:
                self.settings["default_therapist"] = new
            if self.settings.get("last_therapist") == old:
                self.settings["last_therapist"] = new
            self._therapists_changed()

        def on_delete(item: str) -> None:
            if self.settings.get("default_therapist") == item:
                self.settings["default_therapist"] = ""
            if self.settings.get("last_therapist") == item:
                self.settings["last_therapist"] = ""
            self._therapists_changed()

        editor.on_rename = on_rename
        editor.on_delete = on_delete

        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(8, 0))
        ttk.Button(row, text="★ 기본 치료사로 지정", command=self.set_default_therapist).pack(side="left")
        self.default_therapist_lbl = ttk.Label(row, foreground="#2f6fed")
        self.default_therapist_lbl.pack(side="left", padx=(10, 0))
        self._update_default_label()

    def _update_default_label(self) -> None:
        default = self.settings.get("default_therapist") or "(지정 안 됨)"
        self.default_therapist_lbl.config(text=f"현재 기본 치료사: {default}")

    def _therapists_changed(self) -> None:
        self._update_default_label()
        self.changed()

    def set_default_therapist(self) -> None:
        idx = self.therapist_editor.selected_index()
        if idx is None:
            messagebox.showinfo("안내", "기본으로 지정할 치료사를 목록에서 선택하세요.", parent=self)
            return
        self.settings["default_therapist"] = self.settings["therapists"][idx]
        self._therapists_changed()

    # ------------------------------------------------------------------
    # 치료 목적 / 시행 기법
    # ------------------------------------------------------------------
    def tab_purposes(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text=" 치료 목적 ")
        ttk.Label(tab, text="메인 화면 토글 버튼에 표시될 치료 목적 항목입니다.").pack(anchor="w")
        ListEditor(
            tab, self.settings["purposes"], lambda _items: self.changed(),
            protected_items=C.DEFAULT_PURPOSES,
        ).pack(fill="both", expand=True, pady=(6, 0))

    def tab_techniques(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text=" 시행 기법 ")
        ttk.Label(tab, text="메인 화면 토글 버튼에 표시될 시행 기법 항목입니다.").pack(anchor="w")
        ListEditor(
            tab, self.settings["techniques"], lambda _items: self.changed(),
            protected_items=C.DEFAULT_TECHNIQUES,
        ).pack(fill="both", expand=True, pady=(6, 0))

    # ------------------------------------------------------------------
    # 진단명
    # ------------------------------------------------------------------
    def tab_diagnoses(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text=" 진단명 ")

        search_row = ttk.Frame(tab)
        search_row.pack(fill="x")
        ttk.Label(search_row, text="🔍 검색:").pack(side="left")
        self.diag_search_var = tk.StringVar()
        ttk.Entry(search_row, textvariable=self.diag_search_var, font=BASE_FONT).pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )
        self.diag_search_var.trace_add("write", lambda *_: self.refresh_diag_list())

        list_row = ttk.Frame(tab)
        list_row.pack(fill="both", expand=True, pady=(6, 0))
        self.diag_listbox = tk.Listbox(list_row, height=9, font=BASE_FONT, activestyle="none")
        sb = ttk.Scrollbar(list_row, orient="vertical", command=self.diag_listbox.yview)
        self.diag_listbox.configure(yscrollcommand=sb.set)
        self.diag_listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.diag_listbox.bind("<<ListboxSelect>>", self._on_diag_select)
        self._diag_view: List[Dict] = []  # 리스트박스 인덱스 → 진단 dict

        entry_row = ttk.Frame(tab)
        entry_row.pack(fill="x", pady=(6, 0))
        ttk.Label(entry_row, text="진단코드:").pack(side="left")
        self.diag_code_var = tk.StringVar()
        ttk.Entry(entry_row, textvariable=self.diag_code_var, width=8, font=BASE_FONT).pack(side="left", padx=(4, 8))
        self.diag_code_var.trace_add("write", self._normalize_diag_code_var)
        ttk.Label(entry_row, text="진단명:").pack(side="left")
        self.diag_name_var = tk.StringVar()
        ttk.Entry(entry_row, textvariable=self.diag_name_var, font=BASE_FONT).pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )
        self._normalizing_diag_code = False

        btn_row = ttk.Frame(tab)
        btn_row.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_row, text="추가", command=self.diag_add).pack(side="left")
        ttk.Button(btn_row, text="수정", command=self.diag_update).pack(side="left", padx=(4, 0))
        ttk.Button(btn_row, text="삭제", command=self.diag_delete).pack(side="left", padx=(4, 0))
        ttk.Button(btn_row, text="★ 즐겨찾기", command=self.diag_toggle_favorite).pack(side="left", padx=(4, 0))

        csv_row = ttk.Frame(tab)
        csv_row.pack(fill="x", pady=(6, 0))
        ttk.Button(csv_row, text="CSV 가져오기", command=self.diag_import_csv).pack(side="left")
        ttk.Button(csv_row, text="CSV 내보내기", command=self.diag_export_csv).pack(side="left", padx=(4, 0))
        ttk.Button(csv_row, text="최근 사용 목록 비우기", command=self.diag_clear_recent).pack(side="left", padx=(4, 0))
        ttk.Label(
            tab,
            text="CSV 형식: 한 줄에 '진단코드,진단명' (첫 줄 헤더는 자동으로 건너뜁니다)",
            foreground="#888888",
        ).pack(anchor="w", pady=(4, 0))

        self.refresh_diag_list()

    def _normalize_diag_code_var(self, *_args) -> None:
        if self._normalizing_diag_code:
            return
        value = self.diag_code_var.get()
        normalized = R.normalize_code(value)
        if value != normalized:
            self._normalizing_diag_code = True
            self.diag_code_var.set(normalized)
            self._normalizing_diag_code = False

    def refresh_diag_list(self) -> None:
        query = self.diag_search_var.get().strip().lower()
        self.diag_listbox.delete(0, "end")
        self._diag_view = []
        diagnoses = self.settings["diagnoses"]
        ordered = [d for d in diagnoses if d.get("favorite")] + [d for d in diagnoses if not d.get("favorite")]
        for d in ordered:
            text = f"{d.get('code', '')} {d.get('name', '')}".strip()
            if query and query not in text.lower():
                continue
            star = "★ " if d.get("favorite") else "    "
            self.diag_listbox.insert("end", star + text)
            self._diag_view.append(d)

    def _selected_diag(self) -> Optional[Dict]:
        sel = self.diag_listbox.curselection()
        return self._diag_view[sel[0]] if sel else None

    def _on_diag_select(self, _e=None) -> None:
        d = self._selected_diag()
        if d:
            self.diag_code_var.set(d.get("code", ""))
            self.diag_name_var.set(d.get("name", ""))

    def diag_add(self) -> None:
        code = R.normalize_code(self.diag_code_var.get())
        name = self.diag_name_var.get().strip()
        if not (code or name):
            return
        for d in self.settings["diagnoses"]:
            if R.normalize_code(d.get("code")) == code and d.get("name") == name:
                messagebox.showinfo("안내", "이미 등록된 진단명입니다.", parent=self)
                return
        self.settings["diagnoses"].append({"code": code, "name": name, "favorite": False})
        self.refresh_diag_list()
        self.changed()

    def diag_update(self) -> None:
        d = self._selected_diag()
        if d is None:
            messagebox.showinfo("안내", "수정할 진단명을 목록에서 먼저 선택하세요.", parent=self)
            return
        code = R.normalize_code(self.diag_code_var.get())
        name = self.diag_name_var.get().strip()
        if not (code or name):
            messagebox.showinfo("안내", "진단코드나 진단명 중 하나는 입력해야 합니다.", parent=self)
            return
        for other in self.settings["diagnoses"]:
            if other is not d and R.normalize_code(other.get("code")) == code and other.get("name") == name:
                messagebox.showinfo("안내", "이미 등록된 진단명입니다.", parent=self)
                return
        d["code"] = code
        d["name"] = name
        self.refresh_diag_list()
        self.changed()

    def diag_delete(self) -> None:
        d = self._selected_diag()
        if d is None:
            messagebox.showinfo("안내", "삭제할 진단명을 목록에서 먼저 선택하세요.", parent=self)
            return
        text = f"{d.get('code', '')} {d.get('name', '')}".strip()
        if not messagebox.askyesno("삭제 확인", f"'{text}'을(를) 삭제할까요?", parent=self):
            return
        self.settings["diagnoses"].remove(d)
        self.refresh_diag_list()
        self.changed()

    def diag_toggle_favorite(self) -> None:
        d = self._selected_diag()
        if d is None:
            messagebox.showinfo("안내", "즐겨찾기로 지정할 진단명을 목록에서 선택하세요.", parent=self)
            return
        d["favorite"] = not d.get("favorite", False)
        self.refresh_diag_list()
        self.changed()

    def diag_import_csv(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, title="진단명 CSV 가져오기",
            filetypes=[("CSV 파일", "*.csv"), ("모든 파일", "*.*")],
        )
        if not path:
            return
        try:
            items, skipped = storage.import_diagnoses_csv(path)
        except Exception as exc:
            messagebox.showerror("가져오기 실패", f"CSV 파일을 읽을 수 없습니다.\n{exc}", parent=self)
            return
        existing = {(R.normalize_code(d.get("code")), d.get("name")) for d in self.settings["diagnoses"]}
        added = 0
        for item in items:
            key = (R.normalize_code(item["code"]), item["name"])
            if key not in existing:
                item["code"] = key[0]
                self.settings["diagnoses"].append(item)
                existing.add(key)
                added += 1
        self.refresh_diag_list()
        self.changed()
        msg = f"{added}개 진단명을 추가했습니다."
        if skipped:
            msg += f" (형식이 잘못된 {skipped}줄은 건너뜀)"
        messagebox.showinfo("가져오기 완료", msg, parent=self)

    def diag_export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self, title="진단명 CSV 내보내기", defaultextension=".csv",
            initialfile="diagnoses.csv",
            filetypes=[("CSV 파일", "*.csv")],
        )
        if not path:
            return
        try:
            storage.export_diagnoses_csv(path, self.settings["diagnoses"])
        except OSError as exc:
            messagebox.showerror("내보내기 실패", f"파일을 저장할 수 없습니다.\n{exc}", parent=self)
            return
        messagebox.showinfo("내보내기 완료", "진단명 목록을 CSV 파일로 저장했습니다.", parent=self)

    def diag_clear_recent(self) -> None:
        if messagebox.askyesno("확인", "최근 사용 진단명 목록을 비울까요?", parent=self):
            self.settings["recent_diagnoses"] = []
            self.changed()

    # ------------------------------------------------------------------
    # 시행 부위
    # ------------------------------------------------------------------
    def tab_regions(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text=" 시행 부위 ")

        ttk.Label(tab, text="자주 사용하는 시행 부위 (메인 화면 드롭다운 위쪽에 표시)").pack(anchor="w")
        ListEditor(
            tab, self.settings["region_favorites"], lambda _items: self.changed(), height=6
        ).pack(fill="both", expand=True, pady=(4, 8))

        ttk.Label(tab, text="최근 사용한 시행 부위 (복사할 때 자동 저장)").pack(anchor="w")
        recent_row = ttk.Frame(tab)
        recent_row.pack(fill="both", expand=True, pady=(4, 0))
        self.recent_region_listbox = tk.Listbox(recent_row, height=5, font=BASE_FONT, activestyle="none")
        sb = ttk.Scrollbar(recent_row, orient="vertical", command=self.recent_region_listbox.yview)
        self.recent_region_listbox.configure(yscrollcommand=sb.set)
        self.recent_region_listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        btn_row = ttk.Frame(tab)
        btn_row.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_row, text="선택 삭제", command=self.region_recent_delete).pack(side="left")
        ttk.Button(btn_row, text="전체 비우기", command=self.region_recent_clear).pack(side="left", padx=(4, 0))
        self.refresh_recent_regions()

    def refresh_recent_regions(self) -> None:
        self.recent_region_listbox.delete(0, "end")
        for r in self.settings["recent_regions"]:
            self.recent_region_listbox.insert("end", r)

    def region_recent_delete(self) -> None:
        sel = self.recent_region_listbox.curselection()
        if not sel:
            return
        del self.settings["recent_regions"][sel[0]]
        self.refresh_recent_regions()
        self.changed()

    def region_recent_clear(self) -> None:
        if messagebox.askyesno("확인", "최근 사용 시행 부위 목록을 비울까요?", parent=self):
            self.settings["recent_regions"] = []
            self.refresh_recent_regions()
            self.changed()

    # ------------------------------------------------------------------
    # 데이터 (저장 위치 / 백업 / 복원 / 기타 설정)
    # ------------------------------------------------------------------
    def tab_data(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text=" 데이터 ")

        ttk.Label(tab, text="데이터 저장 위치 (환자 개인정보는 저장되지 않습니다)").pack(anchor="w")
        path_row = ttk.Frame(tab)
        path_row.pack(fill="x", pady=(4, 10))
        path_var = tk.StringVar(value=storage.data_dir())
        path_entry = ttk.Entry(path_row, textvariable=path_var, font=BASE_FONT, state="readonly")
        path_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(path_row, text="폴더 열기", command=self.open_data_folder).pack(side="left")

        ttk.Separator(tab).pack(fill="x", pady=6)

        ttk.Label(tab, text="백업 / 복원").pack(anchor="w")
        backup_row = ttk.Frame(tab)
        backup_row.pack(fill="x", pady=(4, 10))
        ttk.Button(backup_row, text="백업 파일로 내보내기", command=self.backup).pack(side="left")
        ttk.Button(backup_row, text="백업 파일에서 복원", command=self.restore).pack(side="left", padx=(6, 0))

        ttk.Separator(tab).pack(fill="x", pady=6)

        self.remember_geometry_var = tk.BooleanVar(value=bool(self.settings.get("remember_geometry", True)))
        ttk.Checkbutton(
            tab, text="프로그램 종료 시 창 크기와 위치 기억",
            variable=self.remember_geometry_var, command=self._geometry_option_changed,
        ).pack(anchor="w")

        self.auto_reset_var = tk.BooleanVar(value=bool(self.settings.get("auto_reset_after_copy", False)))
        ttk.Checkbutton(
            tab, text="복사 성공 시 자동으로 초기화 (다음 환자 입력 준비)",
            variable=self.auto_reset_var, command=self._auto_reset_option_changed,
        ).pack(anchor="w", pady=(4, 0))

        minutes_row = ttk.Frame(tab)
        minutes_row.pack(fill="x", pady=(10, 0))
        ttk.Label(minutes_row, text="치료시간(분):").pack(side="left")
        initial_minutes = V.clamp_int(
            self.settings.get("treatment_minutes", C.DEFAULT_TREATMENT_MINUTES),
            C.MIN_TREATMENT_MINUTES,
            C.MAX_TREATMENT_MINUTES,
            C.DEFAULT_TREATMENT_MINUTES,
        )
        self.settings["treatment_minutes"] = initial_minutes
        self.minutes_var = tk.StringVar(value=str(initial_minutes))
        minutes_validate = (
            self.register(
                lambda s: V.is_empty_or_int_in_range(
                    s, C.MIN_TREATMENT_MINUTES, C.MAX_TREATMENT_MINUTES
                )
            ),
            "%P",
        )
        ttk.Spinbox(
            minutes_row,
            from_=C.MIN_TREATMENT_MINUTES,
            to=C.MAX_TREATMENT_MINUTES,
            textvariable=self.minutes_var,
            width=6,
            validate="key",
            validatecommand=minutes_validate,
            font=BASE_FONT,
            command=self._minutes_changed,
        ).pack(side="left", padx=(4, 6))
        ttk.Label(
            minutes_row,
            text=f"(기본 30분 — {C.MIN_TREATMENT_MINUTES}~{C.MAX_TREATMENT_MINUTES}분)",
        ).pack(side="left")
        self.minutes_var.trace_add("write", lambda *_: self._minutes_changed())

    def _geometry_option_changed(self) -> None:
        self.settings["remember_geometry"] = bool(self.remember_geometry_var.get())
        self.changed()

    def _auto_reset_option_changed(self) -> None:
        self.settings["auto_reset_after_copy"] = bool(self.auto_reset_var.get())
        self.changed()

    def _minutes_changed(self) -> None:
        value = self.minutes_var.get().strip()
        if not value:
            return
        if V.is_int_in_range(value, C.MIN_TREATMENT_MINUTES, C.MAX_TREATMENT_MINUTES):
            self.settings["treatment_minutes"] = int(value)
            self.changed()

    def open_data_folder(self) -> None:
        path = storage.data_dir()
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # noqa: S606 (Windows 탐색기 열기)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError:
            messagebox.showinfo("안내", f"폴더를 열 수 없습니다.\n경로: {path}", parent=self)

    def backup(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self, title="백업 파일로 내보내기", defaultextension=".json",
            initialfile=storage.default_backup_filename(),
            filetypes=[("JSON 파일", "*.json")],
        )
        if not path:
            return
        try:
            storage.backup_to(path, self.settings)
        except OSError as exc:
            messagebox.showerror("백업 실패", f"파일을 저장할 수 없습니다.\n{exc}", parent=self)
            return
        messagebox.showinfo("백업 완료", "설정과 등록 데이터를 백업 파일로 저장했습니다.", parent=self)

    def restore(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, title="백업 파일에서 복원",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
        )
        if not path:
            return
        if not messagebox.askyesno(
            "복원 확인",
            "현재 설정과 등록 데이터가 백업 파일 내용으로 교체됩니다.\n계속할까요?",
            parent=self,
        ):
            return
        try:
            restored = storage.restore_from(path)
        except Exception as exc:  # 손상된 파일이어도 기존 데이터 유지
            messagebox.showerror(
                "복원 실패",
                f"백업 파일을 읽을 수 없어 기존 데이터를 유지합니다.\n{exc}",
                parent=self,
            )
            return
        self.settings.clear()
        self.settings.update(restored)
        saved = self.changed()
        if saved is False:
            messagebox.showerror(
                "복원 실패",
                "복원한 내용을 디스크에 저장하지 못했습니다.\n디스크 여유 공간과 권한을 확인해주세요.",
                parent=self,
            )
            return
        messagebox.showinfo("복원 완료", "백업 파일에서 설정을 복원했습니다.\n설정 창을 다시 열면 복원된 내용이 표시됩니다.", parent=self)
        self.destroy()
