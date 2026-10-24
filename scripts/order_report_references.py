"""Write the bibliography in first-citation order, retaining stable cite keys."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]/'document/Mau'
ENTRIES={
'map':r"""\emph{Sơ đồ mặt bằng bảy tầng tòa nhà A4: kích thước, cửa ra vào và sức chứa}, tài liệu đầu vào của nghiên cứu, 2026.""",
'code':r"""Lý Thành Đạt, Đinh Đức Mạnh và Phạm Văn Đạt, \emph{Mã nguồn mô hình sơ tán A4 và cấu hình tái lập}, 2026. \href{https://github.com/Datthanhly/Thuattoanungdung}{GitHub: Datthanhly/Thuattoanungdung}. Phiên bản chương trình cơ sở 2.1.0; kho mã nguồn kèm cấu hình, kiểm thử và dữ liệu thực nghiệm tái lập.""",
'ford':r"""L. R. Ford, Jr. và D. R. Fulkerson, ``Constructing Maximal Dynamic Flows from Static Flows,'' \emph{Operations Research}, 6(3), tr. 419--433, 1958. \url{https://doi.org/10.1287/opre.6.3.419}.""",
'chalmet':r"""L. G. Chalmet, R. L. Francis và P. B. Saunders, ``Network Models for Building Evacuation,'' \emph{Management Science}, 28(1), tr. 86--105, 1982. \url{https://doi.org/10.1287/mnsc.28.1.86}.""",
'survey':r"""T. N. Dhamala, ``A survey on models and algorithms for discrete evacuation planning network problems,'' \emph{Journal of Industrial and Management Optimization}, 11(1), tr. 265--289, 2015. \url{https://doi.org/10.3934/jimo.2015.11.265}.""",
'ahuja':r"""R. K. Ahuja, T. L. Magnanti và J. B. Orlin, \emph{Network Flows: Theory, Algorithms, and Applications}, Prentice Hall, 1993, ISBN 9780136175490. \url{https://www.pearson.com/en-us/subject-catalog/p/P200000003456/9780136175490}.""",
'dijkstra':r"""E. W. Dijkstra, ``A note on two problems in connexion with graphs,'' \emph{Numerische Mathematik}, 1, tr. 269--271, 1959. \url{https://doi.org/10.1007/BF01386390}.""",
'dinic':r"""E. A. Dinic, ``Algorithm for Solution of a Problem of Maximum Flow in Networks with Power Estimation,'' \emph{Soviet Mathematics Doklady}, 11, tr. 1277--1280, 1970. Thư mục tác giả: \url{https://www.cs.bgu.ac.il/~dinitz/pub.html}.""",
'mitflow':r"""D. Karger, \emph{Min Cost Flow}, ghi chú học phần 6.854, MIT, 2021. \url{https://courses.csail.mit.edu/6.854/21/Notes/n10-mincostflow.html}.""",
'clrs':r"""T. H. Cormen, C. E. Leiserson, R. L. Rivest và C. Stein, \emph{Introduction to Algorithms}, ấn bản 4, MIT Press, 2022, ISBN 9780262046305. \url{https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/}.""",
'networkx':r"""NetworkX Developers, \emph{max\_flow\_min\_cost}, tài liệu chính thức, truy cập 24/10/2026. \url{https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.flow.max_flow_min_cost.html}.""",
'tracemalloc':r"""Python Software Foundation, \emph{tracemalloc -- Trace memory allocations}, tài liệu chính thức, truy cập 24/10/2026. \url{https://docs.python.org/3/library/tracemalloc.html}.""",
}


def main():
    order=[]
    for name in ['abstract','section1','section2','section3','section4','section5','appendix']:
        text=(ROOT/'section'/f'{name}.tex').read_text(encoding='utf-8')
        for group in re.findall(r'\\cite\{([^}]+)\}',text):
            for key in group.split(','):
                key=key.strip()
                if key not in order:order.append(key)
    assert set(order)==set(ENTRIES), (set(ENTRIES)-set(order),set(order)-set(ENTRIES))
    text=r'''\clearpage\phantomsection\addcontentsline{toc}{section}{Tài liệu tham khảo}
\begingroup\fontsize{12}{17}\selectfont
\begin{thebibliography}{99}\raggedright
'''
    text+='\n'.join(r'\bibitem{'+k+'} '+ENTRIES[k] for k in order)
    text+='\n'+r'\end{thebibliography}\endgroup'+'\n'
    def compact_link(match):
        url=match.group(1)
        label='DOI: '+url.split('doi.org/')[1] if 'doi.org/' in url else 'Tài liệu trực tuyến'
        return r'\href{'+url+'}{'+label+'}'
    text=re.sub(r'\\url\{([^}]+)\}',compact_link,text)
    (ROOT/'section/ref.tex').write_text(text,encoding='utf-8')
    print('First citation order:',order)


if __name__=='__main__':main()
