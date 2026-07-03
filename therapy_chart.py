# -*- coding: utf-8 -*-
"""
도수치료 진료 기록지 입력 도우미
- 2026.07.01 시행 도수치료 관리급여 기준 진료 기록 항목 작성 보조 프로그램
- 왼쪽: 항목 선택/입력  /  오른쪽: 양식에 맞춘 문장 자동 생성 + 복사 버튼
"""

import calendar
import datetime
import json
import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

APP_TITLE = "도수치료 진료 기록지 입력 도우미"

# ---------------------------------------------------------------------------
# 기본 진단명 목록 (KCD 기준, 도수치료 관련 근골격계 상병 위주)
# 프로그램(exe)과 같은 폴더에 diagnoses.txt 파일을 두면
# 그 파일의 목록(한 줄에 "코드 진단명" 형식)으로 대체됩니다.
# ---------------------------------------------------------------------------
DEFAULT_DIAGNOSES = [
    "M75.1 회전근개증후군",
    "M75.0 어깨의 유착성 관절낭염(오십견)",
    "M75.2 이두근 힘줄염",
    "M75.3 어깨의 석회성 힘줄염",
    "M75.4 어깨의 충돌증후군",
    "M75.5 어깨의 윤활낭염",
    "M54.2 경추통",
    "M54.5 요통",
    "M54.6 흉추통",
    "M54.4 좌골신경통을 동반한 요통",
    "M54.3 좌골신경통",
    "M54.1 신경뿌리병증",
    "M53.1 경완증후군",
    "M50.2 기타 경추간판전위",
    "M50.1 신경뿌리병증을 동반한 경추간판장애",
    "M51.2 기타 명시된 추간판전위",
    "M51.1 신경뿌리병증을 동반한 요추 및 기타 추간판장애",
    "M48.0 척추협착",
    "M43.1 척추전방전위증",
    "M41.9 상세불명의 척주측만증",
    "M40.2 기타 척주후만증",
    "M46.1 달리 분류되지 않은 천장골염",
    "M53.3 달리 분류되지 않은 천미골장애",
    "M62.6 근육의 긴장",
    "M79.1 근육통",
    "M79.7 섬유근통",
    "M25.5 관절통",
    "M25.6 달리 분류되지 않은 관절의 경직",
    "M17.9 상세불명의 무릎관절증",
    "M19.9 상세불명의 관절증",
    "M23.9 상세불명의 무릎의 내부이상",
    "M77.1 외측상과염(테니스엘보)",
    "M77.0 내측상과염(골프엘보)",
    "M65.9 상세불명의 윤활막염 및 힘줄윤활막염",
    "M76.6 아킬레스힘줄염",
    "M72.2 발바닥근막섬유종증(족저근막염)",
    "M24.5 관절의 구축",
    "M62.4 근육의 구축",
    "G56.0 손목터널증후군",
    "S13.4 경추의 염좌 및 긴장",
    "S23.3 흉추의 염좌 및 긴장",
    "S33.5 요추의 염좌 및 긴장",
    "S33.6 천장관절의 염좌 및 긴장",
    "S43.4 어깨관절의 염좌 및 긴장",
    "S63.5 손목의 염좌 및 긴장",
    "S83.4 무릎의 곁인대 염좌 및 긴장",
    "S93.4 발목의 염좌 및 긴장",
]

PURPOSES = ["통증 감소", "자세 교정", "관절가동범위 개선", "근력 강화", "기능 회복"]

TECHNIQUES = [
    "Myofascial Release",
    "Stabilization Exercise",
    "Stretching",
    "Joint Mobilization",
    "Soft Tissue Mobilization",
]

WEEKDAYS_KR = ["일", "월", "화", "수", "목", "금", "토"]


def app_dir() -> str:
    """exe(또는 스크립트)가 위치한 폴더."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def settings_path() -> str:
    return os.path.join(app_dir(), "therapy_chart_settings.json")


def load_settings() -> dict:
    try:
        with open(settings_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except (OSError, ValueError):
        pass
    return {}


def save_settings(data: dict) -> None:
    try:
        with open(settings_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        # 쓰기 권한이 없는 폴더에 설치된 경우 사용자 홈 폴더에 저장
        try:
            fallback = os.path.join(os.path.expanduser("~"), "therapy_chart_settings.json")
            with open(fallback, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass


def load_diagnoses() -> list:
    """같은 폴더의 diagnoses.txt가 있으면 그 목록을, 없으면 기본 목록을 사용."""
    path = os.path.join(app_dir(), "diagnoses.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            items = [line.strip() for line in f if line.strip()]
            if items:
                return items
    except OSError:
        pass
    return list(DEFAULT_DIAGNOSES)


def join_korean(items: list) -> str:
    """['통증 감소', '자세 교정'] -> '통증 감소 및 자세 교정'
    ['a', 'b', 'c'] -> 'a, b 및 c'"""
    items = [s for s in items if s]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " 및 " + items[-1]


class CalendarWidget(ttk.Frame):
    """순수 tkinter 달력 위젯. 날짜 클릭 시 on_select(date) 호출."""

    def __init__(self, master, on_select, font=("맑은 고딕", 10)):
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

    def prev_month(self):
        self.month -= 1
        if self.month == 0:
            self.month = 12
            self.year -= 1
        self.draw()

    def next_month(self):
        self.month += 1
        if self.month == 13:
            self.month = 1
            self.year += 1
        self.draw()

    def pick(self, day):
        self.selected = datetime.date(self.year, self.month, day)
        self.draw()
        self.on_select(self.selected)

    def draw(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self.title_lbl.config(text=f"{self.year}년 {self.month}월")

        for col, name in enumerate(WEEKDAYS_KR):
            color = "#d9534f" if col == 0 else ("#428bca" if col == 6 else "#333333")
            tk.Label(
                self.grid_frame, text=name, font=self.font, fg=color, width=2
            ).grid(row=0, column=col, padx=1, pady=1)

        cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
        today = datetime.date.today()
        for row, week in enumerate(cal.monthdayscalendar(self.year, self.month), start=1):
            for col, day in enumerate(week):
                if day == 0:
                    tk.Label(self.grid_frame, text="", width=2).grid(row=row, column=col)
                    continue
                date = datetime.date(self.year, self.month, day)
                is_selected = date == self.selected
                bg = "#2f6fed" if is_selected else ("#e8f0fe" if date == today else "#f0f0f0")
                fg = "white" if is_selected else ("#d9534f" if col == 0 else ("#428bca" if col == 6 else "black"))
                btn = tk.Button(
                    self.grid_frame,
                    text=str(day),
                    width=2,
                    relief="flat",
                    font=self.font,
                    bg=bg,
                    fg=fg,
                    activebackground="#2f6fed",
                    activeforeground="white",
                    command=lambda d=day: self.pick(d),
                )
                btn.grid(row=row, column=col, padx=1, pady=1)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(1000, 640)
        try:
            self.state("zoomed")  # Windows: 시작 시 전체 화면(최대화)
        except tk.TclError:
            self.geometry("1280x800")

        self.base_font = ("맑은 고딕", 11)
        self.bold_font = ("맑은 고딕", 11, "bold")
        self.title_font = ("맑은 고딕", 12, "bold")

        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure(".", font=self.base_font)
        style.configure("TCheckbutton", font=self.base_font)
        style.configure("TLabelframe.Label", font=self.title_font, foreground="#2f6fed")

        self.settings = load_settings()
        self.diagnoses = load_diagnoses()

        # ------------------------- 상태 변수 -------------------------
        self.diag_var = tk.StringVar(value="M75.1 회전근개증후군")
        self.purpose_vars = [(p, tk.BooleanVar(value=(p in ("통증 감소", "자세 교정")))) for p in PURPOSES]
        self.purpose_extra_var = tk.StringVar()
        self.therapist_var = tk.StringVar()
        self.new_therapist_var = tk.StringVar()
        self.date_selected = datetime.date.today()
        self.count_var = tk.StringVar(value="1")
        self.region_var = tk.StringVar()
        self.tech_vars = [(t, tk.BooleanVar(value=False)) for t in TECHNIQUES]
        self.tech_extra_var = tk.StringVar()
        self.minutes_var = tk.StringVar(value="30")

        therapists = self.settings.get("therapists", [])
        if therapists:
            self.therapist_var.set(therapists[0])

        self.build_ui()

        # 값이 바뀔 때마다 오른쪽 문장 갱신
        for var in (
            self.diag_var, self.purpose_extra_var, self.therapist_var,
            self.count_var, self.region_var, self.tech_extra_var, self.minutes_var,
        ):
            var.trace_add("write", lambda *_: self.update_output())
        for _, v in self.purpose_vars + self.tech_vars:
            v.trace_add("write", lambda *_: self.update_output())

        self.update_output()

    # ------------------------------------------------------------------
    # UI 구성
    # ------------------------------------------------------------------
    def build_ui(self):
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        left_outer = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left_outer, weight=1)
        paned.add(right, weight=1)

        # -------- 왼쪽: 스크롤 가능한 입력 영역 --------
        canvas = tk.Canvas(left_outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        left = ttk.Frame(canvas, padding=12)
        left_id = canvas.create_window((0, 0), window=left, anchor="nw")

        def on_frame_configure(_e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(e):
            canvas.itemconfigure(left_id, width=e.width)

        left.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        def on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        digits_only = (self.register(lambda s: s.isdigit() or s == ""), "%P")

        # 1. 진단명 ------------------------------------------------------
        f_diag = ttk.LabelFrame(left, text="① 진단명", padding=10)
        f_diag.pack(fill="x", pady=(0, 10))
        ttk.Label(f_diag, text="직접 입력하거나, 아래 목록에서 검색 후 클릭하세요.").pack(anchor="w")
        diag_entry = ttk.Entry(f_diag, textvariable=self.diag_var, font=self.base_font)
        diag_entry.pack(fill="x", pady=(4, 4))

        self.diag_search_var = tk.StringVar()
        search_row = ttk.Frame(f_diag)
        search_row.pack(fill="x")
        ttk.Label(search_row, text="🔍 검색:").pack(side="left")
        search_entry = ttk.Entry(search_row, textvariable=self.diag_search_var, font=self.base_font)
        search_entry.pack(side="left", fill="x", expand=True, padx=(4, 0))

        list_row = ttk.Frame(f_diag)
        list_row.pack(fill="x", pady=(4, 0))
        self.diag_list = tk.Listbox(list_row, height=5, font=self.base_font, activestyle="none")
        diag_sb = ttk.Scrollbar(list_row, orient="vertical", command=self.diag_list.yview)
        self.diag_list.configure(yscrollcommand=diag_sb.set)
        self.diag_list.pack(side="left", fill="both", expand=True)
        diag_sb.pack(side="right", fill="y")

        def refresh_diag_list(*_):
            q = self.diag_search_var.get().strip().lower()
            self.diag_list.delete(0, "end")
            for item in self.diagnoses:
                if q in item.lower():
                    self.diag_list.insert("end", item)

        def pick_diag(_e=None):
            sel = self.diag_list.curselection()
            if sel:
                self.diag_var.set(self.diag_list.get(sel[0]))

        self.diag_search_var.trace_add("write", refresh_diag_list)
        self.diag_list.bind("<<ListboxSelect>>", pick_diag)
        refresh_diag_list()

        # 2. 치료목적 ----------------------------------------------------
        f_purpose = ttk.LabelFrame(left, text="② 치료목적 (클릭하여 선택)", padding=10)
        f_purpose.pack(fill="x", pady=(0, 10))
        grid = ttk.Frame(f_purpose)
        grid.pack(fill="x")
        for i, (label, var) in enumerate(self.purpose_vars):
            ttk.Checkbutton(grid, text=label, variable=var).grid(
                row=i // 3, column=i % 3, sticky="w", padx=(0, 16), pady=2
            )
        extra_row = ttk.Frame(f_purpose)
        extra_row.pack(fill="x", pady=(6, 0))
        ttk.Label(extra_row, text="＋ 직접 추가:").pack(side="left")
        ttk.Entry(extra_row, textvariable=self.purpose_extra_var, font=self.base_font).pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )

        # 3. 시행자 ------------------------------------------------------
        f_ther = ttk.LabelFrame(left, text="③ 시행자 (물리치료사)", padding=10)
        f_ther.pack(fill="x", pady=(0, 10))
        row = ttk.Frame(f_ther)
        row.pack(fill="x")
        ttk.Label(row, text="치료사 선택:").pack(side="left")
        self.therapist_combo = ttk.Combobox(
            row,
            textvariable=self.therapist_var,
            values=self.settings.get("therapists", []),
            state="readonly",
            font=self.base_font,
        )
        self.therapist_combo.pack(side="left", fill="x", expand=True, padx=(4, 0))

        reg_row = ttk.Frame(f_ther)
        reg_row.pack(fill="x", pady=(6, 0))
        ttk.Label(reg_row, text="이름 등록:").pack(side="left")
        new_entry = ttk.Entry(reg_row, textvariable=self.new_therapist_var, font=self.base_font, width=14)
        new_entry.pack(side="left", padx=(4, 4))
        ttk.Button(reg_row, text="등록", command=self.add_therapist).pack(side="left")
        ttk.Button(reg_row, text="삭제", command=self.remove_therapist).pack(side="left", padx=(4, 0))
        new_entry.bind("<Return>", lambda _e: self.add_therapist())

        # 4. 시행일시 ----------------------------------------------------
        f_date = ttk.LabelFrame(left, text="④ 시행일시 (달력에서 날짜 클릭)", padding=10)
        f_date.pack(fill="x", pady=(0, 10))
        self.calendar = CalendarWidget(f_date, on_select=self.on_date_selected)
        self.calendar.pack()

        # 5. 시행횟수 / 시행부위 / 치료시간 ------------------------------
        f_misc = ttk.LabelFrame(left, text="⑤ 시행횟수 · 시행부위 · 치료시간", padding=10)
        f_misc.pack(fill="x", pady=(0, 10))

        row1 = ttk.Frame(f_misc)
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="시행횟수:", width=10).pack(side="left")
        ttk.Entry(
            row1, textvariable=self.count_var, width=6, justify="center",
            validate="key", validatecommand=digits_only, font=self.base_font,
        ).pack(side="left")
        ttk.Label(row1, text="회차").pack(side="left", padx=(4, 0))

        row2 = ttk.Frame(f_misc)
        row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="시행부위:", width=10).pack(side="left")
        ttk.Entry(row2, textvariable=self.region_var, font=self.base_font).pack(
            side="left", fill="x", expand=True
        )

        row3 = ttk.Frame(f_misc)
        row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="치료시간:", width=10).pack(side="left")
        ttk.Entry(
            row3, textvariable=self.minutes_var, width=6, justify="center",
            validate="key", validatecommand=digits_only, font=self.base_font,
        ).pack(side="left")
        ttk.Label(row3, text="분").pack(side="left", padx=(4, 0))

        # 6. 시행기법 ----------------------------------------------------
        f_tech = ttk.LabelFrame(left, text="⑥ 시행기법 (클릭하여 선택)", padding=10)
        f_tech.pack(fill="x", pady=(0, 10))
        for label, var in self.tech_vars:
            ttk.Checkbutton(f_tech, text=label, variable=var).pack(anchor="w", pady=1)
        extra_row2 = ttk.Frame(f_tech)
        extra_row2.pack(fill="x", pady=(6, 0))
        ttk.Label(extra_row2, text="＋ 직접 추가:").pack(side="left")
        ttk.Entry(extra_row2, textvariable=self.tech_extra_var, font=self.base_font).pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )

        # 7. 치료 효과 평가 (보류) --------------------------------------
        f_eval = ttk.LabelFrame(left, text="⑦ 치료 효과 평가", padding=10)
        f_eval.pack(fill="x", pady=(0, 10))
        ttk.Label(f_eval, text="(기능 준비 중 — 추후 업데이트 예정)", foreground="#888888").pack(anchor="w")

        # -------- 오른쪽: 생성된 기록 + 복사 버튼 --------
        right_inner = ttk.Frame(right, padding=12)
        right_inner.pack(fill="both", expand=True)

        ttk.Label(right_inner, text="진료 기록 미리보기", font=self.title_font, foreground="#2f6fed").pack(anchor="w")

        self.output = tk.Text(
            right_inner,
            font=("맑은 고딕", 13),
            wrap="word",
            relief="solid",
            borderwidth=1,
            padx=14,
            pady=14,
            spacing3=10,
        )
        self.output.pack(fill="both", expand=True, pady=(8, 8))
        self.output.configure(state="disabled")

        bottom = ttk.Frame(right_inner)
        bottom.pack(fill="x")
        self.copy_feedback = ttk.Label(bottom, text="", foreground="#2e8b57", font=self.bold_font)
        self.copy_feedback.pack(side="left")
        copy_btn = tk.Button(
            bottom,
            text="📋 전체 복사",
            font=("맑은 고딕", 13, "bold"),
            bg="#2f6fed",
            fg="white",
            activebackground="#1d4fc4",
            activeforeground="white",
            relief="flat",
            padx=24,
            pady=8,
            cursor="hand2",
            command=self.copy_output,
        )
        copy_btn.pack(side="right")

    # ------------------------------------------------------------------
    # 동작
    # ------------------------------------------------------------------
    def add_therapist(self):
        name = self.new_therapist_var.get().strip()
        if not name:
            return
        therapists = self.settings.get("therapists", [])
        if name not in therapists:
            therapists.append(name)
            self.settings["therapists"] = therapists
            save_settings(self.settings)
            self.therapist_combo.configure(values=therapists)
        self.therapist_var.set(name)
        self.new_therapist_var.set("")

    def remove_therapist(self):
        name = self.therapist_var.get()
        therapists = self.settings.get("therapists", [])
        if name in therapists:
            if not messagebox.askyesno("삭제 확인", f"'{name}' 치료사를 목록에서 삭제할까요?"):
                return
            therapists.remove(name)
            self.settings["therapists"] = therapists
            save_settings(self.settings)
            self.therapist_combo.configure(values=therapists)
            self.therapist_var.set(therapists[0] if therapists else "")

    def on_date_selected(self, date: datetime.date):
        self.date_selected = date
        self.update_output()

    def build_text(self) -> str:
        purposes = [label for label, var in self.purpose_vars if var.get()]
        extra_p = self.purpose_extra_var.get().strip()
        if extra_p:
            purposes += [s.strip() for s in extra_p.split(",") if s.strip()]

        techniques = [label for label, var in self.tech_vars if var.get()]
        extra_t = self.tech_extra_var.get().strip()
        if extra_t:
            techniques += [s.strip() for s in extra_t.split(",") if s.strip()]

        therapist = self.therapist_var.get().strip()
        d = self.date_selected
        count = self.count_var.get().strip()
        minutes = self.minutes_var.get().strip()

        lines = [
            f"진단명 : {self.diag_var.get().strip()}",
            f"치료목적 : {join_korean(purposes)}",
            f"시행자 : {therapist + ' 물리치료사' if therapist else ''}",
            f"시행일시 : {d.year}년 {d.month:02d}월 {d.day:02d}일",
            f"시행횟수 : {count + '회차' if count else ''}",
            f"시행부위 : {self.region_var.get().strip()}",
            f"시행기법 : {', '.join(techniques)}",
            f"치료시간 : {minutes + '분' if minutes else ''}",
        ]
        return "\n".join(lines)

    def update_output(self):
        text = self.build_text()
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def copy_output(self):
        text = self.build_text()
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()  # 클립보드 내용 유지
        self.copy_feedback.config(text="✔ 복사되었습니다. 차트에 붙여넣기(Ctrl+V) 하세요.")
        self.after(2500, lambda: self.copy_feedback.config(text=""))


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
