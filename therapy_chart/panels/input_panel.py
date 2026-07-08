# -*- coding: utf-8 -*-
"""왼쪽 입력 패널 컴포넌트."""

import tkinter as tk
from tkinter import ttk, simpledialog
from typing import Dict, Optional, Callable, Any

from .. import constants as C
from ..widgets import ACCENT, CalendarWidget, ChipGroup, ScrollableFrame
from ..app_state import AppState

BASE_FONT = ("맑은 고딕", 11)
BOLD_FONT = ("맑은 고딕", 11, "bold")
TITLE_FONT = ("맑은 고딕", 12, "bold")

class InputPanel(ttk.Frame):
    def __init__(self, parent, state: AppState, status_callback: Callable[[str, str], None], **kwargs):
        super().__init__(parent, **kwargs)
        self.state = state
        self.show_status = status_callback

        # 스크롤 가능 프레임 적용
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        self.inner = self.scroll.inner

        self._field_titles: Dict[str, tk.Widget] = {}
        self._build_ui()
        self.refresh_from_settings()

        # state의 region_var 감지를 통해 즐겨찾기 버튼 갱신
        self.state.region_var.trace_add("write", lambda *_: self._refresh_region_fav_button())

    def _section(self, title: str, field_label: Optional[str] = None) -> ttk.Frame:
        """제목 라벨을 따로 가진 LabelFrame 생성 (누락 강조용)."""
        lbl = ttk.Label(self.inner, text=title, font=TITLE_FONT, foreground=ACCENT)
        frame = ttk.LabelFrame(self.inner, labelwidget=lbl, padding=10)
        frame.pack(fill="x", pady=(0, 10))
        if field_label:
            self._field_titles[field_label] = lbl
            lbl._normal_text = title  # type: ignore[attr-defined]
        return frame

    def _build_ui(self):
        digits_only = (self.register(lambda s: s.isdigit() or s == ""), "%P")

        # ① 진단명 ------------------------------------------------------
        f_diag = self._section("① 진단명", C.LABEL_DIAGNOSIS)
        code_row = ttk.Frame(f_diag)
        code_row.pack(fill="x")
        ttk.Label(code_row, text="진단코드:").pack(side="left")
        ttk.Entry(code_row, textvariable=self.state.diag_code_var, width=9, font=BASE_FONT).pack(side="left", padx=(4, 10))
        ttk.Label(code_row, text="진단명:").pack(side="left")
        ttk.Entry(code_row, textvariable=self.state.diag_name_var, font=BASE_FONT).pack(
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
        self._diag_view = []
        ttk.Label(
            f_diag, text="목록 클릭 시 자동 입력 · 추가/삭제/즐겨찾기/CSV 관리는 [설정]",
            foreground="#888888",
        ).pack(anchor="w", pady=(4, 0))

        # ② 치료목적 ----------------------------------------------------
        f_purpose = self._section("② 치료목적 (클릭하여 다중 선택)", C.LABEL_PURPOSE)
        self.purpose_chips = ChipGroup(
            f_purpose, self.state.settings["purposes"], per_row=2,
            on_change=lambda: self.state.update_purposes(self.purpose_chips.get_selected())
        )
        self.purpose_chips.pack(fill="x")

        # ③ 시행자 ------------------------------------------------------
        f_ther = self._section("③ 시행자 (물리치료사)", C.LABEL_THERAPIST)
        row = ttk.Frame(f_ther)
        row.pack(fill="x")
        ttk.Label(row, text="치료사 선택:").pack(side="left")
        self.therapist_combo = ttk.Combobox(
            row, textvariable=self.state.therapist_var, state="readonly", font=BASE_FONT
        )
        self.therapist_combo.pack(side="left", fill="x", expand=True, padx=(4, 6))
        self.therapist_combo.bind("<<ComboboxSelected>>", self._on_therapist_selected)
        ttk.Button(row, text="＋ 등록", command=self.quick_add_therapist).pack(side="left")
        ttk.Label(
            f_ther, text="이름 뒤 '물리치료사'는 자동으로 붙습니다 · 관리는 [설정]",
            foreground="#888888",
        ).pack(anchor="w", pady=(4, 0))

        # ④ 시행일시 ----------------------------------------------------
        f_date = self._section("④ 시행일시 (달력에서 날짜 클릭)", C.LABEL_DATE)
        self.calendar = CalendarWidget(f_date, on_select=self.state.update_date)
        self.calendar.pack()

        # ⑤ 시행횟수 / 시행부위 / 치료시간 ------------------------------
        f_misc = self._section("⑤ 시행횟수 · 시행부위 · 치료시간")
        row1 = ttk.Frame(f_misc)
        row1.pack(fill="x", pady=2)
        lbl_count = ttk.Label(row1, text="시행횟수:", width=10)
        lbl_count.pack(side="left")
        self._field_titles[C.LABEL_COUNT] = lbl_count
        lbl_count._normal_text = "시행횟수:"  # type: ignore[attr-defined]
        ttk.Spinbox(
            row1, from_=1, to=999, textvariable=self.state.count_var, width=6, justify="center",
            validate="key", validatecommand=digits_only, font=BASE_FONT,
        ).pack(side="left")
        ttk.Label(row1, text="회차 ('회차'는 자동으로 붙습니다)").pack(side="left", padx=(4, 0))

        row2 = ttk.Frame(f_misc)
        row2.pack(fill="x", pady=2)
        lbl_region = ttk.Label(row2, text="시행부위:", width=10)
        lbl_region.pack(side="left")
        self._field_titles[C.LABEL_REGION] = lbl_region
        lbl_region._normal_text = "시행부위:"  # type: ignore[attr-defined]
        self.region_combo = ttk.Combobox(row2, textvariable=self.state.region_var, font=BASE_FONT)
        self.region_combo.pack(side="left", fill="x", expand=True)
        self.region_fav_btn = ttk.Button(row2, text="☆ 즐겨찾기", width=10,
                                         command=self.toggle_region_favorite)
        self.region_fav_btn.pack(side="left", padx=(4, 0))
        ttk.Label(row2, text="(직접 입력 또는 ▼)").pack(side="left", padx=(4, 0))

        row3 = ttk.Frame(f_misc)
        row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="치료시간:", width=10).pack(side="left")
        self.minutes_lbl = ttk.Label(row3, font=BOLD_FONT)
        self.minutes_lbl.pack(side="left")
        ttk.Label(row3, text="(변경은 [설정] > 데이터 탭)").pack(side="left", padx=(6, 0))

        # ⑥ 시행기법 ----------------------------------------------------
        f_tech = self._section("⑥ 시행기법 (클릭하여 다중 선택)", C.LABEL_TECHNIQUE)
        self.tech_chips = ChipGroup(
            f_tech, self.state.settings["techniques"], per_row=2,
            on_change=lambda: self.state.update_techniques(self.tech_chips.get_selected())
        )
        self.tech_chips.pack(fill="x")

        # ⑦ 치료 효과 평가 (선택 입력) ----------------------------------
        f_eval = self._section("⑦ 치료 효과 평가 (선택 입력 — 입력 시에만 출력)")
        imp_row = ttk.Frame(f_eval)
        imp_row.pack(fill="x", pady=2)
        ttk.Label(imp_row, text="주관적 호전도:", width=12).pack(side="left")
        self.improvement_chips = ChipGroup(
            imp_row, C.IMPROVEMENT_OPTIONS, per_row=3, on_change=self._on_improvement_toggled
        )
        self.improvement_chips.pack(side="left")

        vas_row = ttk.Frame(f_eval)
        vas_row.pack(fill="x", pady=2)
        ttk.Label(vas_row, text="VAS:", width=12).pack(side="left")
        ttk.Label(vas_row, text="치료 전").pack(side="left")
        ttk.Spinbox(
            vas_row, from_=0, to=10, textvariable=self.state.vas_before_var, width=4, justify="center",
            validate="key", validatecommand=digits_only, font=BASE_FONT,
        ).pack(side="left", padx=(4, 10))
        ttk.Label(vas_row, text="→ 치료 후").pack(side="left")
        ttk.Spinbox(
            vas_row, from_=0, to=10, textvariable=self.state.vas_after_var, width=4, justify="center",
            validate="key", validatecommand=digits_only, font=BASE_FONT,
        ).pack(side="left", padx=(4, 6))
        ttk.Label(vas_row, text="(0~10, 둘 다 입력 시 출력)").pack(side="left")

        note_row = ttk.Frame(f_eval)
        note_row.pack(fill="x", pady=2)
        ttk.Label(note_row, text="기타 평가:", width=12).pack(side="left")
        ttk.Entry(note_row, textvariable=self.state.eval_note_var, font=BASE_FONT).pack(
            side="left", fill="x", expand=True
        )
        ttk.Label(f_eval, text="예: ROM 개선, 치료 전후 통증 유발 동작 감소", foreground="#888888").pack(
            anchor="w", pady=(2, 0)
        )

    def refresh_from_settings(self) -> None:
        """설정(치료사/목적/기법/진단/부위/시간) 갱신 시 UI 업데이트"""
        settings = self.state.settings

        therapists = settings["therapists"]
        self.therapist_combo.configure(values=therapists)
        if self.state.therapist_var.get() not in therapists:
            self.state.therapist_var.set("")

        self.purpose_chips.set_items(settings["purposes"])
        self.tech_chips.set_items(settings["techniques"])
        self.minutes_lbl.config(text=f"{settings['treatment_minutes']}분")

        # 시행 부위 드롭다운
        regions = list(settings["region_favorites"])
        for r in settings["recent_regions"]:
            if r not in regions:
                regions.append(r)
        self.region_combo.configure(values=regions)
        self._refresh_region_fav_button()

        # 최근 사용 진단명
        self._recent_diags = list(settings["recent_diagnoses"])
        self.recent_diag_combo.configure(
            values=[f"{d.get('code', '')} {d.get('name', '')}".strip() for d in self._recent_diags]
        )
        self.refresh_diag_list()

    def refresh_diag_list(self) -> None:
        query = self.diag_search_var.get().strip().lower()
        self.diag_list.delete(0, "end")
        self._diag_view = []
        diagnoses = self.state.settings["diagnoses"]
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
        self.state.diag_code_var.set(d.get("code", ""))
        self.state.diag_name_var.set(d.get("name", ""))

    def _on_recent_diag_selected(self, _e=None) -> None:
        idx = self.recent_diag_combo.current()
        if idx < 0 or idx >= len(self._recent_diags):
            return
        d = self._recent_diags[idx]
        self.state.diag_code_var.set(d.get("code", ""))
        self.state.diag_name_var.set(d.get("name", ""))

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
        if name not in self.state.settings["therapists"]:
            self.state.settings["therapists"].append(name)
        if not self.state.settings.get("default_therapist"):
            self.state.settings["default_therapist"] = name

        self.state.therapist_var.set(name)
        self.state.settings["last_therapist"] = name
        self.state.save_settings()
        self.refresh_from_settings()

    def _on_therapist_selected(self, _e=None) -> None:
        self.state.settings["last_therapist"] = self.state.therapist_var.get()
        self.state.save_settings()

    def toggle_region_favorite(self) -> None:
        region = self.state.region_var.get().strip()
        if not region:
            self.show_status("즐겨찾기로 등록할 시행부위를 먼저 입력하세요.", C.MISSING_COLOR)
            return
        favorites = self.state.settings["region_favorites"]
        if region in favorites:
            favorites.remove(region)
            self.show_status(f"'{region}' 즐겨찾기 해제", C.OK_COLOR)
        else:
            favorites.append(region)
            self.show_status(f"★ '{region}' 즐겨찾기 등록", C.OK_COLOR)
        self.state.save_settings()
        self.refresh_from_settings()

    def _refresh_region_fav_button(self) -> None:
        if not hasattr(self, "region_fav_btn"):
            return
        region = self.state.region_var.get().strip()
        if region and region in self.state.settings["region_favorites"]:
            self.region_fav_btn.config(text="★ 즐겨찾기")
        else:
            self.region_fav_btn.config(text="☆ 즐겨찾기")

    def _on_improvement_toggled(self) -> None:
        """주관적 호전도는 단일 선택 — 마지막 클릭만 유지한다."""
        selected = self.improvement_chips.get_selected()
        if len(selected) > 1:
            keep = selected[-1]
            for chip in self.improvement_chips.chips:
                chip.set_selected(chip.label == keep)
            self.improvement_chips.selection_order = [keep]
            selected = [keep]

        val = selected[0] if selected else ""
        self.state.improvement_var.set(val)

    def mark_missing_fields(self, missing_labels: list[str]):
        """부모(App)가 누락 항목을 계산하고 패널에 마킹을 요청할 때 사용합니다."""
        for label, widget in self._field_titles.items():
            normal = getattr(widget, "_normal_text", str(widget.cget("text")))
            if label in missing_labels:
                widget.configure(text=f"{normal} ⚠", foreground=C.MISSING_COLOR)
            else:
                widget.configure(text=normal, foreground=ACCENT if normal.startswith(("①", "②", "③", "④", "⑥")) else "")
