#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quay phim hai phần về cách bức tranh được sinh ra bằng lập trình.

    Phần 1 - định bản phác hoạ: khung tranh trống, các ô bố cục hiện ra, rồi
             bản vẽ bằng mã được dựng dần từng hình một, đúng thứ tự mà
             chương trình gọi lệnh vẽ.
    Phần 2 - dây chuyền dựng bản cuối: ảnh chụp bức tranh tường đi qua các
             bước tìm góc, nắn phẳng, tách hai màu, dò biên, dựng vector.

Dải dưới khung hình không ghi tên bước mà chiếu chính những dòng mã làm nên
cảnh đang xem, gõ ra từng chữ như đang viết chương trình.

Yêu cầu: pip install pillow numpy scikit-image imageio imageio-ffmpeg

    python3 quay_phim_lap_trinh.py anh_chup.jpg -o qua_trinh_lap_trinh.mp4
"""

from __future__ import annotations

import argparse
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import vach_net_tu_anh as vn
import ve_tranh_co_dong as lo

RONG_KH, CAO_KH = 1280, 1280        # khung hình
CAO_MA = 320                        # dải mã phía dưới
CAO_HINH = CAO_KH - CAO_MA

NEN = (18, 19, 24)
NEN_MA = (12, 13, 17)
VIEN_MA = (38, 40, 50)

MAU_MA = {
    "thuong": (214, 218, 230),
    "khoa": (198, 140, 245),        # từ khoá
    "chuoi": (150, 220, 160),       # chuỗi ký tự
    "so": (240, 180, 120),          # con số
    "ham": (120, 190, 250),         # tên hàm
    "ghi_chu": (108, 114, 132),     # ghi chú
    "ten_tep": (120, 128, 148),
}

TU_KHOA = {"def", "for", "in", "if", "else", "return", "import", "as", "from",
           "with", "and", "or", "not", "while", "lambda", "True", "False", "None"}

_MONO = ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
         "C:/Windows/Fonts/consola.ttf"]


def _phong_ma(co):
    import os
    for d in _MONO:
        if os.path.exists(d):
            return ImageFont.truetype(d, co)
    return ImageFont.load_default(size=co)


# --------------------------------------------------------------------------
# Dải mã phía dưới khung hình
# --------------------------------------------------------------------------
def _tach_tu(dong: str):
    """Tách một dòng mã thành các mẩu kèm màu, đủ để tô cho dễ đọc."""
    if dong.lstrip().startswith("#"):
        return [(dong, "ghi_chu")]
    mau = []
    for tu in re.findall(r'"[^"]*"|\'[^\']*\'|\w+|\W', dong):
        if tu[:1] in "\"'":
            loai = "chuoi"
        elif tu in TU_KHOA:
            loai = "khoa"
        elif re.fullmatch(r"\d+(\.\d+)?", tu):
            loai = "so"
        elif re.fullmatch(r"[A-Za-z_]\w*", tu):
            loai = "ham"
        else:
            loai = "thuong"
        mau.append((tu, loai))
    return mau


def ve_bang_ma(ten_tep: str, dong: list, hien: int, so_dong: int = 5) -> Image.Image:
    """Vẽ dải mã: các dòng đã xong hiện đủ, dòng cuối đang gõ dở `hien` ký tự."""
    anh = Image.new("RGB", (RONG_KH, CAO_MA), NEN_MA)
    ve = ImageDraw.Draw(anh)
    ve.line([(0, 0), (RONG_KH, 0)], fill=VIEN_MA, width=2)
    phong = _phong_ma(30)
    nho = _phong_ma(22)
    ve.text((40, 26), ten_tep, font=nho, fill=MAU_MA["ten_tep"], anchor="lm")

    xong, con = [], ""
    dem = hien
    for d in dong:
        if dem >= len(d):
            xong.append(d)
            dem -= len(d)
        else:
            con = d[:dem]
            break
    hien_thi = (xong + ([con] if con else []))[-so_dong:]

    y = 62
    for d in hien_thi:
        x = 40
        for tu, loai in _tach_tu(d):
            ve.text((x, y), tu, font=phong, fill=MAU_MA[loai])
            x += ve.textlength(tu, font=phong)
        if d is hien_thi[-1] and con:
            ve.rectangle([x + 2, y + 4, x + 12, y + 28], fill=(150, 160, 190))
        y += 44
    return anh


def khung(noi_dung: Image.Image, ten_tep: str, dong: list, hien: int) -> Image.Image:
    k = Image.new("RGB", (RONG_KH, CAO_KH), NEN)
    o = CAO_HINH - 60
    ty = min((RONG_KH - 80) / noi_dung.width, o / noi_dung.height)
    nd = noi_dung.resize((max(1, int(noi_dung.width * ty)),
                          max(1, int(noi_dung.height * ty))), Image.LANCZOS)
    k.paste(nd, ((RONG_KH - nd.width) // 2, (CAO_HINH - nd.height) // 2))
    k.paste(ve_bang_ma(ten_tep, dong, hien), (0, CAO_HINH))
    return k


# --------------------------------------------------------------------------
# Phần 1: bản vẽ bằng mã, ghi lại từng lệnh vẽ rồi phát lại dần
# --------------------------------------------------------------------------
class TranhGhi(lo.Tranh):
    """Khung vẽ có ghi nhật ký: mỗi lệnh vẽ được lưu lại để phát lại dần."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.nhat_ky = []
        self.dang_phat = False

    def _luu(self, ten, doi_so):
        self.nhat_ky.append((ten, (self.k, self.ox, self.oy), doi_so))

    def to(self, diem, mau=None, muot=0, kin=True):
        if self.dang_phat:
            return super().to(diem, mau, muot, kin)
        self._luu("to", ([tuple(p) for p in diem], mau, muot, kin))

    def tron(self, tam, ban_kinh, mau=None):
        if self.dang_phat:
            return super().tron(tam, ban_kinh, mau)
        self._luu("tron", (tuple(tam), ban_kinh, mau))

    def chu_vua_o(self, chu, o, mau=None):
        if self.dang_phat:
            return super().chu_vua_o(chu, o, mau)
        self._luu("chu_vua_o", (chu, tuple(o), mau))

    def chu(self, chu, tam, co, mau=None, neo="lm"):
        if self.dang_phat:
            return super().chu(chu, tam, co, mau, neo)
        self._luu("chu", (chu, tuple(tam), co, mau, neo))

    def phat(self, tu: int, den: int):
        """Vẽ thật các lệnh trong khoảng đã cho."""
        self.dang_phat = True
        for ten, khung_toa_do, doi_so in self.nhat_ky[tu:den]:
            self.k, self.ox, self.oy = khung_toa_do
            getattr(self, ten)(*doi_so)
        self.dang_phat = False

    def anh_hien(self) -> Image.Image:
        return self.anh.reduce(self.ty_le) if self.ty_le > 1 else self.anh.copy()


O_BO_CUC = [((0.02, 0.05), (0.46, 0.83)),      # ô chân dung
            ((0.49, 0.09), (0.79, 0.81)),      # ô bản đồ
            ((0.84, 0.10), (0.99, 0.28)),      # ô ngôi sao
            ((0.03, 0.83), (0.50, 0.95))]      # ô dòng chữ


def _khung_bo_cuc(rong, cao, so_o: int, mo: float = 1.0) -> Image.Image:
    """Các ô bố cục vẽ bằng nét đứt, dựng nên bản phác hoạ."""
    anh = Image.new("RGB", (rong, cao), lo.DO)
    ve = ImageDraw.Draw(anh)
    for i, ((x0, y0), (x1, y1)) in enumerate(O_BO_CUC[:so_o]):
        hop = [x0 * rong, y0 * cao, x1 * rong, y1 * cao]
        mau = tuple(int(v * mo) for v in lo.VANG)
        buoc, dai = 26, 14
        for x in range(int(hop[0]), int(hop[2]), buoc):
            ve.line([(x, hop[1]), (min(x + dai, hop[2]), hop[1])], fill=mau, width=3)
            ve.line([(x, hop[3]), (min(x + dai, hop[2]), hop[3])], fill=mau, width=3)
        for y in range(int(hop[1]), int(hop[3]), buoc):
            ve.line([(hop[0], y), (hop[0], min(y + dai, hop[3]))], fill=mau, width=3)
            ve.line([(hop[2], y), (hop[2], min(y + dai, hop[3]))], fill=mau, width=3)
    return anh


MA_PHAC_HOA = [
    "# phác hoạ: dựng khung tranh rồi định vị các mảng",
    "RONG, CAO = 1600, 1560",
    "DO, VANG = BANG_MAU[\"tuong\"]",
    "t = Tranh(rong_ra=2000, ty_le=3)",
    "O_BAN_DO = (800, 156, 1248, 1240)",
    "ve_ngoi_sao(t, tam=(1420, 288), ban_kinh=124)",
    "ve_dong_chu(t, \"2-9-1945\", o=(56, 1306, 792, 1472))",
]

MA_VE_HINH = [
    "# mỗi mảng, mỗi nét đều là một lệnh vẽ",
    "ve_ban_do(t)      # bờ biển từ toạ độ kinh - vĩ độ",
    "ve_ten_dao(t)",
    "ve_ngoi_sao(t)",
    "t.dat_khung(1.08, 0.0, -96.0)",
    "ve_chan_dung(t)",
    "t.to(THAN, muot=2)",
    "t.to(DAU, muot=3)",
    "t.net(CHAN_TOC, 9, dang=\"nhon\")",
    "for lon, dam in _lon_toc(rng):",
    "    t.net(lon, 7.5 * dam, dang=\"vuot\")",
    "for soi, dam in _soi_rau(rng):",
    "    t.net(soi, 5 * dam, dang=\"vuot\")",
    "ve_micro(t)",
    "ve_dong_chu(t, chu=\"2-9-1945\")",
    "t.luu(\"tranh_co_dong_2_9_1945.svg\")",
]

MA_DAY_CHUYEN = [
    "# dây chuyền: từ ảnh chụp bức tường ra bản vector",
    "anh = Image.open(\"anh_chup.jpg\").convert(\"RGB\")",
    "goc = tim_khung(np.asarray(anh))",
    "goc = lui_khung(goc, 0.014)",
    "phang = nan_phang(anh, goc, 1900, 1814)",
    "r, g, b = np.asarray(phang).T",
    "do_vang = np.minimum(r, g) - b",
    "m = apply_hysteresis_threshold(do_vang, 8, 40)",
    "m &= (r > 90) & (g > 105)",
    "m = remove_small_objects(m, 12)",
    "for p in measure.find_contours(m, 0.5):",
    "    q = approximate_polygon(p, tolerance=0.9)",
    "    hinh.append((dien_tich(q), mau_ben_trong(q, m), q))",
    "hinh.sort(key=lambda h: -h[0])",
    "for dt, mau, q in hinh:",
    "    t.to(q, VANG if mau == \"vang\" else DO)",
    "t.luu(\"tranh_tuong_2_9_1945.svg\")",
]


def _go_dan(dong, so_khung, i, phan=0.75):
    """Số ký tự đã gõ ra ở khung hình thứ i."""
    tong = sum(len(d) for d in dong)
    t = min(1.0, (i + 1) / max(1, int(so_khung * phan)))
    return int(tong * t)


def phan_phac_hoa(fps, lap):
    """Phần 1: khung trống, ô bố cục, rồi bản vẽ hiện dần theo từng lệnh."""
    t = TranhGhi(rong_ra=900, ty_le=2)
    lo.ve_ban_do(t)
    lo.ve_ten_dao(t)
    lo.ve_ngoi_sao(t)
    t.dat_khung(1.08, 0.0, -96.0)
    lo.ve_chan_dung(t, 29)
    lo.ve_micro(t)
    t.dat_khung()
    lo.ve_dong_chu(t)
    rong, cao = t.rong_ra, t.cao_ra

    n = lap(fps * 1.2)                                   # khung tranh trống
    for i in range(n):
        yield khung(Image.new("RGB", (rong, cao), lo.DO), "ve_tranh_co_dong.py",
                    MA_PHAC_HOA[:4], _go_dan(MA_PHAC_HOA[:4], n, i))

    n = lap(fps * 3)                                     # các ô bố cục
    for i in range(n):
        so_o = min(len(O_BO_CUC), 1 + int(len(O_BO_CUC) * i / (n * 0.8)))
        yield khung(_khung_bo_cuc(rong, cao, so_o), "ve_tranh_co_dong.py",
                    MA_PHAC_HOA, _go_dan(MA_PHAC_HOA, n, i))

    n = lap(fps * 7)                                     # vẽ dần từng lệnh
    tong = len(t.nhat_ky)
    da_ve = 0
    for i in range(n):
        den = int(tong * min(1.0, (i + 1) / (n * 0.92)) ** 0.85)
        t.phat(da_ve, den)
        da_ve = den
        yield khung(t.anh_hien(), "ve_tranh_co_dong.py",
                    MA_VE_HINH, _go_dan(MA_VE_HINH, n, i, 0.9))

    t.phat(da_ve, tong)
    cuoi = t.anh_hien()
    for _ in range(lap(fps * 1.6)):
        yield khung(cuoi, "ve_tranh_co_dong.py", MA_VE_HINH, sum(len(d) for d in MA_VE_HINH))


def phan_day_chuyen(duong_anh, fps, lap):
    """Phần 2: ảnh chụp đi qua dây chuyền để ra bản vector cuối cùng."""
    ma = MA_DAY_CHUYEN
    tong_ma = sum(len(d) for d in ma)

    def cat_ma(den_dong, ti):
        """Số ký tự gõ tới, tính theo dòng mã ứng với cảnh đang chiếu."""
        truoc = sum(len(d) for d in ma[:den_dong])
        rieng = sum(len(d) for d in ma[den_dong:den_dong + 1])
        return int(truoc + rieng * min(1.0, ti))

    anh = Image.open(duong_anh).convert("RGB")
    px = np.asarray(anh).astype(np.int16)

    n = lap(fps * 2)
    for i in range(n):
        yield khung(anh, "vach_net_tu_anh.py", ma, cat_ma(1, (i + 1) / (n * 0.7)))

    goc = vn.lui_khung(vn.tim_khung(px), 0.014)
    n = lap(fps * 2.2)
    for i in range(n):
        ti = min(1.0, (i + 1) / (n * 0.6))
        tam = anh.copy()
        ve = ImageDraw.Draw(tam)
        for j in range(4):
            p, q = goc[j], goc[(j + 1) % 4]
            if ti > j / 4.0:
                k = min(1.0, (ti - j / 4.0) * 4)
                ve.line([p, (p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k)],
                        fill=(90, 240, 160), width=3)
        for p in goc:
            ve.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], fill=(90, 240, 160))
        yield khung(tam, "vach_net_tu_anh.py", ma, cat_ma(3, ti))

    W, H = anh.size
    x0 = min(p[0] for p in goc); x1 = max(p[0] for p in goc)
    y0 = min(p[1] for p in goc); y1 = max(p[1] for p in goc)
    chu_nhat = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    n = lap(fps * 2.4)
    for i in range(n + lap(fps // 2)):
        ti = min(1.0, i / n)
        muot = ti * ti * (3 - 2 * ti)
        dich = [(p[0] + (q[0] - p[0]) * muot, p[1] + (q[1] - p[1]) * muot)
                for p, q in zip(goc, chu_nhat)]
        hs = vn._he_so_phoi_canh(dich, goc)
        yield khung(anh.transform((W, H), Image.PERSPECTIVE, hs, Image.BICUBIC),
                    "vach_net_tu_anh.py", ma, cat_ma(4, ti))

    ty = (goc[2][1] - goc[0][1]) / max(1e-6, goc[1][0] - goc[0][0])
    rong = 1900
    cao = int(round(rong * ty))
    phang = vn.nan_phang(anh, goc, rong, cao)
    m = vn.mat_na_vang(phang, nho_nhat=12.0)
    anh_m = Image.fromarray(np.dstack([np.where(m, 250, 30).astype("uint8"),
                                       np.where(m, 238, 26).astype("uint8"),
                                       np.where(m, 58, 30).astype("uint8")]))
    n = lap(fps * 2.6)
    for i in range(n):
        ti = min(1.0, (i + 1) / (n * 0.55))
        yield khung(Image.blend(phang, anh_m, ti), "vach_net_tu_anh.py",
                    ma, cat_ma(6 + int(ti * 3), ti))

    hinh = vn.vach_net(m, 0.9, 12.0, 1.1, bo_qua=[o for _, o in vn.O_CHU])
    n = lap(fps * 3)
    for i in range(n):
        den = int(len(hinh) * (i + 1) / n)
        anh_b = Image.new("RGB", (rong, cao), NEN)
        ve = ImageDraw.Draw(anh_b)
        for _, mau, q in hinh[:den]:
            diem = [(float(x), float(y)) for y, x in q]
            ve.line(diem + [diem[0]], fill=lo.VANG if mau == "vang" else (170, 60, 70),
                    width=2, joint="curve")
        yield khung(anh_b, "vach_net_tu_anh.py", ma, cat_ma(10 + int(2 * i / n), (i + 1) / n))

    n = lap(fps * 3.4)
    for i in range(n):
        den = int(len(hinh) * (i + 1) / n)
        anh_t = Image.new("RGB", (rong, cao), lo.DO)
        ve = ImageDraw.Draw(anh_t)
        for _, mau, q in hinh[:den]:
            ve.polygon([(float(x), float(y)) for y, x in q],
                       fill=lo.VANG if mau == "vang" else lo.DO)
        yield khung(anh_t, "ve_theo_tuong.py", ma, cat_ma(14 + int(2 * i / n), (i + 1) / n))

    cuoi = Image.new("RGB", (rong, cao), lo.DO)
    ve = ImageDraw.Draw(cuoi)
    for _, mau, q in hinh:
        ve.polygon([(float(x), float(y)) for y, x in q],
                   fill=lo.VANG if mau == "vang" else lo.DO)
    for c, o in vn.O_CHU:
        ox0, oy0, ox1, oy1 = o
        hop = lo.lay_phong(100).getbbox(c)
        co = int(100 * min((ox1 - ox0) * rong / max(1, hop[2] - hop[0]),
                           (oy1 - oy0) * cao / max(1, hop[3] - hop[1])))
        ve.text((ox0 * rong, (oy0 + oy1) / 2 * cao), c,
                font=lo.lay_phong(max(10, co)), fill=lo.VANG, anchor="lm")
    for _ in range(lap(fps * 3)):
        yield khung(cuoi, "ve_theo_tuong.py", ma, tong_ma)


def dung_phim(duong_anh, fps=25, nhanh=1.0):
    def lap(n):
        return max(1, int(round(n / nhanh)))
    for k in phan_phac_hoa(fps, lap):
        yield k
    for k in phan_day_chuyen(duong_anh, fps, lap):
        yield k


def main() -> None:
    bp = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    bp.add_argument("anh", help="ảnh chụp bức tranh tường")
    bp.add_argument("-o", "--output", default="qua_trinh_lap_trinh.mp4",
                    help="tệp phim xuất ra (.mp4 hoặc .gif)")
    bp.add_argument("--fps", type=int, default=25, help="số khung hình mỗi giây")
    bp.add_argument("--nhanh", type=float, default=1.0, help="hệ số tua nhanh")
    ts = bp.parse_args()

    khung_hinh = dung_phim(ts.anh, ts.fps, ts.nhanh)
    if ts.output.lower().endswith(".gif"):
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
        with iio.get_writer(ts.output, fps=ts.fps, quality=8, macro_block_size=8) as w:
            for k in khung_hinh:
                w.append_data(np.asarray(k))
                so += 1
    print(f"Đã lưu {ts.output} ({so} khung hình, {so / ts.fps:.1f} giây)")


if __name__ == "__main__":
    main()
