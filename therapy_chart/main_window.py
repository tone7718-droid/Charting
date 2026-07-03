# -*- coding: utf-8 -*-
"""메인 창 UI.

왼쪽: 항목 입력/선택, 오른쪽: 진료 기록 미리보기 + 복사/초기화/설정 버튼.
진료 기록 생성·검증 로직은 record 모듈, 저장은 storage 모듈에 위임한다.
"""

from __future__ import annotations

import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Dict, List, Optional

from . import constants as C
from . import record as R
from . import storage
from .settings_dialog import SettingsDialog
from .widgets import ACCENT, CalendarWidget, ChipGroup, ScrollableFrame

BASE_FONT = ("맑은 고딕", 11)
BOLD_FONT = ("맑은 고딕", 11, "bold")
TITLE_FONT = ("맑은 고딕", 12, "bold")
PREVIEW_FONT = ("맑은 고딕", 13)

MISSING_COLOR = "#d9534f"   # 필수 항목 누락 강조색
OK_COLOR = "#2e8b57"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(C.APP_NAME)
        self.minsize(1000, 640)

        self.settings: Dict = storage.load_settings()
        self._restore_geometry()

        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure(".", font=BASE_FONT)
        style.configure("TCheckbutton", font=BASE_FONT)

        # ------------------------- 입력 상태 -------------------------
        self.diag_code_var = tk.StringVar()
        self.diag_name_var = tk.StringVar()
        self.therapist_var = tk.StringVar()
        self.count_var = tk.StringVar(value="1")
        self.region_var = tk.StringVar()
        self.date_selected: datetime.date = datetime.date.today()

        # 미리보기 상태: "auto"(자동 생성) / "editing"(직접 수정 중) / "manual"(수정 내용 유지)
        self.preview_mode = "auto"
        self._suppress_uppercase = False  # 대문자 변환 재귀 방지
        self._marked_missing: List[str] = []  # 현재 강조 표시된 누락 항목

        self.build_ui()
        self._bind_shortcuts()
        self._select_initial_therapist()
        self.refresh_from_settings()
        self.update_preview()

        # 입력 변경 감지 → 미리보기 갱신
        self.diag_code_var.trace_add("write", self._on_code_changed)
        for var in (self.diag_name_var, self.therapist_var, self.count_var, self.region_var):
            var.trace_add("write", lambda *_: self.update_preview())

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(300, self.first_run_check)

    # ==================================================================
    # UI 구성
    # ==================================================================
    def build_ui(self) -> None:
        # 치료사 미등록 안내 배너
        self.banner = tk.Label(
            self, text="⚠ 설정에서 치료사를 먼저 등록해주세요.",
            font=BOLD_FONT, bg="#fff3cd", fg="#856404", pady=6,
        )
        # (표시는 refresh_from_settings에서 결정)

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        left_scroll = ScrollableFrame(paned)
        right = ttk.Frame(paned)
        paned.add(left_scroll, weight=1)
        paned.add(right, weight=1)
        left = left_scroll.inner

        digits_only = (self.register(lambda s: s.isdigit() or s == ""), "%P")

        # 필수 항목 강조를 위한 섹션 제목 라벨 저장소: 라벨명 → (위젯, 원래 텍스트)
        self._field_titles: Dict[str, tk.Widget] = {}

        def section(parent, title: str, field_label: Optional[str] = None) -> ttk.Frame:
            """제목 라벨을 따로 가진 LabelFrame 생성 (누락 강조용)."""
            lbl = ttk.Label(parent, text=title, font=TITLE_FONT, foreground=ACCENT)
            frame = ttk.LabelFrame(parent, labelwidget=lbl, padding=10)
            frame.pack(fill="x", pady=(0, 10))
            if field_label:
                self._field_titles[field_label] = lbl
                lbl._normal_text = title  # type: ignore[attr-defined]
            return frame

        # ① 진단명 ------------------------------------------------------
        f_diag = section(left, "① 진단명", C.LABEL_DIAGNOSIS)
        code_row = ttk.Frame(f_diag)
        code_row.pack(fill="x")
        ttk.Label(code_row, text="진단코드:").pack(side="left")
        ttk.Entry(code_row, textvariable=self.diag_code_var, width=9, font=BASE_FONT).pack(side="left", padx=(4, 10))
        ttk.Label(code_row, text="진단명:").pack(side="left")
        ttk.Entry(code_row, textvariable=self.diag_name_var, font=BASE_FONT).pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )

        recent_row = ttk.Frame(f_diag)
        recent_row.pack(fill="x", pady=(6, 0))
        ttk.Label(recent_row, text="최근 사용:").pack(side="left")
        self.recent_diag_combo = ttk.Combobox(recent_row, state="readonly", font=BASE_FONT)
        self.recent_diag_combo.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.recent_diag_combo.bind("<<ComboboxSelected>>", self._on_recent_diag_selected)

        search_row = ttk.Frame(f_diag)
        search_row.pack(fill="x", pady=(6, 0))
        ttk.Label(search_row, text="🔍 저장 목록 검색:").pack(side="left")
        self.diag_search_var = tk.StringVar()
        ttk.Entry(search_row, textvariable=self.diag_search_var, font=BASE_FONT).pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )
        self.diag_search_var.trace_add("write", lambda *_: self.refresh_diag_list())

        list_row = ttk.Frame(f_diag)
        list_row.pack(fill="x", pady=(4, 0))
        self.diag_list = tk.Listbox(list_row, height=5, font=BASE_FONT, activestyle="none")
        diag_sb = ttk.Scrollbar(list_row, orient="vertical", command=self.diag_list.yview)
        self.diag_list.configure(yscrollcommand=diag_sb.set)
        self.diag_list.pack(side="left", fill="both", expand=True)
        diag_sb.pack(side="right", fill="y")
        self.diag_list.bind("<<ListboxSelect>>", self._on_diag_list_selected)
        self._diag_view: List[Dict] = []
        ttk.Label(
            f_diag, text="목록 클릭 시 자동 입력 · 추가/삭제/즐겨찾기/CSV 관리는 [설정]",
            foreground="#888888",
        ).pack(anchor="w", pady=(4, 0))

        # ② 치료목적 ----------------------------------------------------
        f_purpose = section(left, "② 치료목적 (클릭하여 다중 선택)", C.LABEL_PURPOSE)
        self.purpose_chips = ChipGroup(
            f_purpose, self.settings["purposes"], per_row=2, on_change=self.update_preview
        )
        self.purpose_chips.pack(fill="x")

        # ③ 시행자 ------------------------------------------------------
        f_ther = section(left, "③ 시행자 (물리치료사)", C.LABEL_THERAPIST)
        row = ttk.Frame(f_ther)
        row.pack(fill="x")
        ttk.Label(row, text="치료사 선택:").pack(side="left")
        self.therapist_combo = ttk.Combobox(
            row, textvariable=self.therapist_var, state="readonly", font=BASE_FONT
        )
        self.therapist_combo.pack(side="left", fill="x", expand=True, padx=(4, 6))
        self.therapist_combo.bind("<<ComboboxSelected>>", self._on_therapist_selected)
        ttk.Button(row, text="＋ 등록", command=self.quick_add_therapist).pack(side="left")
        ttk.Label(
            f_ther, text="이름 뒤 '물리치료사'는 자동으로 붙습니다 · 관리는 [설정]",
            foreground="#888888",
        ).pack(anchor="w", pady=(4, 0))

        # ④ 시행일시 ----------------------------------------------------
        f_date = section(left, "④ 시행일시 (달력에서 날짜 클릭)", C.LABEL_DATE)
        self.calendar = CalendarWidget(f_date, on_select=self.on_date_selected)
        self.calendar.pack()

        # ⑤ 시행횟수 / 시행부위 / 치료시간 ------------------------------
        f_misc = section(left, "⑤ 시행횟수 · 시행부위 · 치료시간")
        row1 = ttk.Frame(f_misc)
        row1.pack(fill="x", pady=2)
        lbl_count = ttk.Label(row1, text="시행횟수:", width=10)
        lbl_count.pack(side="left")
        self._field_titles[C.LABEL_COUNT] = lbl_count
        lbl_count._normal_text = "시행횟수:"  # type: ignore[attr-defined]
        ttk.Spinbox(
            row1, from_=1, to=999, textvariable=self.count_var, width=6, justify="center",
            validate="key", validatecommand=digits_only, font=BASE_FONT,
        ).pack(side="left")
        ttk.Label(row1, text="회차 ('회차'는 자동으로 붙습니다)").pack(side="left", padx=(4, 0))

        row2 = ttk.Frame(f_misc)
        row2.pack(fill="x", pady=2)
        lbl_region = ttk.Label(row2, text="시행부위:", width=10)
        lbl_region.pack(side="left")
        self._field_titles[C.LABEL_REGION] = lbl_region
        lbl_region._normal_text = "시행부위:"  # type: ignore[attr-defined]
        self.region_combo = ttk.Combobox(row2, textvariable=self.region_var, font=BASE_FONT)
        self.region_combo.pack(side="left", fill="x", expand=True)
        ttk.Label(row2, text="(직접 입력 또는 ▼ 선택)").pack(side="left", padx=(4, 0))

        row3 = ttk.Frame(f_misc)
        row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="치료시간:", width=10).pack(side="left")
        self.minutes_lbl = ttk.Label(row3, font=BOLD_FONT)
        self.minutes_lbl.pack(side="left")
        ttk.Label(row3, text="(변경은 [설정] > 데이터 탭)").pack(side="left", padx=(6, 0))

        # ⑥ 시행기법 ----------------------------------------------------
        f_tech = section(left, "⑥ 시행기법 (클릭하여 다중 선택)", C.LABEL_TECHNIQUE)
        self.tech_chips = ChipGroup(
            f_tech, self.settings["techniques"], per_row=2, on_change=self.update_preview
        )
        self.tech_chips.pack(fill="x")

        # -------- 오른쪽: 미리보기 + 버튼 --------
        right_inner = ttk.Frame(right, padding=12)
        right_inner.pack(fill="both", expand=True)

        head_row = ttk.Frame(right_inner)
        head_row.pack(fill="x")
        ttk.Label(head_row, text="진료 기록 미리보기", font=TITLE_FONT, foreground=ACCENT).pack(side="left")
        self.edit_btn = ttk.Button(head_row, text="✏ 직접 수정", command=self.toggle_edit_mode)
        self.edit_btn.pack(side="right")
        self.regen_btn = ttk.Button(head_row, text="🔄 자동 생성 내용으로 갱신", command=self.regenerate_preview)
        # (regen_btn은 직접 수정 상태에서만 표시)

        # 창이 낮아도 버튼/상태 표시가 잘리지 않도록 아래쪽부터 먼저 배치
        bottom = ttk.Frame(right_inner)
        bottom.pack(side="bottom", fill="x", pady=(6, 0))
        self.status_lbl = ttk.Label(right_inner, text="", font=BOLD_FONT)
        self.status_lbl.pack(side="bottom", fill="x")

        self.output = tk.Text(
            right_inner, font=PREVIEW_FONT, wrap="word", relief="solid",
            borderwidth=1, padx=14, pady=14, spacing3=10,
        )
        self.output.pack(fill="both", expand=True, pady=(8, 6))
        self.output.configure(state="disabled")
        ttk.Button(bottom, text="초기화 (Ctrl+R)", command=self.reset_inputs).pack(side="left")
        ttk.Button(bottom, text="⚙ 설정", command=self.open_settings).pack(side="left", padx=(6, 0))
        tk.Button(
            bottom, text="📋 전체 복사 (Ctrl+Shift+C)", font=("맑은 고딕", 13, "bold"),
            bg=ACCENT, fg="white", activebackground="#1d4fc4", activeforeground="white",
            relief="flat", padx=20, pady=8, cursor="hand2", command=self.copy_output,
        ).pack(side="right")

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-Shift-C>", lambda _e: self.copy_output())
        self.bind_all("<Control-Shift-c>", lambda _e: self.copy_output())
        self.bind_all("<Control-r>", lambda _e: self.reset_inputs())
        self.bind_all("<Control-R>", lambda _e: self.reset_inputs())

    # ==================================================================
    # 설정 연동 / 갱신
    # ==================================================================
    def refresh_from_settings(self) -> None:
        """설정(치료사/목적/기법/진단/부위/시간)이 바뀐 뒤 화면을 갱신한다."""
        therapists = self.settings["therapists"]
        self.therapist_combo.configure(values=therapists)
        if self.therapist_var.get() not in therapists:
            self.therapist_var.set("")
        if not self.therapist_var.get():
            self._select_initial_therapist()
        if len(therapists) == 1:
            self.therapist_var.set(therapists[0])  # 한 명뿐이면 자동 선택

        self.purpose_chips.set_items(self.settings["purposes"])
        self.tech_chips.set_items(self.settings["techniques"])
        self.minutes_lbl.config(text=f"{self.settings['treatment_minutes']}분")

        # 시행 부위 드롭다운: 즐겨찾기 + 최근 사용 (중복 제거)
        regions = list(self.settings["region_favorites"])
        for r in self.settings["recent_regions"]:
            if r not in regions:
                regions.append(r)
        self.region_combo.configure(values=regions)

        # 최근 사용 진단명
        self._recent_diags = list(self.settings["recent_diagnoses"])
        self.recent_diag_combo.configure(
            values=[f"{d.get('code', '')} {d.get('name', '')}".strip() for d in self._recent_diags]
        )

        self.refresh_diag_list()

        # 치료사 미등록 배너
        if therapists:
            self.banner.pack_forget()
        else:
            self.banner.pack(fill="x", before=self.winfo_children()[1] if len(self.winfo_children()) > 1 else None)

        self.update_preview()

    def _select_initial_therapist(self) -> None:
        """시작 시 치료사 선택: 마지막 선택 > 기본 치료사 > 한 명뿐이면 그 치료사."""
        therapists = self.settings["therapists"]
        for candidate in (self.settings.get("last_therapist"), self.settings.get("default_therapist")):
            if candidate and candidate in therapists:
                self.therapist_var.set(candidate)
                return
        if len(therapists) == 1:
            self.therapist_var.set(therapists[0])

    def save_settings(self) -> None:
        if not storage.save_settings(self.settings):
            self.show_status("⚠ 설정 저장에 실패했습니다. 디스크 상태를 확인해주세요.", MISSING_COLOR)

    def on_settings_changed(self) -> None:
        """설정 다이얼로그에서 변경이 있을 때마다 호출."""
        self.save_settings()
        self.refresh_from_settings()

    def open_settings(self) -> None:
        SettingsDialog(self, self.settings, on_change=self.on_settings_changed)

    def first_run_check(self) -> None:
        """첫 실행(치료사 미등록) 시 등록 창을 자동으로 띄운다."""
        if not self.settings["therapists"]:
            self.quick_add_therapist(first_run=True)

    # ==================================================================
    # 진단명
    # ==================================================================
    def _on_code_changed(self, *_args) -> None:
        """진단코드 소문자 → 대문자 자동 변환."""
        if self._suppress_uppercase:
            return
        value = self.diag_code_var.get()
        upper = value.upper()
        if value != upper:
            self._suppress_uppercase = True
            self.diag_code_var.set(upper)
            self._suppress_uppercase = False
        self.update_preview()

    def refresh_diag_list(self) -> None:
        query = self.diag_search_var.get().strip().lower()
        self.diag_list.delete(0, "end")
        self._diag_view = []
        diagnoses = self.settings["diagnoses"]
        ordered = [d for d in diagnoses if d.get("favorite")] + [d for d in diagnoses if not d.get("favorite")]
        for d in ordered:
            text = f"{d.get('code', '')} {d.get('name', '')}".strip()
            if query and query not in text.lower():
                continue
            star = "★ " if d.get("favorite") else "    "
            self.diag_list.insert("end", star + text)
            self._diag_view.append(d)

    def _on_diag_list_selected(self, _e=None) -> None:
        sel = self.diag_list.curselection()
        if not sel:
            return
        d = self._diag_view[sel[0]]
        self.diag_code_var.set(d.get("code", ""))
        self.diag_name_var.set(d.get("name", ""))

    def _on_recent_diag_selected(self, _e=None) -> None:
        idx = self.recent_diag_combo.current()
        if idx < 0 or idx >= len(self._recent_diags):
            return
        d = self._recent_diags[idx]
        self.diag_code_var.set(d.get("code", ""))
        self.diag_name_var.set(d.get("name", ""))

    # ==================================================================
    # 치료사
    # ==================================================================
    def quick_add_therapist(self, first_run: bool = False) -> None:
        prompt = "치료사 이름을 입력하세요.\n(출력 시 '물리치료사'가 자동으로 붙습니다)"
        if first_run:
            prompt = "처음 실행하셨네요!\n" + prompt
        name = simpledialog.askstring("치료사 등록", prompt, parent=self)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name not in self.settings["therapists"]:
            self.settings["therapists"].append(name)
        if not self.settings.get("default_therapist"):
            self.settings["default_therapist"] = name
        self.therapist_var.set(name)
        self.settings["last_therapist"] = name
        self.save_settings()
        self.refresh_from_settings()

    def _on_therapist_selected(self, _e=None) -> None:
        self.settings["last_therapist"] = self.therapist_var.get()
        self.save_settings()
        self.update_preview()

    # ==================================================================
    # 날짜
    # ==================================================================
    def on_date_selected(self, date: datetime.date) -> None:
        self.date_selected = date
        self.update_preview()

    # ==================================================================
    # 진료 기록 생성 / 미리보기
    # ==================================================================
    def current_record(self) -> R.TherapyRecord:
        return R.TherapyRecord(
            diagnosis_code=self.diag_code_var.get(),
            diagnosis_name=self.diag_name_var.get(),
            purposes=self.purpose_chips.get_selected(),
            therapist=self.therapist_var.get(),
            date=self.date_selected,
            count=self.count_var.get(),
            region=self.region_var.get(),
            techniques=self.tech_chips.get_selected(),
            minutes=int(self.settings.get("treatment_minutes", C.DEFAULT_TREATMENT_MINUTES)),
        )

    def update_preview(self) -> None:
        """왼쪽 입력이 바뀔 때 호출. 자동 모드에서만 미리보기를 덮어쓴다."""
        self._refresh_missing_marks()
        if self.preview_mode != "auto":
            # 직접 수정 중에는 덮어쓰지 않고 안내만 표시
            self.show_status(
                "왼쪽 항목이 변경되었습니다. [자동 생성 내용으로 갱신]을 누르면 반영됩니다.", "#856404", sticky=True
            )
            return
        text = self.current_record().build_text()
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    # ------------------------------------------------------------------
    # 직접 수정 모드
    # ------------------------------------------------------------------
    def toggle_edit_mode(self) -> None:
        if self.preview_mode == "auto" or self.preview_mode == "manual":
            if self.preview_mode == "auto":
                pass  # 현재 자동 생성 내용에서 편집 시작
            self.preview_mode = "editing"
            self.output.configure(state="normal")
            self.output.focus_set()
            self.edit_btn.config(text="✔ 편집 종료")
            self.regen_btn.pack(side="right", padx=(0, 6))
            self.show_status("직접 수정 중입니다. 편집이 끝나면 [편집 종료]를 누르세요.", "#856404", sticky=True)
        else:  # editing → 편집 종료 (수정 내용 유지, 읽기 전용 전환)
            self.preview_mode = "manual"
            self.output.configure(state="disabled")
            self.edit_btn.config(text="✏ 직접 수정")
            self.show_status("직접 수정한 내용이 유지됩니다. (자동 갱신 일시 중지)", "#856404", sticky=True)

    def regenerate_preview(self) -> None:
        """직접 수정 내용을 버리고 왼쪽 입력값으로 다시 생성한다."""
        if self.preview_mode != "auto":
            if not messagebox.askyesno(
                "갱신 확인", "직접 수정한 내용이 사라지고 왼쪽 입력값으로 다시 생성됩니다.\n계속할까요?"
            ):
                return
        self.preview_mode = "auto"
        self.edit_btn.config(text="✏ 직접 수정")
        self.regen_btn.pack_forget()
        self.output.configure(state="disabled")
        self.clear_status()
        self.update_preview()

    # ==================================================================
    # 필수 항목 검사 / 강조 표시
    # ==================================================================
    def _mark_missing(self, missing: List[str]) -> None:
        self._marked_missing = list(missing)
        for label, widget in self._field_titles.items():
            normal = getattr(widget, "_normal_text", str(widget.cget("text")))
            if label in missing:
                widget.configure(text=f"{normal} ⚠", foreground=MISSING_COLOR)
            else:
                widget.configure(text=normal, foreground=ACCENT if normal.startswith(("①", "②", "③", "④", "⑥")) else "")

    def _refresh_missing_marks(self) -> None:
        """입력이 바뀔 때, 강조돼 있던 항목 중 채워진 것의 표시를 해제한다."""
        if not self._marked_missing:
            return
        still_missing = set(self.current_record().missing_fields())
        remaining = [m for m in self._marked_missing if m in still_missing]
        self._mark_missing(remaining)
        if not remaining:
            self.clear_status()

    # ==================================================================
    # 복사 / 초기화
    # ==================================================================
    def copy_output(self) -> None:
        try:
            if self.preview_mode == "auto":
                rec = self.current_record()
                missing = rec.missing_fields()
                if missing:
                    self._mark_missing(missing)
                    self.show_status(
                        f"필수 항목을 확인해주세요: {', '.join(missing)}", MISSING_COLOR, sticky=True
                    )
                    return
                text = rec.build_text()
                self._remember_recents(rec)
            else:
                text = self.output.get("1.0", "end-1c")
                if not text.strip():
                    self.show_status("복사할 내용이 없습니다.", MISSING_COLOR)
                    return
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()  # 클립보드 내용 유지
            self.show_status("✔ 진료기록이 클립보드에 복사되었습니다.", OK_COLOR)
        except Exception:
            self.show_status("⚠ 복사 중 문제가 발생했습니다. 다시 시도해주세요.", MISSING_COLOR)

    def _remember_recents(self, rec: R.TherapyRecord) -> None:
        """복사 성공 시 최근 사용 진단명/시행 부위를 저장한다."""
        code = R.normalize_code(rec.diagnosis_code)
        name = rec.diagnosis_name.strip()
        if code or name:
            self.settings["recent_diagnoses"] = storage.push_recent(
                self.settings["recent_diagnoses"], {"code": code, "name": name}
            )
        region = rec.region.strip()
        if region:
            self.settings["recent_regions"] = storage.push_recent(
                self.settings["recent_regions"], region
            )
        self.save_settings()
        self.refresh_from_settings()

    def reset_inputs(self) -> None:
        """현재 환자 입력만 초기화한다. 치료사/설정/저장 목록은 유지."""
        if not messagebox.askyesno("초기화 확인", "현재 입력한 내용을 초기화할까요?\n(치료사·설정·저장 목록은 유지됩니다)"):
            return
        self.diag_code_var.set("")
        self.diag_name_var.set("")
        self.diag_search_var.set("")
        self.count_var.set("1")
        self.region_var.set("")
        self.purpose_chips.clear_selection()
        self.tech_chips.clear_selection()
        self.date_selected = datetime.date.today()
        self.calendar.set_date(self.date_selected)

        # 시행자는 기본 치료사로
        therapists = self.settings["therapists"]
        default = self.settings.get("default_therapist")
        if default and default in therapists:
            self.therapist_var.set(default)
        elif len(therapists) == 1:
            self.therapist_var.set(therapists[0])
        else:
            self.therapist_var.set("")

        # 직접 수정 내용도 초기화하고 자동 모드로 복귀
        self.preview_mode = "auto"
        self.edit_btn.config(text="✏ 직접 수정")
        self.regen_btn.pack_forget()
        self.output.configure(state="disabled")
        self._mark_missing([])
        self.clear_status()
        self.update_preview()

    # ==================================================================
    # 상태 메시지
    # ==================================================================
    def show_status(self, text: str, color: str, sticky: bool = False) -> None:
        self.status_lbl.config(text=text, foreground=color)
        if hasattr(self, "_status_after") and self._status_after:
            self.after_cancel(self._status_after)
            self._status_after = None
        if not sticky:
            self._status_after = self.after(2500, self.clear_status)

    def clear_status(self) -> None:
        self.status_lbl.config(text="")
        self._status_after = None

    # ==================================================================
    # 종료 처리
    # ==================================================================
    def _restore_geometry(self) -> None:
        geometry = self.settings.get("window_geometry", "")
        if self.settings.get("remember_geometry", True) and geometry:
            try:
                self.geometry(geometry)
                return
            except tk.TclError:
                pass
        try:
            self.state("zoomed")  # Windows: 최대화로 시작
        except tk.TclError:
            self.geometry("1280x800")

    def on_close(self) -> None:
        try:
            if self.settings.get("remember_geometry", True) and self.state() == "normal":
                self.settings["window_geometry"] = self.geometry()
            self.settings["last_therapist"] = self.therapist_var.get()
            storage.save_settings(self.settings)
        except Exception:
            pass
        self.destroy()
