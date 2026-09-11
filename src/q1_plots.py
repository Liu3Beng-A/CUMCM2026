"""Q1 所有图表（除了Prophet外）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.q1_data_prep import build_q1_data
from src.utils import FIGURES_DIR, ensure_dir
from src.plot_style import apply_style, save_fig, COLORS


def fig_design_quality(data):
    """5.1.1 设计质量 - 方案/单元结构、上方位占比"""
    plt = apply_style()
    plan_total = data['plan_total']
    unit_total = data['unit_total']

    # 计算派生指标
    plan_total = plan_total.copy()
    plan_total['CTR'] = plan_total['点击量'] / plan_total['展现量'].replace(0, np.nan)
    plan_total['CPC'] = plan_total['消费额'] / plan_total['点击量'].replace(0, np.nan)
    plan_total['上方位占比'] = plan_total['上方位展现量'] / plan_total['展现量'].replace(0, np.nan)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # (a) 5个方案的核心指标对比
    ax = axes[0, 0]
    x = np.arange(len(plan_total))
    w = 0.25
    ax.bar(x - w, plan_total['展现量'] / 1e6, w, label='展现量(百万)', color=COLORS['primary'])
    ax.bar(x, plan_total['点击量'] / 1e3, w, label='点击量(千)', color=COLORS['secondary'])
    ax.bar(x + w, plan_total['消费额'] / 1e4, w, label='消费额(万)', color=COLORS['accent'])
    ax.set_xticks(x)
    ax.set_xticklabels([str(p) for p in plan_total['方案ID']], rotation=15)
    ax.set_title('(a) 5个方案核心指标对比')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylabel('数值')

    # (b) 12个单元的上方位占比
    ax = axes[0, 1]
    unit_total2 = unit_total.copy()
    unit_total2['上方位占比'] = unit_total2['上方位展现量'] / unit_total2['展现量'].replace(0, np.nan)
    unit_total2['label'] = unit_total2['推广单元ID'].astype(str)
    sorted_u = unit_total2.sort_values('上方位占比', ascending=False)
    colors = [COLORS['success'] if 0.4 <= v <= 0.7 else COLORS['danger']
              for v in sorted_u['上方位占比']]
    ax.barh(range(len(sorted_u)), sorted_u['上方位占比'], color=colors)
    ax.set_yticks(range(len(sorted_u)))
    ax.set_yticklabels(sorted_u['label'], fontsize=9)
    ax.axvline(0.4, color='gray', linestyle='--', alpha=0.5, label='合理下限0.4')
    ax.axvline(0.7, color='gray', linestyle='--', alpha=0.5, label='合理上限0.7')
    ax.set_title('(b) 12个推广单元的上方位占比（绿=合理，红=异常）')
    ax.set_xlabel('上方位占比')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # (c) 方案的CTR/CPC/上方位占比综合
    ax = axes[1, 0]
    ax2 = ax.twinx()
    ax.bar(x, plan_total['CTR'], w*2, color=COLORS['primary'], alpha=0.7, label='CTR')
    ax2.plot(x, plan_total['CPC'], color=COLORS['danger'], marker='o', linewidth=2, label='CPC(元)')
    ax.set_xticks(x)
    ax.set_xticklabels([str(p) for p in plan_total['方案ID']], rotation=15)
    ax.set_title('(c) 各方案CTR与CPC')
    ax.set_ylabel('CTR', color=COLORS['primary'])
    ax2.set_ylabel('CPC(元)', color=COLORS['danger'])
    ax.grid(True, alpha=0.3)

    # (d) 上方位竞价效率（CTR/CPC的倍数）
    ax = axes[1, 1]
    plan_total['上方位CTR'] = plan_total['上方位点击量'] / plan_total['上方位展现量'].replace(0, np.nan)
    plan_total['上方位CPC'] = plan_total['上方位消费额'] / plan_total['上方位点击量'].replace(0, np.nan)
    ax.scatter(plan_total['CPC'], plan_total['上方位CTR'], s=plan_total['消费额']/5000, alpha=0.6, color=COLORS['primary'])
    for _, row in plan_total.iterrows():
        ax.annotate(str(int(row['方案ID'])), (row['CPC'], row['上方位CTR']), fontsize=9)
    ax.set_xlabel('CPC（元）')
    ax.set_ylabel('上方位CTR')
    ax.set_title('(d) 各方案出价-效益地图（圆=消费额）')
    ax.grid(True, alpha=0.3)

    fig.suptitle('问题 1：设计质量与创意分析', fontsize=14, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, 'q1_design_quality')
    plt.close(fig)


def fig_keyword_management(data):
    """5.1.2 关键词管理 - 有效率、长尾分布、跳出率"""
    plt = apply_style()
    dfk = data['keyword_total']

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # (a) 关键词有效率饼图
    ax = axes[0, 0]
    eff_cnt = dfk['有消费'].sum()
    no_eff = (~dfk['有消费']).sum()
    ax.pie([eff_cnt, no_eff],
           labels=[f'有消费关键词\n({eff_cnt}个)', f'无消费关键词\n({no_eff}个)'],
           colors=[COLORS['success'], COLORS['danger']],
           autopct='%1.1f%%', startangle=90,
           wedgeprops=dict(width=0.4))
    ax.set_title(f'(a) 关键词有效率 ({eff_cnt/(eff_cnt+no_eff)*100:.1f}%)')

    # (b) 长尾分布（Pareto）
    ax = axes[0, 1]
    eff = dfk[dfk['消费额'] > 0].copy()
    eff_sorted = eff.sort_values('消费额', ascending=False).reset_index(drop=True)
    total = eff_sorted['消费额'].sum()
    cum = eff_sorted['消费额'].cumsum() / total
    ax2 = ax.twinx()
    ax.bar(range(len(eff_sorted)), eff_sorted['消费额'],
           color=COLORS['primary'], alpha=0.6, label='各关键词消费额')
    ax2.plot(range(len(eff_sorted)), cum, color=COLORS['danger'], linewidth=1.5, label='累计占比')
    ax2.axhline(0.8, color='gray', linestyle='--', alpha=0.5)
    ax2.axhline(0.5, color='gray', linestyle='--', alpha=0.5)
    idx80 = (cum >= 0.8).idxmax()
    idx20 = int(len(eff_sorted) * 0.2)
    ax2.annotate(f'前{idx20}个词({idx20/len(eff_sorted)*100:.1f}%)\n占{cum.iloc[idx20]*100:.1f}%消费',
                 (idx20, cum.iloc[idx20]), xytext=(idx20+50, 0.9),
                 arrowprops=dict(arrowstyle='->', color='black'))
    ax.set_title('(b) 关键词消费分布的帕累托分析')
    ax.set_xlabel('关键词（按消费降序）')
    ax.set_ylabel('消费额（元）', color=COLORS['primary'])
    ax2.set_ylabel('累计占比', color=COLORS['danger'])
    ax.grid(True, alpha=0.3)

    # (c) 跳出率分布 + 平均访问时长
    ax = axes[1, 0]
    df_plot = dfk[(dfk['有消费'])].copy()
    bounce = df_plot['跳出率'].dropna() if '跳出率' in df_plot.columns else pd.Series()
    if len(bounce) > 0:
        ax.hist(bounce, bins=30, color=COLORS['primary'], alpha=0.7, edgecolor='white')
        ax.axvline(bounce.median(), color=COLORS['danger'], linestyle='--', linewidth=2, label=f'中位数={bounce.median():.3f}')
        ax.set_title('(c) 有效关键词跳出率分布')
        ax.set_xlabel('跳出率')
        ax.set_ylabel('关键词数')
        ax.legend()
        ax.grid(True, alpha=0.3)

    # (d) CPC分布
    ax = axes[1, 1]
    cpc = df_plot['CPC'].dropna()
    cpc_clip = cpc[cpc < 20]  # 截掉极端值
    ax.hist(cpc_clip, bins=50, color=COLORS['accent'], alpha=0.7, edgecolor='white')
    ax.axvline(cpc.median(), color=COLORS['danger'], linestyle='--', linewidth=2, label=f'中位数={cpc.median():.2f}元')
    ax.axvline(cpc.quantile(0.9), color='gray', linestyle=':', linewidth=2, label=f'P90={cpc.quantile(0.9):.2f}元')
    ax.set_title('(d) 有效关键词的CPC分布')
    ax.set_xlabel('CPC(元/点击)')
    ax.set_ylabel('关键词数')
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.suptitle('问题 1：关键词管理与运用分析', fontsize=14, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, 'q1_keyword_management')
    plt.close(fig)


def fig_bid_strategy(data):
    """5.1.3 出价策略 - CPC分布、上方位竞价、月度预算节奏"""
    plt = apply_style()
    dfc = data['campaign_daily']
    daily = data['daily_full']

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # (a) CPC + 上方位CPC 时间序列
    ax = axes[0, 0]
    daily_ts = daily.copy().sort_values('日期')
    ax.plot(daily_ts['日期'], daily_ts['CPC'], color=COLORS['primary'], alpha=0.7, linewidth=0.8, label='整体CPC')
    ax.plot(daily_ts['日期'], daily_ts['上方位CPC'], color=COLORS['danger'], alpha=0.7, linewidth=0.8, label='上方位CPC')
    ax.set_title('(a) 每日CPC vs 上方位CPC走势')
    ax.set_ylabel('CPC(元)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # (b) 月度预算执行节奏
    ax = axes[0, 1]
    daily['月份'] = daily['日期'].dt.to_period('M')
    monthly = daily.groupby('月份')[['总消费额', '新注册数']].sum().reset_index()
    monthly['月份'] = monthly['月份'].astype(str)
    ax2 = ax.twinx()
    ax.bar(monthly['月份'], monthly['总消费额'], color=COLORS['primary'], alpha=0.7, label='消费额')
    ax2.plot(monthly['月份'], monthly['新注册数'], color=COLORS['danger'], marker='o', linewidth=2, label='注册量')
    ax.set_title('(b) 月度预算执行节奏')
    ax.set_ylabel('消费额(元)', color=COLORS['primary'])
    ax2.set_ylabel('新注册数', color=COLORS['danger'])
    ax.set_xticklabels(monthly['月份'], rotation=45)
    ax.legend(loc='upper left')
    ax2.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # (c) 方案维度CPC箱线图
    ax = axes[1, 0]
    cpc_data = []
    plan_ids_cpc = []
    for pid, grp in dfc.groupby('方案ID'):
        cpcs = grp['CPC'].dropna()
        cpcs = cpcs[cpcs < 20]
        if len(cpcs) > 0:
            cpc_data.append(cpcs.values)
            plan_ids_cpc.append(str(pid))

    # 改-A：用小提琴图显示分布密度，并叠加简化的箱（不画 outlier 圆点）
    # 比纯 boxplot 少很多空心圆，更清爽；比纯 violin 多中位数/IQR 信息
    positions = np.arange(len(cpc_data))
    parts = ax.violinplot(cpc_data, positions=positions, widths=0.7,
                          showmeans=False, showmedians=False, showextrema=False)
    for pc, color in zip(parts['bodies'], list(COLORS.values()) * 2):
        pc.set_facecolor(color)
        pc.set_edgecolor('black')
        pc.set_alpha(0.55)
        pc.set_linewidth(1.0)

    # 在小提琴上叠加 IQR 箱（四分位）+ 中位数细线（纯 box-style 但不画 outlier）
    bp = ax.boxplot(cpc_data, positions=positions, widths=0.18,
                    patch_artist=True, showfliers=False, showmeans=True,
                    medianprops=dict(color='black', linewidth=1.8),
                    meanprops=dict(marker='D', markerfacecolor='white',
                                   markeredgecolor='black', markersize=6),
                    whiskerprops=dict(color='black', linewidth=1.0),
                    capprops=dict(color='black', linewidth=1.0))
    for patch, color in zip(bp['boxes'], list(COLORS.values()) * 2):
        patch.set_facecolor(color); patch.set_alpha(0.95)

    # 在 x 轴下方注释"样本数 N"
    for i, n in enumerate([len(c) for c in cpc_data]):
        ax.text(i, -0.12, f'N={n}', transform=ax.get_xaxis_transform(),
                ha='center', va='top', fontsize=8, color='#555555')

    ax.set_xticks(positions)
    ax.set_xticklabels(plan_ids_cpc, rotation=45, ha='right')
    ax.set_title('(c) 各方案的 CPC 分布（小提琴 + IQR 箱）')
    ax.set_ylabel('CPC(元)')
    ax.set_xlabel('方案ID（N 为样本数）')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(bottom=0)

    # (d) 上方位消费占比饼图
    ax = axes[1, 1]
    top_cons = dfc['上方位消费额'].sum()
    body_cons = dfc['消费额'].sum() - top_cons
    ax.pie([top_cons, body_cons],
           labels=[f'上方位\n({top_cons/dfc["消费额"].sum()*100:.1f}%)',
                   f'非上方位\n({body_cons/dfc["消费额"].sum()*100:.1f}%)'],
           colors=[COLORS['accent'], COLORS['primary']],
           autopct='%1.1f%%', startangle=90)
    ax.set_title('(d) 消费额在上方位 vs 普通位置的分布')

    fig.suptitle('问题 1：出价策略与预算分析', fontsize=14, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, 'q1_bid_strategy')
    plt.close(fig)


def fig_time_pattern(data):
    """5.1.4 时间规律 - 月度/周度/日度"""
    plt = apply_style()
    daily = data['daily_full'].copy()
    daily = daily.sort_values('日期')

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # (a) 整体每日趋势 + 月度均线
    ax = axes[0, 0]
    ax.plot(daily['日期'], daily['总消费额'], color=COLORS['primary'], alpha=0.4, linewidth=0.8, label='日消费额')
    daily['消费额_30日'] = daily['总消费额'].rolling(30).mean()
    ax.plot(daily['日期'], daily['消费额_30日'], color=COLORS['danger'], linewidth=2, label='30日移动均线')
    ax2 = ax.twinx()
    ax2.plot(daily['日期'], daily['新注册数'], color=COLORS['success'], alpha=0.4, linewidth=0.8, label='日注册数')
    ax2.plot(daily['日期'], daily['新注册数'].rolling(30).mean(), color=COLORS['accent'], linewidth=2, label='注册数30日均线')
    ax.set_title('(a) 每日消费与注册量趋势')
    ax.set_ylabel('消费额(元)', color=COLORS['primary'])
    ax2.set_ylabel('新注册数', color=COLORS['success'])
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left')
    ax2.legend(loc='upper right')

    # (b) 周内分布
    ax = axes[0, 1]
    daily['星期几'] = daily['日期'].dt.dayofweek
    weekly = daily.groupby('星期几').agg({'总消费额': 'sum', '新注册数': 'sum'}).reset_index()
    weekly['星期'] = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    x = np.arange(len(weekly))
    ax.bar(x - 0.2, weekly['总消费额']/1e4, 0.4, label='消费额(万)', color=COLORS['primary'])
    ax.bar(x + 0.2, weekly['新注册数']/1e2, 0.4, label='注册数(百)', color=COLORS['accent'])
    ax.set_xticks(x)
    ax.set_xticklabels(weekly['星期'])
    ax.set_title('(b) 周内消费与注册分布')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # (c) 注册转化率 vs CPC 散点
    ax = axes[1, 0]
    plot_data = daily.dropna(subset=['注册转化率', 'CPC']).copy()
    plot_data = plot_data[plot_data['CPC'] < 10]
    scatter = ax.scatter(plot_data['CPC'], plot_data['注册转化率'],
                         s=plot_data['总消费额']/100, alpha=0.5, c=plot_data['日期'],
                         cmap='viridis', edgecolors='white', linewidth=0.5)
    ax.set_xlabel('CPC(元)')
    ax.set_ylabel('注册转化率')
    ax.set_title('(c) 注册转化率 vs CPC（圆=消费额）')
    ax.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax, label='日期')

    # (d) 月度注册量增长
    ax = axes[1, 1]
    daily['月份'] = daily['日期'].dt.to_period('M')
    monthly = daily.groupby('月份')[['总消费额', '新注册数']].sum().reset_index()
    monthly['月份'] = monthly['月份'].astype(str)
    monthly['每元注册'] = monthly['新注册数'] / monthly['总消费额'].replace(0, np.nan)
    ax.plot(monthly['月份'], monthly['每元注册'], color=COLORS['success'], marker='o', linewidth=2)
    ax.set_title('(d) 月度单位注册量趋势（越高越好）')
    ax.set_ylabel('注册数/消费额(元)')
    ax.set_xticklabels(monthly['月份'], rotation=45)
    ax.grid(True, alpha=0.3)

    fig.suptitle('问题 1：投放策略与时间规律', fontsize=14, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, 'q1_time_pattern')
    plt.close(fig)


def fig_score_radar(result):
    """5.1.6 综合评分雷达图"""
    plt = apply_style()
    from math import pi

    cats = list(result['dimensions'].keys())
    scores = [result['dimensions'][c]['score'] for c in cats]
    weights = [result['dimensions'][c].get('weight_mixed',
              result['dimensions'][c].get('weight', 0.25)) for c in cats]

    # 雷达角度
    n = len(cats)
    angles = [n_ / float(n) * 2 * pi for n_ in range(n)]
    angles += angles[:1]
    scores_plot = scores + scores[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.fill(angles, scores_plot, color=COLORS['primary'], alpha=0.25)
    ax.plot(angles, scores_plot, color=COLORS['primary'], linewidth=2)

    # 权重气泡
    for i, (a, s, w) in enumerate(zip(angles[:-1], scores, weights)):
        ax.scatter([a], [s], s=w * 800, color=COLORS['accent'], alpha=0.6, edgecolors='black', zorder=5)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([f'{c}\n({s:.1f}分, w={w})' for c, s, w in zip(cats, scores, weights)],
                       fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=8)
    ax.set_title(f'问题 1：SEM投放策略合理性综合评分雷达图\n综合得分: {result["overall_score"]} 分 / {result["grade"]}',
                 fontsize=14, fontweight='bold', pad=20)
    ax.grid(True)

    fig.tight_layout()
    save_fig(fig, 'q1_score_radar')
    plt.close(fig)


def fig_score_breakdown(result):
    """综合评分明细柱状图"""
    plt = apply_style()
    cats = list(result['dimensions'].keys())
    scores = [result['dimensions'][c]['score'] for c in cats]

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [COLORS['success'] if s >= 70 else (COLORS['accent'] if s >= 55 else COLORS['danger'])
              for s in scores]
    bars = ax.barh(cats, scores, color=colors, edgecolor='black', linewidth=1.5)

    for bar, s in zip(bars, scores):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f'{s:.1f}', va='center', fontsize=12, fontweight='bold')

    ax.axvline(60, color='gray', linestyle='--', alpha=0.5, label='及格线(60)')
    ax.set_xlim(0, 110)
    ax.set_xlabel('评分(0-100)')
    ax.set_title(f'问题 1：综合评分总览 ({result["overall_score"]} 分 / {result["grade"]})')
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_fig(fig, 'q1_score_breakdown')
    plt.close(fig)


if __name__ == '__main__':
    from src.q1_scoring import run_scoring
    print('[Q1] 加载数据...', flush=True)
    data = build_q1_data()

    print('[Q1] 1) 设计质量图表...', flush=True)
    fig_design_quality(data)
    print('[Q1] 2) 关键词管理图表...', flush=True)
    fig_keyword_management(data)
    print('[Q1] 3) 出价策略图表...', flush=True)
    fig_bid_strategy(data)
    print('[Q1] 4) 时间规律图表...', flush=True)
    fig_time_pattern(data)

    # 评分
    print('[Q1] 5) 评分 + 雷达图...', flush=True)
    result = run_scoring()
    fig_score_radar(result)
    fig_score_breakdown(result)

    print('[Q1] 完成', flush=True)
