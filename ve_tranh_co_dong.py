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
import random

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


def lam_muot(diem, lan: int = 3, kin: bool = False):
    """Bo tròn đường gấp khúc bằng phép cắt góc Chaikin.

    Mỗi lượt thay một đỉnh bằng hai điểm nằm trên hai cạnh kề, cạnh gãy vì
    thế biến thành cung cong. Ba lượt là đủ mượt mà vẫn giữ được dáng hình.
    """
    d = [(float(x), float(y)) for x, y in diem]
    for _ in range(max(0, lan)):
        moi = [] if kin else [d[0]]
        n = len(d)
        het = n if kin else n - 1
        for i in range(het):
            (x0, y0), (x1, y1) = d[i], d[(i + 1) % n]
            moi.append((0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1))
            moi.append((0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1))
        if not kin:
            moi.append(d[-1])
        d = moi
    return d


def _be_rong(t: float, day: float, dang: str) -> float:
    """Bề rộng nét tại vị trí t (0..1) dọc theo đường, theo từng dáng bút."""
    if dang == "deu":
        return day
    if dang == "vuot":                      # vuốt nhọn dần về cuối nét
        return day * max(0.06, (1.0 - t) ** 0.75)
    if dang == "nhon":                      # nhọn cả hai đầu
        return day * max(0.08, math.sin(math.pi * t) ** 0.65)
    return day * (0.60 + 0.40 * math.sin(math.pi * t) ** 0.7)   # "bung"


def than_net(diem, day: float, dang: str = "bung"):
    """Biến một đường thành dải có bề rộng thay đổi, như vệt bút lông.

    Trả về đa giác bao quanh đường: đi hết mép trái rồi vòng ngược mép phải.
    """
    d = [p for i, p in enumerate(diem)
         if i == 0 or (p[0] - diem[i - 1][0]) ** 2 + (p[1] - diem[i - 1][1]) ** 2 > 1e-6]
    if len(d) < 2:
        return [], []
    doan = [math.hypot(d[i + 1][0] - d[i][0], d[i + 1][1] - d[i][1])
            for i in range(len(d) - 1)]
    tong = sum(doan) or 1.0
    coi, moc = 0.0, [0.0]
    for l in doan:
        coi += l
        moc.append(coi / tong)

    trai, phai, ban_kinh = [], [], []
    for i, (x, y) in enumerate(d):
        xt, yt = d[max(0, i - 1)]
        xs, ys = d[min(len(d) - 1, i + 1)]
        tx, ty = xs - xt, ys - yt
        dai = math.hypot(tx, ty) or 1.0
        ux, uy = -ty / dai, tx / dai            # pháp tuyến đơn vị
        r = _be_rong(moc[i], day, dang) / 2.0
        ban_kinh.append(r)
        trai.append((x + ux * r, y + uy * r))
        phai.append((x - ux * r, y - uy * r))
    return trai + phai[::-1], [(d[0], ban_kinh[0]), (d[-1], ban_kinh[-1])]


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

    def to(self, diem, mau=VANG, muot=0, kin=True):
        self.ve.polygon(self.q(lam_muot(diem, muot, kin) if muot else diem), fill=mau)

    def net(self, diem, day, mau=DO, kin=False, dang="bung", muot=3):
        """Vẽ một nét bút: bo cong đường đi rồi trải bề rộng thay đổi dọc nét."""
        d = lam_muot(diem, muot, kin)
        if kin:
            d = d + [d[0]]
            dang = "deu"
        than, dau_cuoi = than_net(d, day, dang)
        if not than:
            return
        self.ve.polygon(self.q(than), fill=mau)
        for (x, y), r in dau_cuoi:          # bo tròn hai đầu nét
            if r > 0.5:
                self.tron((x, y), r, mau)

    def tron(self, tam, ban_kinh, mau=VANG):
        x, y = tam
        cx, cy = (x * self.k + self.ox) * self.s, (y * self.k + self.oy) * self.s
        r = ban_kinh * self.k * self.s
        self.ve.ellipse([cx - r, cy - r, cx + r, cy + r], fill=mau)

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
    (708, 1200), (712, 1292), (500, 1300), (220, 1300), (8, 1292), (12, 1200),
    (30, 1090), (84, 930), (190, 860), (280, 800),
]

RAU = [
    (292, 586), (316, 578), (340, 574), (364, 578), (388, 586), (394, 640),
    (384, 700), (362, 756), (340, 800), (318, 756), (298, 700), (288, 640),
]

CHAN_TOC = [(206, 392), (218, 342), (242, 308), (276, 292), (310, 300),
            (340, 308), (370, 300), (404, 292), (438, 308), (462, 342), (474, 392)]

TAM_SO, SO_RX, SO_RY = (340, 436), 152.0, 226.0    # hình cầu xấp xỉ hộp sọ


def _theo_so(goc: float, ban_kinh: float):
    """Điểm trên mặt cầu sọ: goc = 0 là thẳng đỉnh đầu, dương là lệch phải."""
    return (TAM_SO[0] + math.sin(goc) * SO_RX * ban_kinh,
            TAM_SO[1] - math.cos(goc) * SO_RY * ban_kinh)


def _toa_do_so(p):
    dx, dy = (p[0] - TAM_SO[0]) / SO_RX, (p[1] - TAM_SO[1]) / SO_RY
    return math.atan2(dx, -dy), math.hypot(dx, dy)


def _diem_tren(duong, u: float):
    """Điểm nằm ở vị trí u (0..1) tính theo chiều dài của một đường."""
    doan = [math.hypot(duong[i + 1][0] - duong[i][0], duong[i + 1][1] - duong[i][1])
            for i in range(len(duong) - 1)]
    moc = u * sum(doan)
    for i, l in enumerate(doan):
        if moc <= l or i == len(doan) - 1:
            k = moc / l if l else 0.0
            return (duong[i][0] + (duong[i + 1][0] - duong[i][0]) * k,
                    duong[i][1] + (duong[i + 1][1] - duong[i][1]) * k)
        moc -= l
    return duong[-1]


def _lon_toc(rng, so_lon: int = 8):
    """Sinh các lọn tóc chải ngược, mỗi lọn trượt trên mặt cầu hộp sọ.

    Điểm xuất phát nằm trên chân tóc; từ đó lọn vừa dâng lên đỉnh (bán kính
    tăng) vừa xoay dần về giữa (góc thu lại), nên các lọn chạy song song ôm
    lấy hộp sọ chứ không chụm vào một điểm.
    """
    duong = lam_muot(CHAN_TOC, 3)
    lon = []
    for i in range(so_lon):
        u = min(0.985, max(0.015, (i + 0.5) / so_lon + rng.uniform(-0.028, 0.028)))
        goc0, r0 = _toa_do_so(_diem_tren(duong, u))
        goc1 = goc0 * 0.55
        r1 = min(0.95, r0 + (0.23 - 0.10 * abs(goc0)) * rng.uniform(0.78, 1.26))
        lon.append(([_theo_so(goc0 + (goc1 - goc0) * k, r0 + (r1 - r0) * k)
                     for k in (0.0, 0.34, 0.68, 1.0)], rng.uniform(0.86, 1.18)))
    return lon


def _soi_rau(rng, so_soi: int = 5):
    """Sinh các sợi râu toả từ cằm rồi chụm dần về chóp râu."""
    soi = []
    for i in range(so_soi):
        u = (i + 0.5) / so_soi + rng.uniform(-0.03, 0.03)
        x0 = 312 + u * 56
        p0 = (x0, 606 + abs(u - 0.5) * 14)
        p2 = (340 + (x0 - 340) * 0.36, 722 - abs(u - 0.5) * 60)
        p2 = (p2[0], p2[1] * rng.uniform(0.97, 1.03))
        p1 = ((p0[0] + p2[0]) / 2 + (x0 - 340) * 0.16, (p0[1] + p2[1]) / 2)
        soi.append(([p0, p1, p2], rng.uniform(0.85, 1.15)))
    return soi


def ve_chan_dung(t: Tranh, hat_giong: int = 29) -> None:
    rng = random.Random(hat_giong)      # nhịp tay vẽ, cùng hạt giống thì cùng nét
    t.to(THAN, muot=2)
    t.to(DAU, muot=3)

    # --- tóc ---
    t.net(CHAN_TOC, 15, dang="nhon")
    for lon, dam in _lon_toc(rng):
        t.net(lon, 11 * dam, dang="vuot")

    # --- tai ---
    t.net([(204, 432), (196, 466), (206, 496)], 10, dang="nhon")
    t.net([(476, 432), (484, 466), (474, 496)], 10, dang="nhon")

    # --- lông mày rậm, thon dần về đuôi ---
    t.net([(250, 414), (288, 390), (330, 404)], 19, dang="vuot")
    t.net([(430, 414), (392, 390), (350, 404)], 19, dang="vuot")

    # --- mắt: mí trên trĩu, tròng đen nhỏ ---
    for cx in (288, 392):
        t.net([(cx - 33, 452), (cx - 12, 433), (cx + 14, 435), (cx + 33, 454)], 15,
              dang="nhon")
        t.tron((cx + 2, 452), 13, DO)
        t.net([(cx - 25, 470), (cx, 477), (cx + 25, 468)], 8, dang="nhon")

    # --- mũi ---
    t.net([(330, 430), (322, 498), (328, 520), (344, 528)], 13, dang="bung")
    t.net([(358, 514), (368, 524), (356, 532)], 9, dang="nhon")

    # --- ria mép và miệng ---
    t.to([(296, 552), (320, 548), (340, 556), (360, 548), (384, 552), (386, 568),
          (360, 562), (340, 568), (320, 562), (294, 568)], DO, muot=2)
    t.net([(322, 600), (340, 604), (358, 600)], 8, dang="nhon")
    t.net([(306, 548), (300, 572)], 7, dang="vuot")          # nếp pháp lệnh
    t.net([(374, 548), (380, 572)], 7, dang="vuot")

    # --- chòm râu: viền phần dưới, bên trong là các sợi toả ---
    t.to(RAU, muot=3)
    t.net(RAU[4:] + RAU[:1], 13, dang="nhon")
    for soi, dam in _soi_rau(rng):
        t.net(soi, 8 * dam, dang="vuot")

    # --- cổ, vai và áo ---
    t.net([(286, 622), (304, 656)], 10, dang="vuot")               # ngấn dưới hàm
    t.net([(394, 622), (376, 656)], 10, dang="vuot")
    t.net([(280, 800), (190, 860), (84, 930)], 16, muot=2)         # đường vai
    t.net([(400, 800), (540, 864), (648, 928)], 16, muot=2)
    t.net([(286, 792), (340, 872), (394, 792)], 18)                # cổ áo chữ V
    t.net([(312, 796), (340, 842), (368, 796)], 11)                # cổ sơ mi bên trong
    t.net([(286, 792), (234, 856), (204, 964), (196, 1120), (194, 1290)], 16,
          muot=2)                                                  # ve áo
    t.net([(394, 792), (448, 856), (478, 964), (486, 1120), (488, 1290)], 16,
          muot=2)
    t.net([(340, 872), (340, 1080), (340, 1290)], 13, dang="deu")  # nẹp áo
    for y in (992, 1108):
        t.tron((340, y), 16, DO)
    tui = [(236, 1022), (278, 1014), (320, 1006), (322, 1028), (324, 1050),
           (282, 1058), (240, 1066), (238, 1044)]
    t.net(tui, 11, kin=True, muot=1)                               # túi ngực


def ve_micro(t: Tranh) -> None:
    """Chiếc micro trên giá, đặt trước ngực."""
    t.to([(624, 1290), (624, 792), (656, 792), (656, 1290)])
    t.net([(592, 824), (688, 824)], 17, dang="nhon")
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
    # Bờ biển được bo cong nhẹ: dáng chữ S mềm lại mà vẫn giữ các mũi đất.
    t.to(_diem_ban_do(DAT_LIEN), muot=2)
    t.to(_diem_ban_do(PHU_QUOC), muot=2)
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
def ve_toan_bo(rong_ra=1600, ty_le=3, cua_cuon=False, chu="2-9-1945",
               hat_giong=29) -> Image.Image:
    t = Tranh(ty_le=ty_le)
    ve_ban_do(t)
    ve_ten_dao(t)
    ve_ngoi_sao(t)
    t.dat_khung(1.08, 0.0, -96.0)      # chân dung vẽ lớn hơn cho cân khuôn hình
    ve_chan_dung(t, hat_giong)
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
    bp.add_argument("--seed", type=int, default=29,
                    help="hạt giống cho nhịp tay vẽ của các lọn tóc và sợi râu")
    ts = bp.parse_args()

    anh = ve_toan_bo(rong_ra=ts.rong, ty_le=ts.ty_le, cua_cuon=ts.cua_cuon,
                     chu=ts.chu, hat_giong=ts.seed)
    anh.save(ts.output)
    print(f"Đã lưu {ts.output} ({anh.size[0]}x{anh.size[1]})")


if __name__ == "__main__":
    main()
