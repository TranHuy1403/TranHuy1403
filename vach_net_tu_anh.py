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
from PIL import Image, ImageDraw
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


def lui_khung(goc, lui: float):
    """Lùi bốn góc vào phía trong, để không lấy phải viền cửa quanh bức tranh."""
    tx = sum(p[0] for p in goc) / 4.0
    ty = sum(p[1] for p in goc) / 4.0
    return [(x + (tx - x) * lui, y + (ty - y) * lui) for x, y in goc]


def nan_phang(anh: Image.Image, goc, rong: int, cao: int) -> Image.Image:
    hs = _he_so_phoi_canh([(0, 0), (rong, 0), (rong, cao), (0, cao)], goc)
    return anh.transform((rong, cao), Image.PERSPECTIVE, hs, Image.BICUBIC)


def mat_na_vang(anh: Image.Image, don: int = 1, nho_nhat: float = 14.0,
                nguong_vang: int = 40, nguong_thap: int = 8,
                nguong_luc: int = 105, va_dut: int = 0) -> np.ndarray:
    """Vùng màu vàng của bức tranh.

    Không dùng cửa sổ sắc màu vì các vạch vàng mảnh trên nền đỏ - nét tóc,
    vành tai, đường viền hộp sọ - bị pha màu nên sắc màu ngả sang cam và rơi
    ra ngoài cửa sổ. Thay vào đó dùng "độ vàng" min(R, G) - B: màu vàng cho
    trị số cao, màu đỏ cho trị số âm, còn vệt loá trắng thì gần 0. Cách này
    giữ được cả những nét mảnh chỉ rộng vài điểm ảnh.

    Các nét mảnh nhất - vành tai, sợi tóc trên đỉnh đầu, đường hàm - trong
    ảnh gốc chỉ dày chừng một điểm ảnh nên độ vàng của chúng bị pha loãng,
    không vượt nổi ngưỡng chính. Vì vậy dùng ngưỡng trễ hai mức: mức cao
    khoanh những mảng chắc chắn là màu vẽ, mức thấp vét thêm các nét mảnh,
    nhưng chỉ giữ phần nối liền với mảng chắc chắn - nhờ đó vệt loá rời rạc
    trên cửa cuốn không lọt vào.

    Riêng độ vàng thì chưa đủ: những nét vẽ nâu sẫm trong vùng vàng - khe
    mắt, mí mắt - vẫn cho độ vàng dương nên bị xếp nhầm là màu vàng, khiến
    con mắt vỡ vụn thành mấy chấm. Chúng khác nét vàng ở kênh lục: nét nâu
    có G chừng 40-110, còn nét vàng dù mảnh vẫn có G trên 110. Vì vậy có
    thêm điều kiện `nguong_luc`.
    """
    px = np.asarray(anh).astype(np.float32)
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    do_vang = np.minimum(r, g) - b
    m = filters.apply_hysteresis_threshold(do_vang, nguong_thap, nguong_vang)
    m = m & (r > 90) & (g > nguong_luc)
    # Nếu ảnh chụp có vạch ngang cắt nét mảnh thành đoạn đứt quãng thì phép
    # đóng theo chiều dọc nối chúng lại mà không dính sang nét bên cạnh.
    if va_dut:
        m = morphology.closing(m, np.ones((va_dut, 1), bool))
    vun = max(4, int(nho_nhat))          # giữ lại được cả những đảo nhỏ
    m = morphology.remove_small_objects(m, vun)
    m = morphology.remove_small_holes(m, vun)
    if don:
        m = morphology.closing(m, morphology.disk(don))
        m = morphology.opening(m, morphology.disk(don))
    return m


def gop_net_do(m: np.ndarray, toi_da: float = 3000, no: int = 3,
               lap_lo: float = 120) -> np.ndarray:
    """Nối các mảnh đỏ nhỏ nằm lọt trong vùng vàng cho thành nét liền.

    Nét đỏ mảnh trên nền vàng - khe mắt, nếp áo, nếp nhăn - trong ảnh chụp
    bị nhoè và đứt thành từng mảnh vụn, vạch nét ra sẽ thành một đám đốm rời
    rạc. Ở đây các mảnh đỏ nhỏ được nở ra cho dính lại thành nét, còn những
    mảng đỏ lớn - nền tranh, hốc mắt - thì giữ nguyên. Sau cùng lấp nốt các
    lỗ quá nhỏ để hết đốm vụn.
    """
    do = ~m
    nhan = measure.label(do)
    dt = np.bincount(nhan.ravel())
    nho = np.isin(nhan, np.nonzero((dt > 0) & (dt < toi_da))[0]) & do
    if no:
        nho = morphology.closing(nho, morphology.disk(no))
    return morphology.remove_small_holes(m & ~nho, int(max(4, lap_lo)))


def _dien_tich(p):
    x, y = p[:, 1], p[:, 0]
    return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def _mau_ben_trong(p, m: np.ndarray) -> str:
    """Màu của vùng nằm trong một đường biên.

    Tô đa giác ra một mặt nạ nhỏ bằng đúng khung bao của nó, lùi vào một
    điểm ảnh rồi đối chiếu với mặt nạ vàng. Cách này đúng với mọi hình, kể
    cả hình lõm nhiều ngóc ngách mà phép cắt ngang một đường không kham nổi.
    """
    y0, y1 = int(np.floor(p[:, 0].min())), int(np.ceil(p[:, 0].max()))
    x0, x1 = int(np.floor(p[:, 1].min())), int(np.ceil(p[:, 1].max()))
    rong, cao = x1 - x0 + 3, y1 - y0 + 3
    if rong < 3 or cao < 3:
        return "vang"
    hinh = Image.new("1", (rong, cao), 0)
    ImageDraw.Draw(hinh).polygon([(x - x0 + 1, y - y0 + 1) for y, x in p], fill=1)
    trong = np.asarray(hinh)
    if trong.sum() > 12:                      # lùi vào để tránh chính đường biên
        trong = morphology.binary_erosion(trong, morphology.disk(1))
    vung = np.zeros((cao, rong), bool)
    ya, yb = max(0, y0 - 1), min(m.shape[0], y0 - 1 + cao)
    xa, xb = max(0, x0 - 1), min(m.shape[1], x0 - 1 + rong)
    vung[ya - (y0 - 1):yb - (y0 - 1), xa - (x0 - 1):xb - (x0 - 1)] = m[ya:yb, xa:xb]
    if not trong.any():
        return "vang"
    return "vang" if vung[trong].mean() > 0.5 else "do"


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
        xx, yy = float(q[:, 1].mean()), float(q[:, 0].mean())
        if any(x0 * rong - 12 < xx < x1 * rong + 12 and y0 * cao - 10 < yy < y1 * cao + 10
               for x0, y0, x1, y1 in bo_qua):
            continue                      # nằm trong ô chữ, để phông chữ lo
        hinh.append((_dien_tich(q), _mau_ben_trong(q, m), q))
    hinh.sort(key=lambda t: -t[0])          # hình lớn vẽ trước, hình nhỏ đè lên
    return hinh


def main() -> None:
    bp = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    bp.add_argument("anh", help="ảnh chụp bức tranh tường")
    bp.add_argument("-o", "--output", default="net_tranh_tuong.json",
                    help="tệp dữ liệu vector xuất ra")
    bp.add_argument("--lui", type=float, default=0.014,
                    help="tỉ lệ lùi bốn góc vào trong, để không lấy phải viền cửa")
    bp.add_argument("--nguong-vang", type=int, default=40,
                    help="mức cao của ngưỡng trễ: độ vàng min(R,G)-B của những "
                         "mảng chắc chắn là màu vẽ")
    bp.add_argument("--nguong-thap", type=int, default=8,
                    help="mức thấp của ngưỡng trễ: hạ xuống thì vét thêm các nét "
                         "mảnh, nhưng dễ dính nhiễu")
    bp.add_argument("--nguong-luc", type=int, default=105,
                    help="ngưỡng kênh lục để tách nét vẽ nâu sẫm ra khỏi màu vàng")
    bp.add_argument("--gop-net", type=float, default=3000,
                    help="mảng đỏ nhỏ hơn ngần này (điểm ảnh vuông) thì được nở ra "
                         "cho dính lại thành nét liền; 0 là tắt")
    bp.add_argument("--no-net", type=int, default=1,
                    help="bán kính nở khi gộp các mảnh nét đỏ")
    bp.add_argument("--lap-lo", type=float, default=24,
                    help="lấp các lỗ đỏ nhỏ hơn ngần này cho hết đốm vụn")
    bp.add_argument("--va-dut", type=int, default=0,
                    help="chiều cao phép đóng dọc để vá vết đứt do vạch cửa cuốn")
    bp.add_argument("--rong", type=int, default=1900,
                    help="bề rộng ảnh sau khi nắn phẳng, tính bằng điểm ảnh")
    bp.add_argument("--dung-sai", type=float, default=0.9,
                    help="sai số cho phép khi giản lược đường biên (điểm ảnh)")
    bp.add_argument("--nho-nhat", type=float, default=12.0,
                    help="bỏ qua các hình có diện tích nhỏ hơn ngần này")
    bp.add_argument("--mem", type=float, default=1.1,
                    help="độ làm mềm mặt nạ trước khi dò biên")
    bp.add_argument("--xem", help="ghi thêm ảnh nắn phẳng ra tệp này để đối chiếu")
    ts = bp.parse_args()

    anh = Image.open(ts.anh).convert("RGB")
    goc = lui_khung(tim_khung(np.asarray(anh).astype(np.int16)), ts.lui)
    ty_le = (goc[2][1] - goc[0][1]) / max(1e-6, goc[1][0] - goc[0][0])
    cao = int(round(ts.rong * ty_le))
    phang = nan_phang(anh, goc, ts.rong, cao)
    if ts.xem:
        phang.save(ts.xem)

    he = (ts.rong / 1900.0) ** 2          # các ngưỡng diện tích tính theo khổ chuẩn
    m = mat_na_vang(phang, nho_nhat=ts.nho_nhat * he, nguong_vang=ts.nguong_vang,
                    nguong_thap=ts.nguong_thap, nguong_luc=ts.nguong_luc,
                    va_dut=ts.va_dut)
    if ts.gop_net:
        m = gop_net_do(m, ts.gop_net * he, ts.no_net, ts.lap_lo * he)
    hinh = vach_net(m, ts.dung_sai, ts.nho_nhat * he, ts.mem,
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
