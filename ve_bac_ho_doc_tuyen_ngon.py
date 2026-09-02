#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vẽ lại bức ảnh tư liệu: Chủ tịch Hồ Chí Minh đọc Tuyên ngôn Độc lập
tại Quảng trường Ba Đình, ngày 2 tháng 9 năm 1945.

Toàn bộ hình được dựng bằng các hình khối cơ bản (đa giác, ellipse, đường
cong) rồi phủ các hiệu ứng ảnh cũ: nhoè nhẹ, hạt phim, ám màu nâu sepia,
tối bốn góc (vignette) và khung viền ảnh.

Yêu cầu: Python 3.8+ và thư viện Pillow  ->  pip install pillow

Cách dùng:
    python3 ve_bac_ho_doc_tuyen_ngon.py
    python3 ve_bac_ho_doc_tuyen_ngon.py -o anh.png --che-do xam --chu-thich
"""

from __future__ import annotations

import argparse
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

# --------------------------------------------------------------------------
# Kích thước khung tranh gốc (mọi toạ độ bên dưới đều tính theo hệ này)
# --------------------------------------------------------------------------
RONG, CAO = 900, 1200

# Bảng màu làm việc (ảnh sẽ được ám nâu ở bước cuối nên ở đây chỉ cần
# đúng về độ sáng - tối, không cần đúng màu thật).
MAU = {
    "nen_tren": (132, 130, 126),
    "nen_duoi": (74, 73, 71),
    "hao_quang": (170, 168, 162),
    "ao": (192, 187, 172),      # áo kaki sáng màu
    "ao_toi": (132, 128, 117),
    "ao_sang": (238, 234, 222),
    "da": (152, 137, 117),
    "da_toi": (120, 106, 88),
    "toc": (46, 40, 34),
    "rau": (122, 113, 100),
    "mat": (36, 31, 27),
    "ban": (54, 51, 47),
    "ban_sang": (86, 82, 76),
    "giay": (238, 234, 223),
    "kim_loai": (74, 72, 69),
    "kim_loai_sang": (176, 173, 166),
}


class BucTranh:
    """Khung vẽ có siêu lấy mẫu (supersampling) và hai lớp sáng / tối riêng."""

    def __init__(self, ty_le: int = 3):
        self.s = ty_le
        kich_thuoc = (RONG * ty_le, CAO * ty_le)
        self.anh = Image.new("RGB", kich_thuoc, MAU["nen_duoi"])
        self.ve = ImageDraw.Draw(self.anh)
        # Lớp mặt nạ: 0 = giữ nguyên, 255 = tô tối / sáng hoàn toàn.
        self.lop_toi = Image.new("L", kich_thuoc, 0)
        self.ve_toi = ImageDraw.Draw(self.lop_toi)
        self.lop_net = Image.new("L", kich_thuoc, 0)      # bóng nét, gần như không nhoè
        self.ve_net = ImageDraw.Draw(self.lop_net)
        self.lop_sang = Image.new("L", kich_thuoc, 0)
        self.ve_sang = ImageDraw.Draw(self.lop_sang)

    # -- tiện ích toạ độ ---------------------------------------------------
    def q(self, diem):
        """Quy đổi một dãy điểm sang hệ toạ độ đã phóng to."""
        return [(x * self.s, y * self.s) for x, y in diem]

    def h(self, hop):
        """Quy đổi một hình chữ nhật (x0, y0, x1, y1)."""
        x0, y0, x1, y1 = hop
        return [x0 * self.s, y0 * self.s, x1 * self.s, y1 * self.s]

    def n(self, gia_tri):
        return gia_tri * self.s

    # -- các nét vẽ cơ bản -------------------------------------------------
    def da_giac(self, diem, mau):
        self.ve.polygon(self.q(diem), fill=mau)

    def bau_duc(self, hop, mau):
        self.ve.ellipse(self.h(hop), fill=mau)

    def duong(self, diem, mau, day=2):
        self.ve.line(self.q(diem), fill=mau, width=max(1, self.n(day)), joint="curve")

    def toi(self, hinh, dam=255, net=False):
        """Ghi một vùng vào lớp tối (hinh: ('da_giac'|'bau_duc', dữ liệu)).

        net=True dùng cho các chi tiết nhỏ cần giữ nét: nếp nhăn, mí mắt,
        ngón tay, mép túi áo...
        """
        but = self.ve_net if net else self.ve_toi
        loai, du_lieu = hinh
        if loai == "bau_duc":
            but.ellipse(self.h(du_lieu), fill=dam)
        else:
            but.polygon(self.q(du_lieu), fill=dam)

    def sang(self, hinh, dam=255):
        loai, du_lieu = hinh
        if loai == "bau_duc":
            self.ve_sang.ellipse(self.h(du_lieu), fill=dam)
        else:
            self.ve_sang.polygon(self.q(du_lieu), fill=dam)

    # -- hoàn thiện --------------------------------------------------------
    def hop_nhat(self, nhoe=6, do_toi=0.62, do_net=0.55, do_sang=0.3):
        """Trộn các lớp sáng / tối vào ảnh chính."""
        toi_mau = Image.new("RGB", self.anh.size, (28, 25, 22))
        mn_toi = self.lop_toi.filter(ImageFilter.GaussianBlur(self.n(nhoe)))
        mn_toi = mn_toi.point(lambda v: int(v * do_toi))
        self.anh = Image.composite(toi_mau, self.anh, mn_toi)

        mn_net = self.lop_net.filter(ImageFilter.GaussianBlur(self.n(1.2)))
        mn_net = mn_net.point(lambda v: int(v * do_net))
        self.anh = Image.composite(toi_mau, self.anh, mn_net)
        mn_sang = self.lop_sang.filter(ImageFilter.GaussianBlur(self.n(nhoe + 2)))
        mn_sang = mn_sang.point(lambda v: int(v * do_sang))
        self.anh = Image.composite(
            Image.new("RGB", self.anh.size, (247, 244, 236)), self.anh, mn_sang
        )
        self.ve = ImageDraw.Draw(self.anh)

    def thu_nho(self):
        return self.anh.resize((RONG, CAO), Image.LANCZOS)


# --------------------------------------------------------------------------
# 1. Phông nền
# --------------------------------------------------------------------------
def ve_nen(t: BucTranh) -> None:
    tren, duoi = MAU["nen_tren"], MAU["nen_duoi"]
    for y in range(CAO):
        k = y / CAO
        mau = tuple(int(tren[i] + (duoi[i] - tren[i]) * k) for i in range(3))
        t.ve.rectangle(t.h((0, y, RONG, y + 1)), fill=mau)

    # Quầng sáng phía sau đầu cho chân dung nổi lên khỏi phông.
    hao_quang = Image.new("L", t.anh.size, 0)
    ImageDraw.Draw(hao_quang).ellipse(t.h((150, 60, 720, 700)), fill=88)
    hao_quang = hao_quang.filter(ImageFilter.GaussianBlur(t.n(70)))
    t.anh = Image.composite(
        Image.new("RGB", t.anh.size, MAU["hao_quang"]), t.anh, hao_quang
    )
    t.ve = ImageDraw.Draw(t.anh)


# --------------------------------------------------------------------------
# 2. Bàn phủ khăn và tập bản Tuyên ngôn
# --------------------------------------------------------------------------
def ve_bong_nguoi(t: BucTranh) -> None:
    """Bóng của người hắt lên phông, đặt lệch sang phải như nguồn sáng bên trái."""
    t.toi(("da_giac", [(214, 1010), (250, 640), (330, 566), (432, 528), (540, 566),
                       (640, 640), (700, 800), (742, 1010)]), 60)
    t.toi(("bau_duc", (386, 208, 566, 500)), 55)


def ve_ban(t: BucTranh) -> None:
    t.da_giac([(0, 1006), (RONG, 990), (RONG, CAO), (0, CAO)], MAU["ban"])
    t.duong([(0, 1008), (RONG, 992)], MAU["ban_sang"], day=4)
    # Nếp gấp buông xuống của khăn phủ bàn.
    for x in range(30, RONG, 78):
        lech = random.randint(-14, 14)
        t.toi(("da_giac", [(x, 1010), (x + 20, 1010), (x + 26 + lech, CAO),
                           (x + lech, CAO)]), 120, net=True)
        t.sang(("da_giac", [(x + 20, 1012), (x + 30, 1012), (x + 36 + lech, CAO), (x + 26 + lech, CAO)]), 70)


def ve_ban_tuyen_ngon(t: BucTranh) -> None:
    """Tập giấy bản Tuyên ngôn đặt trên mặt bàn."""
    giay = [(288, 1000), (520, 982), (556, 1030), (322, 1054)]
    t.da_giac(giay, MAU["giay"])
    t.toi(("da_giac", [(288, 1000), (322, 1054), (316, 1062), (284, 1008)]), 120)
    # Vài hàng chữ mờ trên trang giấy.
    for i in range(7):
        y = 1000 + i * 7
        t.duong([(306 + i, y + 4), (306 + i + random.randint(140, 210), y - 12 + i)],
                (176, 170, 158), day=1)


# --------------------------------------------------------------------------
# 3. Thân người: áo kaki bốn túi
# --------------------------------------------------------------------------
def _vien(t: BucTranh, diem, dam=120, day=7):
    """Viền tối mềm chạy quanh một hình khối để tách nó khỏi phông."""
    t.ve_toi.line(t.q(list(diem) + [diem[0]]), fill=dam,
                  width=max(1, t.n(day)), joint="curve")


def ve_than(t: BucTranh) -> None:
    than = [
        (150, 1010), (168, 828), (196, 694), (250, 608), (320, 552), (382, 518),
        (432, 508), (482, 518), (544, 552), (614, 608), (668, 694), (696, 828),
        (714, 1010),
    ]
    t.da_giac(than, MAU["ao"])
    _vien(t, than, dam=150, day=10)

    # Khối sáng tối của thân áo: nguồn sáng chếch từ trái phía trước.
    t.toi(("da_giac", [(150, 1010), (168, 828), (202, 688), (256, 612), (276, 668),
                       (222, 764), (214, 1010)]), 150)
    t.toi(("da_giac", [(714, 1010), (696, 828), (662, 688), (608, 612), (588, 668),
                       (642, 768), (652, 1010)]), 165)
    t.sang(("da_giac", [(328, 586), (432, 556), (536, 586), (526, 674), (432, 630),
                        (338, 664)]), 80)

    # Đường vai và tay áo tách khỏi thân.
    for x0, x1, huong in ((252, 292, -1), (612, 572, 1)):
        t.toi(("da_giac", [(x0, 600), (x0 + 14 * huong, 606), (x1 + 14 * huong, 1010),
                           (x1, 1010)]), 110)

    # Cổ áo đứng, hai ve áo mở.
    t.da_giac([(382, 520), (432, 500), (482, 520), (496, 576), (432, 546), (368, 576)],
              MAU["ao_toi"])
    t.sang(("da_giac", [(394, 528), (432, 514), (470, 528), (474, 558), (432, 536),
                        (392, 558)]), 60)
    t.toi(("da_giac", [(368, 570), (432, 542), (496, 570), (490, 586), (432, 558),
                       (374, 586)]), 150, net=True)

    # Nẹp áo và hàng cúc.
    t.da_giac([(418, 548), (448, 552), (462, 1010), (434, 1010)], MAU["ao_toi"])
    t.toi(("da_giac", [(418, 548), (430, 550), (440, 1010), (426, 1010)]), 90)
    for y in (664, 754, 844, 934):
        t.bau_duc((434, y - 9, 452, y + 9), MAU["ao_toi"])
        t.toi(("bau_duc", (432, y - 10, 454, y + 10)), 150, net=True)
        t.sang(("bau_duc", (437, y - 6, 446, y + 1)), 110)

    # Hai túi ngực có nắp.
    for x0, x1 in ((262, 380), (508, 626)):
        t.duong([(x0, 716), (x1, 708), (x1 + 4, 808), (x0 + 2, 816), (x0, 716)],
                MAU["ao_toi"], day=3)
        t.da_giac([(x0 - 6, 704), (x1 + 6, 696), (x1 + 8, 732), (x0 - 4, 740)], MAU["ao"])
        t.toi(("da_giac", [(x0 - 6, 728), (x1 + 8, 720), (x1 + 8, 736), (x0 - 4, 744)]),
              170, net=True)
        t.sang(("da_giac", [(x0 - 4, 706), (x1 + 6, 698), (x1 + 6, 708), (x0 - 4, 716)]), 60)

    # Nếp nhăn vải.
    for a, b, c, d in ((248, 852, 306, 1000), (306, 892, 348, 1006),
                       (588, 842, 552, 1000), (642, 792, 612, 970)):
        t.toi(("da_giac", [(a, b), (a + 13, b), (c + 13, d), (c, d)]), 95)

    # Đường nách áo tách cánh tay khỏi thân, tay buông xuống mặt bàn.
    t.toi(("da_giac", [(250, 620), (272, 616), (300, 830), (306, 1010), (282, 1010),
                       (274, 838)]), 105)
    t.sang(("da_giac", [(206, 718), (244, 700), (266, 900), (268, 1006), (232, 1006),
                        (222, 880)]), 55)
    canh_tay = [(186, 754), (256, 734), (300, 936), (306, 964), (232, 986), (212, 908)]
    t.da_giac(canh_tay, MAU["ao"])
    t.toi(("da_giac", [(256, 734), (272, 746), (312, 938), (306, 964), (280, 952)]), 130)
    t.toi(("da_giac", [(186, 754), (202, 750), (224, 902), (238, 978), (216, 982)]), 95)
    t.sang(("da_giac", [(214, 752), (248, 742), (284, 918), (256, 930)]), 60)
    t.toi(("da_giac", [(222, 938), (304, 914), (310, 942), (228, 966)]), 110,
          net=True)                                                       # cửa tay áo


def _ngon_tay(t: BucTranh, p0, p1, day, mau):
    """Một ngón tay: đoạn thẳng bo tròn hai đầu."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    dai = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / dai * day / 2, dx / dai * day / 2
    t.da_giac([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
               (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], mau)
    t.bau_duc((x0 - day / 2, y0 - day / 2, x0 + day / 2, y0 + day / 2), mau)
    t.bau_duc((x1 - day / 2, y1 - day / 2, x1 + day / 2, y1 + day / 2), mau)


def ve_ban_tay(t: BucTranh) -> None:
    """Bàn tay đặt hờ trên mặt bàn, các ngón hơi khép."""
    t.toi(("bau_duc", (196, 1004, 344, 1044)), 140)          # bóng đổ trên mặt bàn

    ban_tay = [(214, 960), (262, 956), (306, 980), (318, 1006), (300, 1024),
               (250, 1026), (216, 1006)]
    t.da_giac(ban_tay, MAU["da"])
    t.toi(("da_giac", ban_tay), 95)
    for i in range(3):                                        # kẽ ngón tay
        t.ve_net.line(t.q([(268 + i * 6, 972 + i * 14), (312 - i * 4, 992 + i * 11)]),
                      fill=85, width=t.n(2), joint="curve")
    t.toi(("da_giac", [(214, 960), (230, 958), (240, 1012), (222, 1010)]), 110)
    t.sang(("da_giac", [(232, 962), (272, 964), (300, 986), (280, 996), (244, 978)]), 65)




# --------------------------------------------------------------------------
VIEN_MAT = [
    (432, 196), (468, 202), (496, 222), (513, 256), (518, 302), (512, 352),
    (500, 400), (480, 440), (456, 466), (432, 478), (408, 466), (384, 440),
    (364, 400), (352, 352), (346, 302), (351, 256), (368, 222), (396, 202),
]


def ve_dau(t: BucTranh) -> None:
    # Cổ, luôn nằm trong bóng của cằm.
    t.da_giac([(404, 430), (460, 430), (470, 546), (394, 546)], MAU["da"])
    t.toi(("da_giac", [(404, 430), (460, 430), (470, 546), (394, 546)]), 120)
    t.toi(("da_giac", [(400, 432), (464, 432), (466, 486), (398, 486)]), 70)
    # bóng cằm hắt xuống cổ

    # Tai.
    for hop in ((338, 312, 358, 372), (506, 312, 526, 372)):
        t.bau_duc(hop, MAU["da"])
        t.toi(("bau_duc", (hop[0] + 5, hop[1] + 12, hop[2] - 5, hop[3] - 14)), 120)

    # Khuôn mặt gầy, xương gò má cao.
    t.da_giac(VIEN_MAT, MAU["da"])
    _vien(t, VIEN_MAT, dam=120, day=7)
    t.toi(("da_giac", [(346, 302), (355, 250), (372, 226), (380, 300), (386, 396),
                       (406, 452), (380, 434), (356, 370)]), 145)   # nửa mặt trong bóng
    t.toi(("da_giac", [(518, 302), (511, 252), (496, 230), (490, 312), (484, 400),
                       (462, 458), (488, 434), (510, 366)]), 120)
    t.toi(("da_giac", [(382, 438), (432, 462), (482, 438), (472, 458), (432, 476),
                       (392, 458)]), 90)                            # bóng dưới hàm
    t.sang(("da_giac", [(402, 240), (462, 240), (472, 300), (460, 356), (432, 370),
                        (404, 356), (392, 300)]), 105)              # trán, sống mũi
    t.sang(("bau_duc", (386, 340, 430, 386)), 60)                   # gò má trái đón sáng

    # Tóc thưa chải ngược để lộ vầng trán cao.
    toc = [(366, 230), (396, 202), (432, 194), (468, 202), (498, 228), (512, 260),
           (517, 302), (503, 290), (494, 250), (466, 232), (432, 228), (398, 234),
           (370, 254), (355, 296), (347, 302), (353, 258)]
    t.da_giac(toc, MAU["toc"])
    t.toi(("da_giac", toc), 200)
    # Vài sợi tóc lơ thơ ở chân tóc cho bớt cứng.
    for _ in range(40):
        x0 = random.uniform(360, 504)
        lech = abs(x0 - 432) / 84.0
        y0 = 228 + lech * 26
        t.ve_net.line(t.q([(x0, y0), (x0 + random.uniform(-3, 3), y0 + random.uniform(3, 11))]),
                      fill=random.randint(60, 150), width=t.n(1))
    for i in range(22):
        x0 = 362 + i * 6.6
        lech = abs(x0 - 432) / 84.0
        t.sang(("da_giac", [(x0, 222 + lech * 26), (x0 + 2, 222 + lech * 26),
                            (x0 + (x0 - 432) * 0.08 + 2, 206 + lech * 30),
                            (x0 + (x0 - 432) * 0.08, 206 + lech * 30)]), 55)
    t.toi(("bau_duc", (342, 250, 380, 330)), 120)   # tóc mai
    t.toi(("bau_duc", (484, 250, 522, 330)), 110)

    # Nếp nhăn trán và lông mày.
    t.ve_net.line(t.q([(392, 270), (432, 266), (472, 270)]), fill=60,
                  width=t.n(2), joint="curve")
    t.ve_net.line(t.q([(398, 284), (432, 281), (466, 284)]), fill=48,
                  width=t.n(2), joint="curve")
    for diem in ([(378, 304), (398, 295), (420, 300)], [(446, 300), (468, 295), (488, 304)]):
        t.ve_net.line(t.q(diem), fill=165, width=t.n(3), joint="curve")

    # Mắt hơi nhìn xuống trang giấy, hốc mắt sâu.
    for cx, ng in ((398, -1), (468, 1)):
        t.toi(("bau_duc", (cx - 30, 302, cx + 30, 344)), 120)       # hốc mắt sâu
        mi = [(cx - 18, 321), (cx - 7, 315), (cx + 7, 315), (cx + 18, 321),
              (cx + 6, 329), (cx - 6, 329)]
        t.da_giac(mi, (192, 184, 170))
        t.bau_duc((cx - 5 + ng, 318, cx + 6 + ng, 329), MAU["mat"])
        t.toi(("da_giac", mi), 70, net=True)
        t.ve_net.line(t.q([(cx - 19, 320), (cx - 7, 314), (cx + 7, 314), (cx + 19, 320)]),
                      fill=190, width=t.n(3), joint="curve")        # mí trên trĩu xuống
        t.da_giac([(cx - 20, 310), (cx - 7, 305), (cx + 8, 306), (cx + 20, 313),
                   (cx + 18, 318), (cx - 18, 316)], MAU["da"])      # nếp mí
        t.ve_net.line(t.q([(cx - 16, 334), (cx, 336), (cx + 16, 333)]),
                      fill=75, width=t.n(2), joint="curve")         # bọng mắt

    # Mũi dài, sống mũi đón sáng.
    t.toi(("da_giac", [(421, 304), (431, 304), (438, 366), (426, 376), (412, 364)]), 85)
    t.sang(("da_giac", [(429, 302), (438, 302), (440, 358), (430, 358)]), 100)
    t.toi(("bau_duc", (414, 366, 424, 376)), 95, net=True)
    t.toi(("bau_duc", (441, 366, 451, 376)), 95, net=True)
    t.sang(("bau_duc", (426, 356, 442, 372)), 60)                   # đầu mũi đón sáng
    t.ve_net.line(t.q([(418, 378), (432, 381), (446, 378)]), fill=120,
                  width=t.n(2), joint="curve")                      # chân mũi

    # Má hóp và nếp pháp lệnh.
    t.toi(("bau_duc", (360, 346, 404, 418)), 135)
    t.toi(("bau_duc", (460, 346, 504, 418)), 125)
    t.ve_net.line(t.q([(410, 382), (405, 398), (404, 414)]), fill=60,
                  width=t.n(2), joint="curve")
    t.ve_net.line(t.q([(454, 382), (459, 398), (460, 414)]), fill=52,
                  width=t.n(2), joint="curve")

    # Ria mép thưa và miệng đang nói.
    t.da_giac([(406, 394), (432, 388), (458, 394), (460, 404), (432, 398), (404, 404)],
              MAU["rau"])
    t.toi(("da_giac", [(406, 394), (432, 388), (458, 394), (460, 404), (432, 398),
                       (404, 404)]), 85)
    t.ve_net.line(t.q([(412, 410), (432, 414), (452, 409)]), fill=150,
                  width=t.n(3), joint="curve")                       # khe môi hé mở
    t.toi(("da_giac", [(414, 412), (432, 416), (450, 411), (446, 421), (432, 424),
                       (418, 421)]), 70, net=True)                   # môi dưới
    t.sang(("da_giac", [(416, 424), (448, 424), (442, 432), (422, 432)]), 45)


def ve_chom_rau(t: BucTranh) -> None:
    """Chòm râu buông xuống, vẽ sau cùng để phủ lên cổ áo."""
    rau = [(418, 448), (432, 444), (446, 448), (443, 492), (433, 540), (423, 492)]
    t.toi(("da_giac", rau), 85)
    for _ in range(70):
        x0 = random.uniform(417, 447)
        dai = random.uniform(40, 96)
        cong = (x0 - 432) * 0.45 + random.uniform(-4, 4)
        t.ve_net.line(t.q([(x0, 446), (x0 + cong * 0.4, 446 + dai * 0.6),
                           (432 + cong, 446 + dai)]),
                      fill=random.randint(70, 130), width=t.n(1), joint="curve")
    t.sang(("da_giac", [(426, 452), (438, 452), (436, 500), (429, 500)]), 40)


# --------------------------------------------------------------------------
# 5. Chiếc micro trước mặt
# --------------------------------------------------------------------------
def ve_micro(t: BucTranh) -> None:
    # Lưới micro.
    hop = (556, 470, 664, 632)
    t.ve.rounded_rectangle(t.h(hop), radius=t.n(54), fill=MAU["kim_loai"])
    for y in range(482, 626, 11):
        r = 52 * math.sqrt(max(0.0, 1 - ((y - 551) / 84.0) ** 2))
        t.duong([(610 - r, y), (610 + r, y)], MAU["kim_loai_sang"], day=1)
    for x in range(566, 660, 12):
        h = 80 * math.sqrt(max(0.0, 1 - ((x - 610) / 56.0) ** 2))
        t.duong([(x, 551 - h), (x, 551 + h)], (108, 105, 100), day=1)
    t.sang(("bau_duc", (570, 492, 604, 606)), 110)
    t.toi(("bau_duc", (632, 486, 668, 620)), 140)

    # Vòng đai, thân micro và chân đế.
    t.ve.rounded_rectangle(t.h((558, 628, 662, 658)), radius=t.n(12), fill=MAU["kim_loai"])
    t.sang(("da_giac", [(566, 634), (600, 634), (600, 652), (566, 652)]), 110)
    t.da_giac([(582, 658), (638, 658), (626, 742), (594, 742)], MAU["kim_loai"])
    t.da_giac([(598, 742), (622, 742), (626, 992), (594, 992)], MAU["kim_loai"])
    t.sang(("da_giac", [(602, 668), (610, 668), (606, 986), (600, 986)]), 120)
    t.bau_duc((548, 972, 672, 1022), MAU["kim_loai"])
    t.sang(("bau_duc", (566, 980, 640, 998)), 80)
    t.toi(("bau_duc", (540, 1000, 690, 1034)), 170, net=True)   # bóng đổ trên mặt bàn


# --------------------------------------------------------------------------
# 6. Hiệu ứng ảnh chụp năm 1945
# --------------------------------------------------------------------------
def hieu_ung_anh_cu(anh: Image.Image, che_do: str = "sepia", hat: float = 1.0) -> Image.Image:
    anh = anh.filter(ImageFilter.GaussianBlur(0.7))

    if che_do in ("sepia", "xam"):
        xam = anh.convert("L")
        # Uốn nhẹ đường tông màu cho giống phim đen trắng thời đó:
        # vùng sáng không bị cháy, vùng tối vẫn còn chi tiết.
        xam = xam.point(lambda v: int(255 * (v / 255.0) ** 1.12))
        if che_do == "sepia":
            anh = ImageOps.colorize(xam, black=(42, 32, 22), white=(247, 240, 224),
                                    mid=(150, 130, 100))
        else:
            anh = xam.convert("RGB")

    # Tối bốn góc.
    vignette = Image.new("L", anh.size, 0)
    ImageDraw.Draw(vignette).ellipse(
        (-int(RONG * 0.30), -int(CAO * 0.18),
         int(RONG * 1.30), int(CAO * 1.18)), fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(120))
    anh = Image.composite(anh, Image.new("RGB", anh.size, (26, 20, 14)), vignette)

    # Hạt phim.
    if hat > 0:
        nhieu = Image.effect_noise(anh.size, 22 * hat).convert("L")
        anh = Image.blend(anh, Image.merge("RGB", (nhieu, nhieu, nhieu)), 0.075 * hat)
        # Vài vết xước dọc của bản in cũ.
        ve = ImageDraw.Draw(anh)
        for _ in range(int(3 * hat)):
            x = random.choice([random.randint(20, 300), random.randint(700, 880)])
            y0 = random.randint(0, anh.size[1] - 160)
            ve.line([(x, y0), (x + random.randint(-3, 3), y0 + random.randint(70, 220))],
                    fill=(186, 178, 164), width=1)

    # Khung viền kiểu ảnh in tráng thủ công.
    anh = ImageOps.expand(anh, border=18, fill=(238, 232, 216))
    anh = ImageOps.expand(anh, border=2, fill=(122, 112, 96))
    return anh


def ghi_chu_thich(anh: Image.Image) -> Image.Image:
    """Thêm dòng chú thích dưới ảnh (bỏ qua nếu máy không có phông chữ)."""
    dong = [
        "Chủ tịch Hồ Chí Minh đọc Tuyên ngôn Độc lập",
        "Quảng trường Ba Đình, ngày 2 tháng 9 năm 1945",
    ]
    duong_dan = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "C:/Windows/Fonts/times.ttf",
    ]
    phong = None
    for d in duong_dan:
        if os.path.exists(d):
            phong = ImageFont.truetype(d, 26)
            break
    if phong is None:
        return anh

    cao_them = 96
    khung = Image.new("RGB", (anh.size[0], anh.size[1] + cao_them), (238, 232, 216))
    khung.paste(anh, (0, 0))
    ve = ImageDraw.Draw(khung)
    y = anh.size[1] + 18
    for i, chu in enumerate(dong):
        rong_chu = ve.textbbox((0, 0), chu, font=phong)[2]
        ve.text(((anh.size[0] - rong_chu) / 2, y + i * 34), chu,
                font=phong, fill=(74, 62, 48))
    return khung


# --------------------------------------------------------------------------
def ve_toan_bo(che_do: str = "sepia", hat: float = 1.0, ty_le: int = 3,
               chu_thich: bool = False) -> Image.Image:
    t = BucTranh(ty_le=ty_le)
    ve_nen(t)
    ve_bong_nguoi(t)
    ve_ban(t)
    ve_dau(t)          # đầu và cổ vẽ trước để cổ áo trùm lên
    ve_than(t)
    ve_chom_rau(t)
    ve_ban_tuyen_ngon(t)
    ve_ban_tay(t)
    ve_micro(t)
    t.hop_nhat()
    anh = hieu_ung_anh_cu(t.thu_nho(), che_do=che_do, hat=hat)
    if chu_thich:
        anh = ghi_chu_thich(anh)
    return anh


def main() -> None:
    bp = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    bp.add_argument("-o", "--output", default="tuyen_ngon_doc_lap.png",
                    help="tên tệp ảnh xuất ra (mặc định: tuyen_ngon_doc_lap.png)")
    bp.add_argument("--che-do", choices=["sepia", "xam", "mau"], default="sepia",
                    help="tông màu: sepia (ảnh cũ), xam (đen trắng), mau (giữ màu vẽ)")
    bp.add_argument("--hat", type=float, default=1.0,
                    help="độ đậm của hạt phim, 0 là tắt (mặc định: 1.0)")
    bp.add_argument("--ty-le", type=int, default=3,
                    help="hệ số siêu lấy mẫu, càng lớn nét càng mịn (mặc định: 3)")
    bp.add_argument("--chu-thich", action="store_true",
                    help="in thêm dòng chú thích dưới ảnh")
    bp.add_argument("--seed", type=int, default=1945,
                    help="hạt giống ngẫu nhiên cho nếp vải, sợi râu, hạt phim")
    tham_so = bp.parse_args()

    random.seed(tham_so.seed)
    anh = ve_toan_bo(che_do=tham_so.che_do, hat=tham_so.hat,
                     ty_le=tham_so.ty_le, chu_thich=tham_so.chu_thich)
    anh.save(tham_so.output)
    print(f"Đã lưu {tham_so.output} ({anh.size[0]}x{anh.size[1]})")


if __name__ == "__main__":
    main()
