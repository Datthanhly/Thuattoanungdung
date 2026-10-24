# A4 - Phenikaa: tối ưu sơ tán và báo cáo LaTeX

Mã nguồn: [Datthanhly/Thuattoanungdung](https://github.com/Datthanhly/Thuattoanungdung).
Báo cáo hiện hành: [nguồn LaTeX theo mẫu](document/Mau/main.tex),
[PDF báo cáo N01](output/pdf/Bao_cao_Thuat_toan_ung_dung_N01.pdf),
[hướng dẫn biên dịch](document/Mau/README.md).

## Tải và khôi phục dữ liệu thực nghiệm

```powershell
git clone https://github.com/Datthanhly/Thuattoanungdung.git
cd Thuattoanungdung
python -m pip install -r requirements.txt
python scripts/restore_benchmark_data.py
```

Kho mã nguồn lưu dữ liệu gốc dưới dạng `data/benchmarks/a4_open_ground.zip`.
Lệnh khôi phục tạo lại các thư mục benchmark, khảo sát độ nhạy và 46 lượt bổ sung
tại `outputs/a4_open_ground/`. Các tệp đã có cùng nội dung được giữ nguyên;
lệnh dừng nếu gặp tệp khác nội dung. Có thể chạy kiểm thử và biên dịch báo cáo
ngay sau khi cài phụ thuộc; chỉ cần khôi phục khi muốn phát lại lịch hoặc tạo lại bảng/hình.

[Xem GIF demo](outputs/a4_open_ground/a4_evacuation.gif).

Dự án nhập **ảnh cuối cùng người dùng gửi ngày 24/10/2026**: 7 tầng, 27 khu phòng, tổng sức chứa **1.360 người**, phòng 705 **40 người**. Không dùng các ảnh trước có tổng 1.400 hoặc thay đổi thứ tự phòng.

**Bỏ khu WC gần cụm cầu thang 2 khỏi đồ thị**, giữ sảnh và hai cụm cầu thang. Không biến phần WC bỏ đi thành diện tích chứa hoặc lối tắt. Đây là mô phỏng thuật toán trên sơ đồ do người dùng cung cấp, chưa khảo sát/kiểm định PCCC.

## Chạy nhanh

Python 3.11 trở lên. Chạy tại thư mục này:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q

# Một lượt M4 đầy tải: 1.360 là giả định tất cả phòng đủ sức chứa tối đa.
python -m a4_evac run --method M4 --scenario safe --output outputs/a4_open_ground/demo

# So sánh đủ bốn phương pháp.
python demo.py --output outputs/a4_compare

# Demo nhỏ hơn, dễ thử nhanh.
python demo.py --load 0.25 --duration 600 --output outputs/a4_quick

# Số người bất kỳ trong khoảng 0..1360, phân bố ngẫu nhiên có seed.
python -m a4_evac run --people 600 --seed 2026 --scenario smoke --output outputs/a4_600
```

Lượt đầy tải có thể cần vài phút tùy máy/phương pháp. Runtime báo riêng trong metric; không gồm thời gian ghi toàn bộ CSV và dựng hình. Bật `--memory` để đo peak cấp phát Python bằng tracemalloc, sẽ chậm hơn. Không bật thì chỉ số bộ nhớ là null, không phải 0 MB.

## Mô hình nhập từ ảnh

| Tầng | Sức chứa tối đa | Chiều dài theo các khối (m) |
|---:|---:|---:|
| 1 | 180 | 66,4 |
| 2 | 180 | 69,6 |
| 3 | 200 | 69,6 |
| 4 | 200 | 68,8 |
| 5 | 200 | 65,2 |
| 6 | 240 | 60,8 |
| 7 | 160 | 52,0 |

Mỗi khu ghép là một nguồn dân số, không tách thành các nguồn trùng sức chứa. Độ sâu phòng 8,8 m và hành lang 2 m lấy theo ảnh. Có 50 cửa phòng theo quy ước: khu ghép/phòng dài ≥8 m có hai cửa; phòng ngắn hơn có một cửa. Vị trí chính xác chưa đo nên hai cửa đặt tại 20%/80%, một cửa ở giữa chiều dài khu phòng.

Tọa độ ngang là **tọa độ cục bộ từng tầng**. Các tầng có chiều dài và vị trí lõi khác nhau trong ảnh, nên không suy ra mô hình 3D đúng tỉ lệ. Chỉ các nút cùng cụm STAIR ở hai tầng liên tiếp được nối bằng đường xuống giả định; không có thang máy hay đường đi lên trong mô hình này.

### Quy tắc thoát và tham số mô phỏng

Theo thông tin bổ sung của người dùng, **hành lang tầng 1 hở, không có rào bảo vệ: qua cửa phòng tầng 1 là được tính đã thoát ra ngoài**. Bảy cửa phòng tầng 1 là bảy nút EXIT, vẫn giới hạn lưu lượng theo bề rộng cửa phòng giả định. Không thêm thời gian hay cửa chung sau cửa phòng.

Người từ tầng 2–7 đi xuống thang, qua sảnh tầng 1 rồi ra hành lang hở là thoát. EXIT1/EXIT2 chỉ hai vùng thoát từ sảnh thang, không phải hai cổng ra ngoài; năng lực hấp thụ 1.360 người/bước không tạo nút thắt mới, lưu lượng vẫn bị giới hạn bởi cạnh tiếp cận sảnh/thang. Tổng cộng có 9 nút hấp thụ. Đã bỏ tham số `assumed_outside_exit_width_m`. **Lõi thang 5 m trên ảnh không phải số đo bề rộng thông thủy vế thang**; mô hình giả định bề rộng sử dụng 1,5 m.

Demo riêng tầng 1: `outputs/a4_open_ground/ground_floor_demo/ground_floor.gif`, 180/180 người thoát trong 35 giây mô phỏng với tham số mặc định. Chương trình ghi nhận thoát ngay ở mốc đến cửa, vẫn giữ thời gian đi bên trong phòng và lưu lượng qua cửa. Hành lang hở tầng 1 là biên kết thúc mô phỏng; chưa mô phỏng đi tới điểm tập kết hoặc khói ngoài trời.

Các tham số tốc độ đi bộ, đường giữa tầng, năng lực cửa, dung lượng nút và cháy/khói nằm trong `data/a4/model_parameters.json`. Chạy:

```powershell
python -m a4_evac generate-data
python -m a4_evac run --assumptions data/a4/model_parameters.json --output outputs/a4_custom
```

`data/a4/assumptions.json` ghi riêng nguồn và các mục chưa đo. Các kích thước trực tiếp từ ảnh được khóa trong bộ sinh; sửa hình học bằng `a4_evac/data.py` hoặc nạp `--building path/to/building.json`, không đổi chiều sâu phòng bằng một tham số tốc độ.

Hành lang hai hướng được chia hai làn cố định 1 m; mỗi chiều chỉ được cấp năng lực của 1 m, không cấp toàn bộ 2 m cho cả hai chiều. Cạnh đi d bước có dung lượng đang đi `C=d*U`: tối đa d đoàn khởi hành U người/bước cùng hiện diện. Đây là mô hình đoàn/ô giả định. Nếu muốn nhập C chặt hơn, phải bổ sung solver ràng buộc chồng lấp; chương trình từ chối thay vì âm thầm vượt tổng sức chứa.

## Thuật toán tự viết

- Dijkstra và hàm A* có heuristic tùy chọn; Dijkstra động dự báo nguy cơ lúc đến.
- Dijkstra đa nguồn cho cháy/khói, lịch đóng nút/cạnh đơn điệu. Đến đúng mốc nguy hiểm bị cấm.
- Dinic với level graph và blocking flow; DFS lặp tránh giới hạn đệ quy.
- Min-Cost Flow dùng potentials, reduced costs và blocking flow trên các đường có cùng chi phí nhỏ nhất.
- Time-Expanded Network: nút in/out để khống chế tổng chứa; cạnh đi/chờ; năng lực cửa mỗi bước; cắt các trạng thái không kịp tới cửa bằng cận dưới hợp lệ.
- M4 tối đa số người thoát, tìm horizon ngắn nhất rồi tối thiểu tổng thời điểm thoát. Khi thiếu người: makespan toàn dân số là N/A.
- Phân rã luồng nguyên thành nhóm đi/chờ, validator độc lập và replay kiểm tra bảo toàn dân số.

NetworkX chỉ xuất hiện trong tests làm oracle, không giải bài toán chính.

M1 giữ đường ban đầu. M2 tính lại đường theo nguy cơ. M3 xét dung lượng khi chọn bước tiếp theo, có thể kém M1/M2 vì là heuristic. Baseline dùng thứ tự ID và đặt chỗ bảo thủ tới khi rời nút. Mọi lịch đều qua cùng validator và bộ phát lại.

## Kịch bản và kết quả

```powershell
python -m a4_evac benchmark --output outputs/a4_open_ground/benchmark

# Tiếp tục khi đã có các lượt cùng đầu vào được lưu.
python -m a4_evac benchmark --output outputs/a4_open_ground/benchmark --resume

# Phát lại lịch đã xuất, không gọi lại optimizer.
python -m a4_evac replay outputs/a4_open_ground/benchmark/safe/M4

# GIF từ lịch đã kiểm tra.
python -m a4_evac gif outputs/a4_open_ground/benchmark/safe/M4 --output outputs/a4_open_ground/a4_evacuation.gif --frame-ms 600
```

`safe`: không nguy cơ. `smoke`: phòng 403 có khói lúc 120s, cháy lúc 180s. `stair_block`: khói tại cụm 1 tầng 4 lúc 90s. `exit_block`: vùng thoát từ sảnh thang 1 ra hành lang hở tầng 1 (EXIT1) không thể tiếp cận từ 120s; các cửa phòng tầng 1 và vùng thoát thang 2 vẫn mở. Đây là các kịch bản giả định, không phải sự kiện thực tế.

GIF mặc định hiển thị mỗi bước mô phỏng trong 600 ms (trước đây 120 ms), giữ khung cuối 3 giây. Điều chỉnh bằng `--frame-ms 1000` để chậm hơn, hoặc `--frame-ms 300` để nhanh hơn. Cờ này cũng dùng với `run`, `compare` hoặc `benchmark` khi bật `--gif`. Tệp `.playback.json` lưu cấu hình thời gian phát riêng với lịch và chỉ số mô phỏng.

Mỗi thư mục phương pháp có `building.json`, `rooms.csv`, `occupancy.json`, `scenario.json`, `assumptions.json`, `schedule.json/.csv`, `simulation_trace.json/.csv`, `hazards.csv`, `queue_lengths.csv`, `validation.json`, `metrics.json`. Thư mục đợt chạy có `comparison.csv/json`, bản đồ PNG và các đường số người đã thoát theo thời gian. Đợt benchmark hiện đo một lần/tổ hợp, không suy rộng thành thống kê nhiều mẫu.

Kết quả của mô hình hành lang tầng 1 hở được lưu riêng tại `outputs/a4_open_ground/benchmark`. Các kết quả trước khi bổ sung thông tin hành lang hở được giữ trong thư mục cũ để đối chiếu; không trộn vào báo cáo mới.

Đã chạy đủ 16 tổ hợp, đầy tải, bước 5 s, thời hạn 900 s:

| Kịch bản | M4: người thoát | M4: hoàn tất (s) |
|---|---:|---:|
| Không sự cố | 1360/1360 | 390 |
| Khói tại phòng 403 | 1360/1360 | 425 |
| Khói ở thang 1 tầng 4 | 1248/1360 | N/A |
| Chặn vùng thoát từ sảnh thang 1 tầng 1 | 1360/1360 | 665 |

Không sự cố: M1/M2 hoàn tất ở 500 s, M3 ở 530 s. Cả 16 lịch đã phát lại và kiểm tra độc lập. Chặn vùng thoát từ sảnh thang 1 trong mô hình mới khác với đóng cửa chung trong mô hình cũ; không so sánh trực tiếp hai kịch bản đó như cùng đầu vào. Mỗi tổ hợp hiện chỉ đo một lần.

`node_occupancy` trong trace là số tại nút sau khởi hành. Cộng nó với `active_moves`, `evacuated_total` và `exposed_unplanned_total` luôn bằng tổng dân số. Ảnh chụp trước khởi hành được lưu riêng để kiểm tra sức chứa nút. Số người mắc kẹt/phơi nhiễm không bị coi là đã thoát hoặc biến mất; số vi phạm an toàn bằng 0 chỉ áp dụng các hành động đã lập lịch.

## Báo cáo LaTeX

```powershell
python -m a4_evac report --results outputs/a4_open_ground/benchmark --output document
.\build_report.ps1
python scripts/package_latex.py
```

- `document/main.tex`: tệp chính, biên dịch **XeLaTeX**.
- `document/chapters/`: các chương tiếng Việt để chỉnh sửa.
- `document/tables/`: bảng khu phòng, giả định và kết quả, sinh từ dữ liệu thực.
- `document/figures/`: sơ đồ dựng lại và biểu đồ.
- `document/measured_results.json`: số liệu gốc cho bảng.
- `output/pdf/A4_Phenikaa_report.pdf`: bản biên dịch để xem.
- `document/A4_Phenikaa_Overleaf.zip`: nguồn LaTeX và hình/bảng để tải lên Overleaf, chọn XeLaTeX.

Điền tên, MSSV, lớp, giảng viên ở trang bìa. Có font dự phòng để dùng Overleaf với XeLaTeX. Giữ bản sao phần tự chỉnh trước khi sinh báo cáo lại vì các chương sẽ được tạo lại. Không dùng số minh họa thay bảng chạy thực.

## Cấu trúc mã

```text
a4_evac/data.py          # chép ảnh A4, dựng topology, lưu nguồn/giả định
a4_evac/algorithms.py    # Dijkstra/A*, multi-source, Dinic, Min-Cost Flow
a4_evac/hazards.py       # lịch nguy cơ và đường đi an toàn
a4_evac/optimize.py      # mạng thời gian, mục tiêu nhiều bước, tách luồng
a4_evac/baselines.py     # ba phương pháp đối chứng
a4_evac/schedule.py      # validator và replay độc lập
a4_evac/runner.py        # đo, xuất dữ liệu, metric
a4_evac/visuals.py       # sơ đồ, biểu đồ, GIF từ lịch
a4_evac/latex.py         # sinh báo cáo tiếng Việt
a4_evac/cli.py           # các lệnh chạy
tests/                  # ví dụ tính tay, oracle, biên thời gian, A4 và replay
document/               # mã LaTeX để viết báo cáo
```

Chưa có giao diện web, rolling horizon, mô phỏng CFD, nhóm người khác tốc độ hay tuyến trú ẩn đi lên. Không dùng kết quả như phương án thoát nạn đã được phê duyệt.
