# -*- coding: utf-8 -*-
"""사용자 설정 및 등록 데이터의 로컬 저장.

- 저장 위치: Windows 표준 사용자 데이터 경로 %APPDATA%\TherapyChart\settings.json
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
import hashlib
import json
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple

from . import constants as C

SETTINGS_FILENAME = "settings.json"
BACKUP_BASENAME = "manual_therapy_helper_backup"

_last_load_warning = ""
_last_save_error = ""

class _Settings(dict):
    """읽은 파일의 내용 해시를 함께 보관하는 설정 딕셔너리."""

    def __init__(self, values: Dict, revision: Optional[str]):
        super().__init__(values)
        self.revision = revision


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


def get_last_load_warning() -> str:
    """마지막 설정 로드 중 사용자에게 안내할 경고 메시지."""
    return _last_load_warning


def get_last_save_error() -> str:
    """마지막 설정 저장 실패 사유. 예: conflict, io."""
    return _last_save_error


def _file_revision(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None


@contextmanager
def _settings_lock(path: str):
    """로드와 저장을 같은 프로세스 간 잠금으로 보호한다."""
    with open(path + ".lock", "a+b") as lock:
        if os.fstat(lock.fileno()).st_size == 0:
            lock.write(b"\0")
            lock.flush()
        if sys.platform.startswith("win"):
            import msvcrt

            def acquire():
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)

            def release():
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            def acquire():
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            def release():
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

        deadline = time.monotonic() + 3
        while True:
            try:
                acquire()
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.05)
        try:
            yield
        finally:
            release()


def _apply_settings(settings: Dict, values: Dict) -> None:
    """열린 목록 편집기가 참조하는 리스트를 유지하며 설정을 갱신한다."""
    for key in list(settings):
        if key not in values:
            del settings[key]
    for key, value in values.items():
        current = settings.get(key)
        if isinstance(current, list) and isinstance(value, list):
            current[:] = value
        else:
            settings[key] = value


def _backup_corrupt_settings(path: str) -> Optional[str]:
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"{path}.corrupt-{timestamp}"
    candidate = base
    suffix = 2
    while os.path.exists(candidate):
        candidate = f"{base}-{suffix}"
        suffix += 1
    try:
        os.replace(path, candidate)
        return candidate
    except OSError:
        return None


def _mark_settings_corrupt(path: str) -> None:
    global _last_load_warning
    backup = _backup_corrupt_settings(path)
    if backup:
        _last_load_warning = f"설정 파일이 손상되어 기본값으로 시작합니다. 백업: {backup}"
    else:
        _last_load_warning = "설정 파일이 손상되어 기본값으로 시작합니다. 백업 파일을 만들지 못했습니다."


def _normalize_code_value(code: object) -> str:
    """저장/CSV용 진단코드 정규화. 점(.) 없는 대문자 표기로 맞춘다."""
    return str(code or "").strip().upper().replace(".", "")


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
        # 치료 시간(분)
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
        # 복사 성공 시 자동으로 초기화 (다음 환자 입력 준비)
        "auto_reset_after_copy": False,
    }


def _legacy_settings_file() -> Optional[str]:
    """구버전(1.x)이 EXE 옆 폴더에 저장하던 설정 파일 경로."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "therapy_chart_settings.json")
    return path if os.path.isfile(path) else None


def _coerce_settings(merged: Dict) -> Dict:
    """각 설정 값의 타입을 검사해, 잘못된 값만 기본값으로 되돌린다.

    사용자가 설정 파일을 직접 편집했거나 손상·구버전 백업을 복원해도
    프로그램 전체가 종료되지 않고 해당 항목만 안전하게 복구된다.
    """
    defaults = default_settings()

    def as_str_list(value):
        if not isinstance(value, list):
            return None
        return [str(v) for v in value if isinstance(v, (str, int, float))]

    # 문자열 리스트 항목
    for key in ("therapists", "purposes", "techniques", "region_favorites", "recent_regions"):
        cleaned = as_str_list(merged.get(key))
        merged[key] = cleaned if cleaned is not None else list(defaults[key])

    # 문자열 항목
    for key in ("default_therapist", "last_therapist", "window_geometry"):
        if not isinstance(merged.get(key), str):
            merged[key] = defaults[key]

    # 불리언 항목
    for key in ("remember_geometry", "auto_reset_after_copy"):
        if not isinstance(merged.get(key), bool):
            merged[key] = defaults[key]

    # 치료시간: 설정 범위 정수로 강제
    minutes = merged.get("treatment_minutes")
    try:
        merged["treatment_minutes"] = max(
            C.MIN_TREATMENT_MINUTES,
            min(C.MAX_TREATMENT_MINUTES, int(minutes)),
        )
    except (TypeError, ValueError, OverflowError):
        merged["treatment_minutes"] = defaults["treatment_minutes"]

    # 진단명: {code, name, favorite} 딕셔너리 리스트
    diagnoses = merged.get("diagnoses")
    if not isinstance(diagnoses, list):
        merged["diagnoses"] = list(defaults["diagnoses"])
    else:
        cleaned = []
        seen = set()
        for d in diagnoses:
            if not isinstance(d, dict):
                continue
            item = {
                "code": _normalize_code_value(d.get("code", "")),
                "name": str(d.get("name", "")),
                "favorite": bool(d.get("favorite", False)),
            }
            key = (item["code"], item["name"])
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(item)
        merged["diagnoses"] = cleaned

    # 최근 사용 진단명: {code, name} 딕셔너리 리스트
    recent = merged.get("recent_diagnoses")
    if not isinstance(recent, list):
        merged["recent_diagnoses"] = []
    else:
        cleaned_recent = []
        seen_recent = set()
        for d in recent:
            if not isinstance(d, dict):
                continue
            item = {"code": _normalize_code_value(d.get("code", "")), "name": str(d.get("name", ""))}
            key = (item["code"], item["name"])
            if key in seen_recent:
                continue
            seen_recent.add(key)
            cleaned_recent.append(item)
        merged["recent_diagnoses"] = cleaned_recent

    return merged


def merge_with_defaults(loaded: Dict) -> Dict:
    """저장된 설정에 없는 키를 기본값으로 채우고, 값 타입을 검증한다."""
    merged = default_settings()
    for key, value in loaded.items():
        merged[key] = value
    return _coerce_settings(merged)


def load_settings() -> Dict:
    """설정을 읽는다. 파일이 없거나 손상됐으면 기본값을 반환한다."""
    global _last_load_warning
    _last_load_warning = ""
    path = settings_file()
    with _settings_lock(path):
        return _load_settings_locked(path)


def _load_settings_locked(path: str) -> Dict:
    try:
        with open(path, "rb") as f:
            content = f.read()
        data = json.loads(content.decode("utf-8"))
        if isinstance(data, dict):
            return _Settings(merge_with_defaults(data), hashlib.sha256(content).hexdigest())
        _mark_settings_corrupt(path)
        return _Settings(default_settings(), _file_revision(path))
    except ValueError:
        if os.path.exists(path):
            _mark_settings_corrupt(path)
            return _Settings(default_settings(), _file_revision(path))
    except FileNotFoundError:
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
    return _Settings(settings, _file_revision(path))


def save_settings(settings: Dict, replacement: Optional[Dict] = None) -> bool:
    """설정을 저장한다. 임시 파일에 쓴 뒤 교체하여 파일 손상을 방지한다.

    저장 직전에 타입과 범위를 한 번 더 검증하고, 호출자가 들고 있는
    settings 딕셔너리도 정리된 값으로 갱신한다. 예를 들어 설정 창에서
    치료시간에 9999를 직접 입력해도 600분으로 보정되어 저장·화면 갱신된다.
    """
    global _last_save_error
    _last_save_error = ""
    tmp = None
    try:
        path = settings_file()
        with _settings_lock(path):
            if isinstance(settings, _Settings) and settings.revision != _file_revision(path):
                _last_save_error = "conflict"
                return False
            cleaned = merge_with_defaults(settings if replacement is None else replacement)
            content = json.dumps(cleaned, ensure_ascii=False, indent=2).encode("utf-8")
            with tempfile.NamedTemporaryFile(mode="wb", dir=os.path.dirname(path),
                                             prefix="settings-", suffix=".tmp", delete=False) as f:
                tmp = f.name
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
            tmp = None
            _apply_settings(settings, cleaned)
            if isinstance(settings, _Settings):
                settings.revision = hashlib.sha256(content).hexdigest()
        return True
    except OSError:
        _last_save_error = "io"
        return False
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def reload_settings(settings: Dict) -> None:
    """디스크의 최신 설정으로 바꾸고 다음 저장의 기준도 갱신한다."""
    latest = load_settings()
    _apply_settings(settings, latest)
    if isinstance(settings, _Settings):
        settings.revision = latest.revision


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

    utf-8-sig(BOM 포함 UTF-8) → cp949 순으로 시도한다.
    파일 전체를 메모리에 올리지 않고 스트리밍으로 읽는다.

    반환: (읽은 진단 목록, 건너뛴 줄 수)
    파일 오류 시 OSError/ValueError를 발생시킨다 (호출 측에서 안내 처리).
    """
    for encoding in ("utf-8-sig", "cp949"):
        items: List[Dict] = []
        skipped = 0
        try:
            with open(path, "r", encoding=encoding, newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    cells = [c.strip() for c in row]
                    if not any(cells):
                        continue
                    if cells[0].lower() in _CSV_HEADER_WORDS:
                        continue  # 헤더 행
                    code = _normalize_code_value(cells[0] if cells else "")
                    name = cells[1] if len(cells) > 1 else ""
                    if not (code or name):
                        skipped += 1
                        continue
                    items.append({"code": code, "name": name, "favorite": False})
        except UnicodeDecodeError:
            continue

        if not items:
            raise ValueError("가져올 수 있는 진단명이 없습니다.")
        return items, skipped

    raise ValueError("파일 인코딩을 인식할 수 없습니다. UTF-8 또는 CP949(엑셀) 형식으로 저장해주세요.")


def export_diagnoses_csv(path: str, diagnoses: List[Dict]) -> None:
    """진단명 목록을 CSV로 저장한다. 엑셀 호환을 위해 utf-8-sig 사용."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["진단코드", "진단명"])
        for d in diagnoses:
            writer.writerow([_normalize_code_value(d.get("code", "")), d.get("name", "")])


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
