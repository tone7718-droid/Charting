# -*- coding: utf-8 -*-
"""진료 기록 생성 및 필수 항목 검증 로직 단위 테스트."""

import datetime
import unittest

from therapy_chart import record as R
from therapy_chart import constants as C


def sample_record(**overrides) -> R.TherapyRecord:
    """모든 필수 항목이 채워진 기본 레코드."""
    values = dict(
        diagnosis_code="M751",
        diagnosis_name="회전근개증후군",
        purposes=["통증 감소", "자세 교정", "관절가동범위 개선"],
        therapist="홍길동",
        date=datetime.date(2026, 7, 3),
        count="3",
        region="허리",
        techniques=["Myofascial Release", "Stabilization Exercise"],
        minutes=30,
    )
    values.update(overrides)
    return R.TherapyRecord(**values)


class TestNormalizeCode(unittest.TestCase):
    def test_lowercase_converted_to_uppercase(self):
        self.assertEqual(R.normalize_code("m751"), "M751")

    def test_whitespace_stripped(self):
        self.assertEqual(R.normalize_code("  m54.5 "), "M54.5")

    def test_empty(self):
        self.assertEqual(R.normalize_code(""), "")
        self.assertEqual(R.normalize_code(None), "")


class TestDiagnosisDisplay(unittest.TestCase):
    def test_code_and_name(self):
        self.assertEqual(R.diagnosis_display("M751", "회전근개증후군"), "M751 회전근개증후군")

    def test_name_only(self):
        self.assertEqual(R.diagnosis_display("", "회전근개증후군"), "회전근개증후군")

    def test_code_only(self):
        self.assertEqual(R.diagnosis_display("m751", ""), "M751")


class TestTherapistDisplay(unittest.TestCase):
    def test_suffix_added(self):
        self.assertEqual(R.therapist_display("홍길동"), "홍길동 물리치료사")

    def test_suffix_not_duplicated(self):
        self.assertEqual(R.therapist_display("김철수 물리치료사"), "김철수 물리치료사")

    def test_empty(self):
        self.assertEqual(R.therapist_display(""), "")


class TestFormatDate(unittest.TestCase):
    def test_zero_padding(self):
        self.assertEqual(R.format_date(datetime.date(2026, 7, 3)), "2026년 07월 03일")

    def test_two_digit_values(self):
        self.assertEqual(R.format_date(datetime.date(2026, 12, 25)), "2026년 12월 25일")


class TestJoinItems(unittest.TestCase):
    def test_comma_space_separator(self):
        self.assertEqual(R.join_items(["통증 감소", "자세 교정"]), "통증 감소, 자세 교정")

    def test_single_item(self):
        self.assertEqual(R.join_items(["통증 감소"]), "통증 감소")

    def test_empty(self):
        self.assertEqual(R.join_items([]), "")


class TestBuildText(unittest.TestCase):
    def test_full_output_format(self):
        expected = (
            "진단명 : M751 회전근개증후군\n"
            "치료목적 : 통증 감소, 자세 교정, 관절가동범위 개선\n"
            "시행자 : 홍길동 물리치료사\n"
            "시행일시 : 2026년 07월 03일\n"
            "시행횟수 : 3회차\n"
            "시행부위 : 허리\n"
            "시행기법 : Myofascial Release, Stabilization Exercise\n"
            "치료시간 : 30분"
        )
        self.assertEqual(sample_record().build_text(), expected)

    def test_no_blank_lines_and_order(self):
        lines = sample_record().build_lines()
        self.assertEqual(len(lines), 8)
        labels = [line.split(" : ")[0] for line in lines]
        self.assertEqual(labels, C.REQUIRED_FIELD_ORDER)

    def test_count_suffix_auto_added(self):
        self.assertIn("시행횟수 : 3회차", sample_record(count="3").build_text())

    def test_no_trailing_period(self):
        for line in sample_record().build_lines():
            self.assertFalse(line.endswith("."))

    def test_name_only_diagnosis(self):
        text = sample_record(diagnosis_code="").build_text()
        self.assertIn("진단명 : 회전근개증후군", text)

    def test_code_only_diagnosis(self):
        text = sample_record(diagnosis_name="").build_text()
        self.assertIn("진단명 : M751", text)


class TestMissingFields(unittest.TestCase):
    def test_complete_record_has_no_missing(self):
        self.assertEqual(sample_record().missing_fields(), [])

    def test_missing_region_and_technique(self):
        rec = sample_record(region="", techniques=[])
        self.assertEqual(rec.missing_fields(), ["시행부위", "시행기법"])

    def test_diagnosis_code_or_name_is_enough(self):
        self.assertEqual(sample_record(diagnosis_code="").missing_fields(), [])
        self.assertEqual(sample_record(diagnosis_name="").missing_fields(), [])
        rec = sample_record(diagnosis_code="", diagnosis_name="")
        self.assertIn("진단명", rec.missing_fields())

    def test_count_must_be_positive_number(self):
        self.assertIn("시행횟수", sample_record(count="").missing_fields())
        self.assertIn("시행횟수", sample_record(count="0").missing_fields())
        self.assertIn("시행횟수", sample_record(count="abc").missing_fields())
        self.assertEqual(sample_record(count="1").missing_fields(), [])

    def test_missing_order_follows_output_order(self):
        rec = R.TherapyRecord()  # 전부 비어 있음 (날짜/시간은 기본값 존재)
        missing = rec.missing_fields()
        self.assertEqual(
            missing,
            ["진단명", "치료목적", "시행자", "시행횟수", "시행부위", "시행기법"],
        )


if __name__ == "__main__":
    unittest.main()
