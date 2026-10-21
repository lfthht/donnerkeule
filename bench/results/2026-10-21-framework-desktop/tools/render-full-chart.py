#!/usr/bin/env python3
"""Render a reproducible, standalone PNG from the completed run and live inventory."""
import json
import math
from pathlib import Path
import statistics

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
from matplotlib.text import Text
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
load = lambda name: json.loads((ROOT/name).read_text())
summary = load('summary.json')
samples = load('measurements.json')
validation = load('benchmark-validation.json')
method = load('method.json')
hardware = load('chart-hardware.json')
images = load('images.json')
telemetry = load('telemetry-summary.json')
models = load('models-sha256.json')
probes = [json.loads(p.read_text()) for p in ROOT.glob('probe-*.json')]
assert validation['passed'] and validation['measurements'] == 40
assert validation['exact_outputs'] == validation['matched_pairs'] == 20
assert validation['matched_speculative_work'] == 20
assert validation['all_four_rails_per_native_measurement']
assert validation['restored'] and validation['kernel_warnings'] == 0
assert len(samples) == 40 and all(s['generated_tokens'] == 256 and s['cached_tokens'] == 0 for s in samples)
assert len(hardware['hosts']) == 2
for host in hardware['hosts']:
    assert host['dmi']['board_name'] == 'FRANMFCP06'
    assert host['dmi']['board_version'] == 'A6'
    assert sum(int(m['Size'].split()[0]) for m in host['memory_devices']) == 128
    assert all(m['Configured Memory Speed'] == '8000 MT/s' for m in host['memory_devices'])
    assert 'MCX4131A-BCAT' in host['nic_pcie']['lspci_relevant']
    assert host['nic_pcie']['current_link_speed'] == '8.0 GT/s PCIe'
    assert host['nic_pcie']['current_link_width'] == '4'
    assert host['nic_pcie']['max_link_width'] == '8'
    assert host['root_port_pcie']['max_link_speed'] == '16.0 GT/s PCIe'
    assert host['root_port_pcie']['max_link_width'] == '4'
    assert host['rdma']['fw_ver'] == '14.32.1912'
    assert host['rdma']['gid3_type'] == 'RoCE v2'
    assert len(host['usb4_links']) == 2
    assert all(l['rx_speed'] == l['tx_speed'] == '20.0 Gb/s' and l['rx_lanes'] == l['tx_lanes'] == '2' for l in host['usb4_links'])
assert [(x['name'],x['sha256'],x['size']) for x in models[0]] == [(x['name'],x['sha256'],x['size']) for x in models[1]]

W, H, DPI = 20, 28.3, 200
BG, WHITE = '#f2f5f9', '#ffffff'
INK, MUTED, GRID = '#17283e', '#506176', '#dce4ef'
BLUE, ORANGE, GREEN = '#1864ab', '#d56b22', '#168264'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11.5,
    'text.color':INK,'axes.labelcolor':MUTED,'xtick.color':MUTED,'ytick.color':MUTED,
    'axes.edgecolor':GRID,'axes.spines.top':False,'axes.spines.right':False,
    'svg.fonttype':'none','axes.unicode_minus':True})
fig = plt.figure(figsize=(W,H),dpi=DPI,facecolor=BG)
texts = []

def text(x,y,s,size=11.5,color=INK,weight='normal',**kw):
    obj = fig.text(x/W,1-y/H,s,fontsize=size,color=color,weight=weight,
        ha=kw.pop('ha','left'),va=kw.pop('va','top'),**kw)
    texts.append(obj)
    return obj

def card(x,y,w,h,face=WHITE,edge='none',radius=.13):
    patch = FancyBboxPatch((x/W,1-(y+h)/H),w/W,h/H,
        boxstyle=f'round,pad=0,rounding_size={radius/W}',transform=fig.transFigure,
        facecolor=face,edgecolor=edge,linewidth=.8,zorder=-5)
    fig.patches.append(patch)

def section(y,n,title,subtitle=None):
    text(.66,y,n,11.5,BLUE,'bold')
    text(1.08,y-.02,title,16,INK,'bold')
    if subtitle:
        text(19.34,y,subtitle,10.5,MUTED,ha='right')

def lines(x,y,rows,step=.285,size=11.2):
    for i,row in enumerate(rows):
        if isinstance(row,tuple):
            text(x,y+i*step,row[0],size,row[1],row[2] if len(row)>2 else 'normal')
        else:
            text(x,y+i*step,row,size,MUTED)

def table(x,y,w,h,labels,rows,widths,colors=None,size=11.2):
    ax = fig.add_axes([x/W,1-(y+h)/H,w/W,h/H]); ax.axis('off')
    tbl = ax.table(cellText=rows,colLabels=labels,colWidths=widths,
        loc='center',cellLoc='left',colLoc='left',bbox=[0,0,1,1])
    tbl.auto_set_font_size(False);tbl.set_fontsize(size)
    for (r,c),cell in tbl.get_celld().items():
        cell.set_linewidth(.5);cell.set_edgecolor(GRID);cell.PAD=.06
        if r == 0:
            cell.set_facecolor('#e4ebf4');cell.get_text().set_weight('bold');cell.get_text().set_color(INK)
        else:
            cell.set_facecolor(WHITE if r%2 else '#f7f9fc')
            cell.get_text().set_color(INK)
            if colors and c == 1:
                cell.get_text().set_color(colors[r-1]);cell.get_text().set_weight('bold')
    return tbl

text(.66,.48,'MEASURED COMPARISON  /  21 OCTOBER 2026',11.5,BLUE,'bold')
text(.66,.92,'Gufo: dual USB4 RDMA vs Mellanox',29,INK,'bold')
text(.66,1.48,'Two Framework Desktop motherboards · Qwen3.8-Flash-Next-UD-Q4_K_XL · 16K–128K input',14.2,MUTED)

overall = validation['overall_request_speedup_equal_context_weights']
extra_time = (1/overall-1)*100
kpi_x = [.66,7.00,13.34]
for x in kpi_x: card(x,1.96,6,1.12)
text(.88,2.13,'Prefill within 1%',22,INK,'bold')
text(.88,2.62,'Paired rates at all four input depths',11.4,MUTED)
text(7.22,2.13,f'+{extra_time:.2f}% USB4 time',22,ORANGE,'bold')
text(7.22,2.62,'Whole request · equal context weights',11.4,MUTED)
text(13.56,2.13,'20 matched pairs',21.5,INK,'bold')
text(13.56,2.62,'5 pairs at each of the 4 input depths',11.4,MUTED)

section(3.40,'01','Verified hardware and transport paths','Hardware read back from both hosts after the run')
for x in kpi_x: card(x,3.80,6,3.63)
text(.90,4.00,'2 × Framework Desktop mainboards',13.6,INK,'bold')
lines(.90,4.40,[
    'FRANMFCP06 · board revision A6 · BIOS 03.04',
    'AMD Ryzen AI Max+ 395 per board',
    '16 CPU cores / 32 threads per board',
    'Integrated AMD Radeon 8060S per board',
    '128 GB unified memory per board',
    'LPDDR5 · 8000 MT/s · 8 × 16 GB (SMBIOS)',
    'Total: 32 CPU cores / 256 GB installed RAM',
    'Ubuntu 26.04.1 LTS on both hosts',
    'Kernel 7.2.6-070206-generic on both',
],step=.288,size=11.15)
text(7.24,4.00,'Mellanox ConnectX-4 Lx',14.5,BLUE,'bold')
lines(7.24,4.40,[
    ('MCX4131A-BCAT · one card per board',INK,'bold'),
    'Single-port 40GbE · direct copper DAC',
    '40 Gb/s Ethernet link · full duplex',
    'Firmware 14.32.1912 · mlx5 / hardware RoCE v2',
    'Card capability: PCIe 3.0 ×8',
    ('Actual link on BOTH boards: PCIe 3.0 ×4',BLUE,'bold'),
    '8.0 GT/s per lane · 31.51 Gb/s before overhead*',
    'Motherboard root capability: PCIe 4.0 ×4',
    'HCA MT4117 · PSID MT_2430110027',
],step=.288,size=11.15)
text(13.58,4.00,'Dual USB4 · native Donnerkeule RDMA',13.8,ORANGE,'bold')
lines(13.58,4.40,[
    ('2 × 40 Gb/s links · 80 Gb/s nominal combined',INK,'bold'),
    'Each cable: 20 Gb/s per lane × 2 lanes',
    '2 controllers · 2 payload rails each · 4 total',
    'Hardware DMA through native verbs',
    ('Measured payload: 51.67 / 50.20 Gb/s**',ORANGE,'bold'),
    'Forward / reverse · one QP · 16 MiB WRITE',
    'Pinned base e4039b6 + repaired local module',
    '25 µs progress interval · post burst 128',
    'GPU DMA-BUF windows during Gufo inference',
],step=.288,size=11.15)
text(.70,7.58,'* PCIe 3.0 ×4: 8 GT/s × 4 × 128/130 = 31.51 Gb/s before TLP/RDMA overhead; a theoretical ceiling, not a measured NIC payload rate.',10.4,MUTED)
text(.70,7.82,'** USB4 host-memory preflight: 3 s per direction (central 1 s reported), queue depth 32, CPU 0. Separate from GPU inference; no Soft-RoCE/RXE.',10.4,MUTED)

section(8.26,'02','Gufo performance by input depth','Rates in tokens/second · times in seconds')
legend = [Line2D([0],[0],color=BLUE,lw=7,label='Mellanox 40GbE / RoCE v2'),
          Line2D([0],[0],color=ORANGE,lw=7,label='Dual USB4 / native RDMA')]
fig.legend(handles=legend,loc='upper left',bbox_to_anchor=(.66/W,1-8.62/H),
    ncol=2,frameon=False,fontsize=12,handlelength=1.2,columnspacing=2.3,borderaxespad=0)

depths = method['depths']
arms = ('mellanox','usb4-two')
colors = (BLUE,ORANGE)
metrics = [
    ('prefill_tokens_per_second','Prefill throughput','tokens / second',2700,0),
    ('decode_tokens_per_second','Token generation','tokens / second',100,1),
    ('ttft_seconds','Time to first token','seconds',80,2),
    ('elapsed_seconds','Whole request · 256 output tokens','seconds',85,2),
]
for idx,(key,title,unit,ylim,decimals) in enumerate(metrics):
    col, row = idx%2, idx//2
    x, y = .66+col*9.53, 9.08+row*3.22
    card(x,y,9.15,2.97)
    text(x+.24,y+.16,title,14,INK,'bold')
    ax = fig.add_axes([(x+.72)/W,1-(y+2.52)/H,8.05/W,1.91/H],facecolor=WHITE)
    for j,(arm,color) in enumerate(zip(arms,colors)):
        offset = -.19 if j==0 else .19
        xx = np.arange(4)+offset
        values = [next(s[key] for s in summary if s['arm']==arm and s['depth']==d) for d in depths]
        groups = [[s[key] for s in samples if s['arm']==arm and s['depth']==d] for d in depths]
        error = [[v-min(g) for v,g in zip(values,groups)],[max(g)-v for v,g in zip(values,groups)]]
        ax.bar(xx,values,.32,color=color,alpha=.88,zorder=2)
        ax.errorbar(xx,values,yerr=error,color=color,fmt='none',lw=1.2,capsize=4,zorder=4)
        for k,(position,value,group) in enumerate(zip(xx,values,groups)):
            ax.scatter(position+np.linspace(-.07,.07,5),group,s=13,color=WHITE,
                edgecolors=color,linewidths=.7,zorder=5)
            ax.text(position,max(group)+ylim*.035,f'{value:,.{decimals}f}',
                ha='center',va='bottom',fontsize=10.6,color=color,weight='bold')
    ax.set_xticks(np.arange(4),[f'{d//1024}K' for d in depths],fontsize=11)
    ax.set_xlim(-.65,3.65);ax.set_ylim(0,ylim)
    ax.set_ylabel(unit,fontsize=10.8);ax.set_axisbelow(True)
    ax.grid(axis='y',color=GRID,linewidth=.7)
    ax.tick_params(axis='both',length=0,pad=6,labelsize=10.5)
    for spine in ax.spines.values():spine.set_visible(False)
    text(x+4.58,y+2.67,'Input tokens',10.5,MUTED,ha='center')

text(.70,15.30,'Bars and labels: medians of 5 requests. Dots: individual requests. Whiskers: observed min–max, not confidence intervals. 1K = 1,024 tokens.',10.8,MUTED)
text(.70,15.57,'Network payload bandwidth and Gufo token throughput describe different workloads; measured rates and request times are shown separately.',10.8,MUTED)

section(16.02,'03','Exact median results','5 measured requests per transport at every depth')
rows=[];row_colors=[]
for d in depths:
    for arm,color in zip(arms,colors):
        s=next(r for r in summary if r['depth']==d and r['arm']==arm)
        rows.append([f'{d//1024}K','Mellanox' if arm=='mellanox' else 'Dual USB4',
            f"{s['prefill_tokens_per_second']:,.2f}",f"{s['decode_tokens_per_second']:.2f}",
            f"{s['ttft_seconds']:.3f}",f"{s['elapsed_seconds']:.3f}"])
        row_colors.append(color)
table(.66,16.43,18.68,2.37,['Input','Transport','Prefill (tokens/s)','Generation (tokens/s)','First token (s)','Whole request (s)'],
    rows,[.08,.17,.20,.22,.16,.17],colors=row_colors,size=11.2)

section(19.15,'04','Paired USB4 change relative to Mellanox','Same prompt and generated output within each pair')
paired_rows=[]
for r in validation['contexts']:
    paired_rows.append([f"{r['depth']//1024}K",f"{100*(r['prefill_speedup']-1):+.2f}%",
        f"{100*(r['generation_speedup']-1):+.2f}%",f"{100*(1/r['ttft_speedup']-1):+.2f}%",
        f"{100*(1/r['request_speedup']-1):+.2f}%",str(r['pairs'])])
table(.66,19.57,18.68,1.51,['Input','Prefill rate','Generation rate','First-token time','Whole-request time','Matched pairs'],
    paired_rows,[.08,.16,.18,.19,.20,.19],size=11.2)
text(.70,21.24,'Percent change = (USB4 / Mellanox − 1) × 100, using geometric means of the 5 paired ratios per context; ratios of medians can differ.',10.5,MUTED)

section(21.73,'05','Matched settings, correctness and recovery')
card(.66,22.14,9.15,2.97);card(10.19,22.14,9.15,2.97)
text(.90,22.32,'Engine and measurement controls',13.5,INK,'bold')
lines(.90,22.70,[
    'Gufo 0.18.0 · Qwen3.8-Flash-Next-UD-Q4_K_XL',
    'Tensor parallel across 2 hosts · concurrency 1',
    '256 generated tokens · MTP ceiling 7 · thinking off',
    'Fresh uncached prompts; actual inputs: 16,384 / 32,770 / 65,535 / 131,074',
    '5 paired repetitions per depth; transport and context order rotated',
    '40 measured requests; loading and 40 warm-ups excluded',
    'Same images, model files, ROCr fix and optimized math; no forced --quality',
    'Matched stock FCLK 2000 MHz; ordinary Gufo CPU affinity',
],step=.272,size=10.9)
text(10.43,22.32,'Recorded validation and end state',13.5,GREEN,'bold')
lines(10.43,22.70,[
    ('PASS · exact generated-output hashes in 20 / 20 pairs',GREEN,'bold'),
    'Matched speculative draft / accepted work in all 20 pairs',
    'GPU DMA-BUF on both ranks for both transports',
    'Both USB4 cables / all four rails carried payload in all 20 native requests',
    'Zero new kernel warnings / errors in the completed run',
    'Mellanox defaults, providers and automatic GPU power restored',
    'Both GPU smoke checks passed; management and original services healthy',
    'No promotion or persistent startup changes',
],step=.272,size=10.9)

section(25.45,'06','Recorded GPU telemetry','Sampled amdgpu sensors during the scored requests')
telemetry_rows=[];telemetry_colors=[]
for host in ('board01','board02'):
    for arm,color in zip(arms,colors):
        group=[t for t in telemetry if t['host']==host and t['arm']==arm]
        telemetry_rows.append(['Board 01' if host.endswith('01') else 'Board 02',
            'Mellanox' if arm=='mellanox' else 'Dual USB4',
            f"{max(t['temperature_max_c'] for t in group):.0f} °C",
            f"{max(t['power_max_w'] for t in group):.1f} W",
            f"{min(t['sclk_min_mhz'] for t in group):,}–{max(t['sclk_max_mhz'] for t in group):,} MHz"])
        telemetry_colors.append(color)
table(.66,25.86,18.68,1.26,['Host','Transport','Max exposed temperature','Peak reported power','Observed GPU clock range'],
    telemetry_rows,[.13,.17,.24,.20,.26],colors=telemetry_colors,size=10.7)

text(.70,27.38,'Provenance: transport-gufo-20261021T093913Z · raw requests, counters, telemetry and command logs retained with the results.',10.3,MUTED)
text(.70,27.64,f"Image {images['gufo']['image_id'][:16]}… · module {method['native_sha256'][:16]}… · 5 model/MTP files matched across both hosts (114.12 GB).",10.3,MUTED)
text(.70,27.90,'Link rates, PCIe ceilings, host-memory payload and GPU inference rates describe different measurements; rates use decimal Gbit/s.',10.3,MUTED)

fig.canvas.draw()
renderer=fig.canvas.get_renderer()
out_of_bounds=[]
for obj in fig.findobj(Text):
    if not obj.get_visible() or not obj.get_text().strip():continue
    box=obj.get_window_extent(renderer)
    if box.x0 < -1 or box.y0 < -1 or box.x1 > W*DPI+1 or box.y1 > H*DPI+1:
        out_of_bounds.append(obj.get_text())
assert not out_of_bounds, out_of_bounds
out=ROOT/'gufo-transport-full.png'
fig.savefig(out,dpi=DPI,facecolor=BG,metadata={
    'Title':'Gufo: dual USB4 RDMA vs Mellanox on two Framework Desktop mainboards',
    'Description':'Completed measured comparison. Hardware verified live; five paired repetitions per input depth; 256 output tokens. Data and renderer retained alongside PNG.',
    'Software':'Matplotlib; render-full-chart.py',
})
plt.close(fig)
from PIL import Image
with Image.open(out) as im:
    assert im.size == (4000,5660), im.size
    print(f'{out}\n{im.width} × {im.height} pixels; {out.stat().st_size:,} bytes')
