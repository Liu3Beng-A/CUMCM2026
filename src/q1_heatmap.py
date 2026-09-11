"""Q1 方案×维度评分热力图

输出：results/figures/q1_heatmap.png
- X 轴：4 个一级维度
- Y 轴：5 个方案
- 颜色：0-100 评分（红→黄→绿）
- 单元格标注：精确分值
- 顶部附加：综合得分横条
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from src.utils import FIGURES_DIR, TABLES_DIR, ensure_dir
from src.plot_style import apply_style, save_fig, COLORS


def fig_heatmap():
    """生成 方案×维度 评分热力图"""
    apply_style()

    # 1) 加载评分
    plan_scores_path = os.path.join(TABLES_DIR, 'q1_plan_scores.csv')
    if not os.path.exists(plan_scores_path):
        raise FileNotFoundError(f'未找到 {plan_scores_path}，请先运行 q1_scoring')

    df = pd.read_csv(plan_scores_path, encoding='utf-8-sig')
    plan_ids = df['方案ID'].astype(str).tolist()
    dims = ['设计质量与创意', '关键词管理与运用', '出价策略与预算', '投放策略与时间']

    # 加载权重（用于排序与标签）
    weights_path = os.path.join(TABLES_DIR, 'q1_weights.json')
    with open(weights_path, 'r', encoding='utf-8') as f:
        weights = json.load(f)
    mixed_w = weights['mixed_weights']

    # 加载 0 分诊断（用于标注）
    diag_path = os.path.join(TABLES_DIR, 'q1_zero_score_diagnosis.csv')
    diag = pd.read_csv(diag_path, encoding='utf-8-sig') if os.path.exists(diag_path) else None

    # 2) 计算综合得分
    score_mat = df[dims].values
    w_vec = np.array([mixed_w[d] for d in dims])
    overall = score_mat @ w_vec

    # 3) 按综合分降序排序
    order = np.argsort(-overall)
    df_sorted = df.iloc[order].reset_index(drop=True)
    score_mat = score_mat[order]
    overall_sorted = overall[order]
    plan_ids_sorted = [plan_ids[i] for i in order]

    # 4) 自定义 colormap：红(0) → 黄(50) → 绿(100)
    cmap = LinearSegmentedColormap.from_list(
        'sem_radar', [COLORS['danger'], COLORS['accent'], '#F4D35E', COLORS['success'], COLORS['primary']]
    )

    # 5) 画图
    fig = plt.figure(figsize=(13, 8))
    gs = fig.add_gridspec(2, 1, height_ratios=[4.5, 1], hspace=0.35)
    ax = fig.add_subplot(gs[0])

    im = ax.imshow(score_mat, aspect='auto', cmap=cmap, vmin=0, vmax=100)

    # 轴标签
    ax.set_xticks(range(len(dims)))
    ax.set_xticklabels([
        f'{d}\n(权重 {mixed_w[d]*100:.1f}%)' for d in dims
    ], fontsize=10)
    ax.set_yticks(range(len(plan_ids_sorted)))
    ax.set_yticklabels([f'方案 {pid}\n(综合 {overall_sorted[i]:.1f})'
                        for i, pid in enumerate(plan_ids_sorted)],
                       fontsize=11, fontweight='bold')

    # 单元格内填值
    for i in range(len(plan_ids_sorted)):
        for j in range(len(dims)):
            v = score_mat[i, j]
            color = 'white' if v < 35 or v > 75 else 'black'
            ax.text(j, i, f'{v:.1f}', ha='center', va='center',
                    color=color, fontsize=12, fontweight='bold')

    # 0 分单元格加红色边框
    for i in range(len(plan_ids_sorted)):
        for j in range(len(dims)):
            if score_mat[i, j] == 0:
                ax.add_patch(plt.Rectangle(
                    (j - 0.5, i - 0.5), 1, 1,
                    fill=False, edgecolor='red', linewidth=3, zorder=10
                ))

    ax.set_title('问题 1：5 方案 × 4 维度 评分热力图\n'
                 '(红色边框 = 0 分异常；颜色映射：红(差) → 黄 → 绿(优))',
                 fontsize=13, fontweight='bold', pad=12)

    # 颜色条
    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label('评分 (0-100)', fontsize=11)

    # 6) 底部综合分横条（颜色按 A≥85/B70-84/C60-69/D50-59/E<50 阈值映射）
    ax2 = fig.add_subplot(gs[1])
    bar_colors = [COLORS['success'] if s >= 70 else
                  (COLORS['accent'] if s >= 50 else COLORS['danger'])
                  for s in overall_sorted]
    bars = ax2.barh(range(len(plan_ids_sorted)), overall_sorted,
                    color=bar_colors, edgecolor='black', linewidth=1.2)
    ax2.set_yticks(range(len(plan_ids_sorted)))
    ax2.set_yticklabels([f'方案 {pid}' for pid in plan_ids_sorted], fontsize=10)
    ax2.invert_yaxis()
    ax2.set_xlabel('综合评分（CRITIC 70:30 混合）', fontsize=11)
    ax2.set_xlim(0, 100)
    ax2.axvline(60, color='gray', linestyle='--', alpha=0.5, label='C/D 阈值线(60)')
    ax2.axvline(50, color='red',  linestyle=':', alpha=0.5, label='D/E 阈值线(50)')
    for bar, s in zip(bars, overall_sorted):
        ax2.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                 f'{s:.1f}', va='center', fontsize=11, fontweight='bold')
    ax2.legend(loc='lower right')
    ax2.grid(True, alpha=0.3, axis='x')
    # 修正口径：底部条展示的是扣分前综合分（与上方热力图保持一致），
    # 扣分后综合分见 q1_penalty_compare.png。
    ax2.set_title('方案综合得分（扣分前；扣分后对比见 q1_penalty_compare.png）', fontsize=11)

    save_fig(fig, 'q1_heatmap')
    plt.close(fig)

    # 7) 同时输出一张"扣分前后对比"小图
    if os.path.exists(os.path.join(TABLES_DIR, 'q1_score.json')):
        with open(os.path.join(TABLES_DIR, 'q1_score.json'), 'r', encoding='utf-8') as f:
            result = json.load(f)
        _fig_penalty_compare(plan_ids_sorted, score_mat, dims, mixed_w, result, diag)


def _fig_penalty_compare(plan_ids_sorted, score_mat, dims, mixed_w, result, diag):
    """画一张"扣分前后"对比图，专门展示 525368335 / 495817671 为何扣到 0

    改-6：
    - 扣分前：从 q1_plan_scores.csv（未被扣分污染）
    - 扣分后：从 q1_score.json 的 plan_scores（已扣分）
    """
    apply_style()
    overall_before = score_mat @ np.array([mixed_w[d] for d in dims])

    fig, ax = plt.subplots(figsize=(11, 6))

    # 当前综合分（应用扣分）
    with open(os.path.join(TABLES_DIR, 'q1_score.json'), 'r', encoding='utf-8') as f:
        result = json.load(f)
    overall_after = np.array([
        result['plan_scores'][pid]['设计质量与创意'] * mixed_w['设计质量与创意']
      + result['plan_scores'][pid]['关键词管理与运用'] * mixed_w['关键词管理与运用']
      + result['plan_scores'][pid]['出价策略与预算'] * mixed_w['出价策略与预算']
      + result['plan_scores'][pid]['投放策略与时间'] * mixed_w['投放策略与时间']
        for pid in plan_ids_sorted
    ])

    y = np.arange(len(plan_ids_sorted))
    h = 0.35
    bars1 = ax.barh(y - h/2, overall_before, h, label='扣分前',
                    color=COLORS['primary'], edgecolor='black')
    bars2 = ax.barh(y + h/2, overall_after, h, label='扣分后',
                    color=COLORS['danger'], edgecolor='black')

    for bar, v in zip(bars1, overall_before):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f'{v:.1f}', va='center', fontsize=10)
    # 修复（2026-09-12）：扣分后条形较短，白色文字放在条形外、白底上不可见。
    # 改为深色文字放在条形内部，确保 57.28 / 56.60 / 55.26 / 51.08 / 33.23 都能看清。
    for bar, v in zip(bars2, overall_after):
        # 文字放在条形内（右端偏左 2 单位），用白色加粗；如条形太短则外置深色文字
        if bar.get_width() > 8:
            ax.text(bar.get_width() - 1.5, bar.get_y() + bar.get_height()/2,
                    f'{v:.1f}', va='center', ha='right', fontsize=10,
                    color='white', fontweight='bold')
        else:
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                    f'{v:.1f}', va='center', fontsize=10,
                    color=COLORS['danger'], fontweight='bold')

    ax.set_yticks(y)
    ax.set_yticklabels([f'方案 {pid}' for pid in plan_ids_sorted], fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel('综合评分', fontsize=11)
    ax.set_title('问题 1：节日 Bootstrap 扣分前后综合分对比\n'
                 '(扣分来源：春节/劳动/国庆法定节假日 p<0.001 → -30 分)',
                 fontsize=13, fontweight='bold')
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3, axis='x')
    ax.set_xlim(0, 100)

    save_fig(fig, 'q1_penalty_compare')
    plt.close(fig)


if __name__ == '__main__':
    print('[q1] 生成方案×维度热力图...', flush=True)
    fig_heatmap()
    print('[done] results/figures/q1_heatmap.png')
    print('[done] results/figures/q1_penalty_compare.png')
