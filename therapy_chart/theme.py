# -*- coding: utf-8 -*-
"""공통 UI 테마.

색상과 폰트, ttk 스타일을 한 곳에서 관리해 화면 전체의 일관성을 유지한다.
"""

import tkinter as tk
from tkinter import ttk

FONT_FAMILY = "맑은 고딕"
BASE_FONT = (FONT_FAMILY, 11)
BOLD_FONT = (FONT_FAMILY, 11, "bold")
TITLE_FONT = (FONT_FAMILY, 12, "bold")
SECTION_FONT = (FONT_FAMILY, 12, "bold")
PREVIEW_FONT = (FONT_FAMILY, 13)
SMALL_FONT = (FONT_FAMILY, 10)
SMALL_BOLD_FONT = (FONT_FAMILY, 10, "bold")
BUTTON_FONT = (FONT_FAMILY, 11, "bold")
PRIMARY_BUTTON_FONT = (FONT_FAMILY, 13, "bold")

APP_BG = "#F5F7FB"
CARD_BG = "#FFFFFF"
SUBTLE_BG = "#F8FAFC"
PREVIEW_BG = "#FFFFFF"
BORDER = "#D9E2EC"
BORDER_STRONG = "#B8C4D4"
TEXT = "#1F2937"
TEXT_MUTED = "#6B7280"
TEXT_LIGHT = "#FFFFFF"

ACCENT = "#2F6FED"
ACCENT_DARK = "#1D4FC4"
ACCENT_SOFT = "#E8F0FE"
SUCCESS = "#2E8B57"
SUCCESS_SOFT = "#EAF7EF"
WARNING = "#D97706"
WARNING_SOFT = "#FFF7E6"
DANGER = "#D9534F"
DANGER_SOFT = "#FDECEC"

CHIP_OFF_BG = "#F8FAFC"
CHIP_OFF_FG = TEXT
CHIP_BORDER = "#CBD5E1"


def configure_styles(root: tk.Misc) -> None:
    """앱 전체 ttk 스타일을 설정한다."""
    try:
        root.configure(bg=APP_BG)
    except tk.TclError:
        pass

    style = ttk.Style(root)
    try:
        style.theme_use("vista")
    except tk.TclError:
        pass

    style.configure(".", font=BASE_FONT)
    style.configure("TFrame", background=APP_BG)
    style.configure("App.TFrame", background=APP_BG)
    style.configure("Card.TFrame", background=CARD_BG)
    style.configure("Subtle.TFrame", background=SUBTLE_BG)
    style.configure("TLabel", background=APP_BG, foreground=TEXT, font=BASE_FONT)
    style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT, font=BASE_FONT)
    style.configure("Muted.TLabel", background=CARD_BG, foreground=TEXT_MUTED, font=SMALL_FONT)
    style.configure("Title.TLabel", background=APP_BG, foreground=ACCENT, font=TITLE_FONT)
    style.configure("CardTitle.TLabel", background=CARD_BG, foreground=TEXT, font=TITLE_FONT)
    style.configure("Status.TLabel", background=APP_BG, foreground=TEXT_MUTED, font=BOLD_FONT)
    style.configure("TCheckbutton", background=APP_BG, font=BASE_FONT)
    style.configure("TLabelframe", background=CARD_BG, bordercolor=BORDER, relief="solid")
    style.configure("TLabelframe.Label", background=APP_BG, foreground=ACCENT, font=SECTION_FONT)
    style.configure("Card.TLabelframe", background=CARD_BG, bordercolor=BORDER, relief="solid")
    style.configure("Card.TLabelframe.Label", background=APP_BG, foreground=ACCENT, font=SECTION_FONT)
