# -*- coding: utf-8 -*-
"""설정 저장 / CSV / 백업·복원 로직 단위 테스트."""

import json
import multiprocessing
import os
import tempfile
import unittest
from unittest.mock import patch

from therapy_chart import storage


def _save_worker(appdata, ready, start, results, name):
    os.environ["APPDATA"] = appdata
    settings = storage.load_settings()
    settings["therapists"] = [name]
    ready.put(name)
    if start.wait(10):
        ok = storage.save_settings(settings)
        results.put((ok, storage.get_last_save_error(), name))


class StorageTestCase(unittest.TestCase):
    """APPDATA를 임시 폴더로 돌려 실제 사용자 데이터를 건드리지 않는다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._old_appdata = os.environ.get("APPDATA")
        os.environ["APPDATA"] = self.tmp.name

    def tearDown(self):
        if self._old_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = self._old_appdata
        self.tmp.cleanup()


class TestSettingsRoundtrip(StorageTestCase):
    def test_backup_failure_preserves_existing_file_and_cleans_temp(self):
        path = os.path.join(self.tmp.name, "backup.json")
        original = {"therapists": ["original"]}
        for failure in ("dump", "fsync", "replace"):
            with self.subTest(failure=failure):
                storage.backup_to(path, original)
                target = storage.json if failure == "dump" else storage.os
                with patch.object(target, failure, side_effect=OSError("write failed")):
                    with self.assertRaises(OSError):
                        storage.backup_to(path, {"therapists": ["new"]})
                with open(path, encoding="utf-8") as f:
                    self.assertEqual(json.load(f), original)
                self.assertEqual(os.listdir(self.tmp.name), ["backup.json"])

    def test_backup_success_replaces_existing_file(self):
        path = os.path.join(self.tmp.name, "backup.json")
        storage.backup_to(path, {"therapists": ["original"]})
        storage.backup_to(path, {"therapists": ["new"]})
        self.assertEqual(storage.restore_from(path)["therapists"], ["new"])
        self.assertEqual(os.listdir(self.tmp.name), ["backup.json"])

    def test_save_preserves_list_editor_references(self):
        settings = storage.load_settings()
        items = settings["therapists"]
        items.append("first")
        self.assertTrue(storage.save_settings(settings))
        self.assertIs(settings["therapists"], items)
        items.append("second")
        self.assertTrue(storage.save_settings(settings))
        self.assertEqual(storage.load_settings()["therapists"], ["first", "second"])

    def test_failed_save_leaves_in_memory_values_and_no_temp_file(self):
        settings = storage.load_settings()
        settings["treatment_minutes"] = 9999
        with patch.object(storage.os, "replace", side_effect=OSError("disk error")):
            self.assertFalse(storage.save_settings(settings))
        self.assertEqual(settings["treatment_minutes"], 9999)
        self.assertEqual(storage.get_last_save_error(), "io")
        self.assertFalse(any(name.endswith(".tmp") for name in os.listdir(storage.data_dir())))

    def test_replacement_is_applied_only_after_successful_save(self):
        settings = storage.load_settings()
        settings["therapists"] = ["original"]
        self.assertTrue(storage.save_settings(settings))
        with patch.object(storage.os, "replace", side_effect=OSError("disk error")):
            self.assertFalse(storage.save_settings(settings, replacement={"therapists": ["restored"]}))
        self.assertEqual(settings["therapists"], ["original"])
        self.assertEqual(storage.load_settings()["therapists"], ["original"])
        self.assertTrue(storage.save_settings(settings, replacement={"therapists": ["restored"]}))
        self.assertEqual(settings["therapists"], ["restored"])
        self.assertEqual(storage.load_settings()["therapists"], ["restored"])

    def test_content_change_detected_even_when_timestamp_is_unchanged(self):
        settings = storage.load_settings()
        self.assertTrue(storage.save_settings(settings))
        path = storage.settings_file()
        stat = os.stat(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"therapists": ["external"]}, f)
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertFalse(storage.save_settings(settings))
        self.assertEqual(storage.get_last_save_error(), "conflict")

    def test_reload_recovers_from_conflict_and_preserves_lists(self):
        stale = storage.load_settings()
        latest = storage.load_settings()
        latest["therapists"] = ["external"]
        self.assertTrue(storage.save_settings(latest))
        self.assertFalse(storage.save_settings(stale))
        items = stale["therapists"]
        storage.reload_settings(stale)
        self.assertIs(items, stale["therapists"])
        self.assertEqual(items, ["external"])
        items.append("local")
        self.assertTrue(storage.save_settings(stale))
        self.assertEqual(storage.load_settings()["therapists"], ["external", "local"])

    def test_two_processes_cannot_both_overwrite_same_revision(self):
        settings = storage.load_settings()
        self.assertTrue(storage.save_settings(settings))
        context = multiprocessing.get_context("spawn")
        ready, results = context.Queue(), context.Queue()
        start = context.Event()
        processes = [context.Process(target=_save_worker, args=(self.tmp.name, ready, start, results, name))
                     for name in ("first", "second")]
        try:
            for process in processes:
                process.start()
            ready.get(timeout=10)
            ready.get(timeout=10)
            start.set()
            outcomes = [results.get(timeout=10), results.get(timeout=10)]
            self.assertEqual(sum(ok for ok, _, _ in outcomes), 1)
            self.assertEqual([error for ok, error, _ in outcomes if not ok], ["conflict"])
            winner = next(name for ok, _, name in outcomes if ok)
            self.assertEqual(storage.load_settings()["therapists"], [winner])
        finally:
            start.set()
            for process in processes:
                if process.pid is not None:
                    process.join(timeout=10)
                    if process.is_alive():
                        process.terminate()
                        process.join()
            ready.close()
            results.close()

    def test_defaults_when_no_file(self):
        settings = storage.load_settings()
        self.assertEqual(settings["treatment_minutes"], 30)
        self.assertIn("통증 감소", settings["purposes"])
        self.assertIn("Stretching", settings["techniques"])
        self.assertTrue(any(d["code"] == "M751" for d in settings["diagnoses"]))

    def test_save_and_reload_korean(self):
        settings = storage.load_settings()
        settings["therapists"] = ["홍길동", "김영희"]
        settings["default_therapist"] = "홍길동"
        self.assertTrue(storage.save_settings(settings))
        reloaded = storage.load_settings()
        self.assertEqual(reloaded["therapists"], ["홍길동", "김영희"])
        self.assertEqual(reloaded["default_therapist"], "홍길동")

    def test_save_coerces_settings_in_memory_and_on_disk(self):
        settings = storage.load_settings()
        settings["treatment_minutes"] = 9999
        settings["diagnoses"] = [{"code": "m75.1", "name": "회전근개증후군", "favorite": False}]
        self.assertTrue(storage.save_settings(settings))
        self.assertEqual(settings["treatment_minutes"], 600)
        self.assertEqual(settings["diagnoses"][0]["code"], "M751")
        reloaded = storage.load_settings()
        self.assertEqual(reloaded["treatment_minutes"], 600)
        self.assertEqual(reloaded["diagnoses"][0]["code"], "M751")

    def test_merge_fills_missing_keys(self):
        merged = storage.merge_with_defaults({"therapists": ["홍길동"]})
        self.assertEqual(merged["therapists"], ["홍길동"])
        self.assertIn("recent_regions", merged)

    def test_corrupt_file_returns_defaults(self):
        with open(storage.settings_file(), "w", encoding="utf-8") as f:
            f.write("{{{ not json")
        settings = storage.load_settings()
        self.assertEqual(settings["treatment_minutes"], 30)
        backups = [
            name for name in os.listdir(storage.data_dir())
            if name.startswith("settings.json.corrupt-")
        ]
        self.assertEqual(len(backups), 1)
        self.assertIn(backups[0], storage.get_last_load_warning())

    def test_save_detects_concurrent_settings_change(self):
        settings = storage.load_settings()
        settings["therapists"] = ["홍길동"]
        self.assertTrue(storage.save_settings(settings))

        first_window = storage.load_settings()
        second_window = storage.load_settings()
        second_window["therapists"] = ["김영희"]
        self.assertTrue(storage.save_settings(second_window))

        first_window["therapists"] = ["박철수"]
        self.assertFalse(storage.save_settings(first_window))
        self.assertEqual(storage.get_last_save_error(), "conflict")
        self.assertEqual(storage.load_settings()["therapists"], ["김영희"])


class TestCoerceSettings(StorageTestCase):
    def test_wrong_types_fall_back_without_crashing(self):
        bad = storage.merge_with_defaults({
            "purposes": None,
            "treatment_minutes": "삼십",
            "therapists": "홍길동",       # 문자열(리스트 아님)
            "remember_geometry": "yes",  # 불리언 아님
        })
        self.assertEqual(bad["purposes"], storage.default_settings()["purposes"])
        self.assertEqual(bad["treatment_minutes"], 30)
        self.assertEqual(bad["therapists"], [])
        self.assertIs(bad["remember_geometry"], True)

    def test_minutes_clamped_to_range(self):
        self.assertEqual(storage.merge_with_defaults({"treatment_minutes": 9999})["treatment_minutes"], 600)
        self.assertEqual(storage.merge_with_defaults({"treatment_minutes": 0})["treatment_minutes"], 1)
        self.assertEqual(storage.merge_with_defaults({"treatment_minutes": 45})["treatment_minutes"], 45)
        # 숫자로 해석 불가한 값은 기본값(30)으로
        self.assertEqual(storage.merge_with_defaults({"treatment_minutes": "삼십"})["treatment_minutes"], 30)

    def test_diagnoses_filtered_to_valid_dicts(self):
        merged = storage.merge_with_defaults({
            "diagnoses": [{"code": "m7.5", "name": "x"}, "not a dict", 123, {"name": "y"}]
        })
        self.assertEqual(len(merged["diagnoses"]), 2)
        self.assertEqual(merged["diagnoses"][0]["code"], "M75")
        self.assertTrue(all(set(d) == {"code", "name", "favorite"} for d in merged["diagnoses"]))

    def test_bad_settings_file_loads_without_crash(self):
        with open(storage.settings_file(), "w", encoding="utf-8") as f:
            json.dump({"purposes": None, "treatment_minutes": "x"}, f)
        settings = storage.load_settings()  # 크래시 없이 복구되어야 함
        self.assertIsInstance(settings["purposes"], list)
        self.assertEqual(settings["treatment_minutes"], 30)


class TestPushRecent(StorageTestCase):
    def test_moves_to_front_without_duplicates(self):
        items = storage.push_recent(["허리", "경추"], "경추")
        self.assertEqual(items, ["경추", "허리"])

    def test_limit(self):
        items = list(range(20))
        result = storage.push_recent(items, 99, limit=15)
        self.assertEqual(len(result), 15)
        self.assertEqual(result[0], 99)


class TestHandEditedSettings(StorageTestCase):
    """메모장으로 고친 설정 파일이나 오래된 백업을 읽어도 데이터를 잃지 않아야 한다."""

    def test_settings_saved_with_bom_are_not_treated_as_corrupt(self):
        settings = storage.default_settings()
        settings["therapists"] = ["홍길동"]
        with open(storage.settings_file(), "w", encoding="utf-8-sig") as f:  # 메모장 'UTF-8(BOM)' 저장
            json.dump(settings, f, ensure_ascii=False)
        loaded = storage.load_settings()
        self.assertEqual(loaded["therapists"], ["홍길동"])
        self.assertEqual(storage.get_last_load_warning(), "")
        self.assertFalse([name for name in os.listdir(self.tmp.name + "/TherapyChart") if "corrupt" in name])
        loaded["therapists"].append("김철수")
        self.assertTrue(storage.save_settings(loaded))
        self.assertEqual(storage.load_settings()["therapists"], ["홍길동", "김철수"])

    def test_backup_saved_with_bom_can_be_restored(self):
        path = os.path.join(self.tmp.name, "backup.json")
        with open(path, "w", encoding="utf-8-sig") as f:
            json.dump({"therapists": ["홍길동"]}, f, ensure_ascii=False)
        self.assertEqual(storage.restore_from(path)["therapists"], ["홍길동"])

    def test_lists_are_trimmed_and_deduplicated(self):
        merged = storage.merge_with_defaults({
            "therapists": [" 홍길동 ", "홍길동", "", "  ", True, "김\n철수"],
            "purposes": ["통증 감소", "통증 감소 "],
            "recent_regions": [f"부위{i}" for i in range(40)],
        })
        self.assertEqual(merged["therapists"], ["홍길동", "김 철수"])
        self.assertEqual(merged["purposes"], ["통증 감소"])
        self.assertEqual(len(merged["recent_regions"]), storage.C.RECENT_LIMIT)

    def test_default_and_last_therapist_must_be_registered(self):
        merged = storage.merge_with_defaults({
            "therapists": ["홍길동"], "default_therapist": "퇴사자", "last_therapist": "홍길동",
        })
        self.assertEqual(merged["default_therapist"], "")
        self.assertEqual(merged["last_therapist"], "홍길동")

    def test_blank_diagnoses_are_dropped_and_names_trimmed(self):
        merged = storage.merge_with_defaults({
            "diagnoses": [{"code": "", "name": "  "}, {"code": "m54.5", "name": " 요통 "}],
            "recent_diagnoses": [{"code": "", "name": ""}, {"code": "M545", "name": "요통"}],
        })
        self.assertEqual(merged["diagnoses"], [{"code": "M545", "name": "요통", "favorite": False}])
        self.assertEqual(merged["recent_diagnoses"], [{"code": "M545", "name": "요통"}])

    def test_window_maximized_defaults_to_false_and_rejects_wrong_type(self):
        self.assertIs(storage.load_settings()["window_maximized"], False)
        self.assertIs(storage.merge_with_defaults({"window_maximized": "yes"})["window_maximized"], False)
        self.assertIs(storage.merge_with_defaults({"window_maximized": True})["window_maximized"], True)


class TestAutoResetMigration(StorageTestCase):
    """v2.1.6부터 '복사 후 자동 초기화'를 기본으로 켠다."""

    def _write(self, data):
        with open(storage.settings_file(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def test_new_install_turns_auto_reset_on(self):
        self.assertIs(storage.load_settings()["auto_reset_after_copy"], True)

    def test_old_settings_are_switched_on_once(self):
        for old in ({"version": 1, "auto_reset_after_copy": False}, {"auto_reset_after_copy": False}):
            with self.subTest(old=old):
                self._write({**old, "therapists": ["홍길동"]})
                loaded = storage.load_settings()
                self.assertIs(loaded["auto_reset_after_copy"], True)
                self.assertEqual(loaded["therapists"], ["홍길동"])
                self.assertEqual(loaded["version"], storage.SETTINGS_VERSION)

    def test_turning_it_off_after_upgrade_is_kept(self):
        self._write({"version": 1, "auto_reset_after_copy": False})
        settings = storage.load_settings()
        settings["auto_reset_after_copy"] = False  # 업데이트 후 사용자가 직접 끔
        self.assertTrue(storage.save_settings(settings))
        self.assertIs(storage.load_settings()["auto_reset_after_copy"], False)


class TestDiagnosisSearch(unittest.TestCase):
    def test_matches_code_with_or_without_dot_and_name(self):
        diagnosis = {"code": "M751", "name": "회전근개증후군"}
        for query in ("m751", "M75.1", "m75", "회전근", "M751 회전", "  "):
            with self.subTest(query=query):
                self.assertTrue(storage.diagnosis_matches(diagnosis, query))
        for query in ("M545", "요통", "7.5.2"):
            with self.subTest(query=query):
                self.assertFalse(storage.diagnosis_matches(diagnosis, query))


class TestDiagnosesCsv(StorageTestCase):
    def test_single_column_rows_are_read_as_name_unless_they_look_like_codes(self):
        path = self._write_csv("회전근개증후군\ntennis elbow\nm75.1\n,요통\n")
        items, skipped = storage.import_diagnoses_csv(path)
        self.assertEqual(skipped, 0)
        self.assertEqual([(d["code"], d["name"]) for d in items],
                         [("", "회전근개증후군"), ("", "tennis elbow"), ("M751", ""), ("", "요통")])

    def _write_csv(self, content: str, encoding: str = "utf-8") -> str:
        path = os.path.join(self.tmp.name, "diag.csv")
        with open(path, "w", encoding=encoding, newline="") as f:
            f.write(content)
        return path

    def test_import_basic(self):
        path = self._write_csv("진단코드,진단명\nm75.1,회전근개증후군\nM54.5,요통\n")
        items, skipped = storage.import_diagnoses_csv(path)
        self.assertEqual(skipped, 0)
        self.assertEqual(items[0]["code"], "M751")  # 대문자 변환 + 점 제거
        self.assertEqual(items[0]["name"], "회전근개증후군")
        self.assertEqual(items[1]["code"], "M545")
        self.assertEqual(len(items), 2)

    def test_import_excel_bom(self):
        path = self._write_csv("code,name\nM751,회전근개증후군\n", encoding="utf-8-sig")
        items, _ = storage.import_diagnoses_csv(path)
        self.assertEqual(items[0]["code"], "M751")

    def test_import_cp949(self):
        # 한글 Windows 엑셀 기본 저장 인코딩
        path = self._write_csv("진단코드,진단명\nM751,회전근개증후군\nM545,요통\n", encoding="cp949")
        items, _ = storage.import_diagnoses_csv(path)
        self.assertEqual(items[0]["name"], "회전근개증후군")
        self.assertEqual(items[1]["name"], "요통")

    def test_import_invalid_file_raises_without_crash(self):
        path = self._write_csv("\n\n\n")
        with self.assertRaises(ValueError):
            storage.import_diagnoses_csv(path)

    def test_export_then_import_roundtrip(self):
        diagnoses = [{"code": "M75.1", "name": "회전근개증후군", "favorite": True}]
        path = os.path.join(self.tmp.name, "out.csv")
        storage.export_diagnoses_csv(path, diagnoses)
        items, _ = storage.import_diagnoses_csv(path)
        self.assertEqual(items[0]["code"], "M751")
        self.assertEqual(items[0]["name"], "회전근개증후군")


class TestBackupRestore(StorageTestCase):
    def test_backup_filename_contains_date(self):
        import datetime
        name = storage.default_backup_filename(datetime.date(2026, 7, 3))
        self.assertEqual(name, "manual_therapy_helper_backup_20260703.json")

    def test_backup_and_restore(self):
        settings = storage.load_settings()
        settings["therapists"] = ["홍길동"]
        path = os.path.join(self.tmp.name, "backup.json")
        storage.backup_to(path, settings)
        restored = storage.restore_from(path)
        self.assertEqual(restored["therapists"], ["홍길동"])
        self.assertIn("purposes", restored)  # 누락 키는 기본값으로 채움

    def test_restore_rejects_wrong_file(self):
        path = os.path.join(self.tmp.name, "wrong.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"totally": "unrelated"}, f)
        with self.assertRaises(ValueError):
            storage.restore_from(path)

    def test_restore_rejects_corrupt_file(self):
        path = os.path.join(self.tmp.name, "corrupt.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("not json at all")
        with self.assertRaises(ValueError):
            storage.restore_from(path)

    def test_backup_contains_no_patient_keys(self):
        """백업 파일에 환자 개인정보성 키가 없어야 한다."""
        settings = storage.load_settings()
        path = os.path.join(self.tmp.name, "backup.json")
        storage.backup_to(path, settings)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        forbidden = {"patient", "환자", "주민등록번호", "차트번호", "연락처", "주소"}
        # 키뿐 아니라 전체 직렬화 문자열(중첩 값 포함)에도 환자정보 표지가 없어야 함
        serialized = json.dumps(data, ensure_ascii=False)
        for word in forbidden:
            self.assertNotIn(word, serialized)


if __name__ == "__main__":
    unittest.main()
