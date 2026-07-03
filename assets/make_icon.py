# -*- coding: utf-8 -*-
"""앱 아이콘(assets/icon.ico) 생성 스크립트.

재생성: python assets/make_icon.py  (Pillow 필요)
파란 라운드 배경 + 흰 기록지(가로줄) + 초록 체크 모티프.
"""
import os

from PIL import Image, ImageDraw

ACCENT = (47, 111, 237, 255)      # 파랑
ACCENT_DK = (29, 79, 196, 255)
WHITE = (255, 255, 255, 255)
LINE = (180, 200, 240, 255)
CHECK = (46, 139, 87, 255)        # 초록

BASE = 256
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def render(size: int) -> Image.Image:
    scale = size / BASE
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def s(v):
        return int(round(v * scale))

    # 파란 라운드 배경 (하단만 살짝 어둡게 입체감)
    d.rounded_rectangle([s(8), s(8), s(248), s(248)], radius=s(48), fill=ACCENT_DK)
    d.rounded_rectangle([s(8), s(8), s(248), s(200)], radius=s(48), fill=ACCENT)

    # 흰 기록지
    d.rounded_rectangle([s(66), s(50), s(190), s(206)], radius=s(16), fill=WHITE)
    # 기록지 가로줄
    for i, y in enumerate((84, 108, 132, 156)):
        x2 = 168 if i % 2 == 0 else 150
        d.rounded_rectangle([s(84), s(y), s(x2), s(y + 8)], radius=s(4), fill=LINE)

    # 초록 체크
    d.line([(s(96), s(170)), (s(116), s(190)), (s(154), s(150))],
           fill=CHECK, width=max(2, s(14)), joint="curve")
    return img


def main() -> None:
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    render(BASE).save(out, format="ICO", sizes=ICO_SIZES)
    print("saved", out)


if __name__ == "__main__":
    main()
