# -*- coding: utf-8 -*-
"""진료 기록 생성 및 필수 항목 검증 로직 단위 테스트."""

import datetime
import unittest

from therapy_chart import constants as C
from therapy_chart import record as R


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
        self.assertEqual(R.normalize_code("  m545 "), "M545")

    def test_dot_removed(self):
        self.assertEqual(R.normalize_code("m75.1"), "M751")
        self.assertEqual(R.normalize_code(" M54.5 "), "M545")

    def test_empty(self):
        self.assertEqual(R.normalize_code(""), "")
        self.assertEqual(R.normalize_code(None), "")


class TestDiagnosisDisplay(unittest.TestCase):
    def test_code_and_name(self):
        self.assertEqual(R.diagnosis_display("M751", "회전근개증후군"), "M751 회전근개증후군")

    def test_name_only(self):
        self.assertEqual(R.diagnosis_display("", "회전근개증후군"), "회전근개증후군")

    def test_code_only(self):
        self.assertEqual(R.diagnosis_display("m75.1", ""), "M751")


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
        text = sample_record(diagnosis_name="", diagnosis_code="m75.1").build_text()
        self.assertIn("진단명 : M751", text)


class TestEvaluation(unittest.TestCase):
    def test_no_eval_line_when_empty(self):
        text = sample_record().build_text()
        self.assertNotIn("치료 효과 평가", text)
        self.assertEqual(len(sample_record().build_lines()), 8)

    def test_eval_line_inserted_between_technique_and_minutes(self):
        rec = sample_record(improvement="호전", vas_before="6", vas_after="3", eval_note="ROM 개선")
        lines = rec.build_lines()
        labels = [line.split(" : ")[0] for line in lines]
        self.assertEqual(len(lines), 9)
        self.assertEqual(labels.index("치료 효과 평가"), labels.index("시행기법") + 1)
        self.assertEqual(labels.index("치료시간"), labels.index("치료 효과 평가") + 1)

    def test_eval_display_combines_only_filled_parts(self):
        self.assertEqual(
            sample_record(improvement="호전", vas_before="6", vas_after="3", eval_note="ROM 개선").eval_display(),
            "주관적 호전도 호전, VAS 6→3, ROM 개선",
        )

    def test_vas_needs_both_before_and_after(self):
        self.assertEqual(sample_record(vas_before="6").eval_display(), "")
        self.assertEqual(sample_record(vas_after="3").eval_display(), "")
        self.assertEqual(sample_record(vas_before="6", vas_after="3").eval_display(), "VAS 6→3")

    def test_vas_must_be_0_to_10_integer(self):
        self.assertTrue(R.is_valid_vas(str(C.MIN_VAS)))
        self.assertTrue(R.is_valid_vas(str(C.MAX_VAS)))
        self.assertFalse(R.is_valid_vas(str(C.MAX_VAS + 1)))
        self.assertFalse(R.is_valid_vas("-1"))
        self.assertFalse(R.is_valid_vas("3.5"))
        self.assertEqual(sample_record(vas_before="99", vas_after="3").eval_display(), "")

    def test_invalid_vas_does_not_hide_other_eval_notes(self):
        self.assertEqual(
            sample_record(vas_before="99", vas_after="3", eval_note="ROM 개선").eval_display(),
            "ROM 개선",
        )

    def test_improvement_only(self):
        self.assertEqual(sample_record(improvement="악화").eval_display(), "주관적 호전도 악화")

    def test_eval_not_required(self):
        # 치료 효과 평가가 비어 있어도 필수 항목 누락이 아니다
        self.assertEqual(sample_record().missing_fields(), [])


class TestMissingLabelsInText(unittest.TestCase):
    def test_full_text_has_no_missing(self):
        text = sample_record().build_text()
        self.assertEqual(R.missing_labels_in_text(text), [])

    def test_detects_emptied_labels(self):
        text = (
            "진단명 : \n"
            "치료목적 : 통증 감소\n"
            "시행자 : 홍길동 물리치료사\n"
            "시행일시 : 2026년 07월 03일\n"
            "시행횟수 : 3회차\n"
            "시행부위 : \n"
            "시행기법 : Myofascial Release\n"
            "치료시간 : 30분"
        )
        self.assertEqual(R.missing_labels_in_text(text), ["진단명", "시행부위"])

    def test_accepts_colon_without_spaces(self):
        text = (
            "진단명:M751 회전근개증후군\n"
            "치료목적:통증 감소\n"
            "시행자:홍길동 물리치료사\n"
            "시행일시:2026년 07월 03일\n"
            "시행횟수:3회차\n"
            "시행부위:허리\n"
            "시행기법:Myofascial Release\n"
            "치료시간:30분"
        )
        self.assertEqual(R.missing_labels_in_text(text), [])

    def test_missing_line_entirely(self):
        # 시행기법 줄을 통째로 지운 경우
        text = (
            "진단명 : M751 회전근개증후군\n"
            "치료목적 : 통증 감소\n"
            "시행자 : 홍길동 물리치료사\n"
            "시행일시 : 2026년 07월 03일\n"
            "시행횟수 : 3회차\n"
            "시행부위 : 허리\n"
            "치료시간 : 30분"
        )
        self.assertIn("시행기법", R.missing_labels_in_text(text))


class TestInvalidValuesInText(unittest.TestCase):
    def test_detects_manual_invalid_count(self):
        text = sample_record(count=str(C.MAX_TREATMENT_COUNT + 1)).build_text()
        self.assertIn("시행횟수(1~999회차)", R.invalid_values_in_text(text))

    def test_detects_manual_invalid_minutes(self):
        text = sample_record(minutes=C.MAX_TREATMENT_MINUTES + 1).build_text()
        self.assertIn("치료시간(1~600분)", R.invalid_values_in_text(text))

    def test_detects_manual_invalid_vas(self):
        text = sample_record(eval_note="").build_text() + "\n치료 효과 평가 : VAS 99→3"
        self.assertIn("VAS(0~10)", R.invalid_values_in_text(text))

    def test_valid_manual_values_have_no_invalids(self):
        self.assertEqual(R.invalid_values_in_text(sample_record(vas_before="6", vas_after="3").build_text()), [])


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

    def test_count_must_be_positive_number_in_configured_range(self):
        self.assertIn("시행횟수", sample_record(count="").missing_fields())
        self.assertIn("시행횟수", sample_record(count="0").missing_fields())
        self.assertIn("시행횟수", sample_record(count="abc").missing_fields())
        self.assertIn("시행횟수", sample_record(count=str(C.MAX_TREATMENT_COUNT + 1)).missing_fields())
        self.assertEqual(sample_record(count=str(C.MIN_TREATMENT_COUNT)).missing_fields(), [])
        self.assertEqual(sample_record(count=str(C.MAX_TREATMENT_COUNT)).missing_fields(), [])

    def test_minutes_must_be_in_configured_range(self):
        self.assertEqual(sample_record(minutes=C.MIN_TREATMENT_MINUTES).missing_fields(), [])
        self.assertEqual(sample_record(minutes=C.MAX_TREATMENT_MINUTES).missing_fields(), [])
        self.assertIn("치료시간", sample_record(minutes=0).missing_fields())
        self.assertIn("치료시간", sample_record(minutes=C.MAX_TREATMENT_MINUTES + 1).missing_fields())

    def test_missing_order_follows_output_order(self):
        rec = R.TherapyRecord()  # 전부 비어 있음 (날짜/시간은 기본값 존재)
        missing = rec.missing_fields()
        self.assertEqual(
            missing,
            ["진단명", "치료목적", "시행자", "시행횟수", "시행부위", "시행기법"],
        )


if __name__ == "__main__":
    unittest.main()
