# Đối chiếu chỉnh sửa báo cáo ngày 24/10/2026

Các số bảng/hình được đánh lại tự động sau khi gộp bảng và thêm phân tích. Bảng danh sách phòng ở phụ lục vẫn là A.1; ký hiệu B.1; dấu vết C.1.

| Nhóm góp ý | Thay đổi |
|---|---|
| Trích dẫn | Dẫn mã nguồn tại 1.4; tài liệu được sắp theo lần xuất hiện đầu. Bổ sung Ford–Fulkerson, Dinic, Ahuja–Magnanti–Orlin, Chalmet và tổng quan Dhamala từ nguồn xuất bản chính thức. |
| Liên kết nguồn | Tài liệu [2] dẫn kho công khai https://github.com/Datthanhly/Thuattoanungdung. Gói `A4_Evac_Source.zip` tiếp tục lưu bản chụp và mã băm từng tệp. |
| Ký hiệu và thuật ngữ | Định nghĩa M4 trong tóm tắt; thêm danh mục thuật ngữ và toàn bộ ký hiệu được yêu cầu vào B.1; dùng “thoát/sơ tán”, phân biệt makespan với “Thoát cuối”. |
| Số và mã lệnh | Dùng `icomma`, thập phân dấu phẩy, phân nhóm nghìn dấu chấm; giữ cú pháp máy trong code. Giả mã dùng 5 môi trường `algorithm`, khối mã font đơn cách. Bullet chuyển sang gạch đầu dòng. |
| Bố cục | Bỏ ngắt trang giữa tiểu mục; dùng `Needspace`, float cho hình/bảng; tiêu đề chạy khớp đề tài. Tài liệu vẫn dùng thân chữ 14 pt và lề theo mẫu, giãn dòng 19 pt. |
| Hình mặt bằng | Vẽ lại vector PDF từ mô hình; chia bản đồ thành hai phần; tầng 1 có hình vector riêng; bỏ tiêu đề trùng caption. |
| Hình thuật toán và phát lại | Nhãn tách nút/đi/chờ riêng; lưu đồ cài đặt nằm ngang; thêm năm khung 0/100/200/300/390 s. |
| Hình kết quả | Nét liền/đứt phân biệt M1/M2; trục tiếng Việt, định dạng số Việt; đường 1.360, mốc nguy cơ và thời điểm thoát cuối; biểu đồ tổng hợp có (a)/(b), nhãn cột và tên kịch bản đầy đủ. |
| Bảng | Gộp 16 tổ hợp, thêm tỷ lệ và thời điểm thoát cuối, giải thích TB/Giải/dấu thiếu; in đậm theo tiêu chí ghi trong caption. Thêm Tổng cho bảng tầng và phòng; thêm nguồn/loại tham số; sửa “Bước đến”. |
| Đối chứng | Thêm M1E chia đều hai thang; khảo sát hệ số M3 = 1/2/4/8 trên bốn kịch bản. M1E đạt 395 s khi không sự cố, thu hẹp chênh lệch với M4 còn 5 s. |
| Nút thắt | Phân tích năng lực 9 người/bước, cận thô 330 s và cận có thời gian tiếp cận 390 s; thêm heatmap và bảng cận theo các lát cắt tầng. |
| Truy vết | Liệt kê 112 người còn lại theo nguồn; phân tích người từ R405 còn lại ở M3; phân biệt trùng tổng lưu lượng với trùng lịch M1/M2. |
| Thực nghiệm bổ sung | Script chạy riêng 46 lượt: 20 đối chứng/ablation, 5 lặp M4, 15 phân bố ở 30/50/70%, 6 cấu hình độ nhạy toàn tòa. Dữ liệu nằm ngoài bộ chính. |
| Khả năng tái lập | Ghi CPU/RAM/Python; đo giai đoạn dựng mạng, dò luồng, tối ưu chi phí, phân rã/kiểm tra; ghi P và số đường tăng. Seed phân bố là `allocation_seed`, tách khỏi seed kịch bản. |
| Hiệu chỉnh | Tốc độ, suất thông hành, khói và sức chứa nút được ghi rõ là tham số minh họa. Phân tích sai số lấy phần nguyên; giải thích khác biệt phòng ghép 601-602 và phòng 705. |
| Văn phong | Thêm tổng quan, bố cục, kế hoạch phân công; tập trung giới hạn tại 5.8; chuyển hướng dẫn XeLaTeX/build/thư mục tài liệu sang README. |

Chưa thực hiện tái sử dụng luồng giữa các horizon, đối chiếu OR-Tools, đo trên máy cô lập hoặc hiệu chỉnh bằng khảo sát hiện trường. Báo cáo nêu chúng là giới hạn/hướng phát triển. Bảng phân công là **kế hoạch đề xuất**, không xác nhận lịch sử đóng góp thực tế của ba thành viên.

Các phép đo thời gian chạy tuần tự nhưng không cô lập tiến trình nền; SD được báo cáo trung thực. Không suy rộng một giá trị runtime thành cam kết thời gian đáp ứng. Các bảng và hình mới được sinh từ dữ liệu đã đo; không điền số giả cho lượt chưa có kết quả.
