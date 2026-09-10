"""Q1 敏感性分析（改-7）

目的：
- 检验评分结果对权重扰动的稳健性
- 对每个一级维度的权重做 ±20% 扰动，观察综合评分极差
- 输出一元敏感性分析 → 龙卷风图（Tornado Chart）

方法：
1. 以当前混合权重为基准
2. 对每个维度的权重逐个做 ±20% 扰动
3. 记录综合评分的变化范围
4. 画龙卷风图：横轴是综合评分变化，纵轴是扰动维度

输出：
- q1_sensitivity.csv：每个维度的扰动范围
- q1_tornado.png：龙卷风图

优点：
- 评委最认可的稳健性可视化
- 一眼看出哪个权重对结果影响最大
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.q1_data_prep import build_q1_data
from src.q1_scoring import (
    score_design_quality, score_keyword_management,
    score_bid_strategy, score_time_strategy, _score_per_plan,
)
from src.q1_weights import compute_weights, SUBJECTIVE_WEIGHTS
from src.utils import FIGURES_DIR, TABLES_DIR, ensure_dir
from src.plot_style import apply_style, save_fig


def perturb_weights(base_weights: dict, key: str, delta: float) -> dict:
    """对单个维度权重做 ±delta 扰动（保持总和=1）"""
    new_w = base_weights.copy()
    # 把增量从其他维度按比例扣除
    others = [k for k in new_w if k != key]
    other_sum = sum(new_w[k] for k in others)
    new_w[key] = base_weights[key] + delta
    if new_w[key] < 0:
        new_w[key] = 0
    # 重新分配剩余给其他维度
    remaining = 1.0 - new_w[key]
    if other_sum > 0:
        for k in others:
            new_w[k] = base_weights[k] * (remaining / other_sum)
    else:
        for k in others:
            new_w[k] = remaining / len(others)
    return new_w


def run_sensitivity(perturb_range=0.20, n_steps=9):
    """主入口"""
    print('[sensitivity] 加载数据...', flush=True)
    data = build_q1_data()

    # 算各维度得分
    print('[sensitivity] 计算各维度得分...', flush=True)
    s1 = score_design_quality(data)['综合评分']
    s2 = score_keyword_management(data)['综合评分']
    s3 = score_bid_strategy(data)['综合评分']
    s4 = score_time_strategy(data)['综合评分']
    scores = {
        '设计质量与创意':   s1,
        '关键词管理与运用': s2,
        '出价策略与预算':   s3,
        '投放策略与时间':   s4,
    }

    # 算基准混合权重
    print('[sensitivity] 算基准混合权重...', flush=True)
    plan_scores = _score_per_plan(data)
    weights_res = compute_weights(plan_scores.values, list(plan_scores.columns), SUBJECTIVE_WEIGHTS)
    base_w = weights_res['mixed_weights']

    # 基准综合分
    base_overall = sum(base_w[k] * scores[k] for k in scores)
    print(f'  基准综合分: {base_overall:.2f}', flush=True)

    # 扰动分析
    deltas = np.linspace(-perturb_range, perturb_range, n_steps)
    rows = []
    print('[sensitivity] 扰动分析...', flush=True)
    for dim in scores:
        low_score = base_overall
        high_score = base_overall
        for d in deltas:
            w_pert = perturb_weights(base_w, dim, d)
            overall = sum(w_pert[k] * scores[k] for k in scores)
            rows.append({
                '维度':      dim,
                '扰动':      round(d, 3),
                '扰动后权重': round(w_pert[dim], 4),
                '综合评分':   round(overall, 2),
            })
            low_score = min(low_score, overall)
            high_score = max(high_score, overall)
        rows.append({
            '维度':      f'{dim}_汇总',
            '扰动':      f'极差={high_score - low_score:.2f}',
            '扰动后权重': '-',
            '综合评分':   f'[{low_score:.2f}, {high_score:.2f}]',
        })

    df = pd.DataFrame(rows)
    out_csv = os.path.join(TABLES_DIR, 'q1_sensitivity.csv')
    df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'[save] {out_csv}', flush=True)

    # 汇总表（仅含 4 个维度的极差）
    summary = []
    for dim in scores:
        sub = df[(df['维度'] == dim) & (~df['扰动'].astype(str).str.contains('极差'))]
        score_range = sub['综合评分'].max() - sub['综合评分'].min()
        summary.append({
            '维度':    dim,
            '基准权重': base_w[dim],
            '扰动下限': sub['综合评分'].min(),
            '扰动上限': sub['综合评分'].max(),
            '极差':    round(score_range, 2),
            '相对变化(%)': round(score_range / base_overall * 100, 2),
        })
    summary_df = pd.DataFrame(summary).sort_values('极差', ascending=False)
    summary_csv = os.path.join(TABLES_DIR, 'q1_sensitivity_summary.csv')
    summary_df.to_csv(summary_csv, index=False, encoding='utf-8-sig')
    print(f'[save] {summary_csv}', flush=True)
    print(summary_df.to_string(index=False), flush=True)

    # ===== 龙卷风图 =====
    plt = apply_style()
    fig, ax = plt.subplots(figsize=(11, 6))

    # 按极差排序
    summary_sorted = summary_df.sort_values('极差', ascending=True)
    y_pos = np.arange(len(summary_sorted))
    labels = summary_sorted['维度'].values
    ranges = summary_sorted['极差'].values

    # 每条柱：从中点向两端延伸
    centers = np.full_like(y_pos, base_overall, dtype=float)
    # 提取每条的 [min, max]
    bottoms = summary_sorted['扰动下限'].values
    tops    = summary_sorted['扰动上限'].values
    # 宽度（左半 + 右半）
    left_widths  = centers - bottoms
    right_widths = tops - centers

    # 用双柱（左半 + 右半）
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#06A77D']
    for i, (lbl, c) in enumerate(zip(labels, colors)):
        # 左半柱（扰动下限方向）
        ax.barh(y_pos[i], left_widths[i], left=centers[i] - left_widths[i],
                height=0.6, color=c, alpha=0.85,
                label=lbl if i == 0 else None)
        # 右半柱（扰动上限方向）
        ax.barh(y_pos[i], right_widths[i], left=centers[i],
                height=0.6, color=c, alpha=0.85)
        # 在柱端标注值
        ax.text(bottoms[i] - 0.3, y_pos[i], f'{bottoms[i]:.1f}',
                va='center', ha='right', fontsize=9)
        ax.text(tops[i] + 0.3, y_pos[i], f'{tops[i]:.1f}',
                va='center', ha='left', fontsize=9)

    ax.axvline(base_overall, color='red', linestyle='--', alpha=0.7, linewidth=1.2,
               label=f'基准综合分={base_overall:.1f}')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=11)
    ax.set_xlabel('综合评分', fontsize=11)
    ax.set_title(f'问题1：权重扰动敏感性分析（龙卷风图 ±{int(perturb_range*100)}%）',
                 fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    ax.legend(loc='lower right')

    # 在图右上角加排名
    rank_text = '\n'.join([f'{i+1}. {lbl} (极差={r:.2f})'
                            for i, (lbl, r) in enumerate(zip(labels[::-1], ranges[::-1]))])
    ax.text(0.98, 0.97, '敏感性排名（极差）:\n' + rank_text,
            transform=ax.transAxes, fontsize=9, va='top', ha='right',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))

    fig.tight_layout()
    save_fig(fig, 'q1_tornado', subdir='results')
    plt.close(fig)

    # 额外的"敏感性曲线图"
    plt = apply_style()
    fig, ax = plt.subplots(figsize=(11, 6))
    for i, dim in enumerate(scores):
        sub = df[(df['维度'] == dim) & (~df['扰动'].astype(str).str.contains('极差'))]
        ax.plot(sub['扰动'] * 100, sub['综合评分'], marker='o',
                label=dim, color=colors[i], linewidth=2)
    ax.axhline(base_overall, color='red', linestyle='--', alpha=0.5,
               label=f'基准分={base_overall:.1f}')
    ax.axvline(0, color='gray', linestyle=':', alpha=0.3)
    ax.set_xlabel('权重扰动 (%)', fontsize=11)
    ax.set_ylabel('综合评分', fontsize=11)
    ax.set_title('问题1：权重扰动敏感性曲线', fontsize=13, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_fig(fig, 'q1_sensitivity_curves', subdir='results')
    plt.close(fig)

    print('\n=== 敏感性分析完成 ===', flush=True)
    return summary_df


if __name__ == '__main__':
    run_sensitivity()
