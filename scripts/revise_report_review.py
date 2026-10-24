"""Apply the one-time editorial revision to the existing LaTeX report."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]/'document/Mau'


def edit(name, callback):
    p=ROOT/'section'/name
    p.write_text(callback(p.read_text(encoding='utf-8')),encoding='utf-8')


def chapter1(s):
    s=s.replace(r'\includegraphics[width=\linewidth,height=12.2cm,keepaspectratio]{figures/a4_floorplan.png}',
        r'''\begin{subfigure}{\linewidth}\centering
\includegraphics[width=\linewidth]{figures/a4_upper.pdf}
\caption{Các tầng 7--5.}\end{subfigure}
\begin{subfigure}{\linewidth}\centering
\includegraphics[width=\linewidth]{figures/a4_lower.pdf}
\caption{Các tầng 4--1.}\end{subfigure}''')
    s=s.replace('Hệ thống thực nghiệm được triển khai dưới dạng giao diện dòng lệnh,',
        'Mã nguồn và cấu hình thực nghiệm được lưu trong gói tái lập của nghiên cứu \\cite{code}. Hệ thống được triển khai dưới dạng giao diện dòng lệnh,')
    s += r'''
\topic{Tổng quan nghiên cứu và vị trí của mô hình}
Ford và Fulkerson \cite{ford} xét bài toán cực đại hóa lượng vận chuyển trong một khoảng thời gian khi mỗi cạnh có thời lượng và năng lực. Điểm cốt lõi là năng lực được khai thác lặp theo thời gian, vì vậy luồng tĩnh riêng lẻ chưa mô tả được lịch khởi hành. Mạng TEN sử dụng trong nghiên cứu kế thừa cách gắn thời gian vào trạng thái, đồng thời bổ sung sức chứa nút và mốc mất an toàn.

Chalmet, Francis và Saunders \cite{chalmet} xây dựng các mô hình mạng cho sơ tán công trình, liên kết cách biểu diễn không gian với số người thoát và thời điểm thoát. Tổng quan của Dhamala \cite{survey} phân biệt các lớp luồng cực đại, luồng chi phí nhỏ nhất, luồng nhanh nhất và luồng đến sớm. M4 sử dụng thứ tự ưu tiên về lượng thoát, thời điểm thoát cuối và tổng thời điểm thoát; việc tối ưu tổng thời điểm không đồng nghĩa tối ưu mọi tiền tố của đường cong tích lũy.

Các cấu trúc mạng dư, luồng cực đại và chi phí giảm được hệ thống hóa trong Ahuja, Magnanti và Orlin \cite{ahuja}. Trong bài toán A4, mạng dư phục vụ hiệu chỉnh phân bổ giữa nhiều nguồn phòng; potentials cho phép dùng đường ngắn nhất khi cạnh ngược xuất hiện chi phí âm. Sự kết hợp này tạo một mô hình điều phối thay vì ghép độc lập các tuyến ngắn nhất.

Khác biệt của trường hợp nghiên cứu là bảy cửa phòng tầng 1 kết thúc trực tiếp ở biên ngoài, trong khi dân số tầng trên phải qua hai hệ thang. Do đó, dân số tầng 1 không được cộng vào lưu lượng bắt buộc qua lát cắt cầu thang. Phân biệt này được sử dụng khi xây dựng cận dưới và phân tích nút thắt ở phần thực nghiệm.

\topic{Bố cục báo cáo và kế hoạch phân công}
Phần 1 xác lập bài toán và dữ liệu. Phần 2 trình bày đồ thị, ràng buộc và hàm mục tiêu. Phần 3 mô tả các thuật toán cùng lập luận tính đúng đắn. Phần 4 trình bày cài đặt và kiểm chứng. Phần 5 phân tích kết quả, đối chứng bổ sung, độ nhạy và giới hạn. Các phụ lục lưu danh sách khu phòng, ký hiệu và dấu vết dữ liệu.

\begin{table}[H]\centering\caption{Kế hoạch phân công nhiệm vụ trong nhóm}
\small\begin{tabularx}{\linewidth}{P{3cm}X}\toprule
Thành viên & Phạm vi phụ trách\\\midrule
Lý Thành Đạt & Tích hợp mô hình đồ thị, bộ tối ưu M4 và kiểm tra tính nhất quán của kết quả.\\
Đinh Đức Mạnh & Chuẩn hóa dữ liệu mặt bằng, mô hình nguy cơ và các phương pháp đối chứng.\\
Phạm Văn Đạt & Thiết kế thực nghiệm, trực quan hóa, tổng hợp bảng và biên tập nội dung.\\\bottomrule
\end{tabularx}\end{table}
Kế hoạch phân công xác định đầu mối cho từng nhóm công việc; việc rà soát ký hiệu, số liệu và kết luận được thực hiện chung. Bảng này mô tả phương án tổ chức công việc, không thay thế nhật ký đóng góp của từng thành viên.
'''
    return s


def chapter2(s):
    s=s.replace('ground_floor.png','ground_vector.pdf')
    s=s.replace(r'\lfloor1,2\times1,3\times5\rfloor=7',r'\lfloor1{,}2\times1{,}3\times5\rfloor=7')
    s=s.replace('$N=1360$',r'$N=1.360$')
    start=s.index(r'\begin{table}[H]\centering\caption{Cấu hình tham số')
    end=s.index(r'\end{table}',start)+len(r'\end{table}')
    s=s[:start]+r'''\begin{table}[H]\centering\caption{Cấu hình tham số cơ sở và phân loại nguồn}
\small\begin{tabularx}{\linewidth}{P{5.1cm}P{2.7cm}X}\toprule
Tham số & Giá trị & Nguồn / loại tham số\\\midrule
Bước thời gian & 5 s & Thiết kế rời rạc hóa.\\
Tốc độ đi bộ / trên thang & 1,2 / 0,7 m/s & Minh họa, cần hiệu chỉnh.\\
Quãng đường giữa hai tầng & 12 m & Giả định hình học.\\
Suất thông hành $q$ & 1,3 người/(m.s) & Minh họa, không phải số đo A4.\\
Bề rộng cửa phòng & 1,2 m & Giả định thông thủy.\\
Bề rộng sử dụng vế thang & 1,5 m & Giả định, khác lõi thang 5 m.\\
Bề rộng hành lang / làn & 2 / 1 m & Sơ đồ / quy tắc chia làn.\\
Sức chứa nút hành lang & 24 người & Minh họa ở mức nút.\\
Sức chứa sảnh / thang & 30 / 36 người & Minh họa ở mức nút.\\
Lan cháy / khói ngang & 0,03 / 0,15 m/s & Độ trễ sự kiện minh họa.\\
Khói lên / xuống một tầng & 25 / 45 s & Độ trễ sự kiện minh họa.\\\bottomrule
\end{tabularx}\end{table}'''+s[end:]
    s=s.replace('$(v,k)^{in}$',r'$(v,k)^{\mathrm{in}}$').replace('$(v,k)^{out}$',r'$(v,k)^{\mathrm{out}}$')
    s=s.replace('$u_k^{in}$',r'$u_k^{\mathrm{in}}$').replace('$u_k^{out}$',r'$u_k^{\mathrm{out}}$').replace('$v_{k+d}^{in}$',r'$v_{k+d}^{\mathrm{in}}$').replace('$u_{k+1}^{in}$',r'$u_{k+1}^{\mathrm{in}}$')
    s=s.replace(r'node[above]{$B_u$}',r'node[above,align=center]{Tách nút\\$B_u$}')
    s=s.replace(r'node[above]{$U_e$, đi}',r'node[above,align=center]{Di chuyển\\$U_e$, $d_e$ bước}')
    s=s.replace(r'node[below right]{chờ}',r'node[below right,align=center]{Chờ một bước\\$B_u$}')
    s=s.replace('Đến từ A','Bước đến A').replace('Đến từ B','Bước đến B')
    return s


def chapter3(s):
    s=s.replace(r"c'(u,v)",r'c^{\prime}(u,v)').replace("n'",r'n^{\prime}').replace("m'",r'm^{\prime}')
    s=s.replace('Mỗi cạnh thuận có một cạnh dư ngược tương ứng.',r'Thuật toán Dinic \cite{dinic} sử dụng đồ thị mức và luồng chặn. Mỗi cạnh thuận có một cạnh dư ngược tương ứng.')
    captions=['Tìm tuyến ngắn nhất tới một tập đích','Lan truyền thời điểm sự kiện',
              'Giải luồng cực đại bằng Dinic','Luồng chi phí nhỏ nhất với potentials và luồng chặn',
              'Tối ưu ba mục tiêu M4 trên TEN']
    s=re.sub(r'\\noindent\\textbf\{Giả mã [123]\. [^\n]+\}\n','',s)
    parts=s.split(r'\begin{lstlisting}')
    assert len(parts)==6
    s=parts[0]
    for i,part in enumerate(parts[1:]):
        block,after=part.split(r'\end{lstlisting}',1)
        s+=r'\begin{algorithm}[H]\caption{'+captions[i]+r'}\label{alg:'+str(i+1)+r'}'+'\n'
        s+=r'\begin{lstlisting}[frame=none]'+block+r'\end{lstlisting}'+'\n'+r'\end{algorithm}'+after
    s=s.replace('Ba phương pháp đối chứng và tính công bằng khi so sánh','Các phương pháp đối chứng và chính sách chia tải')
    s=s.replace(r'\\\bottomrule'+'\n'+r'\end{tabularx}\end{table}'+'\nĐiểm M3',
        r'\\'+'\n'+r'M1E & Chia đều hai thang, giữ tuyến ngắn nhất đến đích đã gán. & Cùng chính sách đặt chỗ và chờ của M1.\\\bottomrule'+'\n'+r'\end{tabularx}\end{table}'+'\nĐiểm M3')
    s=s.replace(r'+4\rho_e+4\rho_v',r'+\alpha\rho_e+\alpha\rho_v')
    s=s.replace('Hệ số 4 là lựa chọn heuristic trong mã, chưa được tối ưu bằng một đợt tìm siêu tham số. M3 do đó có thể kém M1 hoặc M2; không suy ra tính trội chỉ từ việc thêm yếu tố dung lượng.',
        r'''Ở đây $\rho_e$ là tỷ lệ năng lực cạnh đã đặt tại bước $k$; $\rho_v$ là tỷ lệ sức chứa nút đích đã đặt tại bước đến. Cấu hình chính dùng $\alpha=4$; khảo sát bổ sung xét $\alpha\in\{1,2,4,8\}$. M1E gán luân phiên từng người ở tầng trên cho EXIT1 và EXIT2, rồi tính tuyến ngắn nhất đến vùng thoát được gán; 180 người tầng 1 vẫn đi trực tiếp qua cửa phòng. Vì vậy, đối chứng này kiểm tra riêng lợi ích của cân bằng tải khi chưa tối ưu toàn cục.''')
    return s


def chapter4(s):
    start=s.index(r'\begin{tikzpicture}')
    end=s.index(r'\end{tikzpicture}',start)+len(r'\end{tikzpicture}')
    s=s[:start]+r'''\begin{tikzpicture}[>=Stealth,every node/.style={font=\footnotesize,draw,rounded corners,align=center,minimum width=2.1cm,minimum height=1.1cm},node distance=.45cm]
\node (a) {Mặt bằng\\và tham số};
\node[right=of a] (b) {Đồ thị\\và nguy cơ};
\node[right=of b] (c) {Bộ giải\\M1--M4};
\node[right=of c] (d) {Lịch và\\kiểm chứng};
\node[right=of d] (e) {Chỉ số và\\phát lại};
\draw[->] (a)--(b);\draw[->] (b)--(c);\draw[->] (c)--(d);\draw[->] (d)--(e);
\end{tikzpicture}'''+s[end:]
    s=s.replace('Bộ kiểm thử gồm 45 ca đạt yêu cầu','Bộ kiểm thử gồm 48 ca đạt yêu cầu')
    start=s.index(r'\begin{lstlisting}',s.index(r'\topic{Quy trình'))
    end=s.index(r'\end{lstlisting}',start)+len(r'\end{lstlisting}')
    s=s[:start]+r'''\begin{lstlisting}[language={},caption={Các bước chạy thực nghiệm và kiểm tra lịch}]
$results = "outputs/a4_open_ground/benchmark"
python -m pytest -q
python -m a4_evac generate-data
python -m a4_evac benchmark --output $results
python -m a4_evac replay "$results/safe/M4"
\end{lstlisting}'''+s[end:]
    s=s.replace('Các lệnh dưới đây mô tả cấu hình thực thi tại thư mục gốc của dự án.',
        r'Các lệnh dưới đây mô tả quy trình thực nghiệm; hướng dẫn cài đặt và biên dịch tài liệu được tách vào README. Gói mã nguồn kèm báo cáo được dẫn tại \cite{code}.')
    start=s.index(r'\begin{figure}[H]',s.index(r'\topic{Trực quan'))
    end=s.index(r'\end{figure}',start)+len(r'\end{figure}')
    s=s[:start]+r'''\begin{landscape}
\begin{figure}[p]\centering
\includegraphics[width=\linewidth]{figures/timeline.pdf}
\caption{Năm khung phát lại lịch M4 không sự cố tại 0, 100, 200, 300 và 390 s. Số người đã thoát được ghi trên từng khung; các chấm biểu diễn nhóm di chuyển.}
\label{fig:timeline}\end{figure}
\end{landscape}'''+s[end:]
    return s


def normalize(s):
    for old in ['\u2010','\u2011','\u2012','\u2013','\u2014','\u2212']:
        s=s.replace(old,'--' if old in ['\u2013','\u2014'] else '-')
    for a,b in [('lượng cứu','lượng thoát'),('đường cứu','đường sơ tán'),('cứu được','sơ tán được'),
                ('có thể cứu','có thể sơ tán'),('cứu đủ','sơ tán đủ'),('cứu người cuối','thoát cuối'),
                ('cứu tối đa','thoát tối đa')]:s=s.replace(a,b)
    return s


if __name__=='__main__':
    edit('section1.tex',chapter1)
    edit('section2.tex',chapter2)
    edit('section3.tex',chapter3)
    edit('section4.tex',chapter4)
    for p in (ROOT/'section').glob('*.tex'):
        p.write_text(normalize(p.read_text(encoding='utf-8')),encoding='utf-8')
