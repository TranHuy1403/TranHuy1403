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

    __slots__ = ("x", "y", "vx", "vy", "mau", "doi", "tuoi", "lap_lanh")

    def __init__(self, x, y, vx, vy, mau, doi, lap_lanh=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.mau, self.doi, self.tuoi, self.lap_lanh = mau, doi, 0.0, lap_lanh


class PhaoHoa:
    """Bầu trời có pháo hoa, tiến từng khung hình một."""

    def __init__(self, rong: int, cao: int, hat_giong: int = 2, mat_do: float = 0.085):
        self.rong, self.cao = rong, cao
        self.rng = random.Random(hat_giong)
        self.mat_do = mat_do
        self.troi = np.zeros((cao, rong, 3), np.float32)
        self.qua = []           # pháo đang bay lên
        self.tia = []           # tia lửa sau khi nổ
        self.khung = 0

    # -- sinh pháo --
    def ban_len(self, x=None, manh=1.0):
        x = self.rng.uniform(self.rong * 0.10, self.rong * 0.90) if x is None else x
        dich = self.rng.uniform(self.cao * 0.14, self.cao * 0.46)   # độ cao muốn nổ
        # Nhân thêm hệ số vì lực cản ăn bớt vận tốc trên đường bay lên.
        vy = -math.sqrt(max(1.0, 2 * TRONG_LUC * (self.cao - dich))) * 1.55 * manh
        mau = self.rng.choice(BANG_MAU)
        self.qua.append(Tia(x, self.cao + 8, self.rng.uniform(-0.5, 0.5), vy, mau,
                            doi=400))

    def no(self, x, y, mau, so_tia=None):
        """Nổ: các tia toả đều theo mọi hướng, tốc độ phân tán quanh một trị số."""
        so_tia = so_tia or self.rng.randint(200, 340)
        nhanh = self.rng.uniform(3.4, 5.6)
        vong = self.rng.random() < 0.35          # vài quả nổ thành vòng tròn
        for _ in range(so_tia):
            goc = self.rng.uniform(0, math.tau)
            v = nhanh * (self.rng.uniform(0.94, 1.06) if vong
                         else abs(self.rng.gauss(1.0, 0.32)))
            pha = self.rng.uniform(0.82, 1.0)
            m = tuple(c * pha for c in mau)
            self.tia.append(Tia(x, y, math.cos(goc) * v, math.sin(goc) * v, m,
                                doi=self.rng.uniform(55, 120),
                                lap_lanh=self.rng.uniform(0, math.tau)))

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
            self._cham(q.x, q.y, q.mau, 0.55)
            if q.vy > -0.6:                       # tới đỉnh thì nổ
                self.no(q.x, q.y, q.mau)
            else:
                con_lai.append(q)
        self.qua = con_lai

        self.troi *= MO_DAN
        song, xs, ys, ws = [], [], [], []
        for t in self.tia:
            t.tuoi += 1
            if t.tuoi >= t.doi:
                continue
            t.vy = t.vy * CAN + TRONG_LUC
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
