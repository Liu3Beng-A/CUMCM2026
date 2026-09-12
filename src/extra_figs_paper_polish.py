"""
论文润色补充图表生成（5 张高优先级）
====================================

生成 5 张图表，为 Q2/Q3/Q4 论文润色做准备：

1. Q2-5  5 类占比环形图
2. Q3-4 16 天每日投入时间序列
3. Q3-5 12 单元 × 16 天投入热力图
4. Q4-2 6 因素 CV 对比柱状图
5. Q4-3 6 单元 × 7 天投入热力图

依赖：
- src/plot_style.py (统一风格)
- data/processed/q2/keyword_classified.pkl
- results/excel/result3.xlsx (Q3)
- results/excel/result4.xlsx (Q4)
- data/processed/q4/q4_unit_cv.pkl
"""
import os
import sys
import pickle
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.utils import ensure_dir, FIGURES_DIR
from src.plot_style import (apply_style, save_fig, force_cn, PAPER_PALETTE,
                            DIM_COLORS, PLAN_COLORS)

ensure_dir(FIGURES_DIR)


# =====================================================
# 1. Q2-5 5 类占比环形图
# =====================================================
def plot_q2_class_pie():
    """2227 关键词 5 类占比环形图"""
    pkl_path = os.path.join(ROOT, 'data/processed/q2/keyword_classified.pkl')
    with open(pkl_path, 'rb') as f:
        df = pickle.load(f)

    CLASS_NAMES = ['黄金词', '重点词', '潜力词', '问题词', '无效词']
    CLASS_COLORS = {
        '黄金词': '#F18F01',
        '重点词': '#D62246',
        '潜力词': '#06A77D',
        '问题词': '#6C757D',
        '无效词': '#A23B72',
    }
    counts = df['分类'].value_counts().to_dict()
    ordered = [counts.get(k, 0) for k in CLASS_NAMES]
    total = sum(ordered)

    plt = apply_style()
    fig, ax = plt.subplots(figsize=(10, 7))

    # 突出"问题词"（91 个削减目标）和"黄金词"（高价值）
    explode = [0.02, 0.02, 0.02, 0.06, 0.02]

    wedges, texts, autotexts = ax.pie(
        ordered,
        labels=CLASS_NAMES,
        colors=[CLASS_COLORS[k] for k in CLASS_NAMES],
        autopct=lambda p: f'{p:.1f}%\n({int(round(p * total / 100))})',
        startangle=90,
        counterclock=False,
        explode=explode,
        pctdistance=0.78,
        wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2),
        textprops=dict(fontsize=12)
    )
    for t in autotexts:
        t.set_color('white')
        t.set_fontweight('bold')
        t.set_fontsize(10)

    ax.set_title('问题 2：关键词 5 类分布占比（n=2227）', fontsize=14, pad=20)
    ax.text(0, 0, f'总计\n{total}\n关键词',
            ha='center', va='center', fontsize=13, fontweight='bold')

    # 底部注释
    fig.text(0.5, 0.02,
             '注：91 个问题词被识别为削减型极值，占比 19.6%；黄金词 431（19.4%）为高价值保留型。',
             ha='center', fontsize=10, style='italic', color='#444')

    fig.tight_layout()
    save_fig(fig, 'q2_class_pie')
    plt.close(fig)
    print('[1/5] q2_class_pie.png done')


# =====================================================
# 2. Q3-4 16 天每日投入时间序列
# =====================================================
def plot_q3_daily_cost():
    """16 天每日投入金额柱状图（2 月 + 8 月双周）"""
    excel_path = os.path.join(ROOT, 'results/excel/result3.xlsx')
    df = pd.read_excel(excel_path)

    daily = df.groupby('日期')['投入金额'].sum().reset_index().sort_values('日期')
    daily_total = daily['投入金额'].sum()

    plt = apply_style()
    fig, ax = plt.subplots(figsize=(14, 6))

    # 用月份着色：2 月用蓝色，8 月用橙色
    colors = []
    for d in daily['日期']:
        s = str(d)
        if s.startswith('2025-02'):
            colors.append('#2E86AB')
        elif s.startswith('2025-08'):
            colors.append('#F18F01')

    bars = ax.bar(range(len(daily)), daily['投入金额'],
                  color=colors, edgecolor='black', linewidth=0.6)

    # 数值标注
    for bar, v in zip(bars, daily['投入金额']):
        if v > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 80,
                    f'{v:.0f}', ha='center', va='bottom', fontsize=9)
        else:
            ax.text(bar.get_x() + bar.get_width()/2, -250,
                    '零投入', ha='center', va='top', fontsize=8.5,
                    color='#D62246', fontweight='bold')

    # 月份分隔
    feb_end = 7  # 2025-02-01..02-08 = 8 天
    ax.axvline(feb_end - 0.5, color='black', linewidth=1.2, linestyle='--', alpha=0.5)
    ax.text(3.5, daily['投入金额'].max() * 0.95, '2025 年 2 月 (春节)',
            ha='center', fontsize=11, fontweight='bold', color='#2E86AB')
    ax.text(11.5, daily['投入金额'].max() * 0.95, '2025 年 8 月',
            ha='center', fontsize=11, fontweight='bold', color='#F18F01')

    # X 轴标签
    date_labels = [str(d)[5:] for d in daily['日期']]
    ax.set_xticks(range(len(daily)))
    ax.set_xticklabels(date_labels, rotation=0, fontsize=10)

    # 标注 02-06 / 02-08 智能零投入
    for zero_idx in daily.index[daily['投入金额'] == 0].tolist():
        pos = daily.index.get_loc(zero_idx)
        ax.annotate('MILP\n智能零投入', xy=(pos, 0), xytext=(pos, -1500),
                    ha='center', fontsize=8, color='#D62246',
                    arrowprops=dict(arrowstyle='->', color='#D62246', lw=0.8))

    ax.set_title('问题 3：16 天每日投入金额（2 月 + 8 月双周规律）', fontsize=13)
    ax.set_xlabel('日期 (M-D)')
    ax.set_ylabel('投入金额 (元)')
    ax.set_ylim(-2000, daily['投入金额'].max() * 1.15)
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')

    # 底部注释
    fig.text(0.5, -0.02,
             f'总计 51,164.90 元（99.94% 预算 51,164.93）；02-06/02-08 MILP 判定代理收益为负，智能零投入。',
             ha='center', fontsize=10, color='#444')

    # 自定义图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2E86AB', label='2 月 (春节窗口)'),
        Patch(facecolor='#F18F01', label='8 月 (正常月)'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', framealpha=0.9)

    fig.tight_layout()
    save_fig(fig, 'q3_daily_cost')
    plt.close(fig)
    print('[2/5] q3_daily_cost.png done')


# =====================================================
# 3. Q3-5 12 单元 × 16 天投入热力图
# =====================================================
def plot_q3_unit_date_heatmap():
    """12 单元 × 2 月份 双面板 horizontal bar（替代 heatmap）

    改-P0-7.v2：原 heatmap 即使 LogNorm 仍难读（数值差异 350 倍，色阶单调）
    改为：
      1) 双面板：左 02 月（4 天）/ 右 08 月（8 天）
      2) 每面板 horizontal bar：12 单元按月总投入降序
      3) 柱末标总投入 + 日均 + 0 值天数
      4) 顶部摘要（占比 / 日均对比）
      5) 底部表格（12 单元 × 16 天明细）
    """
    excel_path = os.path.join(ROOT, 'results/excel/result3.xlsx')
    df = pd.read_excel(excel_path)

    pivot = df.pivot_table(index='推广单元', columns='日期',
                           values='投入金额', aggfunc='sum', fill_value=0)
    pivot = pivot[sorted(pivot.columns)]
    feb_cols = [c for c in pivot.columns if str(c).startswith('2025-02')]
    aug_cols = [c for c in pivot.columns if str(c).startswith('2025-08')]

    pivot['02_sum'] = pivot[feb_cols].sum(axis=1)
    pivot['08_sum'] = pivot[aug_cols].sum(axis=1)
    pivot['total'] = pivot['02_sum'] + pivot['08_sum']
    pivot['n_zero'] = (pivot[feb_cols + aug_cols] == 0).sum(axis=1)

    # 颜色映射（按总投入排名）: 蓝→红
    sorted_units = pivot['total'].sort_values(ascending=False)
    rank = sorted_units.rank(method='first', ascending=False)
    cmap = plt.get_cmap('coolwarm')
    pivot['color'] = [cmap(0.1 + 0.8 * (rank[u] - 1) / (len(rank) - 1)) for u in pivot.index]

    apply_style()
    fig = plt.figure(figsize=(15, 9))
    gs = fig.add_gridspec(3, 2, height_ratios=[0.6, 3.5, 1.5],
                          hspace=0.35, wspace=0.30,
                          left=0.07, right=0.97, top=0.93, bottom=0.05)

    # ===== 顶部：摘要 KPI =====
    total_02 = pivot['02_sum'].sum()
    total_08 = pivot['08_sum'].sum()
    n_units_02 = (pivot['02_sum'] > 0).sum()
    n_units_08 = (pivot['08_sum'] > 0).sum()
    total = total_02 + total_08

    ax_sum = fig.add_subplot(gs[0, :])
    ax_sum.axis('off')
    ax_sum.text(0.5, 0.5,
                f'16 天总投入 {total:,.0f} 元 = 02 月 4 天 {total_02:,.0f} 元 ({n_units_02} 单元) '
                f'+ 08 月 8 天 {total_08:,.0f} 元 ({n_units_08} 单元)  |  '
                f'02 月日均 {total_02/4:,.0f} 元 / 08 月日均 {total_08/8:,.0f} 元',
                ha='center', va='center', fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#F0F8FF',
                          edgecolor='#2E86AB', linewidth=1.2),
                transform=ax_sum.transAxes)

    # ===== 双面板 horizontal bar =====
    for col, (month_label, sum_col, day_cols, day_n, total_lab) in enumerate([
        ('2025-02 月（4 天）', '02_sum', feb_cols, 4, total_02),
        ('2025-08 月（8 天）', '08_sum', aug_cols, 8, total_08),
    ]):
        ax = fig.add_subplot(gs[1, col])
        # 按该月总投入降序（最大的在顶部）
        df_plot = pivot.sort_values(sum_col, ascending=True).reset_index()
        # 颜色按总投入排名
        colors_list = [pivot.loc[u, 'color'] for u in df_plot['推广单元']]
        bars = ax.barh(df_plot['推广单元'].astype(str), df_plot[sum_col],
                       color=colors_list, edgecolor='black', linewidth=0.7, height=0.7)
        # 柱末标：总投入 + 日均 + 占比
        for i, (bar, val, u) in enumerate(zip(bars, df_plot[sum_col], df_plot['推广单元'])):
            avg = val / day_n if day_n > 0 else 0
            pct = val / total_lab * 100 if total_lab > 0 else 0
            label = f'{val:,.0f} 元\n(日均 {avg:,.0f}, 占比 {pct:.1f}%)'
            ax.text(bar.get_width() * 1.02, bar.get_y() + bar.get_height() / 2,
                    label, ha='left', va='center', fontsize=8.5, color='#222')
        ax.set_xlabel(f'{month_label} 投入金额 (元)', fontsize=10, fontweight='bold')
        ax.set_title(f'{month_label}：12 推广单元投入排名（按总投入降序）',
                     fontsize=11, fontweight='bold', pad=8)
        ax.grid(alpha=0.3, axis='x')
        ax.set_xlim(0, df_plot[sum_col].max() * 1.55)  # 留出标签空间

    # ===== 底部：表格（12 单元 × 16 天明细） =====
    ax_tbl = fig.add_subplot(gs[2, :])
    ax_tbl.axis('off')
    # 构建表格数据：单元 / 02 月日均 / 02 月总 / 08 月日均 / 08 月总 / 16 天总 / 占比
    table_data = []
    pivot_sorted = pivot.sort_values('total', ascending=False)
    for u, row in pivot_sorted.iterrows():
        avg_02 = row['02_sum'] / 4
        avg_08 = row['08_sum'] / 8
        pct = row['total'] / total * 100
        table_data.append([
            str(u),
            f'{row["02_sum"]:,.0f}',
            f'{avg_02:,.0f}',
            f'{row["08_sum"]:,.0f}',
            f'{avg_08:,.0f}',
            f'{row["total"]:,.0f}',
            f'{pct:.1f}%',
            f'{int(row["n_zero"])}/12',
        ])
    header = ['推广单元', '02 月总', '日均', '08 月总', '日均', '16 天总', '占比', '0值天数']
    table = ax_tbl.table(cellText=table_data, colLabels=header,
                         cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.6)
    # 表头颜色
    for j in range(len(header)):
        cell = table[(0, j)]
        cell.set_text_props(fontweight='bold', color='white', fontsize=9.5)
        cell.set_facecolor('#2E86AB')
        cell.set_height(0.13)
    # 数据行：交替底色 + 占比列高亮
    for i in range(1, len(table_data) + 1):
        is_top3 = i <= 3
        for j in range(len(header)):
            cell = table[(i, j)]
            cell.set_facecolor('#FFF8E7' if is_top3 else ('#F5F9FF' if i % 2 == 0 else 'white'))
            cell.set_edgecolor('#CCC')
            if j == 5:  # 16 天总列加粗
                cell.set_text_props(fontweight='bold')

    fig.suptitle('问题 3：12 推广单元 × 16 天 投入金额分析（双面板水平柱状图 + 明细表）',
                 fontsize=13, fontweight='bold', y=0.985)
    save_fig(fig, 'q3_unit_date_heatmap')
    plt.close(fig)
    print('[3/5] q3_unit_date_heatmap.png done')


# =====================================================
# 4. Q4-2 6 因素 CV 对比柱状图
# =====================================================
def plot_q4_cv_bar():
    """6 因素不确定性（CV）对比柱状图"""
    pkl_path = os.path.join(ROOT, 'data/processed/q4/q4_unit_cv.pkl')
    with open(pkl_path, 'rb') as f:
        df = pickle.load(f)

    metric_names_cn = {
        'cv_cpc':              'CPC',
        'cv_impressions':      '展现量',
        'cv_top_imp_pos':      '上方位',
        'cv_clicks':           '点击',
        'cv_browses':          '浏览',
        'cv_regs':             '注册'
    }

    means = {col: df[col].mean() for col in metric_names_cn.keys()}

    plt = apply_style()
    fig, ax = plt.subplots(figsize=(11, 6))

    keys = list(metric_names_cn.keys())
    labels = [metric_names_cn[k] for k in keys]
    values = [means[k] for k in keys]

    # 颜色按 CV 大小：越大越红
    norm_values = np.array(values) / max(values)
    colors = plt.cm.YlOrRd(0.3 + 0.6 * norm_values)

    bars = ax.bar(labels, values, color=colors, edgecolor='black', linewidth=0.6)

    # 数值标注
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{v:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # 注册量突出
    ax.annotate('注册量 CV 最大\n→ 主要不确定性来源',
                xy=(5, values[5]), xytext=(4.2, 1.4),
                fontsize=10, color='#D62246', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='#D62246', lw=1.2))

    ax.set_title('问题 4：6 因素不确定性（变异系数 CV）对比', fontsize=13)
    ax.set_xlabel('指标')
    ax.set_ylabel('变异系数 CV（无量纲）')
    ax.set_ylim(0, max(values) * 1.25)
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')

    # 阈值线（CV > 0.8 视为高不确定性）
    ax.axhline(0.8, color='#D62246', linestyle='--', alpha=0.5, linewidth=1)
    ax.text(5.5, 0.83, '高不确定性阈值 0.8', ha='right',
            fontsize=9, color='#D62246', style='italic')

    fig.tight_layout()
    save_fig(fig, 'q4_cv_compare')
    plt.close(fig)
    print('[4/5] q4_cv_compare.png done')


# =====================================================
# 5. Q4-3 6 单元 × 7 天投入热力图
# =====================================================
def plot_q4_unit_date_heatmap():
    """6 单元 × 7 天 投入热力图"""
    excel_path = os.path.join(ROOT, 'results/excel/result4.xlsx')
    df = pd.read_excel(excel_path)

    pivot = df.pivot_table(index='推广单元', columns='日期',
                           values='投入金额', aggfunc='sum', fill_value=0)
    pivot = pivot[sorted(pivot.columns)]

    # 按总投入降序
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]

    plt = apply_style()
    fig, ax = plt.subplots(figsize=(12, 6))

    im = ax.imshow(pivot.values, aspect='auto', cmap='YlOrRd', interpolation='nearest')

    # 刻度
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([str(c)[5:] for c in pivot.columns], rotation=0, fontsize=10)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([str(u) for u in pivot.index], fontsize=10)

    # 单元格数值
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if v > 0:
                color = 'white' if v > pivot.values.max() * 0.6 else 'black'
                ax.text(j, i, f'{v:.0f}', ha='center', va='center',
                        fontsize=9, color=color, fontweight='bold')

    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cbar.set_label('投入金额 (元)', fontsize=10)

    ax.set_title('问题 4：6 活跃推广单元 × 7 天 投入金额热力图（2026-09-11~17）',
                 fontsize=13, pad=15)
    ax.set_xlabel('日期 (M-D)')
    ax.set_ylabel('推广单元 ID')

    fig.tight_layout()
    save_fig(fig, 'q4_unit_date_heatmap')
    plt.close(fig)
    print('[5/5] q4_unit_date_heatmap.png done')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('=' * 60)
    print('论文润色补充图表生成（5 张）')
    print('=' * 60)
    plot_q2_class_pie()
    plot_q3_daily_cost()
    plot_q3_unit_date_heatmap()
    plot_q4_cv_bar()
    plot_q4_unit_date_heatmap()
    print('=' * 60)
    print('全部 5 张图表已保存到 results/figures/')
    print('=' * 60)
