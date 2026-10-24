"""Vector figures, localized tables and audit analyses for the reviewed report."""
from pathlib import Path
from collections import Counter
import json
import math
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from a4_evac.data import build_a4, write_json
from a4_evac.algorithms import shortest_path
from a4_evac.optimize import exit_lower_bounds

TARGET = ROOT/'document/Mau'
SRC = ROOT/'outputs/a4_open_ground/benchmark'
REVIEW = ROOT/'outputs/a4_open_ground/review_20261024'
NAMES = {'safe': 'Không sự cố', 'smoke': 'Khói phòng 403',
         'stair_block': 'Khói cầu thang', 'exit_block': 'Khóa vùng thoát'}
COLORS = ['#c85555', '#d99c3e', '#4478b8', '#22896b']


def num(value, digits=0):
    if value is None:
        return '--'
    return f'{value:,.{digits}f}'.replace(',', '@').replace('.', ',').replace('@', '.')


def tab(name, cols, headers, rows):
    lines = [r'\small\begin{tabular}{'+cols+'}', r'\toprule',
             ' & '.join(headers)+r'\\\midrule']
    lines += [' & '.join(str(v) for v in row)+r'\\' for row in rows]
    lines += [r'\bottomrule\end{tabular}']
    (TARGET/'tables'/f'{name}.tex').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def savefig(fig, name):
    fig.savefig(TARGET/'figures'/f'{name}.pdf', bbox_inches='tight', pad_inches=.025)


def floor_map(ax, b, floors, state=None):
    from matplotlib.patches import Rectangle
    ax.set_xlim(-8, 71)
    ax.set_ylim(-.2, len(floors)*1.9)
    ax.axis('off')
    for row, f in enumerate(floors):
        y=(len(floors)-row-1)*1.9
        ax.text(-1, y+.7, f'Tầng {f}', ha='right', va='center', fontsize=10, fontweight='bold')
        for block in b.layout[str(f)]['blocks']:
            x,w=block['x0'],block['width_m']
            ax.add_patch(Rectangle((x,y+.4),w,.95,facecolor='#fff0d7' if block['kind']=='room' else '#e5eaf0',edgecolor='#355777',lw=.8))
            if block['kind']=='room':
                ax.text(x+w/2,y+1.08,block['label'],ha='center',fontsize=9 if w<6 else 10,fontweight='bold')
                ax.text(x+w/2,y+.78,f"{num(w,1)} × 8,8 m",ha='center',fontsize=7 if w<6 else 9)
                ax.text(x+w/2,y+.51,f"{block['max_people']} người",ha='center',fontsize=7 if w<6 else 9,color='#a02b20')
                for dx in block['door_x']:
                    ax.plot([dx,dx],[y+.4,y+.57],color='#355777',lw=1.1)
            else:
                ax.text(x+w/2,y+.98,f"Thang {block['label']}",ha='center',fontsize=9,fontweight='bold')
                ax.text(x+w/2,y+.6,f"Sảnh {num(w,1)} m",ha='center',fontsize=8)
        length=b.layout[str(f)]['length_m']
        ax.add_patch(Rectangle((0,y+.1),length,.3,facecolor='#d9f4e6' if f==1 else '#d4eafb',edgecolor='#355777',lw=.8))
        ax.text(length/2,y+.17,'Hành lang hở - biên thoát' if f==1 else 'Hành lang 2 m',ha='center',fontsize=8)
        ax.text(length/2,y-.13,f'{num(length,1)} m',ha='center',fontsize=8,color='#355777')


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    from PIL import Image
    plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42,'font.size':10})
    b=build_a4()
    rows=load(SRC/'comparison.json')
    for name,floors in [('a4_upper',[7,6,5]),('a4_lower',[4,3,2,1]),('ground_vector',[1])]:
        fig,ax=plt.subplots(figsize=(8.5,1.15*len(floors)+.3))
        floor_map(ax,b,floors)
        savefig(fig,name);plt.close(fig)
    # Five legible vector snapshots of the same replay, aggregated by floor.
    # People on an edge are attributed to its source floor, preserving totals.
    from matplotlib.patches import Rectangle
    fig,axes=plt.subplots(1,5,figsize=(9,4.4),layout='constrained')
    trace=load(SRC/'safe/M4/simulation_trace.json')
    for ax,t in zip(axes,[0,100,200,300,390]):
        state=next(r for r in trace if r['time_seconds']==t)
        byfloor=Counter()
        for node,count in state['node_occupancy'].items():byfloor[b.node_by_id[node].floor]+=count
        for edge,count in state['active_moves'].items():byfloor[b.node_by_id[b.edge_by_id[edge].source].floor]+=count
        assert sum(byfloor.values())+state['evacuated_total']==1360
        ax.set(xlim=(0,1),ylim=(-1.2,7.6));ax.axis('off')
        for f in range(1,8):
            value=byfloor[f]
            ax.add_patch(Rectangle((.02,f-1),.96,.8,facecolor=plt.cm.Blues(.08+.65*min(value/400,1)),edgecolor='#63829a'))
            ax.text(.5,f-.6,f'T{f}: {num(value)}',ha='center',va='center',fontsize=12,color='white' if value>300 else '#18374c')
        ax.text(.5,-.4,'Đã thoát',ha='center',fontsize=12,color='#14765d')
        ax.text(.5,-.95,num(state['evacuated_total']),ha='center',fontsize=14,fontweight='bold',color='#14765d')
        ax.set_title(f't = {t} s',fontsize=14)
    savefig(fig,'timeline');plt.close(fig)
    fmt=FuncFormatter(lambda x,pos:num(x))
    # Four vector evacuation curves with separate dash patterns.
    for scenario in NAMES:
        fig,ax=plt.subplots(figsize=(7.4,3.0),layout='constrained')
        for method,color,style in zip(['M1','M2','M3','M4'],COLORS,['-','--','-.','-']):
            trace=load(SRC/scenario/method/'simulation_trace.json')
            ax.step([r['time_seconds'] for r in trace],[r['evacuated_total'] for r in trace],where='post',label=method,color=color,ls=style,lw=2 if method=='M4' else 1.6)
        ax.axhline(1360,color='#555',ls=':',lw=1,label='Dân số 1.360')
        if scenario=='smoke':
            ax.axvline(120,color='#906040',ls=':',lw=1);ax.text(122,530,'Khói: 120 s',rotation=90,fontsize=8)
            ax.axvline(180,color='#a44',ls=':',lw=1);ax.text(182,420,'Cháy: 180 s',rotation=90,fontsize=8)
        elif scenario in ['stair_block','exit_block']:
            t=90 if scenario=='stair_block' else 120
            ax.axvline(t,color='#a44',ls=':',lw=1)
            ax.text(t+3,450,('Khói: ' if scenario=='stair_block' else 'Khóa: ')+f'{t} s',rotation=90,fontsize=8)
        m4=next(r for r in rows if r['method']=='M4' and r['scenario_id']==scenario)
        last=m4['last_rescue_seconds']
        label=f"M4: hoàn tất {last} s" if m4['makespan_seconds'] is not None else f"M4: thoát cuối {last} s; còn {m4['remaining_people']}"
        ax.annotate(label,(last,m4['evacuated_count']),xytext=(.44,.3),textcoords='axes fraction',arrowprops={'arrowstyle':'->','lw':.8},fontsize=9)
        ax.set(xlabel='Thời gian mô phỏng (s)',ylabel='Số người đã thoát',ylim=(0,1460))
        ax.yaxis.set_major_formatter(fmt);ax.grid(alpha=.2)
        ax.legend(ncol=5,fontsize=8,loc='lower left',bbox_to_anchor=(0,1.0),frameon=False)
        savefig(fig,f'{scenario}_comparison');plt.close(fig)
    # Aggregate values, complete scenario labels, panel letters and bar labels.
    fig,axes=plt.subplots(2,1,figsize=(8,5.7),layout='constrained')
    scenarios=list(NAMES)
    for i,method in enumerate(['M1','M2','M3','M4']):
        vals=[next(r for r in rows if r['method']==method and r['scenario_id']==sc) for sc in scenarios]
        x=[j+(i-1.5)*.2 for j in range(4)]
        for ax,key,digits in [(axes[0],'evacuation_rate',1),(axes[1],'runtime_seconds',1)]:
            bars=ax.bar(x,[r[key] for r in vals],.18,color=COLORS[i],label=method)
            ax.bar_label(bars,labels=[num(r[key],digits) for r in vals],fontsize=8,rotation=90,padding=3)
    for ax in axes:
        ax.set_xticks(range(4),list(NAMES.values()),fontsize=9)
        ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
        ax.yaxis.set_major_formatter(fmt)
    axes[0].set(title='(a) Tỷ lệ thoát',ylabel='Tỷ lệ (%)',ylim=(0,125))
    axes[1].set(title='(b) Thời gian giải',ylabel='Thời gian (s)',ylim=(0,120))
    axes[0].legend(ncol=4,fontsize=9)
    savefig(fig,'aggregate');plt.close(fig)
    # Unified results table, maximizing evacuation before comparing means.
    result_lines=[r'\small\setlength{\tabcolsep}{3pt}\begin{tabular}{lrrrrrr}',r'\toprule',
                  r'PP & Thoát & Tỷ lệ (\%) & Hoàn tất & Thoát cuối & TB & Giải\\\midrule']
    for sc,name in NAMES.items():
        selected=[r for r in rows if r['scenario_id']==sc]
        best_count=max(r['evacuated_count'] for r in selected)
        eligible=[r for r in selected if r['evacuated_count']==best_count]
        best_mean=min(r['avg_exit_time_seconds'] for r in eligible)
        best_last=min(r['last_rescue_seconds'] for r in eligible)
        best_runtime=min(r['runtime_seconds'] for r in selected)
        result_lines.append(r'\multicolumn{7}{l}{\textbf{'+name+r'}}\\')
        for r in selected:
            def bold(s,condition):return r'\textbf{'+s+'}' if condition else s
            values=[r['method'],bold(num(r['evacuated_count']),r['evacuated_count']==best_count),
                    bold(num(r['evacuation_rate'],2),r['evacuated_count']==best_count),
                    bold(num(r['makespan_seconds']),r['makespan_seconds']==best_last),
                    bold(num(r['last_rescue_seconds']),r in eligible and r['last_rescue_seconds']==best_last),
                    bold(num(r['avg_exit_time_seconds'],2),r in eligible and r['avg_exit_time_seconds']==best_mean),
                    bold(num(r['runtime_seconds'],3),r['runtime_seconds']==best_runtime)]
            result_lines.append(' & '.join(values)+r'\\')
        result_lines.append(r'\midrule')
    result_lines += [r'\end{tabular}']
    (TARGET/'tables/results_all.tex').write_text('\n'.join(result_lines),encoding='utf-8')
    tab('floors','crrr',['Tầng','Chiều dài (m)','Số khu phòng','Sức chứa'],
        [[f,num(b.layout[str(f)]['length_m'],1),sum(r['floor']==f for r in b.rooms),num(sum(r['max_people'] for r in b.rooms if r['floor']==f))] for f in range(1,8)]
        +[[r'\textbf{Tổng}','--',r'\textbf{27}',r'\textbf{1.360}']])
    tab('rooms','clrrr',['Tầng','Khu phòng','Dài (m)','Tối đa','Số cửa'],
        [[r['floor'],r['label'],num(r['width_m'],1),num(r['max_people']),r['door_count']] for r in b.rooms]
        +[[r'\textbf{Tổng}','--','--',r'\textbf{1.360}',r'\textbf{50}']])
    tab('ten','lrrr',['Kịch bản','Nút TEN','Cạnh thuận','Thoát cuối (s)'],
        [[NAMES[r['scenario_id']],num(r['time_expanded_nodes']),num(r['time_expanded_edges']),num(r['last_rescue_seconds'])] for r in rows if r['method']=='M4'])
    # Rebuild from numeric data: safe to run repeatedly without changing grouping.
    sensitivity=load(TARGET/'data/sensitivity.json')
    tab('sensitivity','rrrrr',[r'$\Delta t$ (s)','Cửa (m)','Thoát','Hoàn tất (s)','TB (s)'],
        [[num(r['dt']),num(r['door_width_m'],1),num(r['evacuated_count']),num(r['makespan_seconds']),num(r['avg_exit_time_seconds'],2)] for r in sensitivity])
    safe=next(r for r in rows if r['scenario_id']=='safe' and r['method']=='M4')
    tab('probes','rr',['Horizon (bước)','Luồng cực đại (người)'],
        [[num(int(k)),num(v)] for k,v in sorted(safe['max_flow_probes'].items(),key=lambda x:int(x[0]))])
    # Identify all unserved source populations, using actual schedules.
    schedules={}
    for sc,m in [('safe','M1'),('safe','M4'),('stair_block','M4'),('exit_block','M3')]:
        schedules[sc,m]=load(SRC/sc/m/'schedule.json')
    done=Counter()
    for j in schedules['stair_block','M4']:
        if j['exit_step'] is not None:done[j['source']]+=j['count']
    missing={k:v-done[k] for k,v in b.full_occupancy.items() if v>done[k]}
    assert sum(missing.values())==112
    tab('unserved','lrr',['Khu phòng','Dân số nguồn','Chưa thoát'],
        [[k[1:],b.full_occupancy[k],v] for k,v in missing.items()]+[[r'\textbf{Tổng}','--',r'\textbf{112}']])
    write_json(TARGET/'data/unserved_sources.json',missing)
    # Static cut lower bounds with optimistic free-flow release and discharge.
    graph={n.id:[] for n in b.nodes}
    for e in b.edges:graph[e.source].append((e.target,e.steps(b.dt),e.id))
    lower=exit_lower_bounds(b)
    cuts=[]
    for f in range(2,8):
        sources=[r['node_id'] for r in b.rooms if r['floor']>=f]
        people=sum(b.full_occupancy[s] for s in sources)
        edges=[e for e in b.edges if e.kind=='STAIR_DOWN' and b.node_by_id[e.source].floor==f]
        terms=[]
        for e in edges:
            release=min(shortest_path(graph,s,{e.source})[0] for s in sources)
            terms.append((e.entry_capacity,release+e.steps(b.dt)+lower[e.target]))
        K=next(k for k in range(181) if sum(u*max(0,k-d+1) for u,d in terms)>=people)
        cuts.append({'floor':f,'people':people,'bound_seconds':K*b.dt,'terms':terms})
    write_json(TARGET/'data/cut_bounds.json',cuts)
    tab('cut_bounds','rrrr',['Lát cắt tầng','Dân số phải qua','Năng lực/bước','Cận dưới (s)'],
        [[f"{r['floor']}--{r['floor']-1}",num(r['people']),18,r['bound_seconds']] for r in cuts])
    # Heatmaps: departure counts / entry capacity, no invented trajectories.
    stairs=[e for e in b.edges if e.kind=='STAIR_DOWN']
    fig,axes=plt.subplots(2,1,figsize=(8,6.3),layout='constrained')
    for ax,method in zip(axes,['M1','M4']):
        counts=Counter()
        for j in schedules['safe',method]:
            for a in j['actions']:
                if a['kind']=='MOVE':counts[a['edge_id'],a['depart']]+=j['count']
        values=[[counts[e.id,k]/e.entry_capacity for k in range(110)] for e in stairs]
        mesh=ax.pcolormesh(range(111),range(len(stairs)+1),values,cmap='YlGnBu',vmin=0,vmax=1,edgecolors='none')
        ax.set_yticks([i+.5 for i in range(len(stairs))],
                      [f"T{b.node_by_id[e.source].floor}→{b.node_by_id[e.target].floor}, thang {e.source[-1]}" for e in stairs],fontsize=8)
        ax.set_xticks(range(0,111,10),[str(k*5) for k in range(0,111,10)])
        ax.set(title=method,xlabel='Thời điểm khởi hành (s)')
    cb=fig.colorbar(mesh,ax=axes,shrink=.8,label='Tỷ lệ sử dụng năng lực vào')
    cb.ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:num(x,1)))
    savefig(fig,'stair_heatmap');plt.close(fig)
    # Additional experiments are materialized only when actual measurements exist.
    balanced=[]
    for sc in NAMES:
        p=REVIEW/f'balanced/{sc}/metrics.json'
        if p.exists():balanced.append(load(p))
    if balanced:
        tab('balanced','lrrrr',['Kịch bản','Thoát','Hoàn tất (s)','TB (s)','Giải (s)'],
            [[NAMES[r['scenario_id']],num(r['evacuated_count']),num(r['makespan_seconds']),num(r['avg_exit_time_seconds'],2),num(r['runtime_seconds'],2)] for r in balanced])
    ablation=[]
    for sc in NAMES:
        vals=[]
        for w in [1,2,4,8]:
            p=REVIEW/f'm3/{sc}/w{w}/metrics.json'
            if p.exists():vals.append((w,load(p)))
        if len(vals)==4:
            ablation.append([NAMES[sc]]+[f"{num(r['evacuated_count'])} / {num(r['makespan_seconds'])}" for w,r in vals])
    if ablation:tab('m3_ablation','lrrrr',['Kịch bản',r'$\alpha=1$',r'$\alpha=2$',r'$\alpha=4$',r'$\alpha=8$'],ablation)
    reps=[load(p) for p in sorted((REVIEW/'runtime').glob('*/metrics.json'))]
    if reps:
        tab('runtime_repeats','rrrrrr',['Lượt','Giải (s)',r'$P$','Tăng luồng','Nút','Cạnh'],
            [[i+1,num(r['runtime_seconds'],2),r['cost_stats'].get('cost_phases',0),num(r['cost_stats'].get('augmentations',0)),num(r['time_expanded_nodes']),num(r['time_expanded_edges'])] for i,r in enumerate(reps)])
        stages=['build','max_flow','min_cost','decompose_validate']
        fig,ax=plt.subplots(figsize=(7.4,3),layout='constrained')
        vals=[statistics.mean(r['phase_seconds'][k] for r in reps) for k in stages]
        bars=ax.bar(['Dựng mạng','Dò luồng\ncực đại','Luồng chi phí\nnhỏ nhất','Phân rã và\nkiểm tra'],vals,color=['#638ca4','#d99c3e','#22896b','#886da5'])
        ax.bar_label(bars,labels=[num(x,2) for x in vals],padding=3)
        ax.set(ylabel='Thời gian trung bình (s)',ylim=(0,max(vals)*1.2))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:num(x,1)))
        savefig(fig,'runtime_stages');plt.close(fig)
        write_json(TARGET/'data/runtime_summary.json',{'n':len(reps),'mean':statistics.mean(r['runtime_seconds'] for r in reps),
            'sd':statistics.stdev(r['runtime_seconds'] for r in reps) if len(reps)>1 else None,'raw':reps})
        env=load(REVIEW/'environment.json')
        cpu=json.loads(env.get('hardware_powershell','{}')).get('Name','CPU không ghi nhận')
        memory=env.get('memory_bytes',0)/1024**3
        mean=statistics.mean(r['runtime_seconds'] for r in reps)
        sd=statistics.stdev(r['runtime_seconds'] for r in reps) if len(reps)>1 else 0
        comment=(f"Máy đo dùng {cpu}, RAM {num(memory,1)} GiB, Windows và Python 3.13.5. "
                 f"Qua {len(reps)} lượt, thời gian giải là {num(mean,2)} $\\pm$ {num(sd,2)} s "
                 "(trung bình và SD mẫu). Các lượt có cùng lượng thoát và thời gian hoàn tất 390 s. "
                 f"Mỗi lượt có {len(reps[0]['max_flow_probes'])} phép dò, "
                 f"{reps[0]['cost_stats'].get('cost_phases',0)} pha chi phí, "
                 f"{num(reps[0]['cost_stats'].get('augmentations',0))} lần tăng luồng trong tối ưu chi phí "
                 f"và {num(reps[0]['probe_stats'].get('augmentations',0))} lần tăng trong các phép dò. "
                 "Độ biến thiên thời gian phản ánh cả điều kiện thực thi trên máy đa dụng; không dùng các phép đo này để suy ra thời gian đáp ứng cố định.\n")
        (TARGET/'data/runtime_comment.tex').write_text(comment,encoding='utf-8')
    poprows=[]
    for pct in [30,50,70]:
        vals=[load(p) for p in sorted((REVIEW/'population').glob(f'p{pct}_*/metrics.json'))]
        if vals:
            def ms(key):
                return num(statistics.mean(r[key] for r in vals),2)+r' $\pm$ '+num(statistics.stdev(r[key] for r in vals),2) if len(vals)>1 else num(vals[0][key],2)
            poprows.append([pct,len(vals),num(vals[0]['total_people']),ms('makespan_seconds'),ms('avg_exit_time_seconds')])
    if poprows:tab('population','rrrrr',[r'Tải (\%)','Seed','Dân số','Hoàn tất (s)','TB (s)'],poprows)
    variants=[]
    for key in ['width12','width18','speed05','speed09','dt10','dt2']:
        p=REVIEW/f'sensitivity/{key}/metrics.json'
        if p.exists():
            r=load(p);params=load(p.with_name('parameters.json'))
            variants.append([num(params['time_step_seconds']),num(params['assumed_stair_usable_width_m'],1),num(params['stair_speed_m_s'],1),num(r['makespan_seconds']),num(r['avg_exit_time_seconds'],2)])
    baseline=next(r for r in rows if r['scenario_id']=='safe' and r['method']=='M4')
    if variants:tab('whole_sensitivity','rrrrr',[r'$\Delta t$ (s)','Thang (m)','Tốc độ (m/s)','Hoàn tất (s)','TB (s)'],
        [[5,'1,5','0,7',390,num(baseline['avg_exit_time_seconds'],2)]]+variants)
    print('Review assets prepared; measured repeats:',len(reps),flush=True)


if __name__=='__main__':
    main()
