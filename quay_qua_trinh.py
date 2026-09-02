#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quay lại quá trình dựng bức tranh thành một đoạn phim.

Phim đi qua đúng các bước mà `vach_net_tu_anh.py` thực hiện, mỗi khung hình
đều lấy từ kết quả thật của bước ấy chứ không dàn dựng:

    ảnh chụp -> tìm bốn góc -> nắn phẳng -> tách vùng vàng
             -> dò biên -> dựng lại thành vector

Yêu cầu: pip install pillow numpy scikit-image imageio imageio-ffmpeg

    python3 quay_qua_trinh.py anh_chup.jpg -o qua_trinh.mp4
    python3 quay_qua_trinh.py anh_chup.jpg -o qua_trinh.gif
"""

from __future__ import annotations

import argparse

import numpy as np
from PIL import Image, ImageDraw

import vach_net_tu_anh as vn
import ve_tranh_co_dong as lo

KH = 1200                      # cạnh khung hình
BANG = 168                     # dải chữ phía dưới
NEN = (24, 20, 22)
CHU = (238, 232, 220)
CHU_MO = (150, 144, 136)


def _phong(co):
    return lo.lay_phong(co)


def khung(noi_dung: Image.Image, tieu_de: str, lenh: str = "") -> Image.Image:
    """Đặt ảnh nội dung vào giữa khung, kèm dòng tiêu đề và dòng lệnh."""
    k = Image.new("RGB", (KH, KH + BANG), NEN)
    o = KH - 80
    ty_le = min(o / noi_dung.width, o / noi_dung.height)
    nd = noi_dung.resize((max(1, int(noi_dung.width * ty_le)),
                          max(1, int(noi_dung.height * ty_le))), Image.LANCZOS)
    k.paste(nd, ((KH - nd.width) // 2, (KH - nd.height) // 2))
    ve = ImageDraw.Draw(k)
    _dong_chu(ve, tieu_de, (60, KH + 44), 44, CHU)
    if lenh:
        _dong_chu(ve, lenh, (60, KH + 108), 30, CHU_MO)
    return k


def _dong_chu(ve, chu, tam, co, mau):
    """Viết một dòng, tự thu nhỏ cỡ chữ nếu dài quá bề ngang khung."""
    rong_toi_da = KH - 2 * tam[0]
    phong = _phong(co)
    while co > 14 and phong.getbbox(chu)[2] > rong_toi_da:
        co -= 2
        phong = _phong(co)
    ve.text(tam, chu, font=phong, fill=mau, anchor="lm")


def _tron(a: Image.Image, b: Image.Image, t: float) -> Image.Image:
    return Image.blend(a.convert("RGB"), b.convert("RGB"), t)


def _anh_mat_na(m: np.ndarray) -> Image.Image:
    """Mặt nạ nhị phân hiện thành vàng trên nền tối."""
    r = np.where(m, 250, 34).astype("uint8")
    g = np.where(m, 238, 30).astype("uint8")
    b = np.where(m, 58, 32).astype("uint8")
    return Image.fromarray(np.dstack([r, g, b]))


def _ve_hinh(hinh, kich_thuoc, den_hinh, vien_thoi=0):
    """Vẽ `den_hinh` hình đầu tiên; `vien_thoi` thì chỉ vẽ đường biên."""
    anh = Image.new("RGB", kich_thuoc, NEN if vien_thoi else lo.DO)
    ve = ImageDraw.Draw(anh)
    for i, (_, mau, q) in enumerate(hinh[:den_hinh]):
        diem = [(float(x), float(y)) for y, x in q]
        if vien_thoi:
            ve.line(diem + [diem[0]], fill=lo.VANG if mau == "vang" else (170, 60, 70),
                    width=2, joint="curve")
        else:
            ve.polygon(diem, fill=lo.VANG if mau == "vang" else lo.DO)
    return anh


def dung_phim(duong_anh: str, fps: int = 25, nhanh: float = 1.0):
    """Sinh lần lượt các khung hình của đoạn phim."""
    def lap(n):
        return max(1, int(round(n / nhanh)))

    anh = Image.open(duong_anh).convert("RGB")
    px = np.asarray(anh).astype(np.int16)

    # --- Bước 1: ảnh chụp ---
    for _ in range(lap(fps * 2)):
        yield khung(anh, "Bước 1 — ảnh chụp bức tranh tường",
                    "$ python3 vach_net_tu_anh.py anh_chup.jpg -o net_tranh_tuong.json")

    # --- Bước 2: tìm bốn góc ---
    goc = vn.lui_khung(vn.tim_khung(px), 0.014)   # lùi vào để bỏ viền cửa
    for i in range(lap(fps * 2)):
        t = min(1.0, i / max(1, lap(fps * 1.2)))
        tam = anh.copy()
        ve = ImageDraw.Draw(tam)
        canh = [(goc[j], goc[(j + 1) % 4]) for j in range(4)]
        for j, (p, q) in enumerate(canh):
            if t > j / 4.0:
                k = min(1.0, (t - j / 4.0) * 4)
                ve.line([p, (p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k)],
                        fill=(90, 240, 160), width=3)
        for p in goc:
            ve.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], fill=(90, 240, 160))
        yield khung(tam, "Bước 2 — tìm bốn góc bức tranh",
                    "lọc điểm ảnh đỏ và vàng, khớp đường thẳng cho hai mép bên")

    # --- Bước 3: nắn phẳng, xoay dần về hình chữ nhật ---
    W, H = anh.size
    x0 = min(p[0] for p in goc); x1 = max(p[0] for p in goc)
    y0 = min(p[1] for p in goc); y1 = max(p[1] for p in goc)
    chu_nhat = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    so_khung = lap(fps * 2)
    for i in range(so_khung + lap(fps // 2)):
        t = min(1.0, i / so_khung)
        muot = t * t * (3 - 2 * t)
        dich = [(p[0] + (q[0] - p[0]) * muot, p[1] + (q[1] - p[1]) * muot)
                for p, q in zip(goc, chu_nhat)]
        hs = vn._he_so_phoi_canh(dich, goc)
        yield khung(anh.transform((W, H), Image.PERSPECTIVE, hs, Image.BICUBIC),
                    "Bước 3 — nắn phẳng bằng biến đổi phối cảnh",
                    "bốn góc được đưa về đúng một hình chữ nhật")

    ty_le = (goc[2][1] - goc[0][1]) / max(1e-6, goc[1][0] - goc[0][0])
    rong = 1900
    cao = int(round(rong * ty_le))
    phang = vn.nan_phang(anh, goc, rong, cao)

    # --- Bước 4: tách vùng vàng ---
    m = vn.mat_na_vang(phang, nho_nhat=12.0)
    anh_m = _anh_mat_na(m)
    for i in range(lap(fps)):
        yield khung(_tron(phang, anh_m, min(1.0, i / max(1, lap(fps * 0.7)))),
                    "Bước 4 — tách vùng vàng theo sắc màu",
                    "ngưỡng trễ hai mức trên độ vàng min(R,G) - B")
    for _ in range(lap(fps)):
        yield khung(anh_m, "Bước 4 — tách vùng vàng theo sắc màu",
                    "mức thấp vét nét mảnh, chỉ giữ phần nối với mảng chắc chắn")

    # --- Bước 5: dò biên ---
    hinh = vn.vach_net(m, 0.9, 12.0, 1.1, bo_qua=[o for _, o in vn.O_CHU])
    so_khung = lap(fps * 3)
    for i in range(so_khung):
        den = int(len(hinh) * (i + 1) / so_khung)
        yield khung(_ve_hinh(hinh, (rong, cao), den, vien_thoi=1),
                    "Bước 5 — dò biên và giản lược thành đa giác",
                    f"marching squares + Douglas-Peucker · {den}/{len(hinh)} hình")

    # --- Bước 6: dựng lại thành vector ---
    so_khung = lap(fps * 4)
    for i in range(so_khung):
        den = int(len(hinh) * (i + 1) / so_khung)
        diem = sum(len(h[2]) for h in hinh[:den])
        yield khung(_ve_hinh(hinh, (rong, cao), den),
                    "Bước 6 — dựng lại thành hình vector",
                    f"vẽ từ hình lớn đến hình nhỏ · {den} hình, {diem} điểm")

    # --- Kết quả ---
    cuoi = _ve_hinh(hinh, (rong, cao), len(hinh))
    ve = ImageDraw.Draw(cuoi)
    for c, o in vn.O_CHU:
        ox0, oy0, ox1, oy1 = o
        rong_o, cao_o = (ox1 - ox0) * rong, (oy1 - oy0) * cao
        hop = lo.lay_phong(100).getbbox(c)
        co = int(100 * min(rong_o / max(1, hop[2] - hop[0]),
                           cao_o / max(1, hop[3] - hop[1])))
        ve.text((ox0 * rong, (oy0 + oy1) / 2 * cao), c, font=lo.lay_phong(max(10, co)),
                fill=lo.VANG, anchor="lm")
    diem = sum(len(h[2]) for h in hinh)
    for _ in range(lap(fps * 3)):
        yield khung(cuoi, "Kết quả — đường nét giữ đúng bản vẽ tay trên tường",
                    f"{len(hinh)} hình, {diem} điểm · xuất được cả PNG lẫn SVG")


def main() -> None:
    bp = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    bp.add_argument("anh", help="ảnh chụp bức tranh tường")
    bp.add_argument("-o", "--output", default="qua_trinh.mp4",
                    help="tệp phim xuất ra (.mp4 hoặc .gif)")
    bp.add_argument("--fps", type=int, default=25, help="số khung hình mỗi giây")
    bp.add_argument("--nhanh", type=float, default=1.0,
                    help="hệ số tua nhanh, 2 là phim ngắn đi một nửa")
    ts = bp.parse_args()

    khung_hinh = dung_phim(ts.anh, ts.fps, ts.nhanh)
    if ts.output.lower().endswith(".gif"):
        # Ảnh động: thu nhỏ và bỏ bớt khung cho tệp gọn.
        ds = []
        for i, k in enumerate(khung_hinh):
            if i % 2:
                continue
            nho = k.resize((640, int(640 * k.height / k.width)), Image.LANCZOS)
            ds.append(nho.convert("P", palette=Image.ADAPTIVE, colors=96))
        ds[0].save(ts.output, save_all=True, append_images=ds[1:],
                   duration=int(2000 / ts.fps), loop=0, optimize=True)
        so = len(ds)
    else:
        import imageio.v2 as iio
        so = 0
        with iio.get_writer(ts.output, fps=ts.fps, quality=8,
                            macro_block_size=8) as w:
            for k in khung_hinh:
                w.append_data(np.asarray(k))
                so += 1
    print(f"Đã lưu {ts.output} ({so} khung hình, {so / ts.fps:.1f} giây)")


if __name__ == "__main__":
    main()
