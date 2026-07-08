# -*- coding: utf-8 -*-
"""상태 관리 (State Management).

애플리케이션 전역 상태와 설정을 관리하며 Observer 패턴을 통해
상태 변경 시 등록된 콜백(리스너)들을 호출합니다.
"""

from __future__ import annotations
import datetime
import tkinter as tk
from typing import Callable, Dict, List, Optional
from . import record as R
from . import storage
from . import constants as C

class AppState:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings: Dict = storage.load_settings()
        self.listeners: List[Callable] = []

        # ------------------------- 입력 상태 -------------------------
        self.diag_code_var = tk.StringVar()
        self.diag_name_var = tk.StringVar()
        self.therapist_var = tk.StringVar()
        self.count_var = tk.StringVar(value="1")
        self.region_var = tk.StringVar()

        # 선택된 날짜와 칩들 (다중 선택 상태 관리를 위해 별도 변수)
        self.date_selected: datetime.date = datetime.date.today()
        self.selected_purposes: List[str] = []
        self.selected_techniques: List[str] = []

        # 치료 효과 평가 (선택 입력)
        self.improvement_var = tk.StringVar()  # 호전/유지/악화 (빈값 = 미선택)
        self.vas_before_var = tk.StringVar()
        self.vas_after_var = tk.StringVar()
        self.eval_note_var = tk.StringVar()

        # 내부 추적 변수
        self._suppress_uppercase = False

        # 변경 감지 바인딩
        self._bind_traces()

    def _bind_traces(self) -> None:
        """Tkinter 변수의 변경을 감지하여 리스너들에게 알립니다."""
        self.diag_code_var.trace_add("write", self._on_code_changed)
        for var in (self.diag_name_var, self.therapist_var, self.count_var, self.region_var,
                    self.improvement_var, self.vas_before_var, self.vas_after_var, self.eval_note_var):
            var.trace_add("write", lambda *_: self.notify_listeners())

    def _on_code_changed(self, *_args) -> None:
        """진단코드 소문자 → 대문자 자동 변환 후 리스너에게 알립니다."""
        if self._suppress_uppercase:
            return
        value = self.diag_code_var.get()
        upper = value.upper()
        if value != upper:
            self._suppress_uppercase = True
            self.diag_code_var.set(upper)
            self._suppress_uppercase = False
        self.notify_listeners()

    def add_listener(self, listener: Callable) -> None:
        """상태 변경을 감지할 리스너(콜백 함수)를 등록합니다."""
        if listener not in self.listeners:
            self.listeners.append(listener)

    def remove_listener(self, listener: Callable) -> None:
        if listener in self.listeners:
            self.listeners.remove(listener)

    def notify_listeners(self) -> None:
        """상태가 변경되었음을 모든 리스너에게 알립니다."""
        for listener in self.listeners:
            listener()

    def update_date(self, date: datetime.date) -> None:
        self.date_selected = date
        self.notify_listeners()

    def update_purposes(self, purposes: List[str]) -> None:
        self.selected_purposes = purposes
        self.notify_listeners()

    def update_techniques(self, techniques: List[str]) -> None:
        self.selected_techniques = techniques
        self.notify_listeners()

    def current_record(self) -> R.TherapyRecord:
        """현재 상태를 기반으로 TherapyRecord 객체를 생성하여 반환합니다."""
        return R.TherapyRecord(
            diagnosis_code=self.diag_code_var.get(),
            diagnosis_name=self.diag_name_var.get(),
            purposes=self.selected_purposes,
            therapist=self.therapist_var.get(),
            date=self.date_selected,
            count=self.count_var.get(),
            region=self.region_var.get(),
            techniques=self.selected_techniques,
            minutes=int(self.settings.get("treatment_minutes", C.DEFAULT_TREATMENT_MINUTES)),
            improvement=self.improvement_var.get(),
            vas_before=self.vas_before_var.get(),
            vas_after=self.vas_after_var.get(),
            eval_note=self.eval_note_var.get(),
        )

    def save_settings(self) -> bool:
        """설정을 디스크에 저장합니다."""
        return storage.save_settings(self.settings)

    def refresh_from_settings(self) -> None:
        """설정 변경 사항을 다시 읽어오고 싶을 때 사용하지만
        보통은 memory 안의 settings 딕셔너리를 직접 조작합니다.
        필요 시 리스너들을 트리거합니다.
        """
        self.notify_listeners()
