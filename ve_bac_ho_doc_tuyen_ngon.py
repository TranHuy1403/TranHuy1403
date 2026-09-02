#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dựng lại bức ảnh tư liệu: Chủ tịch Hồ Chí Minh đọc Tuyên ngôn Độc lập
tại Quảng trường Ba Đình, ngày 2 tháng 9 năm 1945.

Ảnh không được tô bằng các mảng màu phẳng. Chương trình dựng một bản đồ độ
cao (height field) cho toàn cảnh - hộp sọ, gò má, sống mũi, môi, cổ, thân
áo, micro - rồi từ bản đồ ấy tính pháp tuyến bề mặt và chiếu sáng từng điểm
ảnh theo mô hình Lambert cộng phản xạ bóng. Nhờ vậy khối nổi và chuyển sáng
tối là do hình học sinh ra, giống cách ánh sáng rơi trên vật thật.

Sau khi tô bóng, ảnh được phủ các đặc trưng của một tấm ảnh chụp năm 1945:
độ nét giảm dần ra hậu cảnh, hạt phim, ám nâu, tối bốn góc và khung viền.

Yêu cầu: Python 3.8+, Pillow và NumPy  ->  pip install pillow numpy

Cách dùng:
    python3 ve_bac_ho_doc_tuyen_ngon.py
    python3 ve_bac_ho_doc_tuyen_ngon.py -o anh.png --che-do xam --chu-thich
"""

from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

# --------------------------------------------------------------------------
# Khung ảnh và lưới toạ độ
# --------------------------------------------------------------------------
RONG, CAO = 1000, 1340
SS = 2                      # bội số khi raster hoá mặt nạ, để bờ hình mịn

Y, X = np.mgrid[0:CAO, 0:RONG].astype(np.float32)

# Phép biến đổi toạ độ dùng chung: cho phép mô tả từng bộ phận trong hệ toạ độ
# riêng của nó rồi đặt vào khung ảnh với tỉ lệ khác nhau (đầu vẽ to hơn thân).
_BD = [1.0, 0.0, 0.0]      # [tỉ lệ, dời ngang, dời dọc]


def dat_bien_doi(ty_le=1.0, dx=0.0, dy=0.0):
    _BD[:] = [ty_le, dx, dy]


def _tx(x):
    return x * _BD[0] + _BD[1]


def _ty(y):
    return y * _BD[0] + _BD[2]


def _tr(r):
    return r * _BD[0]


# --------------------------------------------------------------------------
# Công cụ: raster hoá mặt nạ và làm mềm
# --------------------------------------------------------------------------
def _khung_ve():
    anh = Image.new("L", (RONG * SS, CAO * SS), 0)
    return anh, ImageDraw.Draw(anh)


def _thu(anh: Image.Image) -> np.ndarray:
    """Thu mặt nạ về đúng khung, lấy trung bình nên bờ hình mịn."""
    nho = anh.resize((RONG, CAO), Image.BOX)
    return np.asarray(nho, dtype=np.float32) / 255.0


def mn_da_giac(diem) -> np.ndarray:
    anh, ve = _khung_ve()
    ve.polygon([(_tx(x) * SS, _ty(y) * SS) for x, y in diem], fill=255)
    return _thu(anh)


def mn_bau_duc(hop) -> np.ndarray:
    x0, y0, x1, y1 = hop
    anh, ve = _khung_ve()
    ve.ellipse([_tx(x0) * SS, _ty(y0) * SS, _tx(x1) * SS, _ty(y1) * SS], fill=255)
    return _thu(anh)


def mn_duong(diem, day, kin=False) -> np.ndarray:
    anh, ve = _khung_ve()
    d = [(_tx(x) * SS, _ty(y) * SS) for x, y in diem]
    if kin:
        d = d + [d[0]]
    ve.line(d, fill=255, width=max(1, int(_tr(day) * SS)), joint="curve")
    return _thu(anh)


def mn_chu_nhat_tron(hop, ban_kinh) -> np.ndarray:
    x0, y0, x1, y1 = hop
    anh, ve = _khung_ve()
    ve.rounded_rectangle([_tx(x0) * SS, _ty(y0) * SS, _tx(x1) * SS, _ty(y1) * SS],
                         radius=_tr(ban_kinh) * SS, fill=255)
    return _thu(anh)


def _hop_mo(a: np.ndarray, k: int) -> np.ndarray:
    """Làm mờ hộp bán kính k bằng ảnh tích phân."""
    if k < 1:
        return a
    dem = np.pad(a, ((k, k), (k, k)), mode="edge")
    tp = dem.cumsum(0).cumsum(1)
    tp = np.pad(tp, ((1, 0), (1, 0)))
    c = 2 * k + 1
    tong = (tp[c:, c:] - tp[:-c, c:] - tp[c:, :-c] + tp[:-c, :-c])
    return tong / float(c * c)


def lam_mem(a: np.ndarray, r: float, lan: int = 3) -> np.ndarray:
    """Xấp xỉ làm mờ Gauss bằng ba lượt mờ hộp."""
    if r <= 0:
        return a
    k = max(1, int(round(r / 1.6)))
    for _ in range(lan):
        a = _hop_mo(a, k)
    return a


def chuyen_muot(a, canh0, canh1):
    t = np.clip((a - canh0) / max(1e-6, canh1 - canh0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _hat_nhieu(hat: int, r: float) -> np.ndarray:
    """Nhiễu ngẫu nhiên đã làm mềm, dùng cho vân da và vân vải."""
    rng = np.random.default_rng(hat)
    return lam_mem(rng.random((CAO, RONG)).astype(np.float32), r) - 0.5


# --------------------------------------------------------------------------
# Bộ dựng cảnh: độ cao, hệ số phản xạ, độ bóng
# --------------------------------------------------------------------------
class Canh:
    def __init__(self):
        self.z = np.zeros((CAO, RONG), np.float32)      # bản đồ độ cao
        self.mau = np.full((CAO, RONG), 0.30, np.float32)   # hệ số phản xạ
        self.bong = np.zeros((CAO, RONG), np.float32)   # độ bóng bề mặt
        self.la_da = np.zeros((CAO, RONG), np.float32)  # vùng da, để tán xạ
        self.tien_canh = np.zeros((CAO, RONG), np.float32)  # vùng nét (không nhoè)

    # --- đắp khối ---
    def doi(self, mat_na, r, cao, mu=0.55):
        """Đắp một khối tròn lên bản đồ độ cao từ mặt nạ đã cho."""
        self.z += _tr(cao) * np.power(np.clip(lam_mem(mat_na, _tr(r)), 0, 1), mu)

    def khoet(self, mat_na, r, sau, mu=0.55):
        self.doi(mat_na, r, -sau, mu)

    def tru(self, mat_na, tam, ban_kinh, cao):
        """Khối trụ đứng: dày nhất ở giữa, mỏng dần ra hai mép."""
        h = np.clip(1.0 - ((X - _tx(tam)) / _tr(ban_kinh)) ** 2, 0, 1)
        self.z += mat_na * _tr(cao) * np.sqrt(h)

    def cau(self, mat_na, tam_x, tam_y, rx, ry, cao):
        h = np.clip(1.0 - ((X - _tx(tam_x)) / _tr(rx)) ** 2
                    - ((Y - _ty(tam_y)) / _tr(ry)) ** 2, 0, 1)
        self.z += mat_na * _tr(cao) * np.sqrt(h)

    # --- tô chất liệu ---
    def to(self, mat_na, mau=None, bong=None, da=False, tien_canh=True):
        m = np.clip(mat_na, 0, 1)
        if mau is not None:
            self.mau = self.mau * (1 - m) + np.asarray(mau, np.float32) * m
        if bong is not None:
            self.bong = self.bong * (1 - m) + bong * m
        if da:
            self.la_da = np.clip(self.la_da + m, 0, 1)
        if tien_canh:
            self.tien_canh = np.clip(self.tien_canh + m, 0, 1)

    def nhan(self, mat_na, he_so):
        """Nhân tối / làm sáng hệ số phản xạ trong một vùng."""
        m = np.clip(mat_na, 0, 1)
        self.mau = self.mau * (1 - m) + self.mau * he_so * m


# --------------------------------------------------------------------------
# 1. Hậu cảnh và bàn
# --------------------------------------------------------------------------
def dung_hau_canh(c: Canh) -> None:
    doc = np.clip(Y / CAO, 0, 1)
    c.mau = 0.44 - 0.19 * doc + 0.025 * _hat_nhieu(11, 26)
    c.z += 2.0 * lam_mem(_hat_nhieu(12, 40), 20)



def dung_ban(c: Canh) -> None:
    """Bàn phủ khăn, vẽ sau thân người vì người đứng phía sau bàn."""
    ban = mn_da_giac([(0, 1212), (RONG, 1196), (RONG, CAO), (0, CAO)])
    c.to(ban, mau=0.10, bong=0.04, tien_canh=False)
    c.z = c.z * (1 - ban) + ban * 30
    c.doi(mn_duong([(0, 1212), (RONG, 1196)], 10), 7, 9)      # mép bàn bắt sáng
    # Nếp khăn buông xuống.
    nep = np.zeros((CAO, RONG), np.float32)
    rng = np.random.default_rng(7)
    for x in range(-20, RONG + 40, 52):
        lech = int(rng.integers(-18, 18))
        nep += mn_da_giac([(x, 1214), (x + 18, 1214), (x + 24 + lech, CAO), (x + lech, CAO)])
    c.doi(np.clip(nep, 0, 1) * ban, 10, 9)
    c.mau = np.where(ban > 0.5, c.mau * (1 + 0.45 * lam_mem(_hat_nhieu(13, 6), 3)), c.mau)


# --------------------------------------------------------------------------
# 2. Thân người trong áo kaki
# --------------------------------------------------------------------------
THAN = [
    (44, 1340), (72, 1130), (110, 960), (180, 846), (296, 768), (410, 726),
    (500, 714), (590, 726), (704, 768), (820, 846), (890, 960), (928, 1130),
    (956, 1340),
]


def dung_than(c: Canh) -> None:
    than = mn_da_giac(THAN)
    c.to(than, mau=0.74, bong=0.04)
    c.tru(than, 500, 430, 120)
    c.doi(mn_bau_duc((330, 740, 670, 1040)), 46, 30)          # lồng ngực
    c.doi(mn_bau_duc((120, 780, 380, 1240)) * than, 40, 20)   # khối vai trái
    c.doi(mn_bau_duc((620, 780, 880, 1240)) * than, 40, 17)

    # Vân vải và nếp nhăn.
    van = lam_mem(_hat_nhieu(21, 9), 4) * than
    c.z += van * 2.4
    c.mau = c.mau * (1 + 0.03 * van * than)
    nep = np.zeros((CAO, RONG), np.float32)
    for a, b, d, e in ((214, 1050, 300, 1330), (300, 1110, 356, 1336),
                       (760, 1030, 690, 1320), (830, 950, 762, 1210),
                       (180, 860, 250, 1010), (820, 860, 750, 1010),
                       (392, 1180, 430, 1336), (620, 1160, 590, 1330)):
        nep += mn_duong([(a, b), ((a + d) / 2 + 10, (b + e) / 2), (d, e)], 10)
    c.khoet(np.clip(nep, 0, 1) * than, 8, 10)

    # Rãnh nách chạy từ vai xuống, tách tay áo khỏi thân.
    for diem in ([(268, 810), (238, 1010), (250, 1340)], [(732, 810), (762, 1010), (750, 1340)]):
        c.khoet(mn_duong(diem, 15) * than, 11, 17)

    # Nẹp áo và hàng cúc.
    nep_ao = mn_da_giac([(472, 748), (520, 754), (536, 1340), (480, 1340)])
    c.to(nep_ao, mau=0.66)
    c.doi(nep_ao, 7, 10)
    c.khoet(mn_duong([(478, 754), (490, 1340)], 5), 4, 8)
    for y in (880, 1000, 1120, 1240):
        cuc = mn_bau_duc((494, y - 13, 522, y + 13))
        c.to(cuc, mau=0.55, bong=0.16)
        c.cau(cuc, 508, y, 15, 15, 11)
        c.khoet(mn_bau_duc((490, y + 10, 526, y + 22)), 6, 6)

    # Cổ áo: bản cổ ôm quanh gáy, hai ve chạy chéo xuống ngực.
    ban_co = mn_da_giac([(408, 742), (452, 700), (548, 700), (592, 742), (598, 790),
                         (548, 748), (452, 748), (402, 790)])
    ve_ao = mn_da_giac([(402, 782), (452, 744), (500, 812), (548, 744), (598, 782),
                        (586, 900), (500, 862), (414, 900)])
    c.to(ban_co, mau=0.72)
    c.to(ve_ao, mau=0.76)
    c.doi(ban_co, 10, 20)
    c.doi(ve_ao, 12, 14)
    c.khoet(mn_duong([(452, 744), (500, 812), (548, 744)], 5), 4, 16)     # khe cổ áo
    c.khoet(mn_duong([(402, 782), (452, 744)], 5), 4, 10)
    c.khoet(mn_duong([(598, 782), (548, 744)], 5), 4, 10)
    c.khoet(mn_duong([(414, 898), (500, 860), (586, 898)], 6), 5, 12)     # mép ve áo
    # Bóng cổ áo hắt lên cổ.
    c.nhan(lam_mem(mn_da_giac([(452, 700), (548, 700), (548, 742), (452, 742)]), 10) * 0.8,
           0.6)

    # Hai túi ngực có nắp.
    for x0, x1 in ((286, 442), (558, 714)):
        tui = mn_da_giac([(x0, 946), (x1, 934), (x1 + 6, 1082), (x0 + 2, 1094)])
        c.doi(tui, 8, 7)
        c.khoet(mn_duong([(x0, 946), (x1, 934), (x1 + 6, 1082), (x0 + 2, 1094)], 5, kin=True),
                4, 9)
        nap = mn_da_giac([(x0 - 8, 932), (x1 + 8, 920), (x1 + 10, 970), (x0 - 6, 982)])
        c.doi(nap, 7, 12)
        c.khoet(mn_duong([(x0 - 6, 980), (x1 + 10, 968)], 6), 5, 11)


# --------------------------------------------------------------------------
# 3. Đầu: hộp sọ, ngũ quan, tóc và râu
# --------------------------------------------------------------------------
VIEN_MAT = [
    (500, 212), (540, 218), (570, 238), (590, 272), (598, 320), (596, 374),
    (588, 426), (572, 474), (550, 516), (524, 546), (500, 556), (476, 546),
    (450, 516), (428, 474), (412, 426), (404, 374), (402, 320), (410, 272),
    (430, 238), (460, 218),
]
MAT_TRAI, MAT_PHAI = 457, 545        # tâm hai mắt
MAT_Y = 374


def _mem_hoa(mat_na, r):
    """Bờ mặt nạ được vuốt mềm để khối không bị cắt vát như giấy dán."""
    return np.clip(lam_mem(mat_na, r) * 1.15, 0, 1)


def dung_dau(c: Canh) -> None:
    mat = mn_da_giac(VIEN_MAT)
    co = mn_da_giac([(464, 516), (536, 516), (550, 668), (450, 668)])

    # Cổ: khối trụ nằm sâu trong bóng cằm.
    c.to(co, mau=0.30, da=True)
    c.tru(_mem_hoa(co, 5), 500, 58, 46)
    c.nhan(co * np.clip(1.6 - np.abs(Y - _ty(560)) / _tr(70), 0, 1) * 0.75, 0.55)

    # Hộp sọ và khuôn mặt. Vòm đầu dùng mặt nạ đã vuốt mềm nên rìa mặt
    # chuyển dần vào hậu cảnh thay vì gãy thành nét cắt.
    c.to(mat, mau=0.42, bong=0.09, da=True)
    c.cau(_mem_hoa(mat, 7), 500, 384, 116, 188, 108)
    c.doi(mn_bau_duc((428, 236, 572, 356)), 32, 22)       # trán
    c.doi(mn_bau_duc((420, 300, 580, 396)), 24, 7)        # ụ mày
    c.khoet(mn_bau_duc((424, 250, 576, 296)), 15, 4)

    # Gò má cao, má hóp, hàm gầy.
    for x in (452, 548):
        c.doi(mn_bau_duc((x - 44, 394, x + 44, 452)), 20, 13)
        c.khoet(mn_bau_duc((x - 38, 450, x + 38, 522)), 22, 12)
    c.doi(mn_bau_duc((466, 494, 534, 552)), 18, 12)       # cằm
    c.khoet(mn_bau_duc((472, 478, 528, 504)), 12, 5)

    # --- hốc mắt, nhãn cầu, mí ---
    for x, lech in ((MAT_TRAI, -2), (MAT_PHAI, -2)):
        c.khoet(mn_bau_duc((x - 40, MAT_Y - 28, x + 40, MAT_Y + 24)), 18, 9)
        c.cau(mn_bau_duc((x - 24, MAT_Y - 18, x + 24, MAT_Y + 18)), x, MAT_Y, 24, 18, 9)

        # Khe mắt hẹp, mí trên trĩu xuống che gần nửa tròng đen.
        khe = mn_da_giac([(x - 22, MAT_Y + 1), (x - 11, MAT_Y - 8), (x + 10, MAT_Y - 8),
                          (x + 22, MAT_Y + 1), (x + 9, MAT_Y + 10), (x - 10, MAT_Y + 10)])
        c.to(khe, mau=0.52, bong=0.45)
        trong = mn_bau_duc((x - 11 + lech, MAT_Y - 12, x + 11 + lech, MAT_Y + 12)) * khe
        c.to(trong, mau=0.075, bong=0.8)
        c.to(mn_bau_duc((x - 4 + lech, MAT_Y - 4, x + 5 + lech, MAT_Y + 5)) * khe,
             mau=0.03, bong=0.85)
        # Mí trên đổ bóng xuống nhãn cầu.
        c.nhan(mn_da_giac([(x - 22, MAT_Y - 1), (x - 10, MAT_Y - 9), (x + 10, MAT_Y - 9),
                           (x + 22, MAT_Y - 1), (x + 18, MAT_Y + 3), (x - 18, MAT_Y + 3)]), 0.4)
        # Gờ mí trên và nếp mí.
        c.doi(mn_da_giac([(x - 26, MAT_Y - 6), (x - 11, MAT_Y - 16), (x + 11, MAT_Y - 16),
                          (x + 26, MAT_Y - 6), (x + 24, MAT_Y + 1), (x - 24, MAT_Y + 1)]),
              6, 4)
        c.khoet(mn_duong([(x - 24, MAT_Y - 8), (x, MAT_Y - 17), (x + 24, MAT_Y - 7)], 2.5),
                2, 6)
        c.doi(mn_da_giac([(x - 22, MAT_Y + 8), (x, MAT_Y + 12), (x + 22, MAT_Y + 7),
                          (x + 18, MAT_Y + 20), (x - 18, MAT_Y + 21)]), 6, 5)   # bọng mắt
        c.khoet(mn_duong([(x - 20, MAT_Y + 14), (x, MAT_Y + 17), (x + 20, MAT_Y + 13)], 2.5),
                2, 4)

    # --- mũi ---
    c.doi(mn_da_giac([(489, 330), (511, 330), (518, 438), (482, 438)]), 13, 16)
    c.cau(mn_bau_duc((484, 430, 518, 462)), 501, 446, 18, 17, 10)      # đầu mũi
    for x in (480, 522):
        c.cau(mn_bau_duc((x - 13, 434, x + 13, 460)), x, 447, 13, 13, 5)
        c.khoet(mn_bau_duc((x - 6, 446, x + 6, 458)), 3, 8)            # lỗ mũi
    c.khoet(mn_duong([(476, 462), (500, 468), (526, 462)], 4), 3, 5)
    c.nhan(mn_bau_duc((470, 424, 532, 470)) * 0.35, 0.9)

    # --- miệng đang nói ---
    c.doi(mn_da_giac([(470, 486), (500, 480), (530, 486), (526, 498), (500, 494),
                      (474, 498)]), 6, 8)                              # môi trên
    c.doi(mn_bau_duc((474, 498, 526, 520)), 8, 11)                     # môi dưới
    khe_mieng = mn_duong([(472, 492), (500, 497), (528, 491)], 6)
    c.khoet(khe_mieng, 3, 15)
    c.to(khe_mieng * 0.9, mau=0.13)
    c.nhan(mn_bau_duc((468, 484, 532, 526)) * 0.5, 0.92)

    # --- nếp nhăn ---
    for diem in ([(450, 288), (500, 282), (550, 288)], [(456, 308), (500, 303), (544, 308)],
                 [(462, 326), (500, 322), (538, 326)]):
        c.khoet(mn_duong(diem, 3.5), 2.5, 4)
    for x, h in ((MAT_TRAI, -1), (MAT_PHAI, 1)):
        for i in range(3):
            c.khoet(mn_duong([(x + h * 32, MAT_Y - 6 + i * 8),
                              (x + h * 46, MAT_Y - 15 + i * 11)], 2.5), 2, 3)
    c.khoet(mn_duong([(476, 452), (464, 484), (462, 508)], 4), 3.5, 6)   # nếp pháp lệnh
    c.khoet(mn_duong([(526, 452), (538, 484), (540, 508)], 4), 3.5, 6)

    # --- tai ---
    for x in (408, 592):
        tai = mn_bau_duc((x - 13, 348, x + 13, 412))
        c.to(tai, mau=0.38, da=True)
        c.doi(_mem_hoa(tai, 3), 9, 18)
        c.khoet(mn_bau_duc((x - 6, 362, x + 6, 400)), 6, 10)

    # Sắc độ tự nhiên của da: trán và sống mũi sáng, thái dương và quanh hàm
    # sẫm hơn, nhờ vậy khuôn mặt không phẳng như một mảng màu.
    c.nhan(np.clip(lam_mem(mn_bau_duc((398, 300, 602, 570)), 26)
                   - lam_mem(mn_bau_duc((440, 250, 560, 470)), 30), 0, 1) * 0.55, 0.84)
    c.nhan(mn_bau_duc((404, 480, 596, 580)) * 0.5, 0.9)
    c.mau = c.mau * (1 + 0.10 * lam_mem(mn_bau_duc((440, 240, 560, 360)), 30))

    # --- chất da ---
    da = np.clip(mat + co, 0, 1)
    c.mau = np.where(da > 0.5, c.mau * (1 + 0.055 * lam_mem(_hat_nhieu(31, 3), 1.5)), c.mau)
    c.z += da * lam_mem(_hat_nhieu(32, 2), 1) * 2.2

    # --- lông mày thưa ---
    rng = np.random.default_rng(41)
    soi = np.zeros((CAO, RONG), np.float32)
    for _ in range(260):
        ben = rng.choice([-1, 1])
        d = rng.uniform(16, 62)
        x0 = 500 + ben * d
        y0 = 316 - (d - 16) * 0.10 + rng.uniform(-4, 4)
        soi += mn_duong([(x0, y0), (x0 + ben * rng.uniform(5, 13), y0 - rng.uniform(1, 5))],
                        rng.uniform(1.2, 2.0))
    soi = np.clip(soi, 0, 1)
    c.mau = c.mau * (1 - soi * 0.72) + 0.10 * soi * 0.72
    c.doi(soi * 0.8, 3, 3)

    # --- tóc thưa chải ngược, để lộ vầng trán cao ---
    toc = mn_da_giac([
        (500, 202), (546, 208), (578, 230), (596, 264), (604, 322), (590, 320),
        (578, 268), (548, 244), (500, 238), (452, 244), (422, 268), (410, 320),
        (396, 322), (404, 264), (422, 230), (454, 208),
    ])
    toc = np.clip(toc + mn_bau_duc((398, 196, 602, 300)) * mn_da_giac(
        [(396, 196), (604, 196), (604, 252), (500, 236), (396, 252)]), 0, 1)
    toc = _mem_hoa(toc, 5)
    c.to(toc, mau=0.085, bong=0.16)
    c.doi(toc, 10, 5)
    rng = np.random.default_rng(43)
    soi = np.zeros((CAO, RONG), np.float32)
    for _ in range(700):
        goc = rng.uniform(-1.4, 1.4)
        r0 = rng.uniform(94, 112)
        x0 = 500 + np.sin(goc) * r0
        y0 = 384 - np.cos(goc) * (r0 * 1.62)
        x1 = 500 + np.sin(goc * 1.07) * (r0 - rng.uniform(5, 24))
        y1 = 384 - np.cos(goc * 1.07) * (r0 * 1.62 - rng.uniform(3, 18))
        soi += mn_duong([(x0, y0), ((x0 + x1) / 2 + rng.uniform(-2.5, 2.5), (y0 + y1) / 2),
                         (x1, y1)], rng.uniform(1.0, 2.2))
    soi = np.clip(soi, 0, 1) * toc
    c.mau = c.mau * (1 - soi * 0.85) + np.clip(c.mau * 2.6, 0, 0.22) * soi * 0.85
    c.z += soi * 1.6

    # --- ria mép mỏng ---
    ria = mn_da_giac([(474, 470), (500, 464), (526, 470), (528, 484), (500, 477),
                      (472, 484)])
    c.to(_mem_hoa(ria, 3) * 0.9, mau=0.20)
    c.doi(ria, 5, 4)
    rng = np.random.default_rng(45)
    soi = np.zeros((CAO, RONG), np.float32)
    for _ in range(260):
        x0 = rng.uniform(474, 526)
        y0 = rng.uniform(466, 474)
        soi += mn_duong([(x0, y0), (x0 + (x0 - 500) * 0.14, y0 + rng.uniform(7, 15))], 1.3)
    soi = np.clip(soi, 0, 1) * np.clip(lam_mem(ria, 4) * 1.6, 0, 1)
    c.mau = c.mau * (1 - soi) + 0.30 * soi


def dung_chom_rau(c: Canh) -> None:
    """Chòm râu buông xuống trước ngực, vẽ sau thân áo để phủ lên cổ áo."""
    rau = mn_da_giac([(480, 522), (500, 516), (520, 522), (517, 610), (501, 706),
                      (485, 610)])
    rau = np.clip(rau + mn_bau_duc((478, 512, 524, 560)), 0, 1)
    c.to(rau, mau=0.19, bong=0.10)
    c.doi(_mem_hoa(rau, 3), 8, 14)

    rng = np.random.default_rng(51)
    soi = np.zeros((CAO, RONG), np.float32)
    for _ in range(760):
        x0 = 500 + rng.uniform(-19, 19)
        dai = rng.uniform(44, 190)
        cong = (x0 - 500) * 0.55 + rng.uniform(-5, 5)
        soi += mn_duong([(x0, 524), (x0 + cong * 0.4, 524 + dai * 0.55),
                         (500 + cong, 524 + dai)], rng.uniform(1.0, 2.0))
    soi = np.clip(soi, 0, 1) * np.clip(rau + lam_mem(rau, 16) * 1.8, 0, 1)
    c.mau = c.mau * (1 - soi) + 0.34 * soi
    c.z += soi * 2.6
    c.to(soi * 0.85, bong=0.12, tien_canh=True)


# --------------------------------------------------------------------------
# 4. Bản Tuyên ngôn, bàn tay và micro
# --------------------------------------------------------------------------
def dung_ban_thao(c: Canh) -> None:
    giay = mn_da_giac([(404, 1200), (700, 1178), (748, 1252), (446, 1282)])
    c.to(giay, mau=0.84, bong=0.08)
    c.doi(giay, 5, 6)
    rng = np.random.default_rng(61)
    chu = np.zeros((CAO, RONG), np.float32)
    for i in range(10):
        y = 1200 + i * 8
        chu += mn_duong([(422 + i, y + 5), (422 + i + int(rng.integers(150, 262)), y - 16 + i)],
                        1.8)
    c.mau = c.mau * (1 - np.clip(chu, 0, 1) * giay * 0.5)
    c.khoet(mn_duong([(404, 1200), (446, 1282)], 5), 4, 5)


def dung_ban_tay(c: Canh) -> None:
    tay = mn_da_giac([(276, 1148), (338, 1140), (392, 1172), (406, 1208), (384, 1234),
                      (314, 1240), (276, 1210)])
    tay = np.clip(tay + mn_bau_duc((262, 1136, 356, 1226)), 0, 1)
    c.to(tay, mau=0.46, bong=0.09, da=True)
    c.doi(tay, 15, 36)
    for i in range(3):                       # kẽ ngón tay
        c.khoet(mn_duong([(344 + i * 9, 1160 + i * 19), (400 - i * 6, 1186 + i * 15)], 5),
                4, 8)
    c.doi(mn_bau_duc((260, 1132, 328, 1188)), 14, 12)     # gốc ngón cái
    c.khoet(mn_duong([(276, 1134), (270, 1180), (282, 1220)], 7), 6, 8)   # cổ tay


def dung_micro(c: Canh) -> None:
    luoi = mn_chu_nhat_tron((742, 706, 898, 942), 76)
    c.to(luoi, mau=0.24, bong=0.5)
    c.tru(luoi, 820, 82, 74)
    # Mắt lưới kim loại.
    mesh = np.zeros((CAO, RONG), np.float32)
    for yy in range(710, 942, 8):
        mesh += mn_duong([(742, yy), (898, yy)], 1.6)
    for xx in range(746, 898, 8):
        mesh += mn_duong([(xx, 706), (xx, 942)], 1.6)
    mesh = np.clip(mesh, 0, 1) * luoi
    c.mau = c.mau * (1 - mesh * 0.5)
    c.z -= mesh * 2.4

    vong = mn_chu_nhat_tron((734, 936, 906, 990), 18)
    c.to(vong, mau=0.28, bong=0.55)
    c.tru(vong, 820, 88, 32)

    than = mn_da_giac([(778, 986), (862, 986), (844, 1080), (798, 1080)])
    c.to(than, mau=0.26, bong=0.45)
    c.tru(than, 820, 44, 30)

    coc = mn_da_giac([(802, 1078), (838, 1078), (842, 1214), (798, 1214)])
    c.to(coc, mau=0.24, bong=0.5)
    c.tru(coc, 820, 22, 22)

    de = mn_bau_duc((730, 1180, 912, 1246))
    c.to(de, mau=0.20, bong=0.4)
    c.cau(de, 821, 1213, 91, 33, 30)


# --------------------------------------------------------------------------
# 5. Chiếu sáng
# --------------------------------------------------------------------------
def chieu_sang(c: Canh) -> np.ndarray:
    zx, zy = np.gradient(lam_mem(c.z, 2.6))
    doc = 0.62                      # hạ độ dốc pháp tuyến cho khối mượt
    nx, ny, nz = -zy * doc, -zx * doc, np.ones_like(c.z) * 1.0
    do_dai = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / do_dai, ny / do_dai, nz / do_dai

    def chuan(v):
        v = np.asarray(v, np.float32)
        return v / np.linalg.norm(v)

    chinh = chuan((-0.42, -0.46, 0.78))     # đèn chính chếch từ trái phía trên
    phu = chuan((0.66, -0.12, 0.55))        # đèn phụ bên phải, yếu
    mat = chuan((0.0, 0.0, 1.0))

    d_chinh = nx * chinh[0] + ny * chinh[1] + nz * chinh[2]
    d_phu = nx * phu[0] + ny * phu[1] + nz * phu[2]

    # Ánh sáng "quấn" quanh khối, mô phỏng nguồn sáng toả rộng ngoài trời.
    khuech = np.clip((d_chinh + 0.24) / 1.24, 0, 1) ** 1.30
    khuech = 0.95 * khuech + 0.22 * np.clip(d_phu, 0, 1)
    moi_truong = 0.21 + 0.09 * np.clip(nz, 0, 1)

    # Tán xạ dưới da: mượt hoá ánh sáng trên vùng da.
    mem = lam_mem(khuech, 9)
    khuech = np.where(c.la_da > 0.4, khuech * 0.55 + mem * 0.45, khuech)

    sang = c.mau * (moi_truong + khuech)

    # Phản xạ bóng.
    hx, hy, hz = chinh[0] + mat[0], chinh[1] + mat[1], chinh[2] + mat[2]
    hd = np.sqrt(hx * hx + hy * hy + hz * hz)
    tia = np.clip(nx * hx / hd + ny * hy / hd + nz * hz / hd, 0, 1)
    sang += c.bong * np.power(tia, 34) * 1.25

    # Bóng bản thân: vùng lõm sâu thì tối thêm.
    lom = np.clip(lam_mem(c.z, 26) - c.z, 0, None)
    sang *= 1.0 - 0.16 * chuyen_muot(lom, 2.0, 26.0)

    # Bóng người hắt lên phông và bóng đổ trên mặt bàn.
    nguoi = chuyen_muot(c.tien_canh, 0.2, 0.8)
    bong_do = np.roll(np.roll(lam_mem(nguoi, 26), 26, axis=1), 18, axis=0)
    sang *= 1.0 - 0.30 * np.clip(bong_do - nguoi, 0, 1)
    return sang


# --------------------------------------------------------------------------
# 6. Hiệu ứng ảnh chụp năm 1945
# --------------------------------------------------------------------------
def thanh_anh(sang: np.ndarray, tien_canh: np.ndarray, che_do: str,
              hat: float, hat_giong: int) -> Image.Image:
    v = np.clip(sang, 0, None)
    v = v / (1.0 + v * 0.55)                       # nén vùng sáng như phim
    v = np.clip(v * 1.30, 0, 1) ** 1.04

    # Hậu cảnh nhoè hơn tiền cảnh: độ sâu trường ảnh của ống kính thời đó.
    net = chuyen_muot(lam_mem(tien_canh, 3), 0.25, 0.75)
    v = v * net + lam_mem(v, 7) * (1 - net)
    # Ảnh chụp luôn mềm hơn nét vẽ một chút.
    v = 0.72 * v + 0.28 * lam_mem(v, 1.6)
    # Làm nét cục bộ (unsharp mask) cho ngũ quan bật lên.
    v = np.clip(v + 0.55 * (v - lam_mem(v, 3.2)) * net, 0, 1)

    # Tối bốn góc.
    r = np.sqrt(((X - RONG / 2) / (RONG * 0.72)) ** 2 + ((Y - CAO / 2) / (CAO * 0.74)) ** 2)
    v *= np.clip(1.06 - 0.62 * r ** 2.4, 0, 1)

    if hat > 0:
        rng = np.random.default_rng(hat_giong)
        nhieu = rng.normal(0, 1, (CAO, RONG)).astype(np.float32)
        nhieu = lam_mem(nhieu, 1.0) * 3.4
        # Hạt bạc nổi rõ ở vùng trung gian, mờ ở vùng sáng và tối.
        v = np.clip(v + nhieu * hat * 0.019 * (v * (1 - v) * 4) ** 0.7, 0, 1)

    x = np.clip(v * 255, 0, 255).astype(np.uint8)
    anh = Image.fromarray(x, mode="L")
    if che_do == "sepia":
        anh = ImageOps.colorize(anh, black=(38, 28, 20), white=(248, 242, 228),
                                mid=(146, 124, 96))
    else:
        anh = anh.convert("RGB")

    if hat > 0:                                    # vài vết xước của bản in cũ
        ve = ImageDraw.Draw(anh)
        rng = np.random.default_rng(hat_giong + 1)
        for _ in range(int(2 * hat)):
            xx = int(rng.choice([rng.integers(24, 200), rng.integers(940, 986)]))
            yy = int(rng.integers(0, CAO - 220))
            ve.line([(xx, yy), (xx + int(rng.integers(-3, 3)), yy + int(rng.integers(90, 240)))],
                    fill=(178, 170, 158), width=1)

    anh = ImageOps.expand(anh, border=20, fill=(240, 234, 218))
    anh = ImageOps.expand(anh, border=2, fill=(120, 110, 94))
    return anh


def ghi_chu_thich(anh: Image.Image) -> Image.Image:
    """Thêm dòng chú thích dưới ảnh (bỏ qua nếu máy không có phông chữ)."""
    dong = ["Chủ tịch Hồ Chí Minh đọc Tuyên ngôn Độc lập",
            "Quảng trường Ba Đình, ngày 2 tháng 9 năm 1945"]
    for d in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/Library/Fonts/Arial Unicode.ttf", "C:/Windows/Fonts/times.ttf"):
        if os.path.exists(d):
            phong = ImageFont.truetype(d, 28)
            break
    else:
        return anh

    khung = Image.new("RGB", (anh.size[0], anh.size[1] + 104), (240, 234, 218))
    khung.paste(anh, (0, 0))
    ve = ImageDraw.Draw(khung)
    for i, chu in enumerate(dong):
        rong = ve.textbbox((0, 0), chu, font=phong)[2]
        ve.text(((anh.size[0] - rong) / 2, anh.size[1] + 20 + i * 36), chu,
                font=phong, fill=(70, 58, 44))
    return khung


# --------------------------------------------------------------------------
def ve_toan_bo(che_do: str = "sepia", hat: float = 1.0, hat_giong: int = 1945,
               chu_thich: bool = False) -> Image.Image:
    c = Canh()
    dat_bien_doi()
    dung_hau_canh(c)
    # Đầu được mô tả trong hệ toạ độ riêng rồi phóng to đặt vào khung ảnh,
    # nhờ vậy phần chân dung chiếm khuôn hình đúng như bức ảnh gốc.
    dat_bien_doi(1.6, -300.0, -242.4)
    dung_dau(c)          # đầu và cổ dựng trước để cổ áo trùm lên
    dat_bien_doi()
    dung_than(c)
    dat_bien_doi(1.6, -300.0, -242.4)
    dung_chom_rau(c)
    dat_bien_doi()
    dung_ban(c)          # mặt bàn che phần dưới thân: người đứng sau bàn
    dung_ban_tay(c)
    dung_ban_thao(c)
    dung_micro(c)
    anh = thanh_anh(chieu_sang(c), c.tien_canh, che_do, hat, hat_giong)
    return ghi_chu_thich(anh) if chu_thich else anh


def main() -> None:
    bp = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    bp.add_argument("-o", "--output", default="tuyen_ngon_doc_lap.png",
                    help="tên tệp ảnh xuất ra (mặc định: tuyen_ngon_doc_lap.png)")
    bp.add_argument("--che-do", choices=["sepia", "xam"], default="sepia",
                    help="tông màu: sepia (ảnh cũ) hoặc xam (đen trắng)")
    bp.add_argument("--hat", type=float, default=1.0,
                    help="độ đậm của hạt phim, 0 là tắt (mặc định: 1.0)")
    bp.add_argument("--chu-thich", action="store_true",
                    help="in thêm dòng chú thích dưới ảnh")
    bp.add_argument("--seed", type=int, default=1945,
                    help="hạt giống ngẫu nhiên cho hạt phim và vết xước")
    ts = bp.parse_args()

    anh = ve_toan_bo(che_do=ts.che_do, hat=ts.hat, hat_giong=ts.seed,
                     chu_thich=ts.chu_thich)
    anh.save(ts.output)
    print(f"Đã lưu {ts.output} ({anh.size[0]}x{anh.size[1]})")


if __name__ == "__main__":
    main()
