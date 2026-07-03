# -*- coding: utf-8 -*-
"""애플리케이션 실행 진입점.

예기치 못한 오류가 발생해도 기술적인 스택 트레이스 대신
이해하기 쉬운 안내문을 표시하고, 상세 내용은 로그 파일에 남긴다.
"""

from __future__ import annotations

import datetime
import os
import traceback


def _log_error(text: str) -> None:
    try:
        from . import storage
        path = os.path.join(storage.data_dir(), "error.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.datetime.now().isoformat()} =====\n{text}\n")
    except Exception:
        pass


def main() -> None:
    try:
        from .main_window import App
        app = App()
        app.mainloop()
    except Exception:
        _log_error(traceback.format_exc())
        try:
            import tkinter as tk
            from tkinter import messagebox
            from . import constants as C

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                C.APP_NAME,
                "프로그램 실행 중 문제가 발생했습니다.\n"
                "프로그램을 다시 실행해보시고, 같은 문제가 반복되면\n"
                "데이터 폴더의 error.log 파일과 함께 문의해주세요.",
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()
