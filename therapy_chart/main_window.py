# -*- coding: utf-8 -*-
"""메인 창 UI.

왼쪽: 항목 입력/선택, 오른쪽: 진료 기록 미리보기 + 복사/초기화/설정 버튼.
진료 기록 생성·검증 로직은 record 모듈, 저장은 storage 모듈에 위임한다.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List

from . import constants as C
from . import record as R
from . import storage
from .app_state import AppState
from .panels import InputPanel, PreviewPanel
from .settings_dialog import SettingsDialog
from .widgets import ACCENT

BOLD_FONT = ("맑은 고딕", 11, "bold")

MISSING_COLOR = "#d9534f"   # 필수 항목 누락 강조색
OK_COLOR = "#2e8b57"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{C.APP_NAME} v{C.APP_VERSION}")
        self.minsize(1000, 640)
        self._set_window_icon()

        self.state = AppState(self)
        self._restore_geometry()

        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure(".", font=("맑은 고딕", 11))
        style.configure("TCheckbutton", font=("맑은 고딕", 11))

        self._marked_missing: List[str] = []  # 현재 강조 표시된 누락 항목

        self.build_ui()
        self._bind_shortcuts()
        self._select_initial_therapist()

        # 상태 리스너 등록 (상태가 변하면 미리보기와 누락표시 업데이트)
        self.state.add_listener(self.on_state_changed)

        self.refresh_from_settings()
        self.on_state_changed()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(300, self.first_run_check)

    def on_state_changed(self) -> None:
        """AppState 변경 시 호출됩니다."""
        rec = self.state.current_record()
        self.preview_panel.update_preview(rec)
        self._refresh_missing_marks()

    def report_callback_exception(self, exc, val, tb):
        """버튼 클릭·trace 등 Tkinter 콜백에서 발생한 예외를 로그로 남기고 안내한다.

        기본 Tk 핸들러는 stderr로만 출력해 error.log에 남지 않으므로 재정의한다.
        """
        import traceback
        from .main import _log_error
        _log_error("".join(traceback.format_exception(exc, val, tb)))
        try:
            self.show_status("⚠ 작업 중 문제가 발생했습니다. 다시 시도해주세요.", MISSING_COLOR)
        except Exception:
            pass

    def _set_window_icon(self) -> None:
        """창 아이콘 적용. EXE(frozen)에서는 번들 경로, 개발 환경에서는 레포 경로."""
        try:
            import sys
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            icon_path = os.path.join(base, "assets", "icon.ico")
            if os.path.isfile(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass  # 아이콘 실패는 치명적이지 않음 (비Windows 환경 포함)

    # ==================================================================
    # UI 구성
    # ==================================================================
    def build_ui(self) -> None:
        # 치료사 미등록 안내 배너
        self.banner = tk.Label(
            self, text="⚠ 설정에서 치료사를 먼저 등록해주세요.",
            font=BOLD_FONT, bg="#fff3cd", fg="#856404", pady=6,
        )

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        self.input_panel = InputPanel(paned, self.state, self.show_status)
        paned.add(self.input_panel, weight=1)

        self.preview_panel = PreviewPanel(paned, self.state, self.show_status, self.reset_inputs, self.copy_output, self.open_settings)
        paned.add(self.preview_panel, weight=1)

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-Shift-C>", lambda _e: self.copy_output())
        self.bind_all("<Control-Shift-c>", lambda _e: self.copy_output())
        self.bind_all("<Control-r>", lambda _e: self.reset_inputs())
        self.bind_all("<Control-R>", lambda _e: self.reset_inputs())

    # ==================================================================
    # 설정 연동 / 갱신
    # ==================================================================
    def refresh_from_settings(self) -> None:
        therapists = self.state.settings["therapists"]
        if not self.state.therapist_var.get():
            self._select_initial_therapist()

        if therapists:
            self.banner.pack_forget()
        else:
            self.banner.pack(fill="x", before=self.winfo_children()[1] if len(self.winfo_children()) > 1 else None)

        self.input_panel.refresh_from_settings()

    def _select_initial_therapist(self) -> None:
        therapists = self.state.settings["therapists"]
        for candidate in (self.state.settings.get("last_therapist"), self.state.settings.get("default_therapist")):
            if candidate and candidate in therapists:
                self.state.therapist_var.set(candidate)
                return
        if len(therapists) == 1:
            self.state.therapist_var.set(therapists[0])

    def save_settings(self) -> bool:
        ok = self.state.save_settings()
        if not ok:
            self.show_status("⚠ 설정 저장에 실패했습니다. 디스크 상태를 확인해주세요.", C.MISSING_COLOR, True)
        return ok

    def on_settings_changed(self) -> bool:
        ok = self.save_settings()
        self.state.refresh_from_settings()
        self.refresh_from_settings()
        return ok

    def open_settings(self) -> None:
        SettingsDialog(self, self.state.settings, on_change=self.on_settings_changed)

    def first_run_check(self) -> None:
        if not self.state.settings["therapists"]:
            self.input_panel.quick_add_therapist(first_run=True)

    # ==================================================================
    # 필수 항목 검사 / 강조 표시
    # ==================================================================
    def _mark_missing(self, missing: List[str]) -> None:
        self._marked_missing = list(missing)
        self.input_panel.mark_missing_fields(missing)

    def _refresh_missing_marks(self) -> None:
        if not self._marked_missing:
            return
        still_missing = set(self.state.current_record().missing_fields())
        remaining = [m for m in self._marked_missing if m in still_missing]
        self._mark_missing(remaining)
        if not remaining:
            self.clear_status()

    # ==================================================================
    # 복사 / 초기화
    # ==================================================================
    def copy_output(self) -> None:
        try:
            if self.preview_panel.preview_mode == "auto":
                rec = self.state.current_record()
                missing = rec.missing_fields()
                if missing:
                    self._mark_missing(missing)
                    self.show_status(
                        f"필수 항목을 확인해주세요: {', '.join(missing)}", C.MISSING_COLOR, True
                    )
                    return
                text = rec.build_text()
                self._remember_recents(rec)
            else:
                text = self.preview_panel.get_current_text()
                if not text.strip():
                    self.show_status("복사할 내용이 없습니다.", C.MISSING_COLOR)
                    return
                missing = R.missing_labels_in_text(text)
                if missing:
                    if not messagebox.askyesno(
                        "필수 항목 확인",
                        f"다음 필수 항목이 비어 있습니다:\n{', '.join(missing)}\n\n그래도 복사할까요?",
                    ):
                        self.show_status(
                            f"필수 항목을 확인해주세요: {', '.join(missing)}", C.MISSING_COLOR, True
                        )
                        return
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
            if self.preview_panel.preview_mode == "auto" and self.state.settings.get("auto_reset_after_copy"):
                self.reset_inputs(confirm=False)
                self.show_status("✔ 복사 완료 — 다음 환자 입력 준비됨", C.OK_COLOR)
            else:
                self.show_status("✔ 진료기록이 클립보드에 복사되었습니다.", C.OK_COLOR)
        except Exception:
            self.show_status("⚠ 복사 중 문제가 발생했습니다. 다시 시도해주세요.", C.MISSING_COLOR)

    def _remember_recents(self, rec: R.TherapyRecord) -> None:
        code = R.normalize_code(rec.diagnosis_code)
        name = rec.diagnosis_name.strip()
        if code or name:
            self.state.settings["recent_diagnoses"] = storage.push_recent(
                self.state.settings["recent_diagnoses"], {"code": code, "name": name}
            )
        region = rec.region.strip()
        if region:
            self.state.settings["recent_regions"] = storage.push_recent(
                self.state.settings["recent_regions"], region
            )
        self.state.save_settings()
        self.refresh_from_settings()

    def reset_inputs(self, confirm: bool = True) -> None:
        if confirm and not messagebox.askyesno(
            "초기화 확인", "현재 입력한 내용을 초기화할까요?\n(치료사·설정·저장 목록은 유지됩니다)"
        ):
            return

        import datetime
        self.state.diag_code_var.set("")
        self.state.diag_name_var.set("")
        self.input_panel.diag_search_var.set("")
        self.state.count_var.set("1")
        self.state.region_var.set("")
        self.input_panel.purpose_chips.clear_selection()
        self.input_panel.tech_chips.clear_selection()
        self.input_panel.improvement_chips.clear_selection()

        # update states manually for chips
        self.state.selected_purposes = []
        self.state.selected_techniques = []

        self.state.improvement_var.set("")
        self.state.vas_before_var.set("")
        self.state.vas_after_var.set("")
        self.state.eval_note_var.set("")
        self.state.date_selected = datetime.date.today()
        self.input_panel.calendar.set_date(self.state.date_selected)

        therapists = self.state.settings["therapists"]
        default = self.state.settings.get("default_therapist")
        if default and default in therapists:
            self.state.therapist_var.set(default)
        elif len(therapists) == 1:
            self.state.therapist_var.set(therapists[0])
        else:
            self.state.therapist_var.set("")

        self.preview_panel.reset_mode()
        self._mark_missing([])
        self.clear_status()
        self.state.notify_listeners()

    # ==================================================================
    # 상태 메시지 (Preview 패널의 status label 이용)
    # ==================================================================
    def show_status(self, text: str, color: str, sticky: bool = False) -> None:
        self.preview_panel.status_lbl.config(text=text, foreground=color)
        if hasattr(self, "_status_after") and self._status_after:
            self.after_cancel(self._status_after)
            self._status_after = None
        if not sticky:
            self._status_after = self.after(2500, self.clear_status)

    def clear_status(self) -> None:
        self.preview_panel.status_lbl.config(text="")
        self._status_after = None

    # ==================================================================
    # 종료 처리
    # ==================================================================
    def _restore_geometry(self) -> None:
        geometry = self.state.settings.get("window_geometry", "")
        if self.state.settings.get("remember_geometry", True) and geometry:
            try:
                self.geometry(geometry)
                return
            except tk.TclError:
                pass
        try:
            super().state("zoomed")
        except tk.TclError:
            self.geometry("1280x800")

    def on_close(self) -> None:
        try:
            if self.state.settings.get("remember_geometry", True) and super().state() == "normal":
                self.state.settings["window_geometry"] = self.geometry()
            self.state.settings["last_therapist"] = self.state.therapist_var.get()
            self.state.save_settings()
        except Exception:
            pass
        self.destroy()
