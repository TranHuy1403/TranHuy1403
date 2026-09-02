# 2-9-1945

Hai chương trình Python vẽ hình về ngày Chủ tịch Hồ Chí Minh đọc bản Tuyên
ngôn Độc lập tại Quảng trường Ba Đình, mồng 2 tháng 9 năm 1945. Mọi hình
đều được sinh ra từ mã, không dùng ảnh có sẵn làm nguyên liệu.

## 1. Tranh cổ động hai màu — `ve_tranh_co_dong.py`

Vẽ theo lối tranh tường quen thuộc: nền đỏ cờ, hình vàng phẳng, không tô
bóng. Bên trái là chân dung Bác bên chiếc micro, bên phải là bản đồ Việt
Nam kèm quần đảo Hoàng Sa và Trường Sa, góc trên là ngôi sao năm cánh,
phía dưới là dòng chữ 2-9-1945.

![Tranh cổ động 2-9-1945](tranh_co_dong_2_9_1945.png)

```bash
pip install pillow
python3 ve_tranh_co_dong.py
```

| Tuỳ chọn | Ý nghĩa |
|---|---|
| `-o`, `--output` | Tên tệp ảnh xuất ra (mặc định `tranh_co_dong_2_9_1945.png`) |
| `--rong` | Chiều rộng ảnh tính bằng điểm ảnh (mặc định `1600`) |
| `--ty-le` | Hệ số siêu lấy mẫu khi vẽ, càng lớn bờ hình càng mịn (mặc định `3`) |
| `--chu` | Dòng chữ phía dưới (mặc định `2-9-1945`) |
| `--seed` | Hạt giống cho nhịp tay vẽ của các lọn tóc và sợi râu (mặc định `29`) |
| `--cua-cuon` | Thêm vạch ngang mô phỏng cánh cửa cuốn nơi vẽ tranh tường |

### Thuật toán vẽ

Bốn ý chính khiến nét vẽ ra dáng bút lông chứ không phải đường máy tính:

1. **Bo cong bằng phép cắt góc Chaikin** (`lam_muot`). Mỗi lượt thay một đỉnh
   bằng hai điểm nằm trên hai cạnh kề, cạnh gãy biến thành cung cong. Ba
   lượt là đủ mượt mà vẫn giữ dáng hình. Đường bờ biển chỉ bo hai lượt nên
   dáng chữ S mềm lại mà các mũi đất không bị mài tròn.
2. **Nét có bề rộng thay đổi** (`than_net`). Thay vì vẽ đường thẳng bề rộng
   cố định, chương trình dựng đa giác bao quanh đường: đi hết mép trái rồi
   vòng ngược mép phải, bề rộng tại mỗi điểm lấy theo một dáng bút —
   `bung` (phình giữa), `vuot` (vuốt nhọn dần về cuối), `nhon` (nhọn cả hai
   đầu), `deu` (đều). Lông mày, sợi râu, lọn tóc đều vuốt nhọn như thật.
3. **Lọn tóc sinh theo hình cầu hộp sọ** (`_lon_toc`). Hộp sọ được xấp xỉ
   bằng một hình cầu dẹt; mỗi lọn xuất phát từ một điểm trên chân tóc rồi
   vừa dâng lên đỉnh (bán kính tăng) vừa xoay dần về giữa (góc thu lại),
   nên các lọn chạy song song ôm lấy hộp sọ thay vì chụm vào một điểm.
   Chòm râu cũng sinh theo cách tương tự, toả từ cằm rồi chụm về chóp râu.
4. **Nhịp tay vẽ**. Vị trí, chiều dài và độ đậm của từng lọn tóc, sợi râu
   được xê dịch ngẫu nhiên trong biên độ hẹp, lấy từ một hạt giống cố định
   (`--seed`) nên cùng hạt giống thì cùng một bức tranh, đổi hạt giống thì
   được một bản chép tay khác.

Ngoài ra:

- **Bản đồ dựng từ toạ độ thật.** Danh sách `DAT_LIEN` ghi các điểm mốc
  trên biên giới và bờ biển theo (kinh độ, vĩ độ), hàm `_diem_ban_do()`
  chiếu thẳng vào ô chứa bản đồ nên dáng chữ S đúng tỉ lệ. Hai quần đảo
  giữ đúng vĩ độ, còn hoành độ được kéo lại gần cho vừa khuôn hình.
- `Tranh.dat_khung()` co giãn và dời cả nhóm hình, nhờ vậy chân dung được
  vẽ trong hệ toạ độ riêng rồi đặt vào khuôn tranh.
- Dòng chữ được vẽ ra mặt nạ riêng rồi co giãn vừa ô đã định, nên bố cục
  không đổi dù máy dùng phông chữ nào.

## 2. Ảnh tư liệu dựng bằng bản đồ độ cao — `ve_bac_ho_doc_tuyen_ngon.py`

Bản thử theo hướng khác: dựng một bản đồ độ cao cho toàn cảnh (hộp sọ, gò
má, sống mũi, thân áo, micro), tính pháp tuyến bề mặt rồi chiếu sáng từng
điểm ảnh, sau đó phủ hiệu ứng ảnh chụp năm 1945 — hạt phim, ám nâu, tối
bốn góc, khung viền.

```bash
pip install pillow numpy
python3 ve_bac_ho_doc_tuyen_ngon.py --chu-thich
```

| Tuỳ chọn | Ý nghĩa |
|---|---|
| `-o`, `--output` | Tên tệp ảnh xuất ra |
| `--che-do` | `sepia` (ảnh cũ) hoặc `xam` (đen trắng) |
| `--hat` | Độ đậm hạt phim, `0` là tắt |
| `--chu-thich` | In thêm dòng chú thích dưới ảnh |
| `--seed` | Hạt giống ngẫu nhiên cho hạt phim và vết xước |

Cách này cho chất liệu và khối nổi, nhưng vì hình học dựng bằng các khối
cơ bản nên kết quả vẫn ở mức tranh dựng máy, không đạt độ giống ảnh chụp.
Bản tranh cổ động ở trên hợp với cách vẽ bằng mã hơn.
