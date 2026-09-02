#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vẽ tranh cổ động hai màu mừng Quốc khánh 2-9-1945.

Bố cục theo lối tranh tường quen thuộc: nền đỏ cờ, hình vàng phẳng, không
tô bóng. Bên trái là chân dung Chủ tịch Hồ Chí Minh bên chiếc micro, bên
phải là bản đồ Việt Nam với quần đảo Hoàng Sa và Trường Sa, góc trên là
ngôi sao năm cánh, phía dưới là dòng chữ 2-9-1945.

Yêu cầu: Python 3.8+ và Pillow  ->  pip install pillow

Cách dùng:
    python3 ve_tranh_co_dong.py
    python3 ve_tranh_co_dong.py -o tranh.png --rong 2400 --cua-cuon
"""

from __future__ import annotations

import argparse
import math
import os

from PIL import Image, ImageDraw, ImageFont

# Khung thiết kế; ảnh xuất ra được co giãn từ khung này.
RONG, CAO = 1600, 1560

DO = (214, 18, 26)          # đỏ cờ
VANG = (255, 211, 0)        # vàng sao

PHONG_CHU = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def lay_phong(co: int):
    for d in PHONG_CHU:
        if os.path.exists(d):
            return ImageFont.truetype(d, co)
    try:                                  # Pillow >= 10.1 có phông mặc định co giãn được
        return ImageFont.load_default(size=co)
    except TypeError:
        return ImageFont.load_default()


class Tranh:
    """Khung vẽ phẳng, siêu lấy mẫu để bờ hình sắc gọn."""

    def __init__(self, ty_le: int = 3):
        self.s = ty_le
        self.anh = Image.new("RGB", (RONG * ty_le, CAO * ty_le), DO)
        self.ve = ImageDraw.Draw(self.anh)
        self.k, self.ox, self.oy = 1.0, 0.0, 0.0

    def dat_khung(self, k=1.0, ox=0.0, oy=0.0):
        """Đặt phép co giãn và dời hình cho các nét vẽ tiếp theo."""
        self.k, self.ox, self.oy = k, ox, oy

    def q(self, diem):
        return [((x * self.k + self.ox) * self.s, (y * self.k + self.oy) * self.s)
                for x, y in diem]

    def h(self, hop):
        x0, y0, x1, y1 = hop
        return [(x0 * self.k + self.ox) * self.s, (y0 * self.k + self.oy) * self.s,
                (x1 * self.k + self.ox) * self.s, (y1 * self.k + self.oy) * self.s]

    def to(self, diem, mau=VANG):
        self.ve.polygon(self.q(diem), fill=mau)

    def net(self, diem, day, mau=DO, kin=False):
        d = self.q(diem)
        if kin:
            d = d + [d[0]]
        self.ve.line(d, fill=mau, width=max(1, int(day * self.k * self.s)), joint="curve")
        r = day * self.k * self.s / 2.0
        for x, y in d:                      # bo tròn hai đầu nét
            self.ve.ellipse([x - r, y - r, x + r, y + r], fill=mau)

    def tron(self, tam, ban_kinh, mau=VANG):
        x, y = tam
        self.ve.ellipse(self.h((x - ban_kinh, y - ban_kinh, x + ban_kinh, y + ban_kinh)),
                        fill=mau)

    def thu_nho(self, rong_ra: int) -> Image.Image:
        cao_ra = int(round(rong_ra * CAO / RONG))
        return self.anh.resize((rong_ra, cao_ra), Image.LANCZOS)


# --------------------------------------------------------------------------
# Chân dung: hình vàng phẳng, ngũ quan tả bằng nét đỏ
# --------------------------------------------------------------------------
DAU = [
    (340, 210), (392, 218), (434, 246), (464, 290), (482, 344), (490, 400),
    (488, 458), (478, 512), (462, 560), (440, 600), (412, 628), (378, 642),
    (340, 646), (302, 642), (268, 628), (240, 600), (218, 560), (202, 512),
    (192, 458), (190, 400), (198, 344), (216, 290), (246, 246), (288, 218),
]

THAN = [
    (292, 600), (388, 600), (400, 800), (540, 864), (648, 928), (692, 1060),
    (706, 1246), (14, 1246), (30, 1090), (84, 930), (190, 860), (280, 800),
]

RAU = [
    (292, 586), (316, 578), (340, 574), (364, 578), (388, 586), (394, 640),
    (384, 700), (362, 756), (340, 800), (318, 756), (298, 700), (288, 640),
]

CHAN_TOC = [(200, 404), (214, 340), (240, 306), (276, 290), (310, 298),
            (340, 306), (370, 298), (404, 290), (440, 306), (466, 340), (480, 404)]

# Các lọn tóc chải ngược: nét ngắn, không chụm vào một điểm.
LON_TOC = [
    [(230, 340), (238, 316), (248, 298)],
    [(268, 308), (278, 282), (290, 262)],
    [(316, 292), (320, 268), (326, 248)],
    [(364, 292), (360, 268), (356, 248)],
    [(412, 308), (404, 282), (394, 262)],
    [(450, 340), (442, 316), (434, 300)],
]


def ve_chan_dung(t: Tranh) -> None:
    t.to(THAN)
    t.to(DAU)

    # --- tóc chải ngược: chân tóc lượn cao, vài lọn hất về sau ---
    t.net(CHAN_TOC, 15)
    for lon in LON_TOC:
        t.net(lon, 9)

    # --- tai ---
    t.net([(204, 432), (196, 466), (206, 496)], 10)
    t.net([(476, 432), (484, 466), (474, 496)], 10)

    # --- lông mày rậm ---
    t.net([(252, 412), (288, 392), (328, 404)], 16)
    t.net([(352, 404), (392, 392), (428, 412)], 16)

    # --- mắt: mí trên trĩu, tròng đen nhỏ ---
    for cx in (288, 392):
        t.net([(cx - 32, 452), (cx - 12, 434), (cx + 14, 436), (cx + 32, 454)], 14)
        t.tron((cx + 2, 452), 13, DO)
        t.net([(cx - 24, 470), (cx, 476), (cx + 24, 468)], 7)

    # --- mũi ---
    t.net([(330, 430), (322, 498), (328, 520), (344, 528)], 12)
    t.net([(358, 514), (368, 524), (356, 532)], 9)          # cánh mũi

    # --- ria mép và miệng ---
    t.to([(296, 552), (320, 548), (340, 556), (360, 548), (384, 552), (386, 568),
          (360, 562), (340, 568), (320, 562), (294, 568)], DO)          # ria mép
    t.net([(324, 600), (340, 604), (356, 600)], 7)                      # khe miệng
    t.net([(306, 548), (300, 572)], 6)                                  # nếp pháp lệnh
    t.net([(374, 548), (380, 572)], 6)

    # --- chòm râu ---
    t.to(RAU)
    t.net(RAU[4:] + RAU[:1], 12)          # chỉ viền phần dưới, đỉnh râu hoà vào cằm
    for dau, cuoi in ((324, 332), (356, 348)):
        t.net([(dau, 600), (cuoi, 692)], 6)

    # --- cổ, vai và áo ---
    t.net([(282, 630), (312, 676), (340, 686)], 10)         # bóng dưới cằm
    t.net([(398, 630), (372, 676)], 10)
    t.net([(280, 800), (190, 860), (84, 930)], 15)          # đường vai
    t.net([(400, 800), (540, 864), (648, 928)], 15)
    t.net([(286, 792), (340, 872), (394, 792)], 17)         # cổ áo mở hình chữ V
    t.net([(312, 796), (340, 842), (368, 796)], 10)         # cổ áo sơ mi bên trong
    t.net([(286, 792), (232, 858), (200, 968), (192, 1246)], 15)   # ve áo trái
    t.net([(394, 792), (450, 858), (482, 968), (490, 1246)], 15)
    t.net([(340, 872), (340, 1246)], 12)                    # nẹp áo
    for y in (992, 1108):
        t.tron((340, y), 16, DO)
    t.net([(236, 1022), (320, 1006), (324, 1050), (240, 1066)], 11, kin=True)  # túi ngực


def ve_micro(t: Tranh) -> None:
    """Chiếc micro trên giá, đặt trước ngực."""
    t.to([(624, 1246), (624, 792), (656, 792), (656, 1246)])
    t.net([(592, 824), (688, 824)], 16)
    t.tron((640, 724), 66)
    t.tron((640, 724), 38, DO)
    t.tron((640, 724), 17)


# --------------------------------------------------------------------------
# Bản đồ Việt Nam
# --------------------------------------------------------------------------
# Các điểm mốc trên biên giới và bờ biển, ghi theo (kinh độ, vĩ độ) rồi chiếu
# thẳng vào ô chứa bản đồ. Danh sách đi từ cực bắc, xuôi bờ biển xuống mũi
# Cà Mau rồi ngược lên theo biên giới phía tây.
DAT_LIEN = [
    (105.32, 23.39),   # Lũng Cú, cực bắc
    (106.00, 22.92), (106.80, 22.50), (107.35, 22.35), (107.97, 21.53),  # biên giới phía bắc
    (107.10, 20.95), (106.80, 20.75), (106.55, 20.20), (106.10, 19.95),  # vịnh Bắc Bộ
    (105.90, 19.70), (105.75, 19.20), (105.70, 18.70), (106.10, 18.35),
    (106.40, 18.10), (106.55, 17.75), (106.60, 17.50), (106.90, 17.15),
    (107.10, 16.90), (107.60, 16.50), (108.05, 16.20), (108.25, 16.05),
    (108.65, 15.45), (108.90, 15.10), (109.10, 14.40), (109.25, 13.77),
    (109.30, 13.10), (109.20, 12.60), (109.20, 12.25), (109.15, 11.90),
    (109.05, 11.60), (108.60, 11.20), (108.10, 10.93), (107.60, 10.55),
    (107.10, 10.35), (106.85, 10.40), (106.60, 9.90), (106.50, 9.60),
    (106.20, 9.35), (105.70, 9.15), (105.30, 8.75), (104.83, 8.56),   # mũi Cà Mau
    (104.90, 9.10), (105.08, 10.00), (104.80, 10.20), (104.48, 10.38),  # bờ tây
    (105.10, 10.70), (105.85, 11.05), (106.10, 11.35), (106.45, 11.65),  # biên giới tây nam
    (106.90, 11.90), (107.35, 12.25), (107.50, 12.80), (107.55, 13.50),
    (107.45, 14.20), (107.50, 14.70), (107.35, 15.40), (107.20, 16.20),
    (106.60, 16.60), (106.20, 17.10), (106.00, 17.60), (105.60, 18.00),
    (105.20, 18.40), (104.70, 18.80), (104.50, 19.20), (104.60, 19.70),
    (104.50, 20.00), (104.30, 20.50), (104.00, 20.90), (103.20, 20.80),
    (102.90, 21.50), (102.15, 22.40),   # cực tây
    (102.80, 22.80), (103.95, 22.80), (104.60, 22.80), (105.32, 23.39),
]
PHU_QUOC = [(103.95, 10.38), (104.08, 10.30), (104.05, 10.05), (103.85, 10.00),
            (103.82, 10.22)]

# Hai quần đảo nằm xa về phía đông; trên tranh cổ động chúng được kéo lại gần
# cho vừa khuôn hình, nhưng vẫn giữ đúng vĩ độ.
HOANG_SA = [(0.30, 16.90), (0.46, 16.60), (0.34, 16.30), (0.52, 16.10), (0.20, 16.45)]
TRUONG_SA = [(0.26, 11.40), (0.44, 11.10), (0.30, 10.75), (0.50, 10.55),
             (0.18, 10.90), (0.40, 10.20)]

O_BAN_DO = (800, 156, 1248, 1240)      # ô chứa bản đồ trong khung tranh
_KINH = (102.15, 109.30)
_VI = (23.39, 8.56)


def _diem_ban_do(diem):
    """Chiếu (kinh độ, vĩ độ) vào ô chứa bản đồ."""
    x0, y0, x1, y1 = O_BAN_DO
    return [(x0 + (kinh - _KINH[0]) / (_KINH[1] - _KINH[0]) * (x1 - x0),
             y0 + (_VI[0] - vi) / (_VI[0] - _VI[1]) * (y1 - y0)) for kinh, vi in diem]


def _diem_dao(cum):
    """Các đảo nhỏ: hoành độ cho sẵn theo tỉ lệ ngang, tung độ theo vĩ độ."""
    x0, y0, x1, y1 = O_BAN_DO
    return [(x1 + 10 + ngang * (x1 - x0) * 0.30,
             y0 + (_VI[0] - vi) / (_VI[0] - _VI[1]) * (y1 - y0)) for ngang, vi in cum]


def ve_ban_do(t: Tranh) -> None:
    t.to(_diem_ban_do(DAT_LIEN))
    t.to(_diem_ban_do(PHU_QUOC))
    for cum, ban_kinh in ((HOANG_SA, 9), (TRUONG_SA, 8)):
        for diem in _diem_dao(cum):
            t.tron(diem, ban_kinh)


def ve_ten_dao(t: Tranh) -> None:
    for chu, cum in (("HOÀNG SA", HOANG_SA), ("TRƯỜNG SA", TRUONG_SA)):
        diem = _diem_dao(cum)
        x = max(d[0] for d in diem) + 24
        y = sum(d[1] for d in diem) / len(diem)
        t.ve.text((x * t.s, y * t.s), chu, font=lay_phong(int(30 * t.s)),
                  fill=VANG, anchor="lm")


# --------------------------------------------------------------------------
# Ngôi sao năm cánh và dòng chữ
# --------------------------------------------------------------------------
def ve_ngoi_sao(t: Tranh, tam=(1420, 288), ban_kinh=124) -> None:
    cx, cy = tam
    diem = []
    for i in range(10):
        r = ban_kinh if i % 2 == 0 else ban_kinh * 0.382
        goc = -math.pi / 2 + i * math.pi / 5
        diem.append((cx + r * math.cos(goc), cy + r * math.sin(goc)))
    t.to(diem)


def ve_dong_chu(t: Tranh, chu="2-9-1945", o=(56, 1306, 792, 1472)) -> None:
    """Chữ được vẽ riêng rồi co giãn vừa ô, không phụ thuộc phông máy."""
    x0, y0, x1, y1 = [v * t.s for v in o]
    phong = lay_phong(400)
    tam = Image.new("L", (int(4200), int(1200)), 0)
    ImageDraw.Draw(tam).text((60, 600), chu, font=phong, fill=255, anchor="lm")
    hop = tam.getbbox()
    if hop is None:
        return
    tam = tam.crop(hop)
    ty_le = min((x1 - x0) / tam.width, (y1 - y0) / tam.height)
    tam = tam.resize((max(1, int(tam.width * ty_le)), max(1, int(tam.height * ty_le))),
                     Image.LANCZOS)
    mau = Image.new("RGB", tam.size, VANG)
    t.anh.paste(mau, (int(x0), int(y0 + ((y1 - y0) - tam.height) / 2)), tam)


def ve_cua_cuon(t: Tranh, buoc=26) -> None:
    """Vạch ngang mô phỏng cánh cửa cuốn nơi bức tranh được vẽ."""
    lop = Image.new("RGB", t.anh.size, (0, 0, 0))
    mat_na = Image.new("L", t.anh.size, 0)
    ve = ImageDraw.Draw(mat_na)
    for y in range(0, CAO, buoc):
        ve.rectangle(t.h((0, y, RONG, y + 2)), fill=34)
    t.anh = Image.composite(lop, t.anh, mat_na)
    t.ve = ImageDraw.Draw(t.anh)


# --------------------------------------------------------------------------
def ve_toan_bo(rong_ra=1600, ty_le=3, cua_cuon=False, chu="2-9-1945") -> Image.Image:
    t = Tranh(ty_le=ty_le)
    ve_ban_do(t)
    ve_ten_dao(t)
    ve_ngoi_sao(t)
    t.dat_khung(1.08, 0.0, -96.0)      # chân dung vẽ lớn hơn cho cân khuôn hình
    ve_chan_dung(t)
    ve_micro(t)
    t.dat_khung()
    ve_dong_chu(t, chu=chu)
    if cua_cuon:
        ve_cua_cuon(t)
    return t.thu_nho(rong_ra)


def main() -> None:
    bp = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    bp.add_argument("-o", "--output", default="tranh_co_dong_2_9_1945.png",
                    help="tên tệp ảnh xuất ra")
    bp.add_argument("--rong", type=int, default=1600, help="chiều rộng ảnh, tính bằng điểm ảnh")
    bp.add_argument("--ty-le", type=int, default=3, help="hệ số siêu lấy mẫu khi vẽ")
    bp.add_argument("--chu", default="2-9-1945", help="dòng chữ phía dưới")
    bp.add_argument("--cua-cuon", action="store_true",
                    help="thêm vạch ngang mô phỏng cánh cửa cuốn")
    ts = bp.parse_args()

    anh = ve_toan_bo(rong_ra=ts.rong, ty_le=ts.ty_le, cua_cuon=ts.cua_cuon, chu=ts.chu)
    anh.save(ts.output)
    print(f"Đã lưu {ts.output} ({anh.size[0]}x{anh.size[1]})")


if __name__ == "__main__":
    main()
