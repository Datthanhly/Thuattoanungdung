# Báo cáo Thuật toán ứng dụng N01

Bản báo cáo trình bày theo văn phong khoa học, với dữ liệu nghiên cứu, giả định mô hình, phương pháp, kiểm chứng và thảo luận kết quả. Tài liệu sử dụng hai bìa có khung/logo, lề trên 3,5 cm, dưới 3 cm, trái 3,5 cm, phải 2 cm và chữ chính Times New Roman 14 pt, dòng 19 pt. Mẫu gốc được lưu ở `../Mau_original_20261024.zip`.

## Thông tin bìa

- Môn: **Thuật toán ứng dụng**, lớp học phần **N01**.
- Lý Thành Đạt — 23010879 — K17 - KHMT.
- Đinh Đức Mạnh — 23010029 — K17 - KHMT.
- Phạm Văn Đạt — 23017150 — K17 - KHMT.
- GVHD giữ **TS. Trần Đình Tân** theo mẫu đã cung cấp; sửa hai dòng bìa nếu thông tin giảng viên thay đổi.

## Biên dịch

Chọn **XeLaTeX**, tệp chính `main.tex`. Trên Windows, tại gốc dự án:

```powershell
.\document\Mau\build.ps1
```

Bản PDF: `../../output/pdf/Bao_cao_Thuat_toan_ung_dung_N01.pdf`. Script chạy ba lượt để ổn định mục lục, danh mục và tham chiếu. Trên Overleaf, tải gói ZIP đi kèm, chọn compiler XeLaTeX.

## Chỉnh nội dung

- `section/section1.tex` đến `section5.tex`: năm phần chính.
- `section/ref.tex`: tài liệu tham khảo có đường dẫn nguồn.
- `section/appendix.tex`: ba phụ lục.
- `tables/`, `figures/`: bảng và hình từ dữ liệu thực.
- `data/`: 16 dòng benchmark, năm cấu hình độ nhạy tầng 1, môi trường, giả định và ví dụ lịch.

Mô hình gồm 27 khu phòng, tổng sức chứa 1.360 người; phòng 705 có sức chứa 40 người. Hành lang tầng 1 hở; cửa phòng tầng 1 là các đích thoát trực tiếp. Khu WC gần cụm thang 2 nằm ngoài phạm vi tính toán; sảnh và hai cụm thang được giữ trong mô hình.

Chuẩn bị lại bảng/hình bằng `python scripts/prepare_mau_report.py`; lệnh này không viết lại các chương và bìa. Nguồn benchmark là `outputs/a4_open_ground/benchmark`; số liệu bổ sung ở `outputs/a4_open_ground/report_sensitivity`. Mỗi tổ hợp chính chỉ đo một lần; không có số liệu đỉnh bộ nhớ khi chưa bật đo.

GIF đi kèm dùng 600 ms cho mỗi bước mô phỏng 5 s; khung cuối giữ 3 s. Tốc độ trình chiếu được ghi riêng trong `.playback.json` và độc lập với các chỉ số thực nghiệm. Tạo lại bằng `python -m a4_evac gif outputs/a4_open_ground/benchmark/safe/M4 --output outputs/a4_open_ground/a4_evacuation.gif --frame-ms 600`.

Đóng gói lại: `python scripts/package_mau_report.py`. Báo cáo là nghiên cứu thuật toán với tham số giả định, không phải phương án PCCC được phê duyệt.

## Kỹ thuật tạo báo cáo và liên kết mã nguồn

Tài liệu tham khảo [2] trỏ đến kho mã nguồn công khai [Datthanhly/Thuattoanungdung](https://github.com/Datthanhly/Thuattoanungdung). Liên kết được trích trong mục 1.4 và 4.5. Tệp `A4_Evac_Source.zip` vẫn được đóng gói để lưu bản chụp mã nguồn cùng báo cáo; gói Overleaf chứa bản chụp này ở thư mục gốc.

Gói nguồn chứa chương trình, kiểm thử, cấu hình, script chạy bổ sung và chỉ số thực nghiệm. `source_sha256.json` xác định chính xác nội dung phiên bản. Các lịch bổ sung dung lượng lớn được lưu tại `outputs/a4_open_ground/review_20261024`, không nhúng toàn bộ vào gói nguồn.

`data/` bên cạnh tệp LaTeX chứa bản chụp số liệu dùng cho bảng và đoạn trích; đây là cấu trúc tạo tài liệu, không phải một giả định khoa học. Thông tin phiên bản Python và phần cứng nằm trong dữ liệu thực nghiệm. XeLaTeX, font dự phòng, `build.ps1` và quy trình đóng gói chỉ phục vụ tạo PDF.

```powershell
# Chạy tại gốc dự án; các solver chạy tuần tự.
python scripts/run_review_experiments.py
python scripts/prepare_mau_report.py
python scripts/order_report_references.py
.\document\Mau\build.ps1
python scripts/package_mau_report.py
```

Script chuẩn bị số liệu không ghi đè các chương đã biên tập. `revise_report_review.py` là phép chuyển đổi biên tập một lần và **không chạy lại** trên bản đã sửa. Các bảng và hình mới được tạo bởi `prepare_review_assets.py`; số liệu thiếu không được thay bằng giá trị ước lượng. Gói `icomma` xử lý dấu phẩy thập phân trong toán; bảng và nhãn hình dùng dấu phẩy cho phần thập phân, dấu chấm phân nhóm nghìn. Cú pháp Python/JSON trong khối mã vẫn giữ đúng quy tắc ngôn ngữ.
