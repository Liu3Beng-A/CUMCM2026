"""
Q2 · 绘图脚本（5 类分布 / 阈值敏感性 / 极值审计 / 推广单元堆叠）
================================================================
依赖：src/q2_classify.py 跑通后生成的 q2_thresholds.json / q2_extreme_audit.csv /
      data/processed/q2/keyword_classified.pkl
"""
import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.utils import ensure_dir, FIGURES_DIR, TABLES_DIR, PROCESSED_DIR
from src.plot_style import apply_style, save_fig, force_cn

CLASS_NAMES = ['黄金词', '重点词', '潜力词', '问题词', '无效词']
CLASS_COLORS = {
    '黄金词': '#F18F01',  # 橙
    '重点词': '#D62246',  # 红
    '潜力词': '#06A77D',  # 绿
    '问题词': '#6C757D',  # 灰
    '无效词': '#A23B72',  # 紫
}

# =====================================================
# 图 1 · 5 类分布（柱状图）
# =====================================================
def plot_class_distribution(thresholds: dict, out_path: str) -> None:
    counts = thresholds['counts']
    counts_ordered = [counts.get(k, 0) for k in CLASS_NAMES]

    plt = apply_style()
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(CLASS_NAMES, counts_ordered,
                  color=[CLASS_COLORS[k] for k in CLASS_NAMES],
                  edgecolor='black', linewidth=0.6)

    # 数值标注
    for bar, c in zip(bars, counts_ordered):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 8,
                f'{c}', ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax.set_title('问题 2：关键词 5 类分布')
    ax.set_xlabel('分类')
    ax.set_ylabel('关键词数')
    ax.set_ylim(0, max(counts_ordered) * 1.15)
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')

    fig.tight_layout()
    save_fig(fig, os.path.basename(out_path).replace('.png', ''))
    plt.close(fig)
    print(f'  ✅ {out_path}')


# =====================================================
# 图 2 · 阈值敏感性（龙卷风图：25 阈值组合下 5 类计数变化率）
# =====================================================
def plot_threshold_sensitivity(thresholds: dict, df_all: pd.DataFrame, out_path: str) -> None:
    """25 个 (成本倍率 × 效益倍率) 组合 → 每类计数变化率 → 龙卷风图"""
    T_c0 = thresholds['T_cost']
    T_b0 = thresholds['T_benefit']

    cost_multipliers = [0.8, 0.9, 1.0, 1.1, 1.2]
    benefit_multipliers = [0.8, 0.9, 1.0, 1.1, 1.2]

    valid_mask = df_all['分类'] != '无效词'
    df_valid = df_valid = df_all[valid_mask].copy()
    cost = df_valid['成本'].astype(float).values
    clicks = df_valid['点击'].astype(float).values
    cpc_inv = clicks / np.maximum(cost, 0.01)

    # 基线计数
    base_counts = {
        '黄金词': int(((cost <= T_c0) & (cpc_inv >= T_b0)).sum()),
        '重点词': int(((cost > T_c0) & (cpc_inv >= T_b0)).sum()),
        '潜力词': int(((cost <= T_c0) & (cpc_inv < T_b0)).sum()),
        '问题词': int(((cost > T_c0) & (cpc_inv < T_b0)).sum()),
    }

    # 25 组合下的每类计数
    class_changes = {k: [] for k in ['黄金词', '重点词', '潜力词', '问题词']}
    for cm in cost_multipliers:
        for bm in benefit_multipliers:
            T_c = T_c0 * cm
            T_b = T_b0 * bm
            class_changes['黄金词'].append(int(((cost <= T_c) & (cpc_inv >= T_b)).sum()))
            class_changes['重点词'].append(int(((cost > T_c) & (cpc_inv >= T_b)).sum()))
            class_changes['潜力词'].append(int(((cost <= T_c) & (cpc_inv < T_b)).sum()))
            class_changes['问题词'].append(int(((cost > T_c) & (cpc_inv < T_b)).sum()))

    # 龙卷风：X 轴 = 计数变化率
    plt = apply_style()
    fig, ax = plt.subplots(figsize=(11, 6))

    y_pos = np.arange(len(['黄金词', '重点词', '潜力词', '问题词']))
    labels = []
    for i, k in enumerate(['黄金词', '重点词', '潜力词', '问题词']):
        vals = class_changes[k]
        rel = (np.array(vals) - base_counts[k]) / max(base_counts[k], 1) * 100
        ax.barh(i, rel.max() - rel.min(),
                left=rel.min(),
                color=CLASS_COLORS[k], alpha=0.6,
                edgecolor='black', linewidth=0.5)
        ax.text(rel.min() - 1, i, f'{rel.min():+.1f}%', ha='right', va='center', fontsize=9)
        ax.text(rel.max() + 1, i, f'{rel.max():+.1f}%', ha='left', va='center', fontsize=9)
        labels.append(f'{k}（基线 {base_counts[k]}）')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.axvline(0, color='black', linewidth=0.8)
    ax.set_xlabel('相对基线计数变化率 (%)')
    ax.set_title('问题 2：阈值敏感性龙卷风图（25 组合 = 5×5 成本×效益倍率）')
    ax.grid(True, alpha=0.3, axis='x', linestyle='--')

    fig.tight_layout()
    save_fig(fig, os.path.basename(out_path).replace('.png', ''))
    plt.close(fig)
    print(f'  ✅ {out_path}')


# =====================================================
# 图 3 · 极值审计 Top 20（横向条形图 + 风险评级）
# =====================================================
def plot_extreme_audit(audit_path: str, out_path: str) -> None:
    df = pd.read_csv(audit_path)
    top = df.head(20).copy()
    # 关键词可能是 int 或 str
    top['kw_label'] = top['关键词'].astype(str)

    risk_color_map = {'高': '#D62246', '中': '#F18F01', '低': '#06A77D'}

    plt = apply_style()
    fig, ax = plt.subplots(figsize=(11, 7))
    bars = ax.barh(top['kw_label'][::-1], top['消费'][::-1],
                   color=[risk_color_map.get(r, '#6C757D') for r in top['风险评级'][::-1]],
                   edgecolor='black', linewidth=0.5)

    for bar, val, risk in zip(bars, top['消费'][::-1], top['风险评级'][::-1]):
        ax.text(bar.get_width() + 200, bar.get_y() + bar.get_height()/2,
                f'{val:,.0f}元', va='center', fontsize=8)
        ax.text(-800, bar.get_y() + bar.get_height()/2,
                risk, va='center', ha='right', fontsize=8, fontweight='bold')

    ax.set_xlabel('消费额（元）')
    ax.set_title(f'问题 2：极值审计 Top 20（共 {len(df)} 词）')
    ax.grid(True, alpha=0.3, axis='x', linestyle='--')

    # 自定义图例
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=risk_color_map[r], edgecolor='black', label=f'{r}风险') for r in ['高', '中', '低']]
    ax.legend(handles=legend_elements, loc='lower right', framealpha=0.9)

    fig.tight_layout()
    save_fig(fig, os.path.basename(out_path).replace('.png', ''))
    plt.close(fig)
    print(f'  ✅ {out_path}')


# =====================================================
# 图 4 · 推广单元 5 类堆叠柱
# =====================================================
def plot_unit_stacked(unit_csv: str, out_path: str) -> None:
    df = pd.read_csv(unit_csv)
    df['key'] = df['方案ID'].astype(str) + '-' + df['推广单元'].astype(str)
    df = df.sort_values('关键词总数', ascending=False)

    x = np.arange(len(df))
    width = 0.65

    plt = apply_style()
    fig, ax = plt.subplots(figsize=(14, 6))

    # 堆叠
    bottom = np.zeros(len(df))
    for cls in CLASS_NAMES:
        vals = df[cls].values
        ax.bar(x, vals, width, bottom=bottom,
               label=cls, color=CLASS_COLORS[cls],
               edgecolor='black', linewidth=0.4)
        bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels(df['key'], rotation=70, fontsize=8, ha='right')
    ax.set_ylabel('关键词数')
    ax.set_title(f'问题 2：{len(df)} 个 (方案, 推广单元) 组合的 5 类堆叠分布')
    ax.legend(ncol=5, loc='upper right', framealpha=0.9, fontsize=9)
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')

    fig.tight_layout()
    save_fig(fig, os.path.basename(out_path).replace('.png', ''))
    plt.close(fig)
    print(f'  ✅ {out_path}')


# =====================================================
# 主流程
# =====================================================
def run():
    print('=' * 60)
    print('Q2 绘图（5 类分布 / 阈值敏感性 / 极值审计 / 推广单元堆叠）')
    print('=' * 60)

    # 读产物
    with open(os.path.join(TABLES_DIR, 'q2_thresholds.json'), 'r', encoding='utf-8') as f:
        thresholds = json.load(f)
    df_all = pd.read_pickle(os.path.join(PROCESSED_DIR, 'q2', 'keyword_classified.pkl'))
    audit_path = os.path.join(TABLES_DIR, 'q2_extreme_audit.csv')
    unit_csv = os.path.join(TABLES_DIR, 'q2_unit_cluster_summary.csv')

    print('\n[图 1] 5 类分布 ...')
    plot_class_distribution(thresholds, os.path.join(FIGURES_DIR, 'q2_class_distribution.png'))

    print('\n[图 2] 阈值敏感性龙卷风图 ...')
    plot_threshold_sensitivity(thresholds, df_all, os.path.join(FIGURES_DIR, 'q2_threshold_sensitivity.png'))

    print('\n[图 3] 极值审计 Top 20 ...')
    plot_extreme_audit(audit_path, os.path.join(FIGURES_DIR, 'q2_extreme_audit.png'))

    print('\n[图 4] 推广单元 5 类堆叠 ...')
    plot_unit_stacked(unit_csv, os.path.join(FIGURES_DIR, 'q2_unit_class_stacked.png'))

    print('\n✅ 4 张图全部生成')


if __name__ == '__main__':
    run()
