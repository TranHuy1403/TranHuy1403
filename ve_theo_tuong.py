#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vẽ lại bức tranh tường từ dữ liệu vector đã vạch nét.

Dữ liệu do `vach_net_tu_anh.py` sinh ra: một danh sách đa giác đã xếp theo
diện tích giảm dần, mỗi đa giác kèm màu của nó. Vẽ lần lượt từ hình lớn đến
hình nhỏ là ra đúng bức tranh, kể cả những chỗ lồng nhau như vành micro hay
con ngươi trong tròng mắt.

Vì đường nét lấy thẳng từ ảnh chụp nên góc cạnh giống hệt bản vẽ tay trên
tường; chương trình này chỉ làm phần dựng hình lại cho sắc nét.

Yêu cầu: pip install pillow

    python3 ve_theo_tuong.py                     # ra tranh_tuong_2_9_1945.png
    python3 ve_theo_tuong.py -o tranh.svg        # bản vector
"""

from __future__ import annotations

import argparse
import json

import ve_tranh_co_dong as lo


def ve_toan_bo(du_lieu, rong_ra=2000, ty_le=3, vector=False, cua_cuon=False,
               chu=True):
    rong, cao = du_lieu["khung"]
    t = (lo.TranhSVG(rong_ra, khung=(rong, cao)) if vector
         else lo.Tranh(rong_ra, ty_le, khung=(rong, cao)))
    for h in du_lieu["hinh"]:
        t.to(h["diem"], lo.VANG if h["mau"] == "vang" else lo.DO)
    if chu:
        for c in du_lieu.get("chu", []):
            x0, y0, x1, y1 = c["o"]
            t.chu_vua_o(c["chu"], (x0 * rong, y0 * cao, x1 * rong, y1 * cao))
    if cua_cuon:
        t.vach_cua_cuon(max(4, int(cao / 60)))
    return t


def main() -> None:
    bp = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    bp.add_argument("-o", "--output", default="tranh_tuong_2_9_1945.png",
                    help="tên tệp xuất ra; đuôi .svg thì xuất bản vector")
    bp.add_argument("--net", default="net_tranh_tuong.json",
                    help="tệp dữ liệu vector đã vạch nét")
    bp.add_argument("--rong", type=int, default=2000, help="bề rộng ảnh xuất ra")
    bp.add_argument("--ty-le", type=int, default=3,
                    help="hệ số siêu lấy mẫu khi vẽ ảnh điểm")
    bp.add_argument("--mau", choices=sorted(lo.BANG_MAU), default="tuong",
                    help="bảng màu: tuong (đo từ bức tường) hoặc co (theo quốc kỳ)")
    bp.add_argument("--khong-chu", action="store_true",
                    help="bỏ hai nhãn Hoàng Sa và Trường Sa")
    bp.add_argument("--cua-cuon", action="store_true",
                    help="thêm vạch ngang mô phỏng cánh cửa cuốn")
    ts = bp.parse_args()

    lo.DO, lo.VANG = lo.BANG_MAU[ts.mau]
    with open(ts.net, encoding="utf-8") as f:
        du_lieu = json.load(f)

    vector = ts.output.lower().endswith(".svg")
    t = ve_toan_bo(du_lieu, ts.rong, ts.ty_le, vector, ts.cua_cuon,
                   chu=not ts.khong_chu)
    co = t.luu(ts.output)
    print(f"Đã lưu {ts.output} ({co[0]}x{co[1]}{', vector' if vector else ''})")


if __name__ == "__main__":
    main()
