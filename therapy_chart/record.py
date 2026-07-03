# -*- coding: utf-8 -*-
"""진료 기록 문장 생성 및 필수 항목 검증 로직.

UI와 완전히 분리된 순수 로직 모듈로, 단위 테스트가 가능하다.
치료 효과 평가 항목은 2차 개발 예정 — 추가 시 이 모듈의
TherapyRecord 필드와 build_lines()에 항목을 확장하면 된다.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List

from . import constants as C

# 다중 선택 항목의 출력 구분자 (쉼표 + 공백)
ITEM_SEPARATOR = ", "

# 시행자 이름 뒤에 자동으로 붙는 직함
THERAPIST_SUFFIX = "물리치료사"


def normalize_code(code: str) -> str:
    """진단코드를 정리한다. 소문자는 자동으로 대문자로 변환한다.

    >>> normalize_code("m751")
    'M751'
    """
    return (code or "").strip().upper()


def diagnosis_display(code: str, name: str) -> str:
    """진단코드/진단명 조합 출력 문자열.

    - 둘 다 있으면: "M751 회전근개증후군"
    - 진단명만 있으면: "회전근개증후군"
    - 진단코드만 있으면: "M751"
    """
    code = normalize_code(code)
    name = (name or "").strip()
    if code and name:
        return f"{code} {name}"
    return code or name


def therapist_display(name: str) -> str:
    """치료사 이름 뒤에 '물리치료사'를 붙인다.

    이름에 이미 '물리치료사'가 포함되어 있으면 중복해서 붙이지 않는다.
    """
    name = (name or "").strip()
    if not name:
        return ""
    if THERAPIST_SUFFIX in name:
        return name
    return f"{name} {THERAPIST_SUFFIX}"


def format_date(date: datetime.date) -> str:
    """날짜를 'YYYY년 MM월 DD일' 형식으로 출력한다. 월/일은 항상 두 자리."""
    return f"{date.year}년 {date.month:02d}월 {date.day:02d}일"


def join_items(items: List[str]) -> str:
    """선택 항목들을 쉼표와 공백으로 구분해 연결한다."""
    return ITEM_SEPARATOR.join(s for s in items if s)


def missing_labels_in_text(text: str) -> List[str]:
    """직접 수정된 미리보기 텍스트에서 값이 비어 있는 필수 항목 라벨을 찾는다.

    각 줄이 '라벨 : 값' 형식이라고 가정하고, 필수 8개 라벨 중
    라벨 줄이 아예 없거나 콜론 뒤 값이 비어 있으면 누락으로 본다.
    (치료 효과 평가는 선택 항목이라 검사 대상이 아니다.)
    """
    values = {}
    for line in text.splitlines():
        if " : " in line:
            label, _, value = line.partition(" : ")
            values[label.strip()] = value.strip()
    missing = []
    for label in C.REQUIRED_FIELD_ORDER:
        if not values.get(label, "").strip():
            missing.append(label)
    return missing


@dataclass
class TherapyRecord:
    """한 건의 도수치료 진료 기록 입력값."""

    diagnosis_code: str = ""
    diagnosis_name: str = ""
    purposes: List[str] = field(default_factory=list)
    therapist: str = ""
    date: datetime.date = field(default_factory=datetime.date.today)
    count: str = ""  # 숫자 문자열 (예: "3")
    region: str = ""
    techniques: List[str] = field(default_factory=list)
    minutes: int = C.DEFAULT_TREATMENT_MINUTES
    # 치료 효과 평가 (선택 입력 — 비어 있으면 출력에서 해당 줄 생략)
    improvement: str = ""    # 주관적 호전도: 호전/유지/악화
    vas_before: str = ""     # VAS 치료 전 (숫자 문자열)
    vas_after: str = ""      # VAS 치료 후 (숫자 문자열)
    eval_note: str = ""      # ROM, 치료 전후 변화 등 자유 입력

    def eval_display(self) -> str:
        """치료 효과 평가 문구. 입력된 조각만 쉼표로 연결한다.

        예: "주관적 호전도 호전, VAS 6→3, ROM 개선"
        VAS는 치료 전·후가 모두 입력됐을 때만 표시한다.
        """
        parts: List[str] = []
        if self.improvement.strip():
            parts.append(f"주관적 호전도 {self.improvement.strip()}")
        before, after = self.vas_before.strip(), self.vas_after.strip()
        if before and after:
            parts.append(f"VAS {before}→{after}")
        if self.eval_note.strip():
            parts.append(self.eval_note.strip())
        return join_items(parts)

    # ------------------------------------------------------------------
    # 출력
    # ------------------------------------------------------------------
    def build_lines(self) -> List[str]:
        """지정된 순서·형식의 진료 기록 줄 목록을 만든다.

        각 항목은 '라벨 : 값' 형식 한 줄씩이며 빈 줄은 넣지 않는다.
        """
        count = self.count.strip()
        lines = [
            f"{C.LABEL_DIAGNOSIS} : {diagnosis_display(self.diagnosis_code, self.diagnosis_name)}",
            f"{C.LABEL_PURPOSE} : {join_items(self.purposes)}",
            f"{C.LABEL_THERAPIST} : {therapist_display(self.therapist)}",
            f"{C.LABEL_DATE} : {format_date(self.date)}",
            f"{C.LABEL_COUNT} : {count + '회차' if count else ''}",
            f"{C.LABEL_REGION} : {self.region.strip()}",
            f"{C.LABEL_TECHNIQUE} : {join_items(self.techniques)}",
        ]
        # 치료 효과 평가는 입력이 있을 때만 출력 (시행기법과 치료시간 사이)
        evaluation = self.eval_display()
        if evaluation:
            lines.append(f"{C.LABEL_EVAL} : {evaluation}")
        lines.append(f"{C.LABEL_MINUTES} : {self.minutes}분")
        return lines

    def build_text(self) -> str:
        return "\n".join(self.build_lines())

    # ------------------------------------------------------------------
    # 필수 항목 검증
    # ------------------------------------------------------------------
    def missing_fields(self) -> List[str]:
        """누락된 필수 항목의 라벨 목록을 지정된 순서로 반환한다.

        빈 목록이면 모든 필수 항목이 입력된 것이다.
        """
        missing: List[str] = []
        if not (normalize_code(self.diagnosis_code) or self.diagnosis_name.strip()):
            missing.append(C.LABEL_DIAGNOSIS)
        if not [p for p in self.purposes if p.strip()]:
            missing.append(C.LABEL_PURPOSE)
        if not self.therapist.strip():
            missing.append(C.LABEL_THERAPIST)
        if not isinstance(self.date, datetime.date):
            missing.append(C.LABEL_DATE)
        count = self.count.strip()
        if not (count.isdigit() and int(count) >= 1):
            missing.append(C.LABEL_COUNT)
        if not self.region.strip():
            missing.append(C.LABEL_REGION)
        if not [t for t in self.techniques if t.strip()]:
            missing.append(C.LABEL_TECHNIQUE)
        if not (isinstance(self.minutes, int) and self.minutes >= 1):
            missing.append(C.LABEL_MINUTES)
        return missing
