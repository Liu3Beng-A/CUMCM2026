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
from src.plot_style import apply_style, save_fig, COLORS


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
    colors = [COLORS['primary'], COLORS['secondary'], COLORS['accent'], COLORS['success']]
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
    ax.set_title(f'问题 1：权重扰动敏感性分析（龙卷风图 ±{int(perturb_range*100)}%）',
                 fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    ax.legend(loc='lower right')

    # 修复（2026-09-12）：显式设置 x 轴下限，给"扰动下限标签"留出 4 个字符的左边距，
    # 否则像出价策略 69.4 这样的低端值会被裁掉左半标签。
    x_min = min(bottoms) - 4
    x_max = max(max(tops), base_overall) + 4
    ax.set_xlim(x_min, x_max)

    # 在图左上角加排名（修复 2026-09-12：右上角会挡住"出价策略与预算"的右端 68.9 标签）
    rank_text = '\n'.join([f'{i+1}. {lbl} (极差={r:.2f})'
                            for i, (lbl, r) in enumerate(zip(labels[::-1], ranges[::-1]))])
    ax.text(0.02, 0.97, '敏感性排名（极差）:\n' + rank_text,
            transform=ax.transAxes, fontsize=8, va='top', ha='left',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='lightyellow',
                      edgecolor='gray', alpha=0.85))

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
    ax.set_title('问题 1：权重扰动敏感性曲线', fontsize=13, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_fig(fig, 'q1_sensitivity_curves', subdir='results')
    plt.close(fig)

    # ===== P1-4: CRITIC vs 业务权重比例敏感性 =====
    run_mix_ratio_sensitivity(scores, plan_scores, weights_res)

    print('\n=== 敏感性分析完成 ===', flush=True)
    return summary_df


def run_mix_ratio_sensitivity(scores, plan_scores, weights_res):
    """P1-4：CRITIC vs 业务 比例敏感性曲线

    检验"70:30 (CRITIC:业务)" 是否稳健：
    - α = 0.0  → 纯业务权重
    - α = 0.3  → 30%CRITIC + 70%业务（即原 70:30）
    - α = 0.5  → 50:50
    - α = 0.7  → 70%CRITIC + 30%业务（即原 30:70）
    - α = 1.0  → 纯 CRITIC

    期望：综合分标准差变化 < 30% → 证明 70:30 选择稳健。
    """
    print('\n=== P1-4: CRITIC:业务 比例敏感性 ===', flush=True)

    critic_w = weights_res['critic_weights']        # CRITIC 权重 dict
    subj_w   = weights_res['subjective_weights']   # 业务权重 dict

    dim_names = list(scores.keys())
    score_vec = np.array([scores[d] for d in dim_names])
    critic_vec = np.array([critic_w[d] for d in dim_names])
    subj_vec   = np.array([subj_w[d]   for d in dim_names])

    ratios = np.linspace(0.0, 1.0, 11)   # 0.0, 0.1, ..., 1.0
    rows = []
    plan_ids = list(plan_scores.index)
    plan_score_matrix = plan_scores.values   # 5×4

    for r in ratios:
        mixed_vec = r * critic_vec + (1 - r) * subj_vec
        mixed_vec = mixed_vec / mixed_vec.sum()

        # 整体综合分
        overall = float(np.dot(mixed_vec, score_vec))

        # 各方案综合分
        plan_overall = plan_score_matrix @ mixed_vec
        plan_overall_std = float(plan_overall.std())

        rows.append({
            'CRITIC占比 α':   round(r, 2),
            '综合评分(全公司)': round(overall, 4),
            '方案综合分标准差': round(plan_overall_std, 4),
            '方案综合分均值':   round(float(plan_overall.mean()), 4),
            '方案综合分极差':   round(float(plan_overall.max() - plan_overall.min()), 4),
        })

    sens_df = pd.DataFrame(rows)

    out_csv = os.path.join(TABLES_DIR, 'q1_mix_ratio_sensitivity.csv')
    sens_df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'[save] {out_csv}', flush=True)

    # 打印关键节点
    print('\n关键节点：', flush=True)
    for r_label, r_val in [('纯业务', 0.0), ('α=0.3 (原70:30)', 0.3), ('50:50', 0.5), ('α=0.7 (原30:70)', 0.7), ('纯CRITIC', 1.0)]:
        row = sens_df[sens_df['CRITIC占比 α'].round(2) == round(r_val, 2)]
        if len(row) > 0:
            r = row.iloc[0]
            print(f'  {r_label:15s} 综合分={r["综合评分(全公司)"]:.2f}, 方案标准差={r["方案综合分标准差"]:.2f}, 极差={r["方案综合分极差"]:.2f}', flush=True)

    # 评估稳健性
    overall_range = sens_df['综合评分(全公司)'].max() - sens_df['综合评分(全公司)'].min()
    plan_std_range = sens_df['方案综合分标准差'].max() - sens_df['方案综合分标准差'].min()
    overall_pct = overall_range / sens_df['综合评分(全公司)'].mean() * 100

    print(f'\n  综合评分极差：{overall_range:.2f} ({overall_pct:.2f}%)', flush=True)
    print(f'  方案标准差极差：{plan_std_range:.4f}', flush=True)

    if overall_pct < 5:
        verdict = '非常稳健'
    elif overall_pct < 15:
        verdict = '稳健'
    elif overall_pct < 30:
        verdict = '一般稳健'
    else:
        verdict = '不够稳健 - 建议重新审视 70:30 选择'

    print(f'  评估：70:30 选择{verdict}', flush=True)

    # ===== 绘图：综合分 vs α 曲线 =====
    plt = apply_style()
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(sens_df['CRITIC占比 α'], sens_df['综合评分(全公司)'],
            marker='o', color=COLORS['primary'], linewidth=2,
            label='综合评分 (全公司)')
    ax.axvline(0.7, color=COLORS['accent'], linestyle='--', alpha=0.7,
               label='原 α=0.7（CRITIC 主导）')
    ax.axvline(0.3, color=COLORS['danger'], linestyle='--', alpha=0.7,
               label='原 α=0.3（业务 主导）')
    ax.set_xlabel('CRITIC 占比 α', fontsize=11)
    ax.set_ylabel('综合评分（全公司）', fontsize=11)
    ax.set_title(f'问题 1：CRITIC vs 业务 比例敏感性 (P1-4)\n'
                 f'极差={overall_range:.2f} ({overall_pct:.2f}%) → {verdict}',
                 fontsize=13, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(np.arange(0, 1.01, 0.1))
    fig.tight_layout()
    save_fig(fig, 'q1_mix_ratio_curve', subdir='results')
    plt.close(fig)

    return sens_df, verdict, overall_pct


if __name__ == '__main__':
    run_sensitivity()
