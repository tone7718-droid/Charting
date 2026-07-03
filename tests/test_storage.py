# -*- coding: utf-8 -*-
"""설정 저장 / CSV / 백업·복원 로직 단위 테스트."""

import json
import os
import tempfile
import unittest

from therapy_chart import storage


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

    def test_merge_fills_missing_keys(self):
        merged = storage.merge_with_defaults({"therapists": ["홍길동"]})
        self.assertEqual(merged["therapists"], ["홍길동"])
        self.assertIn("recent_regions", merged)

    def test_corrupt_file_returns_defaults(self):
        with open(storage.settings_file(), "w", encoding="utf-8") as f:
            f.write("{{{ not json")
        settings = storage.load_settings()
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


class TestDiagnosesCsv(StorageTestCase):
    def _write_csv(self, content: str, encoding: str = "utf-8") -> str:
        path = os.path.join(self.tmp.name, "diag.csv")
        with open(path, "w", encoding=encoding, newline="") as f:
            f.write(content)
        return path

    def test_import_basic(self):
        path = self._write_csv("진단코드,진단명\nm751,회전근개증후군\nM545,요통\n")
        items, skipped = storage.import_diagnoses_csv(path)
        self.assertEqual(skipped, 0)
        self.assertEqual(items[0]["code"], "M751")  # 대문자 변환
        self.assertEqual(items[0]["name"], "회전근개증후군")
        self.assertEqual(len(items), 2)

    def test_import_excel_bom(self):
        path = self._write_csv("code,name\nM751,회전근개증후군\n", encoding="utf-8-sig")
        items, _ = storage.import_diagnoses_csv(path)
        self.assertEqual(items[0]["code"], "M751")

    def test_import_invalid_file_raises_without_crash(self):
        path = self._write_csv("\n\n\n")
        with self.assertRaises(ValueError):
            storage.import_diagnoses_csv(path)

    def test_export_then_import_roundtrip(self):
        diagnoses = [{"code": "M751", "name": "회전근개증후군", "favorite": True}]
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
        for key in data.keys():
            for word in forbidden:
                self.assertNotIn(word, key)


if __name__ == "__main__":
    unittest.main()
