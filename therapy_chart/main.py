# -*- coding: utf-8 -*-
"""애플리케이션 실행 진입점.

예기치 못한 오류가 발생해도 기술적인 스택 트레이스 대신
이해하기 쉬운 안내문을 표시하고, 상세 내용은 로그 파일에 남긴다.
"""

from __future__ import annotations

import datetime
import os
import sys
import traceback


def _enable_dpi_awareness() -> None:
    """Windows 고해상도(배율) 디스플레이에서 창이 화면 밖으로 밀리거나
    흐릿하게 표시되지 않도록 프로세스 DPI 인식을 활성화한다.

    Tk 창을 만들기 전에 호출해야 하며, 실패해도 무시한다(비Windows 등)."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        try:
            # PROCESS_PER_MONITOR_DPI_AWARE (Windows 8.1+)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


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
        _enable_dpi_awareness()
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
