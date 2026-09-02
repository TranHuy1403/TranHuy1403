#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mô phỏng pháo hoa bằng hệ hạt.

Mỗi quả pháo là một hạt bay lên, chịu trọng lực và lực cản; tới đỉnh thì nổ
thành hàng trăm tia. Mỗi tia lại là một hạt riêng, có vận tốc, tuổi thọ và
độ sáng nhấp nháy. Vệt sáng có được nhờ giữ lại khung hình trước rồi nhân
với một hệ số nhỏ hơn một, nên ánh sáng cũ mờ dần thay vì biến mất.

Chạy riêng để xem thử:

    python3 phao_hoa.py -o phao_hoa.mp4 --giay 8
"""

from __future__ import annotations

import argparse
import math
import random

import numpy as np
from PIL import Image, ImageChops, ImageFilter

TRONG_LUC = 0.075          # trọng lực trên mỗi khung hình
CAN = 0.986                # lực cản không khí
MO_DAN = 0.855             # hệ số làm mờ vệt sáng cũ

# Màu pháo: vàng cờ, đỏ son, trắng bạc, cam lửa.
BANG_MAU = [(255, 214, 64), (255, 92, 74), (255, 246, 226), (255, 156, 60),
            (255, 236, 140)]


class Tia:
    """Một tia lửa: vị trí, vận tốc, màu, tuổi thọ."""

    __slots__ = ("x", "y", "vx", "vy", "mau", "doi", "tuoi", "lap_lanh", "nang")

    def __init__(self, x, y, vx, vy, mau, doi, lap_lanh=0.0, nang=1.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.mau, self.doi, self.tuoi, self.lap_lanh = mau, doi, 0.0, lap_lanh
        self.nang = nang            # tia nặng thì rơi nhanh, cho dáng liễu rủ


class PhaoHoa:
    """Bầu trời có pháo hoa, tiến từng khung hình một."""

    def __init__(self, rong: int, cao: int, hat_giong: int = 2, mat_do: float = 0.085):
        self.rong, self.cao = rong, cao
        self.rng = random.Random(hat_giong)
        self.mat_do = mat_do
        self.troi = np.zeros((cao, rong, 3), np.float32)
        self.sao = self._gieo_sao(140)
        y, x = np.mgrid[0:cao, 0:rong]
        r = np.sqrt(((x - rong / 2) / (rong * 0.62)) ** 2
                    + ((y - cao / 2) / (cao * 0.68)) ** 2)
        self.mo_goc = np.clip(1.05 - 0.55 * r ** 2.2, 0, 1).astype(np.float32)
        self.qua = []           # pháo đang bay lên
        self.tia = []           # tia lửa sau khi nổ
        self.khung = 0

    def _gieo_sao(self, so):
        """Vài ngôi sao mờ cho bầu trời có chiều sâu."""
        return [(self.rng.randrange(self.rong), self.rng.randrange(self.cao),
                 self.rng.uniform(0.10, 0.45), self.rng.uniform(0, math.tau))
                for _ in range(so)]

    # -- sinh pháo --
    def ban_len(self, x=None, manh=1.0):
        x = self.rng.uniform(self.rong * 0.10, self.rong * 0.90) if x is None else x
        dich = self.rng.uniform(self.cao * 0.08, self.cao * 0.44)   # độ cao muốn nổ
        # Nhân thêm hệ số vì lực cản ăn bớt vận tốc trên đường bay lên.
        vy = -math.sqrt(max(1.0, 2 * TRONG_LUC * (self.cao - dich))) * 1.78 * manh
        mau = self.rng.choice(BANG_MAU)
        self.qua.append(Tia(x, self.cao + 8, self.rng.uniform(-0.5, 0.5), vy, mau,
                            doi=400))

    def no(self, x, y, mau, kieu=None):
        """Nổ pháo. Mỗi kiểu cho một dáng khác nhau.

        - `vong`  : mọi tia cùng tốc độ, nở thành vòng tròn đều.
        - `cuc`   : tốc độ tản quanh một trị số, dáng bông cúc.
        - `lieu`  : tia nặng và sống lâu, rủ xuống như cành liễu.
        - `kep`   : hai lớp, lõi một màu, vành ngoài một màu khác.
        """
        kieu = kieu or self.rng.choices(["cuc", "vong", "lieu", "kep"],
                                        weights=[4, 3, 2, 3])[0]
        self._chop(x, y, mau)
        if kieu == "lieu":
            mau = (255, 208, 120)
            lop = [(self.rng.uniform(2.0, 3.0), (150, 240), 2.3, 320)]
        elif kieu == "vong":
            lop = [(self.rng.uniform(3.6, 5.0), (60, 100), 1.0, 300)]
        elif kieu == "kep":
            mau2 = self.rng.choice([m for m in BANG_MAU if m != mau])
            lop = [(self.rng.uniform(2.2, 3.0), (50, 90), 1.0, 150),
                   (self.rng.uniform(4.4, 6.2), (60, 110), 1.0, 220)]
        else:
            lop = [(self.rng.uniform(3.4, 5.4), (55, 120), 1.0, 300)]

        for chi_so, (nhanh, doi, nang, so_tia) in enumerate(lop):
            m_lop = mau2 if kieu == "kep" and chi_so == 1 else mau
            deu = kieu in ("vong", "kep")
            for _ in range(so_tia):
                goc = self.rng.uniform(0, math.tau)
                v = nhanh * (self.rng.uniform(0.94, 1.06) if deu
                             else abs(self.rng.gauss(1.0, 0.32)))
                pha = self.rng.uniform(0.82, 1.0)
                self.tia.append(Tia(x, y, math.cos(goc) * v, math.sin(goc) * v,
                                    tuple(c * pha for c in m_lop),
                                    doi=self.rng.uniform(*doi),
                                    lap_lanh=self.rng.uniform(0, math.tau),
                                    nang=nang))
        if self.rng.random() < 0.5:                  # thêm bụi sáng lấp lánh
            for _ in range(70):
                goc = self.rng.uniform(0, math.tau)
                v = abs(self.rng.gauss(1.6, 0.8))
                self.tia.append(Tia(x, y, math.cos(goc) * v, math.sin(goc) * v,
                                    (255, 250, 230), doi=self.rng.uniform(25, 60),
                                    lap_lanh=self.rng.uniform(0, math.tau), nang=0.7))

    def _chop(self, x, y, mau, ban_kinh=52):
        """Chớp sáng ngay lúc nổ, rồi tắt dần theo hệ số làm mờ của bầu trời."""
        x0, x1 = int(max(0, x - ban_kinh)), int(min(self.rong, x + ban_kinh))
        y0, y1 = int(max(0, y - ban_kinh)), int(min(self.cao, y + ban_kinh))
        if x1 <= x0 or y1 <= y0:
            return
        gx = np.arange(x0, x1, dtype=np.float32) - x
        gy = np.arange(y0, y1, dtype=np.float32) - y
        d2 = gy[:, None] ** 2 + gx[None, :] ** 2
        vet = np.exp(-d2 / (2 * (ban_kinh / 2.6) ** 2)).astype(np.float32)
        self.troi[y0:y1, x0:x1] += vet[..., None] * np.asarray(mau, np.float32) * 0.9

    # -- tiến một khung hình --
    def buoc(self) -> np.ndarray:
        self.khung += 1
        if self.rng.random() < self.mat_do:
            self.ban_len()

        con_lai = []
        for q in self.qua:
            q.vy = q.vy * CAN + TRONG_LUC
            q.vx *= CAN
            q.x += q.vx
            q.y += q.vy
            self._cham(q.x, q.y, q.mau, 0.7)
            self.tia.append(Tia(q.x + self.rng.uniform(-1.5, 1.5), q.y,
                                self.rng.uniform(-0.35, 0.35),
                                self.rng.uniform(-0.3, 0.5),
                                (200, 150, 90), doi=self.rng.uniform(5, 13),
                                lap_lanh=self.rng.uniform(0, math.tau), nang=0.5))
            if q.vy > -0.6:                       # tới đỉnh thì nổ
                self.no(q.x, q.y, q.mau)
            else:
                con_lai.append(q)
        self.qua = con_lai

        self.troi *= MO_DAN
        for x, y, sang, pha in self.sao:             # sao nhấp nháy rất nhẹ
            self.troi[y, x] += 90 * sang * (0.7 + 0.3 * math.sin(self.khung * 0.08 + pha))
        song, xs, ys, ws = [], [], [], []
        for t in self.tia:
            t.tuoi += 1
            if t.tuoi >= t.doi:
                continue
            t.vy = t.vy * CAN + TRONG_LUC * t.nang
            t.vx *= CAN
            t.x += t.vx
            t.y += t.vy
            if not (0 <= t.x < self.rong and 0 <= t.y < self.cao):
                if t.y >= self.cao:
                    continue
            con = 1.0 - t.tuoi / t.doi
            sang = con ** 1.6 * (0.75 + 0.25 * math.sin(t.tuoi * 0.55 + t.lap_lanh))
            song.append(t)
            xs.append(t.x); ys.append(t.y); ws.append((t.mau, sang))
        self.tia = song
        self._cham_nhieu(xs, ys, ws)
        return self.troi

    def _cham(self, x, y, mau, sang):
        xi, yi = int(x), int(y)
        if 0 <= xi < self.rong and 0 <= yi < self.cao:
            self.troi[yi, xi] += np.asarray(mau, np.float32) * sang

    def _cham_nhieu(self, xs, ys, ws):
        """Chấm các tia lên bầu trời, mỗi tia loang ra bốn điểm ảnh cho dày nét."""
        if not xs:
            return
        x0 = np.asarray(xs, np.float32)
        y0 = np.asarray(ys, np.float32)
        gia = np.asarray([[c * s for c in m] for m, s in ws], np.float32) * 2.6
        for lech_x, lech_y, phan in ((0, 0, 1.0), (1, 0, 0.6), (0, 1, 0.6), (1, 1, 0.35)):
            xi = np.clip((x0 + lech_x).astype(np.int32), 0, self.rong - 1)
            yi = np.clip((y0 + lech_y).astype(np.int32), 0, self.cao - 1)
            np.add.at(self.troi, (yi, xi), gia * phan)

    # -- kết xuất --
    def anh(self, nen=(12, 10, 20), quang=True) -> Image.Image:
        v = 1.0 - np.exp(-np.clip(self.troi / 255.0, 0, 8) * 2.6)   # nén sáng
        v *= self.mo_goc[..., None]                                 # tối dần bốn góc
        anh = Image.fromarray(np.clip(v * 255, 0, 255).astype(np.uint8), "RGB")
        if quang:
            # Quầng sáng: cộng thêm bản làm mờ, không pha trộn, để đốm sáng
            # giữ nguyên độ chói mà vẫn toả hào quang ra chung quanh.
            hao = anh.filter(ImageFilter.GaussianBlur(9))
            anh = ImageChops.add(anh, Image.eval(hao, lambda p: int(p * 0.75)))
        return ImageChops.add(Image.new("RGB", anh.size, nen), anh)


def main() -> None:
    bp = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    bp.add_argument("-o", "--output", default="phao_hoa.mp4", help="tệp phim xuất ra")
    bp.add_argument("--rong", type=int, default=1280, help="bề ngang khung hình")
    bp.add_argument("--cao", type=int, default=960, help="chiều cao khung hình")
    bp.add_argument("--giay", type=float, default=8.0, help="độ dài, tính bằng giây")
    bp.add_argument("--fps", type=int, default=25, help="số khung hình mỗi giây")
    bp.add_argument("--seed", type=int, default=2, help="hạt giống ngẫu nhiên")
    ts = bp.parse_args()

    import imageio.v2 as iio
    troi = PhaoHoa(ts.rong, ts.cao, ts.seed)
    so = int(ts.giay * ts.fps)
    with iio.get_writer(ts.output, fps=ts.fps, quality=8, macro_block_size=8) as w:
        for i in range(so):
            if i in (2, 14, 30):
                troi.ban_len()
            troi.buoc()
            w.append_data(np.asarray(troi.anh()))
    print(f"Đã lưu {ts.output} ({so} khung hình, {so / ts.fps:.1f} giây)")


if __name__ == "__main__":
    main()
