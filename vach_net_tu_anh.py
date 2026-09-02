#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vạch nét bức tranh tường từ một tấm ảnh chụp, xuất ra dữ liệu vector.

Chương trình làm bốn việc:

1. **Tìm khung tranh.** Lọc các điểm ảnh có màu đỏ hoặc vàng đậm, rồi khớp
   đường thẳng cho mép trái và mép phải để suy ra bốn góc của bức tranh.
2. **Nắn phẳng.** Dùng phép biến đổi phối cảnh đưa bốn góc ấy về đúng một
   hình chữ nhật, khử độ nghiêng của máy ảnh.
3. **Tách hai màu.** Chuyển sang hệ màu HSV rồi lấy vùng vàng theo sắc màu,
   nên các vạch tối của cánh cửa cuốn và vệt loá không ảnh hưởng. Mặt nạ
   được dọn bằng các phép hình thái học.
4. **Vạch biên và giản lược.** Dò biên bằng thuật toán marching squares cho
   độ chính xác dưới một điểm ảnh, rồi giản lược bằng Douglas-Peucker. Mỗi
   đường biên được xác định màu bằng cách lấy mẫu ngay bên trong nó; các
   hình được xếp theo diện tích giảm dần để hình nhỏ nằm đè lên hình lớn.

Kết quả ghi ra tệp JSON, `ve_theo_tuong.py` chỉ cần Pillow là vẽ lại được.

Yêu cầu: pip install pillow numpy scikit-image

    python3 vach_net_tu_anh.py anh_chup.jpg -o net_tranh_tuong.json
"""

from __future__ import annotations

import argparse
import json

import numpy as np
from PIL import Image
from skimage import filters, measure, morphology

# Hai nhãn quần đảo trong tranh quá nhỏ để vạch nét cho ra chữ đọc được, nên
# được ghi lại thành ô chữ (toạ độ theo tỉ lệ khung tranh) để vẽ lại bằng phông.
O_CHU = [("HOÀNG SA", (0.850, 0.452, 0.958, 0.482)),
         ("TRƯỜNG SA", (0.842, 0.788, 0.955, 0.818))]


def tim_khung(px: np.ndarray, le_tren: int = 140):
    """Tìm bốn góc bức tranh: lọc điểm ảnh đỏ hoặc vàng rồi khớp hai mép bên."""
    mx, mn = px.max(2), px.min(2)
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    tranh = (mx - mn > 70) & (mx > 90) & (b < np.maximum(r, g) - 20)
    dem = tranh.sum(1)
    nguong = 0.6 * dem[le_tren:].max()
    hang = [y for y in range(le_tren, len(dem)) if dem[y] > nguong]
    tren, duoi = min(hang), max(hang)
    lui = max(2, (duoi - tren) // 60)          # lùi vào để tránh mép ảnh
    ys = np.arange(tren + lui, duoi - lui)
    trai = np.array([np.nonzero(tranh[y])[0].min() for y in ys])
    phai = np.array([np.nonzero(tranh[y])[0].max() for y in ys])
    kt, kp = np.polyfit(ys, trai, 1), np.polyfit(ys, phai, 1)
    tren += lui
    duoi -= lui
    return [(float(np.polyval(kt, tren)), float(tren)),
            (float(np.polyval(kp, tren)), float(tren)),
            (float(np.polyval(kp, duoi)), float(duoi)),
            (float(np.polyval(kt, duoi)), float(duoi))]


def _he_so_phoi_canh(dich, nguon):
    A, B = [], []
    for (x, y), (u, v) in zip(dich, nguon):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float))


def nan_phang(anh: Image.Image, goc, rong: int, cao: int) -> Image.Image:
    hs = _he_so_phoi_canh([(0, 0), (rong, 0), (rong, cao), (0, cao)], goc)
    return anh.transform((rong, cao), Image.PERSPECTIVE, hs, Image.BICUBIC)


def mat_na_vang(anh: Image.Image, don: int = 2, nho_nhat: float = 14.0) -> np.ndarray:
    """Vùng màu vàng, lấy theo sắc màu nên không sợ vạch cửa cuốn và vệt loá."""
    hsv = np.asarray(anh.convert("HSV")).astype(np.int16)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = (h > 25) & (h < 62) & (s > 60) & (v > 110)
    vun = max(4, int(nho_nhat))          # giữ lại được cả những đảo nhỏ
    m = morphology.remove_small_objects(m, vun)
    m = morphology.remove_small_holes(m, vun)
    if don:
        m = morphology.closing(m, morphology.disk(don))
        m = morphology.opening(m, morphology.disk(max(1, don - 1)))
    return m


def _dien_tich(p):
    x, y = p[:, 1], p[:, 0]
    return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def _diem_ben_trong(p):
    """Một điểm chắc chắn nằm trong đa giác: cắt ngang qua giữa hình."""
    y = (p[:, 0].min() + p[:, 0].max()) / 2.0
    xs = []
    for i in range(len(p)):
        y0, x0 = p[i]
        y1, x1 = p[(i + 1) % len(p)]
        if (y0 - y) * (y1 - y) < 0:
            xs.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
    xs.sort()
    return y, ((xs[0] + xs[1]) / 2.0 if len(xs) >= 2 else float(p[:, 1].mean()))


def vach_net(m: np.ndarray, dung_sai: float, nho_nhat: float, mem: float,
             bo_qua=()):
    """Dò biên vùng vàng rồi giản lược, trả về danh sách hình đã xếp thứ tự.

    `bo_qua` là các ô (theo tỉ lệ khung) sẽ không lấy nét, dành cho phần chữ
    quá nhỏ để vạch cho ra hình, sẽ được vẽ lại bằng phông chữ.
    """
    cao, rong = m.shape
    muot = filters.gaussian(m.astype(float), mem)
    hinh = []
    for p in measure.find_contours(muot, 0.5):
        if len(p) < 10 or _dien_tich(p) < nho_nhat:
            continue
        q = measure.approximate_polygon(p, tolerance=dung_sai)
        if len(q) < 4:
            continue
        yy, xx = _diem_ben_trong(q)
        yi, xi = int(round(yy)), int(round(xx))
        if not (0 <= yi < cao and 0 <= xi < rong):
            continue
        if any(x0 * rong - 12 < xx < x1 * rong + 12 and y0 * cao - 10 < yy < y1 * cao + 10
               for x0, y0, x1, y1 in bo_qua):
            continue                      # nằm trong ô chữ, để phông chữ lo
        hinh.append((_dien_tich(q), "vang" if m[yi, xi] else "do", q))
    hinh.sort(key=lambda t: -t[0])          # hình lớn vẽ trước, hình nhỏ đè lên
    return hinh


def main() -> None:
    bp = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    bp.add_argument("anh", help="ảnh chụp bức tranh tường")
    bp.add_argument("-o", "--output", default="net_tranh_tuong.json",
                    help="tệp dữ liệu vector xuất ra")
    bp.add_argument("--rong", type=int, default=1300,
                    help="bề rộng ảnh sau khi nắn phẳng, tính bằng điểm ảnh")
    bp.add_argument("--dung-sai", type=float, default=0.9,
                    help="sai số cho phép khi giản lược đường biên (điểm ảnh)")
    bp.add_argument("--nho-nhat", type=float, default=4.0,
                    help="bỏ qua các hình có diện tích nhỏ hơn ngần này")
    bp.add_argument("--mem", type=float, default=1.1,
                    help="độ làm mềm mặt nạ trước khi dò biên")
    bp.add_argument("--xem", help="ghi thêm ảnh nắn phẳng ra tệp này để đối chiếu")
    ts = bp.parse_args()

    anh = Image.open(ts.anh).convert("RGB")
    goc = tim_khung(np.asarray(anh).astype(np.int16))
    ty_le = (goc[2][1] - goc[0][1]) / max(1e-6, goc[1][0] - goc[0][0])
    cao = int(round(ts.rong * ty_le))
    phang = nan_phang(anh, goc, ts.rong, cao)
    if ts.xem:
        phang.save(ts.xem)

    m = mat_na_vang(phang, nho_nhat=ts.nho_nhat)
    hinh = vach_net(m, ts.dung_sai, ts.nho_nhat, ts.mem,
                    bo_qua=[o for _, o in O_CHU])

    du_lieu = {
        "khung": [ts.rong, cao],
        "goc_trong_anh": [[round(x, 1), round(y, 1)] for x, y in goc],
        "hinh": [{"mau": mau,
                  "diem": [[round(float(x), 2), round(float(y), 2)] for y, x in q]}
                 for _, mau, q in hinh],
        "chu": [{"chu": chu, "o": list(o)} for chu, o in O_CHU],
    }
    with open(ts.output, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False)
    print(f"Đã vạch {len(hinh)} hình, "
          f"{sum(len(h['diem']) for h in du_lieu['hinh'])} điểm -> {ts.output}")


if __name__ == "__main__":
    main()
