# -*- coding: utf-8 -*-
"""사용자 설정 및 등록 데이터의 로컬 저장.

- 저장 위치: Windows 표준 사용자 데이터 경로 %APPDATA%\\TherapyChart\\settings.json
  (다른 OS에서는 홈 폴더 하위 .config/TherapyChart)
- 저장 형식: JSON (UTF-8)
  데이터 규모가 작고(수백 건 이하의 문자열 목록) 백업/복원이 파일 하나로
  끝나기 때문에 SQLite 대신 JSON을 사용한다. (README 참고)
- 환자 개인정보는 어떤 항목도 저장하지 않는다.
"""

from __future__ import annotations

import copy
import csv
import datetime
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

from . import constants as C

SETTINGS_FILENAME = "settings.json"
BACKUP_BASENAME = "manual_therapy_helper_backup"


def data_dir() -> str:
    """사용자 쓰기 가능한 데이터 폴더 경로. 없으면 생성한다."""
    base = os.environ.get("APPDATA")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, C.APP_ID)
    os.makedirs(path, exist_ok=True)
    return path


def settings_file() -> str:
    return os.path.join(data_dir(), SETTINGS_FILENAME)


def default_settings() -> Dict:
    """최초 실행 시의 기본 설정값."""
    return {
        "version": 1,
        # 치료사
        "therapists": [],
        "default_therapist": "",
        "last_therapist": "",
        # 치료 목적 / 시행 기법 (사용자 정의 항목 포함 전체 목록)
        "purposes": list(C.DEFAULT_PURPOSES),
        "techniques": list(C.DEFAULT_TECHNIQUES),
        # 치료 시간(분) — 값을 설정으로 분리 (1차 버전 기본 30분)
        "treatment_minutes": C.DEFAULT_TREATMENT_MINUTES,
        # 진단명
        "diagnoses": [
            {"code": code, "name": name, "favorite": False}
            for code, name in C.DEFAULT_DIAGNOSES
        ],
        "recent_diagnoses": [],  # [{"code": ..., "name": ...}]
        # 시행 부위
        "region_favorites": [],
        "recent_regions": [],
        # 창 상태
        "remember_geometry": True,
        "window_geometry": "",
    }


def _legacy_settings_file() -> Optional[str]:
    """구버전(1.x)이 EXE 옆 폴더에 저장하던 설정 파일 경로."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "therapy_chart_settings.json")
    return path if os.path.isfile(path) else None


def merge_with_defaults(loaded: Dict) -> Dict:
    """저장된 설정에 없는 키를 기본값으로 채운다 (버전 업그레이드 대비)."""
    merged = default_settings()
    for key, value in loaded.items():
        merged[key] = value
    return merged


def load_settings() -> Dict:
    """설정을 읽는다. 파일이 없거나 손상됐으면 기본값을 반환한다."""
    try:
        with open(settings_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return merge_with_defaults(data)
    except (OSError, ValueError):
        pass

    # 신규 파일이 없으면 구버전 설정(치료사 목록)을 이어받는다.
    settings = default_settings()
    legacy = _legacy_settings_file()
    if legacy:
        try:
            with open(legacy, "r", encoding="utf-8") as f:
                old = json.load(f)
            if isinstance(old, dict) and isinstance(old.get("therapists"), list):
                settings["therapists"] = [str(t) for t in old["therapists"]]
        except (OSError, ValueError):
            pass
    return settings


def save_settings(settings: Dict) -> bool:
    """설정을 저장한다. 임시 파일에 쓴 뒤 교체하여 파일 손상을 방지한다."""
    path = settings_file()
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# 최근 사용 목록
# ---------------------------------------------------------------------------
def push_recent(items: List, value, limit: int = C.RECENT_LIMIT) -> List:
    """value를 최근 목록 맨 앞으로 이동/추가하고 최대 개수를 유지한다."""
    result = [v for v in items if v != value]
    result.insert(0, value)
    return result[:limit]


# ---------------------------------------------------------------------------
# 진단명 CSV 가져오기 / 내보내기
# 형식: 한 줄에 "진단코드,진단명" (헤더 행은 자동으로 건너뜀)
# ---------------------------------------------------------------------------
_CSV_HEADER_WORDS = {"code", "진단코드", "코드", "diagnosis_code"}


def import_diagnoses_csv(path: str) -> Tuple[List[Dict], int]:
    """CSV 파일에서 진단명 목록을 읽는다.

    반환: (읽은 진단 목록, 건너뛴 줄 수)
    파일 오류 시 OSError/ValueError를 발생시킨다 (호출 측에서 안내 처리).
    """
    items: List[Dict] = []
    skipped = 0
    # utf-8-sig: 엑셀에서 저장한 CSV의 BOM 처리
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            cells = [c.strip() for c in row]
            if not any(cells):
                continue
            if cells[0].lower() in _CSV_HEADER_WORDS:
                continue  # 헤더 행
            code = cells[0].upper() if cells else ""
            name = cells[1] if len(cells) > 1 else ""
            if not (code or name):
                skipped += 1
                continue
            items.append({"code": code, "name": name, "favorite": False})
    if not items:
        raise ValueError("가져올 수 있는 진단명이 없습니다.")
    return items, skipped


def export_diagnoses_csv(path: str, diagnoses: List[Dict]) -> None:
    """진단명 목록을 CSV로 저장한다. 엑셀 호환을 위해 utf-8-sig 사용."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["진단코드", "진단명"])
        for d in diagnoses:
            writer.writerow([d.get("code", ""), d.get("name", "")])


# ---------------------------------------------------------------------------
# 백업 / 복원
# ---------------------------------------------------------------------------
def default_backup_filename(today: Optional[datetime.date] = None) -> str:
    d = today or datetime.date.today()
    return f"{BACKUP_BASENAME}_{d.strftime('%Y%m%d')}.json"


def backup_to(path: str, settings: Dict) -> None:
    """설정 전체를 백업 파일로 내보낸다. (환자 정보는 애초에 저장되지 않음)"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def restore_from(path: str) -> Dict:
    """백업 파일을 읽어 설정 dict를 반환한다.

    형식이 잘못된 파일이면 ValueError를 발생시킨다.
    (호출 측은 예외 발생 시 기존 데이터를 그대로 유지해야 한다.)
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("백업 파일 형식이 올바르지 않습니다.")
    known_keys = set(default_settings().keys())
    if not (known_keys & set(data.keys())):
        raise ValueError("이 프로그램의 백업 파일이 아닙니다.")
    return merge_with_defaults(copy.deepcopy(data))
