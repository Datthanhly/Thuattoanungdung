"""Generate an editable Vietnamese XeLaTeX report from measured results."""

import json
from pathlib import Path
import shutil

from .data import build_a4
from .visuals import draw_floorplan


def tex(value):
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
                    "_": r"\_", "{": r"\{", "}": r"\}"}
    return "".join(replacements.get(c, c) for c in str(value))


def create_report(results, output):
    source, root = Path(results), Path(output)
    rows = json.loads((source / "comparison.json").read_text(encoding="utf-8"))
    root.mkdir(parents=True, exist_ok=True)
    figures, tables, chapters = root / "figures", root / "tables", root / "chapters"
    for d in (figures, tables, chapters):
        d.mkdir(exist_ok=True)
    b = build_a4()
    # Use the exact saved assumptions if the result package is available.
    from .data import load_building
    candidates = sorted(source.glob("**/building.json"))
    if candidates:
        b = load_building(candidates[0])
    if b.building_id != build_a4().building_id:
        raise ValueError("Regenerate results with the open-ground-corridor model before creating this report")
    draw_floorplan(b, figures / "a4_floorplan.png", report_mode=True)
    for image in source.glob("*_comparison.png"):
        shutil.copy2(image, figures / image.name)
    room_table = [r"\begin{longtable}{crrrr}", r"\caption{Các khu phòng chép từ ảnh mới nhất.}\label{tab:rooms}\\",
                  r"\toprule Tầng & Phòng/khu & Chiều dài (m) & Chiều sâu (m) & Tối đa \\\midrule\endfirsthead",
                  r"\toprule Tầng & Phòng/khu & Chiều dài (m) & Chiều sâu (m) & Tối đa \\\midrule\endhead"]
    for room in b.rooms:
        room_table.append(f"{room['floor']} & {tex(room['label'])} & {room['width_m']:g} & {room['depth_m']:g} & {room['max_people']} \\")
        room_table[-1] += "\\"
    room_table.extend([r"\midrule\multicolumn{4}{r}{Tổng sức chứa tối đa theo ảnh} & 1360 \\\bottomrule", r"\end{longtable}"])
    (tables / "rooms.tex").write_text("\n".join(room_table), encoding="utf-8")
    result_table = [r"\begin{table}[htbp]\centering",
                    r"\caption{Kết quả thực nghiệm sinh trực tiếp từ chương trình.}\label{tab:results}",
                    r"\begin{tabular}{llrrrr}",
                    r"\toprule Kịch bản & PP & Thoát/Tổng & Hoàn tất (s) & TB thoát (s) & Runtime (s) \\\midrule"]
    for row in rows:
        span = "N/A" if row["makespan_seconds"] is None else f"{row['makespan_seconds']:g}"
        avg = "N/A" if row["avg_exit_time_seconds"] is None else f"{row['avg_exit_time_seconds']:.2f}"
        result_table.append(f"{tex(row['scenario_id'])} & {row['method']} & {row['evacuated_count']}/{row['total_people']} & {span} & {avg} & {row['runtime_seconds']:.3f} " + r"\\")
    result_table.extend([r"\bottomrule", r"\end{tabular}\end{table}"])
    (tables / "results.tex").write_text("\n".join(result_table), encoding="utf-8")
    assumption_rows = [r"\begin{longtable}{p{8cm}r}", r"\toprule Tham số giả định & Giá trị \\\midrule"]
    labels = {
        "time_step_seconds": "Bước thời gian (s)", "walking_speed_m_s": "Tốc độ đi bộ (m/s)",
        "stair_speed_m_s": "Tốc độ trên cầu thang (m/s)", "interfloor_path_m": "Đường đi giữa hai tầng (m)",
        "specific_flow_people_m_s": "Suất thông hành (người/(m.s))",
        "assumed_room_door_width_m": "Bề rộng thông thủy cửa phòng giả định (m)",
        "assumed_stair_usable_width_m": "Bề rộng sử dụng cầu thang giả định (m)",
        "corridor_lane_width_m": "Bề rộng mỗi làn hành lang giả định (m)",
        "corridor_node_storage": "Sức chứa tại nút hành lang (người)",
        "lobby_node_storage": "Sức chứa tại nút sảnh (người)",
        "stair_node_storage": "Sức chứa tại nút cầu thang (người)",
        "fire_propagation_m_s": "Tốc độ lan cháy mô phỏng (m/s)",
        "smoke_propagation_m_s": "Tốc độ lan khói ngang mô phỏng (m/s)",
        "smoke_upstairs_seconds": "Thời gian khói lan lên một tầng (s)",
        "smoke_downstairs_seconds": "Thời gian khói lan xuống một tầng (s)"}
    for key, label in labels.items():
        assumption_rows.append(f"{label} & {b.parameters[key]:g} " + r"\\")
    assumption_rows.extend([r"\bottomrule", r"\end{longtable}"])
    (tables / "assumptions.tex").write_text("\n".join(assumption_rows), encoding="utf-8")
    (root / "main.tex").write_text(MAIN, encoding="utf-8")
    (chapters / "01_problem.tex").write_text(PROBLEM, encoding="utf-8")
    (chapters / "02_model.tex").write_text(MODEL, encoding="utf-8")
    (chapters / "03_algorithms.tex").write_text(ALGORITHMS, encoding="utf-8")
    content = RESULTS + "\n"
    content += "\\subsection{Đọc kết quả đo được}\n"
    for scenario in dict.fromkeys(r["scenario_id"] for r in rows):
        measured = {r["method"]: r for r in rows if r["scenario_id"] == scenario}
        best = measured.get("M4")
        if best is None:
            continue
        content += (f"Kịch bản \\texttt{{{tex(scenario)}}}: M4 cứu được "
                    f"{best['evacuated_count']}/{best['total_people']} người. ")
        if best["makespan_seconds"] is not None:
            content += f"Thời điểm hoàn tất là {best['makespan_seconds']:g} s. "
        else:
            content += "Kế hoạch chưa cứu được toàn bộ dân số trong thời hạn đã đặt; không báo makespan hoàn tất. "
        baseline = measured.get("M1")
        if baseline and baseline["makespan_seconds"] and best["makespan_seconds"] is not None:
            gain = 100 * (baseline["makespan_seconds"] - best["makespan_seconds"]) / baseline["makespan_seconds"]
            content += f"So với M1, thời điểm hoàn tất giảm {gain:.1f}\\%. "
        elif baseline:
            content += f"M1 cứu được {baseline['evacuated_count']} người trong cùng kịch bản. "
        content += "Các con số phụ thuộc giả định về năng lực, nguy cơ và dân số.\n\n"
    content += "\n\\subsection{Kiểm chứng tự động}\n"
    content += (f"Có {len(rows)} lượt chạy trong bảng. Tổng số vi phạm dung lượng ghi nhận là "
                f"{sum(r['capacity_violations'] for r in rows)}, vi phạm an toàn trong hành động đã lập lịch là "
                f"{sum(r['safety_violations'] for r in rows)} và lỗi cấu trúc là {sum(r['structural_violations'] for r in rows)}. "
                "Đây không phải tuyên bố mọi người đều an toàn nếu kế hoạch chưa hoàn tất; số người chưa được cứu và phơi nhiễm được báo riêng.\n")
    content += "\n\\clearpage\n"
    for i, image in enumerate(sorted(figures.glob("*_comparison.png"))):
        content += (r"\begin{figure}[htbp]\centering\includegraphics[width=0.94\textwidth]{figures/" + image.name + "}\n"
                    + r"\caption{Diễn biến số người thoát: " + tex(image.stem.replace("_comparison", "")) + r".}\end{figure}" + "\n")
        if i % 2 == 1:
            content += "\\clearpage\n"
    (chapters / "04_results.tex").write_text(content, encoding="utf-8")
    (chapters / "05_discussion.tex").write_text(DISCUSSION, encoding="utf-8")
    shutil.copy2(source / "comparison.json", root / "measured_results.json")
    (root / "README.md").write_text("""# Báo cáo LaTeX A4

Biên dịch **XeLaTeX** hai lần, hoặc chọn XeLaTeX trên Overleaf:

```powershell
cd document
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

`main.tex` chứa bố cục; `chapters/` là nội dung có thể chỉnh; `tables/` và `figures/` được sinh từ dữ liệu/kết quả thực. Điền tên, MSSV, lớp và giảng viên ở trang bìa. Không thay bảng số liệu bằng số minh họa.

Map là bản chép từ ảnh mới nhất người dùng cung cấp ngày 24/10/2026; chưa khảo sát thực địa. Chỉ ảnh đó có tổng 1.360 và phòng 705=40. Không trộn với các phiên bản trước.

Khu WC gần cầu thang 2 bị bỏ khỏi đồ thị, không được biến thành đường đi hoặc diện tích chờ bổ sung. Theo thông tin bổ sung của người dùng, hành lang tầng 1 hở, không có rào bảo vệ: qua cửa phòng tầng 1 là ra ngoài. Người từ tầng trên thoát khi ra hành lang hở qua sảnh thang tầng 1. Không thêm hai cửa ra ngoài hay tham số bề rộng cổng giả định. Các tham số tốc độ/dung lượng/cháy là giả định, không phải số đo hay chuẩn PCCC.

Đổi kết quả rồi sinh lại bằng `python -m a4_evac report --results outputs/a4_open_ground/benchmark --output document`. Sao lưu phần tự viết trước khi sinh lại vì các file chương được tạo lại.
""", encoding="utf-8")
    print(f"LaTeX report: {root.resolve()}")


MAIN = r"""\documentclass[11pt,a4paper]{report}
\usepackage{fontspec}
\IfFontExistsTF{Times New Roman}{\setmainfont{Times New Roman}}{\setmainfont{TeX Gyre Termes}}
\IfFontExistsTF{Arial}{\setsansfont{Arial}}{\setsansfont{TeX Gyre Heros}}
\IfFontExistsTF{Consolas}{\setmonofont{Consolas}}{\setmonofont{Latin Modern Mono}}
\usepackage[margin=2.5cm]{geometry}
\usepackage{amsmath,amssymb,booktabs,longtable,graphicx,xcolor}
\usepackage[unicode,colorlinks=true,linkcolor=blue!45!black,urlcolor=blue!60!black]{hyperref}
\usepackage{listings}
\lstset{basicstyle=\ttfamily\small,breaklines=true,frame=single,columns=fullflexible}
\renewcommand{\contentsname}{Mục lục}
\renewcommand{\chaptername}{Chương}
\renewcommand{\tablename}{Bảng}
\renewcommand{\figurename}{Hình}
\renewcommand{\bibname}{Tài liệu tham khảo}
\renewcommand{\appendixname}{Phụ lục}
\setcounter{tocdepth}{1}
\setlength{\parskip}{0.25em}
\setlength{\parindent}{1.2em}
\clubpenalty=10000
\widowpenalty=10000
\displaywidowpenalty=10000
\begin{document}
\begin{titlepage}
\centering
{\Large\bfseries TRƯỜNG ĐẠI HỌC PHENIKAA\par}
\vspace{0.7cm}
{\large ĐỒ ÁN MÔN THUẬT TOÁN ỨNG DỤNG\par}
\vspace{2.5cm}
{\LARGE\bfseries TỐI ƯU HÓA SƠ TÁN TRONG TÒA NHÀ A4\par}
\vspace{0.7cm}
{\Large Đồ thị động và mạng luồng mở rộng theo thời gian\par}
\vspace{1.3cm}
{\large Nghiên cứu mô phỏng từ sơ đồ người dùng cung cấp\par}
\vfill
\begin{tabular}{ll}
Sinh viên: & \rule{7cm}{0.4pt} \\[0.5cm]
Mã sinh viên / Lớp: & \rule{7cm}{0.4pt} \\[0.5cm]
Giảng viên hướng dẫn: & \rule{7cm}{0.4pt}
\end{tabular}
\vfill
Hà Nội, tháng 10 năm 2026
\end{titlepage}
\chapter*{Tóm tắt}
\addcontentsline{toc}{chapter}{Tóm tắt}
Đồ án xây dựng mô hình tối ưu lịch sơ tán cho sơ đồ 7 tầng của tòa nhà A4 do người dùng cung cấp. Phiên bản ảnh cuối có 27 khu phòng, tổng sức chứa tối đa 1.360 người; khu vệ sinh gần cụm cầu thang thứ hai không được đưa vào mô hình. Sảnh và hai cụm cầu thang được giữ làm đường di chuyển. Bài toán sử dụng Dijkstra, mô phỏng nguy cơ bằng Dijkstra đa nguồn, Dinic và Min-Cost Flow trên mạng thời gian. Mục tiêu lần lượt là tối đa số người thoát, tối thiểu thời điểm cứu người cuối và tối thiểu tổng thời điểm thoát. Nghiệm được phân rã thành lịch nhóm nguyên và kiểm tra lại bằng một bộ kiểm tra độc lập.

Theo xác nhận bổ sung của người dùng, hành lang tầng 1 hở và không có rào bảo vệ; người ở tầng 1 thoát ngay khi qua cửa phòng, người từ tầng trên thoát khi ra hành lang hở từ sảnh thang tầng 1. Bề rộng thông thủy, tốc độ và dung lượng còn là giả định được công bố. Kết quả chỉ có tính tối ưu trong mô hình đã xây; không phải phương án PCCC được kiểm định.
{\small\setlength{\parskip}{0pt}\tableofcontents}
\clearpage
\input{chapters/01_problem}
\input{chapters/02_model}
\input{chapters/03_algorithms}
\input{chapters/04_results}
\input{chapters/05_discussion}
\appendix
\chapter{Dữ liệu khu phòng}
\input{tables/rooms}
\chapter{Hướng dẫn tái lập}
\begin{lstlisting}
python -m pip install -r requirements.txt
python -m pytest -q
python -m a4_evac generate-data
python -m a4_evac benchmark --output outputs/a4_open_ground/benchmark
python -m a4_evac report --results outputs/a4_open_ground/benchmark
python -m a4_evac replay outputs/a4_open_ground/benchmark/safe/M4
python -m a4_evac gif outputs/a4_open_ground/benchmark/safe/M4
\end{lstlisting}
\begin{thebibliography}{9}\raggedright
\bibitem{user-map} Người dùng, \emph{Sơ đồ mặt bằng 7 tầng -- cửa ra vào và sức chứa A4}, ảnh cuối cùng và thông tin bổ sung rằng hành lang tầng 1 hở, qua cửa phòng là ra ngoài, cung cấp trong cuộc trao đổi ngày 24/10/2026. Nguồn dữ liệu của đồ án, chưa được đối chiếu hồ sơ công trình.
\bibitem{clrs} T. H. Cormen, C. E. Leiserson, R. L. Rivest, C. Stein, \emph{Introduction to Algorithms}, MIT Press, ấn bản 4, 2022. ISBN 9780262046305. \url{https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/}
\bibitem{flows} R. K. Ahuja, T. L. Magnanti, J. B. Orlin, \emph{Network Flows: Theory, Algorithms, and Applications}, Prentice Hall, 1993. ISBN 9780136175490. Thông tin nhà xuất bản: \url{https://www.pearson.com/en-us/subject-catalog/p/nonlinear-systems/P200000003456}
\end{thebibliography}
\end{document}
"""

PROBLEM = r"""\chapter{Bài toán và dữ liệu đầu vào}
\section{Mục tiêu}
Tìm một lịch đi và chờ cho nhiều người, thay vì chỉ tìm một đường ngắn nhất cho từng người. Lịch phải tuân thủ sức chứa tại các phòng, cửa, hành lang, sảnh, cầu thang và các mốc nguy hiểm. Các thuật toán chính được tự cài đặt; NetworkX chỉ làm oracle trong kiểm thử.
\section{Phiên bản sơ đồ được sử dụng}
Sơ đồ mới nhất được chọn làm nguồn duy nhất \cite{user-map}. Các tầng 1 đến 7 có sức chứa lần lượt là 180, 180, 200, 200, 200, 240 và 160 người. Phòng 705 là 40 người; tổng bằng 1.360. Các ảnh cũ trong cuộc trao đổi có thứ tự phòng hoặc tổng khác và không được trộn vào dữ liệu này.

Có 27 \emph{khu phòng} trong mô hình. Các nhãn như 104-105 hay 603-604-605 được gộp thành một nguồn có sức chứa tối đa 80, không đếm thành nhiều nguồn độc lập. Độ sâu phòng là 8,8 m, hành lang rộng 2 m. Khối sảnh/cầu thang trên ảnh có chiều dài theo phương ngang 7,2 m hoặc 13,6 m; phần lõi thang được ghi 5 m. Con số 5 m không được đồng nhất với bề rộng thông thủy của vế thang.
\section{Phạm vi bỏ khu vệ sinh}
Khu vệ sinh gần cầu thang giữa (cụm 2) bị loại khỏi đồ thị: không sinh nút, không gán dân số, không có tuyến đi xuyên và không cộng diện tích đó vào sức chứa sảnh. Sảnh vẫn có nút trung chuyển riêng. Thang máy không được dùng; người mô phỏng di chuyển xuống tầng dưới qua hai cụm thang.
\section{Tọa độ và cửa ra ngoài}
Chiều dài theo các khối trên ảnh khác nhau giữa các tầng. Mỗi tầng dùng tọa độ cục bộ theo thứ tự trái sang phải. Hai nút thang cùng chỉ số được nối theo tầng bằng quãng đường giữa tầng giả định, không dùng chênh lệch tọa độ ngang của ảnh để tính đường chéo vật lý.

Người dùng xác nhận hành lang tầng 1 không có rào bảo vệ và mở trực tiếp ra ngoài. Vì vậy, mỗi cửa phòng tầng 1 chính là một nút thoát hấp thụ: đến cửa là kết thúc sơ tán, không phải đi dọc hành lang tới cửa chung. Người từ tầng trên đi xuống một trong hai thang, qua sảnh tầng 1 rồi ra hành lang hở thì được ghi nhận đã thoát. Hai nhãn EXIT1/EXIT2 chỉ vùng thoát từ sảnh thang, không phải hai cửa bổ sung. Có tổng cộng 9 điểm hấp thụ: 7 cửa phòng tầng 1 và 2 vùng thoát từ thang.

Dân số 1.360 là kịch bản đầy tải, không phải số người có mặt thực. Bề rộng cửa phòng và năng lực thang vẫn cần đo.
\begin{figure}[p]\centering
\includegraphics[width=0.98\textwidth,height=0.86\textheight,keepaspectratio]{figures/a4_floorplan.png}
\caption{Hành lang tầng 1 tô xanh lá: qua cửa phòng là ra ngoài; hai thang thoát qua sảnh ra hành lang hở.}
\label{fig:map}\end{figure}
"""

MODEL = r"""\chapter{Mô hình đồ thị và thời gian}
\section{Đồ thị không gian}
Đặt $G=(V,E)$ có các loại nút ROOM, DOOR, CORRIDOR, LOBBY, STAIR và EXIT. Mỗi khu phòng có một nguồn dân số. Khu ghép hoặc phòng dài ít nhất 8 m có hai cửa, phòng ngắn hơn có một cửa theo chú giải ảnh. Tọa độ chính xác của từng cửa chưa được đo, nên hai cửa được đặt ở khoảng 20\% và 80\% chiều dài phòng; một cửa đặt ở giữa. Có tổng cộng 50 cửa phòng trong bản nhập này.

Cạnh gồm phòng-cửa, cửa-hành lang ở tầng 2--7, hai làn hành lang ở tầng trên, hành lang-sảnh, sảnh-thang và thang xuống tầng dưới. Các cạnh chỉ đi khỏi nguồn phòng. Có 43 cửa phòng tầng trên loại DOOR; 7 cửa phòng tầng 1 mang loại EXIT. Người đã tới nút EXIT không quay lại và không bị cộng thêm một bước thời gian để ra ngoài.

Tầng 1: mỗi cửa phòng hấp thụ theo đúng năng lực cửa đó, không thêm cửa ngoài hoặc bước thời gian. Năng lực hấp thụ hai vùng thoát từ sảnh thang là $N=1360$ (không chặt); lưu lượng thực vẫn bị giới hạn bởi cạnh sảnh-thang/hành lang. Với $D$ là cửa phòng tầng 1, $T_{exit}=T_{arrival}(D)$.

Mô phỏng kết thúc tại hành lang hở tầng 1; không xét đường tới điểm tập kết hoặc khói ngoài trời.
\section{Giả định định lượng}
\input{tables/assumptions}
Các giá trị trong bảng là tham số mô phỏng có thể chỉnh, không được trình bày là tiêu chuẩn PCCC hay số đo thực tế. Đặc biệt, lõi thang 5 m trên ảnh khác với vế thang sử dụng giả định 1,5 m. Hành lang 2 m được chia hai làn cố định mỗi làn 1 m; mỗi hướng có giới hạn riêng, tránh cấp hai lần toàn bộ bề rộng cho hai hướng.
\section{Rời rạc hóa và mạng mở rộng}
Với bước $\Delta t$, cạnh $e$ dài $\ell_e$ và tốc độ $v_e$ có thời lượng:
\[
\tau_e=\ell_e/v_e,\qquad d_e=\lceil\tau_e/\Delta t\rceil.
\]
Với horizon $K$, tạo trạng thái $(v,k)$, $k=0,\ldots,K$. Tách mỗi trạng thái thành in/out với cạnh chứa dung lượng $B_v$. Cạnh đi nối $(u,k)^{out}$ tới $(v,k+d_e)^{in}$. Cạnh chờ chỉ xuất hiện nếu nút cho chờ và còn an toàn tại cả hai đầu. Siêu nguồn cấp dân số ở $k=0$; trạng thái cửa thoát nối siêu đích bằng năng lực cửa ở từng mốc.

Năng lực vào mỗi bước là $U_e=\lfloor w_e q\Delta t\rfloor$, trong đó $q$ là suất thông hành giả định. Để xác định rõ giới hạn người đang đi, mô hình đặt $C_e=d_eU_e$: tối đa $d_e$ đoàn khởi hành liên tiếp cùng hiện diện. Từ $x_{e,k}\le U_e$ suy ra
\[
\sum_{j=k-d_e+1}^{k}x_{e,j}\le d_eU_e=C_e.
\]
Đây là mô hình đoàn/ô tài nguyên giả định, không phải sức chứa đoạn đường đã đo từ mật độ thực tế. Nếu muốn nhập $C_e$ chặt hơn $d_eU_e$, cần ràng buộc chiếm dụng chồng lấp hoặc mô hình khác; chương trình hiện từ chối cấu hình đó để tránh khẳng định sai tính tối ưu.
\section{Nguy cơ cháy và khói}
Thời điểm cháy/khói tới các nút được tính bằng Dijkstra đa nguồn trên đồ thị nguy cơ; liên kết có thể khác đồ thị người đi. Khói có thể lan lên cầu thang dù người chỉ đi xuống. Thời điểm mất an toàn là
\[
T_v=\min(T_v^{fire},T_v^{smoke},T_v^{closure}).
\]
Một nút chỉ hợp lệ khi $t<T_v$. Cạnh đóng bảo thủ khi một trong hai đầu nguy hiểm hoặc tới mốc khóa riêng; cả chuyến đi phải kết thúc trước mốc đóng. Đến đúng lúc nguy hiểm là không hợp lệ.
\section{Thứ tự sự kiện}
Tại mốc k: cập nhật nguy cơ, ghi nhận đến nút, kiểm tra sức chứa, ra lệnh rời nút và ghi người thoát. Sức chứa nút được đo sau đến nhưng trước rời. Trace lưu thêm số người ở nút sau rời để kiểm tra bảo toàn với số đang đi và đã thoát.
"""

ALGORITHMS = r"""\chapter{Thuật toán và tính đúng đắn}
\section{Dijkstra và A*}
Dijkstra dùng heap và danh sách kề với trọng số không âm; parent lưu cạnh để truy vết. Hàm tìm đường tổng quát hỗ trợ A* thông qua heuristic admissible; mặc định h=0 giữ đúng tính tối ưu. Trong mô phỏng động, thời điểm đến là nhãn để kiểm tra nguy cơ trên từng cạnh. Thuật toán bỏ qua hàng đợi khi chọn đường; lệnh di chuyển vẫn phải qua bộ kiểm tra dung lượng.
\section{Dinic và kiểm tra khả thi}
Dinic tạo residual graph, BFS dựng level graph, rồi gửi blocking flow bằng DFS lặp. Dùng stack tránh giới hạn đệ quy khi mạng sâu. Trên TEN ở hạn K, max flow cho $F(K)$, số người thoát tối đa trong mô hình. Mạng chỉ có dung lượng nguyên nên luồng tăng và nghiệm là nguyên. Các trạng thái không thể tới cửa trước K được cắt bằng cận dưới đường đi tự do; phép cắt không loại một lịch hợp lệ vì hàng đợi không thể làm đường đi nhanh hơn.
\section{Mục tiêu theo thứ tự ưu tiên}
Đầu tiên tính $F(K_{max})$. Tìm kiếm nhị phân horizon nhỏ nhất $K^*$ vẫn cứu được đúng lượng người đó. Tính đơn điệu theo horizon giữ vì kéo dài hạn không xóa lựa chọn cũ. Nếu $F(K_{max})<N$, không công bố thời gian hoàn tất toàn bộ; vẫn có thể tìm thời điểm cứu người cuối cho lượng cứu tối đa.

Ở $K^*$, Min-Cost Flow đưa đúng $F(K_{max})$ tới đích. Chỉ các cạnh thoát tại bước k có chi phí k, nên mục tiêu là
\[
\min\sum_{exit,k} k\,x_{exit,k}.
\]
Nhân với $\Delta t$ cho tổng thời điểm thoát tính bằng giây. Khi mọi người được cứu, thứ tự là max số người, min makespan và min tổng thời điểm thoát.
\section{Min-Cost Flow có potentials}
Successive shortest augmenting paths dùng chi phí giảm $c'(u,v)=c(u,v)+p(u)-p(v)$. Cạnh thuận ban đầu có chi phí không âm nên potentials bắt đầu 0; sau Dijkstra cập nhật potentials bằng nhãn khoảng cách hữu hạn. Cạnh residual ngược có chi phí âm tương ứng, cho phép rút lại phân bổ trước.

Mọi đường nguồn-đích có chi phí giảm 0 sau cập nhật có cùng chi phí gốc $p(t)-p(s)$. Chương trình gửi một blocking flow trên các cạnh đó thay vì chạy heap riêng cho từng nhóm nhỏ. Việc gửi nhiều đường rẻ nhất trong cùng pha không đổi mục tiêu và vẫn được đối chứng với NetworkX trên đồ thị nhỏ.
\section{Giải mã và kiểm tra độc lập}
Mạng thuận theo thời gian là DAG. Luồng dương được phân rã thành nhóm nguyên với các hành động MOVE/WAIT và sự kiện EXIT. Bộ kiểm tra không đọc residual graph mà dựng lại từ event log: liên tục vị trí/thời gian, thời lượng cạnh, tồn tại cửa, an toàn, năng lực khởi hành, tổng người đang đi, sức chứa nút và cửa thoát.

Người chưa được chọn cứu vẫn ở nguồn và chiếm chỗ khi nguồn còn an toàn. Trong đồ thị này phòng chỉ có cạnh đi ra, nên người ở lại không bị luồng khác đi xuyên qua. Tiền tố mắc kẹt của baseline dừng tại sự kiện an toàn cuối; về sau nếu nơi đứng nguy hiểm thì số người đó được báo phơi nhiễm riêng.
\section{Độ phức tạp}
Dijkstra có độ phức tạp $O((V+E)\log V)$. Dinic tổng quát là $O(V^2E)$. TEN có $O(VK)$ nút và $O((V+E)K)$ cạnh trước cắt trạng thái. Min-Cost Flow cần các pha Dijkstra và blocking flow; số pha phụ thuộc cấu trúc chi phí và dữ liệu. Không đồng nhất độ phức tạp Dinic với toàn bộ quy trình nhiều horizon. Runtime và bộ nhớ cần được đo thực nghiệm \cite{clrs,flows}.
"""

RESULTS = r"""\chapter{Thiết kế thực nghiệm và kết quả}
\section{Các phương pháp so sánh}
M1 chọn tuyến ngắn nhất tại thời điểm đầu và giữ tuyến; M2 tính lại tuyến theo nguy cơ ở vị trí và thời điểm hiện tại; M3 chọn bước tiếp theo dựa trên đường còn lại, năng lực vào và chỗ đã đặt; M4 tối ưu lịch toàn cục trên TEN. Baseline dùng thứ tự ID để phá hòa và đặt chỗ bảo thủ tới lúc có lệnh rời nút. Tất cả dùng cùng dung lượng, lịch nguy cơ, validator và bộ phát lại. M3 là heuristic, không mặc định tốt hơn M1/M2 trong mọi trường hợp.
\section{Kịch bản}
\begin{itemize}
\item \texttt{safe}: không cháy/khói, tất cả vùng thoát mở.
\item \texttt{smoke}: khói tại phòng 403 lúc 120 s, cháy tại đó lúc 180 s.
\item \texttt{stair\_block}: khói ở cụm thang 1 tầng 4 lúc 90 s.
\item \texttt{exit\_block}: vùng thoát từ sảnh thang 1 ra hành lang hở tầng 1 (EXIT1) mất khả năng tiếp cận lúc 120 s; các cửa phòng tầng 1 và vùng thoát thang 2 vẫn mở. Đây là chặn cục bộ vùng thoát, không phải đóng một cửa chung của hành lang.
\end{itemize}
Các thời điểm và tốc độ nguy cơ là giả định nghiên cứu, không phải sự kiện có thật tại A4. Mỗi tổ hợp trong bảng chạy một lần; đây chưa phải phân tích thống kê nhiều seed hoặc đánh giá biến thiên máy tính. Nếu không bật tracemalloc, peak bộ nhớ được ghi null chứ không điền số ước lượng.
\section{Chỉ số và bảng số liệu}
Số người và tỷ lệ thoát được ưu tiên trước thời gian. Makespan chỉ có khi toàn bộ dân số được cứu; N/A được giữ nguyên ở các lượt thiếu. Thời gian thoát trung bình chỉ tính trên người đã thoát và không thay thế chỉ số toàn dân số. Runtime trong bảng chỉ đo quá trình giải, không gồm dựng biểu đồ/ghi toàn bộ file.
\clearpage
\input{tables/results}
"""

DISCUSSION = r"""\chapter{Thảo luận, giới hạn và kết luận}
\section{Ý nghĩa kết quả}
M4 tối ưu theo các giả định đã công bố, trong đó toàn bộ diễn biến nguy cơ của kịch bản đã được biết trước. Lợi thế có thể đến từ phân chia hai cầu thang, chọn các cửa phòng khác nhau hoặc đặt lịch chờ để tôn trọng năng lực. Phải xem đồng thời số người được cứu, mức bão hòa và thời điểm thoát; một trung bình nhỏ hơn trên tập ít người không chứng minh phương pháp tốt hơn.
\section{Những điểm cần xác minh ở công trình}
Cần đo bề rộng và vị trí cửa phòng, độ thông thủy vế thang, lối vào sảnh và quãng đường giữa tầng. Quy tắc hành lang hở tầng 1 đã được người dùng xác nhận. Sảnh 7,2/13,6 m và lõi thang 5 m trên ảnh không tự xác định năng lực sơ tán. Chiều dài các tầng khác nhau cho thấy đây là sơ đồ cục bộ; không suy ra mô hình hình học 3D chính xác.

Khu vệ sinh bị bỏ khỏi mô hình theo yêu cầu, nhưng không được biến phần bỏ đó thành chỗ chờ trống hay lối tắt. Dân số đầy tải bằng sức chứa tối đa không thay thế dữ liệu số người có mặt theo lịch học.
\section{Giới hạn mô hình}
Mô hình dùng luồng người đồng nhất, không có phản ứng chậm, chen lấn, hỗ trợ di chuyển hay hành vi không tuân thủ. Hai làn hành lang 1 m là cách phân bổ cố định bảo thủ; không giải bài toán hai hướng chia sẻ linh hoạt toàn bộ hành lang. Chỉ cho đi xuống cầu thang; nếu cần tuyến đi lên tới nơi trú ẩn phải bổ sung đồ thị và giả định mới.

Cháy/khói chỉ là lan truyền sự kiện theo đồ thị, không phải CFD, liều phơi nhiễm hoặc mô hình sống sót. Phơi nhiễm được báo là số người ở vị trí không an toàn, không suy diễn tử vong. Không có tái tối ưu rolling horizon khi nhận thông tin mới; muốn làm phải giữ trạng thái đang đi và đã thoát, không đặt người về phòng ban đầu.
\section{Hướng phát triển và kết luận}
Khảo sát thực địa và cập nhật các tham số chưa biết; kiểm chứng với mô phỏng chuyên ngành; đo độ nhạy theo dân số, năng lực và bước thời gian; bổ sung nhiều nhóm người và tái lập lịch. Giao diện web có thể gọi API sau khi lõi dữ liệu và mô hình đã được xác nhận.
Sản phẩm phục vụ học tập và đánh giá thuật toán, không thay thế khảo sát hay thiết kế an toàn PCCC được phê duyệt.
"""
