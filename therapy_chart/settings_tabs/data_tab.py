# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict

from .. import storage
from .. import constants as C

BASE_FONT = ("맑은 고딕", 11)

class DataTab(ttk.Frame):
    def __init__(self, master, settings: Dict, apply_cb: Callable, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.settings = settings
        self.apply_cb = apply_cb

        self.pack(fill="both", expand=True, padx=12, pady=12)

        # 치료 시간
        f_time = ttk.LabelFrame(self, text="기본 치료 시간", padding=10)
        f_time.pack(fill="x", pady=(0, 10))
        ttk.Label(f_time, text="진료 기록에 출력될 시간(분):").pack(side="left")

        self.minutes_var = tk.StringVar(value=str(self.settings.get("treatment_minutes", C.DEFAULT_TREATMENT_MINUTES)))
        digits_only = (self.register(lambda s: s.isdigit() or s == ""), "%P")
        spin = ttk.Spinbox(
            f_time, from_=1, to=600, textvariable=self.minutes_var, width=5, justify="center",
            validate="key", validatecommand=digits_only, font=BASE_FONT
        )
        spin.pack(side="left", padx=8)
        self.minutes_var.trace_add("write", self._on_minutes_change)

        # 백업/복원
        f_backup = ttk.LabelFrame(self, text="백업 및 복원", padding=10)
        f_backup.pack(fill="x", pady=(0, 10))
        ttk.Label(f_backup, text="등록된 치료사, 진단명, 즐겨찾기 등 설정 전체를 백업합니다.").pack(anchor="w", pady=(0, 6))

        btn_row = ttk.Frame(f_backup)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="백업 내보내기...", command=self._export_backup).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="백업 복원...", command=self._import_backup).pack(side="left")

        # 편의 기능
        f_misc = ttk.LabelFrame(self, text="편의 기능", padding=10)
        f_misc.pack(fill="x", pady=(0, 10))

        self.remember_var = tk.BooleanVar(value=self.settings.get("remember_geometry", True))
        chk_geom = ttk.Checkbutton(
            f_misc, text="프로그램 종료 시 창 크기 및 위치 기억",
            variable=self.remember_var, command=self._on_misc_change
        )
        chk_geom.pack(anchor="w")

        self.reset_copy_var = tk.BooleanVar(value=self.settings.get("auto_reset_after_copy", False))
        chk_reset = ttk.Checkbutton(
            f_misc, text="복사 성공 시 자동으로 입력 초기화 (다음 환자 준비)",
            variable=self.reset_copy_var, command=self._on_misc_change
        )
        chk_reset.pack(anchor="w", pady=(4, 0))

        # 데이터 폴더
        f_dir = ttk.LabelFrame(self, text="데이터 저장 위치", padding=10)
        f_dir.pack(fill="x")
        path_lbl = ttk.Label(f_dir, text=storage.data_dir(), font=("맑은 고딕", 9))
        path_lbl.pack(anchor="w")
        ttk.Button(f_dir, text="폴더 열기", command=self._open_data_dir).pack(anchor="w", pady=(6, 0))

    def _on_minutes_change(self, *_args) -> None:
        val = self.minutes_var.get()
        if val.isdigit() and int(val) > 0:
            self.settings["treatment_minutes"] = int(val)
            self.apply_cb()

    def _on_misc_change(self) -> None:
        self.settings["remember_geometry"] = self.remember_var.get()
        self.settings["auto_reset_after_copy"] = self.reset_copy_var.get()
        self.apply_cb()

    def _export_backup(self) -> None:
        path = filedialog.asksaveasfilename(
            title="백업 내보내기",
            defaultextension=".json",
            filetypes=[("JSON 파일", "*.json")],
            initialfile=storage.default_backup_filename(),
            parent=self
        )
        if not path:
            return
        try:
            storage.backup_to(path, self.settings)
            messagebox.showinfo("완료", "백업 파일이 저장되었습니다.", parent=self)
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패:\n{str(e)}", parent=self)

    def _import_backup(self) -> None:
        path = filedialog.askopenfilename(
            title="백업 복원",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
            parent=self
        )
        if not path:
            return
        if not messagebox.askyesno(
            "복원 확인",
            "현재 등록된 모든 설정(치료사, 진단명 등)이 지워지고\n"
            "선택한 백업 파일의 내용으로 덮어씁니다.\n\n계속하시겠습니까?",
            parent=self
        ):
            return

        try:
            new_settings = storage.restore_from(path)
        except Exception as e:
            messagebox.showerror("오류", f"복원 실패:\n{str(e)}\n\n올바른 백업 파일인지 확인해주세요.", parent=self)
            return

        self.settings.clear()
        self.settings.update(new_settings)
        self.apply_cb()

        messagebox.showinfo(
            "복원 완료",
            "성공적으로 복원되었습니다.\n일부 설정은 프로그램을 재시작해야 반영될 수 있습니다.",
            parent=self
        )

    def _open_data_dir(self) -> None:
        path = storage.data_dir()
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
