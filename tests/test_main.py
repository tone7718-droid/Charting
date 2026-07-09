# -*- coding: utf-8 -*-
"""애플리케이션 진입점 보조 로직 테스트."""

import os
import tempfile
import unittest

from therapy_chart import main
from therapy_chart import storage


class TestErrorLog(unittest.TestCase):
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

    def test_log_error_rotates_large_log_before_append(self):
        path = os.path.join(storage.data_dir(), "error.log")
        with open(path, "w", encoding="utf-8") as f:
            f.write("x" * 1_000_001)

        main._log_error("new failure")

        rotated = path + ".1"
        self.assertTrue(os.path.exists(rotated))
        self.assertLess(os.path.getsize(path), 1_000_000)
        with open(path, encoding="utf-8") as f:
            self.assertIn("new failure", f.read())


if __name__ == "__main__":
    unittest.main()
