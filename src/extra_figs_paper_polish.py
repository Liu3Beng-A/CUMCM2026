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
    """12 单元 × 16 天 投入热力图"""
    excel_path = os.path.join(ROOT, 'results/excel/result3.xlsx')
    df = pd.read_excel(excel_path)

    pivot = df.pivot_table(index='推广单元', columns='日期',
                           values='投入金额', aggfunc='sum', fill_value=0)
    pivot = pivot[sorted(pivot.columns)]

    # 按总投入降序
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]

    plt = apply_style()
    fig, ax = plt.subplots(figsize=(14, 8))

    im = ax.imshow(pivot.values, aspect='auto', cmap='YlOrRd', interpolation='nearest')

    # 刻度
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([str(c)[5:] for c in pivot.columns], rotation=0, fontsize=9)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([str(u) for u in pivot.index], fontsize=9)

    # 月份分隔线
    feb_dates = [i for i, c in enumerate(pivot.columns) if str(c).startswith('2025-02')]
    if feb_dates:
        sep = max(feb_dates) + 0.5
        ax.axvline(sep, color='black', linewidth=1.2, linestyle='--', alpha=0.6)

    # 月份标注
    if feb_dates:
        feb_center = (min(feb_dates) + max(feb_dates)) / 2
        aug_center = (min([i for i, c in enumerate(pivot.columns) if str(c).startswith('2025-08')]) +
                      max([i for i, c in enumerate(pivot.columns) if str(c).startswith('2025-08')])) / 2
        ax.text(feb_center, -1.5, '2025-02', ha='center', fontsize=10, fontweight='bold', color='#2E86AB')
        ax.text(aug_center, -1.5, '2025-08', ha='center', fontsize=10, fontweight='bold', color='#F18F01')

    # 颜色条
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label('投入金额 (元)', fontsize=10)

    ax.set_title('问题 3：12 推广单元 × 16 天 投入金额热力图', fontsize=13, pad=20)
    ax.set_xlabel('日期 (M-D)')
    ax.set_ylabel('推广单元 ID')

    fig.tight_layout()
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
