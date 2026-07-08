# -*- coding: utf-8 -*-
"""UI 입력 검증 공통 함수 테스트."""

import unittest

from therapy_chart import ui_validation as V


class TestUiValidation(unittest.TestCase):
    def test_empty_or_int_in_range_allows_empty_during_typing(self):
        self.assertTrue(V.is_empty_or_int_in_range("", 1, 10))

    def test_empty_or_int_in_range_blocks_out_of_range_and_non_digits(self):
        self.assertTrue(V.is_empty_or_int_in_range("1", 1, 10))
        self.assertTrue(V.is_empty_or_int_in_range("10", 1, 10))
        self.assertFalse(V.is_empty_or_int_in_range("0", 1, 10))
        self.assertFalse(V.is_empty_or_int_in_range("11", 1, 10))
        self.assertFalse(V.is_empty_or_int_in_range("3.5", 1, 10))
        self.assertFalse(V.is_empty_or_int_in_range("-1", 1, 10))

    def test_int_in_range_requires_non_empty_integer(self):
        self.assertTrue(V.is_int_in_range("5", 1, 10))
        self.assertFalse(V.is_int_in_range("", 1, 10))
        self.assertFalse(V.is_int_in_range("abc", 1, 10))

    def test_clamp_int(self):
        self.assertEqual(V.clamp_int("5", 1, 10, 3), 5)
        self.assertEqual(V.clamp_int("999", 1, 10, 3), 10)
        self.assertEqual(V.clamp_int("-3", 1, 10, 3), 1)
        self.assertEqual(V.clamp_int("abc", 1, 10, 3), 3)


if __name__ == "__main__":
    unittest.main()
