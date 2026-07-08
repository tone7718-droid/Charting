# -*- coding: utf-8 -*-
"""UI 입력값 검증/보정 공통 함수.

Tkinter validatecommand에서 재사용할 수 있도록 UI 위젯과 분리된 순수 함수로 둔다.
"""


def is_empty_or_int_in_range(value: str, minimum: int, maximum: int) -> bool:
    """빈 문자열이거나 minimum~maximum 범위의 정수 문자열이면 True.

    입력 중간 상태인 빈 문자열은 허용하고, 실제 복사/저장 단계에서 다시 검증한다.
    """
    value = (value or "").strip()
    if value == "":
        return True
    if not value.isdigit():
        return False
    number = int(value)
    return minimum <= number <= maximum


def is_int_in_range(value: str, minimum: int, maximum: int) -> bool:
    """minimum~maximum 범위의 정수 문자열이면 True."""
    value = (value or "").strip()
    if not value.isdigit():
        return False
    number = int(value)
    return minimum <= number <= maximum


def clamp_int(value, minimum: int, maximum: int, default: int) -> int:
    """정수 변환 후 minimum~maximum 범위로 보정한다.

    변환할 수 없으면 default를 같은 범위로 보정해 반환한다.
    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))
