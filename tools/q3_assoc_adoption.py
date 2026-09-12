# -*- coding: utf-8 -*-
"""
Q3 · A4: 关联规则应用率量化
========================================================================
**目标**：评估 §5.3.3 约束 5（"若关键词 a 与 c 关联(lift≥阈值)，则同期激活同步"）的实际效果

**方法**：
  1) 加载 q3_keyword_assoc_rules.csv（cosine 50 + fp_growth 50）
  2) 加载 q3_optimal_plan.pkl（MILP 解）
  3) 对每个 (date, unit)：
     - 收集该日该单元激活的关键词集合 K_day_unit
     - 检查每条关联规则 (a, c) 是否在 K_day_unit 中双方都出现
     - 统计"应用规则数 / 总规则数"
  4) 输出：
     - 总应用率（按规则、按日期、按单元三种口径）
     - 高相似度规则（lift ≥ 0.7）的应用率
     - 关联网络图（叠加 MILP 解：激活词高亮）

**输出**：
  results/tables/q3_assoc_adoption.csv
  results/figures/q3_assoc_network_with_solution.png
  results/tables/q3_assoc_adoption_summary.json
"""
import os, sys, json
import pandas as pd
import numpy as np
import pickle
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import PROCESSED_DIR, RESULTS_DIR, TABLES_DIR, FIGURES_DIR, ensure_dir  # noqa

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.plot_style import apply_style

PROC_Q3 = os.path.join(PROCESSED_DIR, 'q3')
TBL_DIR = TABLES_DIR
FIG_DIR = FIGURES_DIR

LIFT_THRESHOLD_HIGH = 0.7


def load_artifacts():
    plan = pd.read_pickle(os.path.join(PROC_Q3, 'q3_optimal_plan.pkl'))
    rules = pd.read_csv(os.path.join(TABLES_DIR, 'q3_keyword_assoc_rules.csv'))
    # 强制 numeric
    rules['antecedents'] = pd.to_numeric(rules['antecedents'], errors='coerce')
    rules['consequents'] = pd.to_numeric(rules['consequents'], errors='coerce')
    rules = rules.dropna(subset=['antecedents', 'consequents'])
    rules['antecedents'] = rules['antecedents'].astype(int)
    rules['consequents'] = rules['consequents'].astype(int)
    return plan, rules


def compute_adoption(plan, rules):
    """逐规则、逐日期、逐单元计算应用率"""
    rows = []
    grouped = plan.groupby(['date', 'unit_id']).agg(
        keywords=('keyword_id', lambda x: set(x.tolist())),
        cost=('cost', 'sum'),
    ).reset_index()

    high_rules = rules[rules['lift'] >= LIFT_THRESHOLD_HIGH]

    per_unit_date = []
    for _, r in grouped.iterrows():
        d, u, K = r['date'], r['unit_id'], r['keywords']
        if len(K) < 2:
            adopted = 0
            adopted_high = 0
            total = len(rules)
            total_high = len(high_rules)
        else:
            # 计算同时出现在 K 中的规则数
            def _count(rule_df):
                cnt = 0
                for _, rr in rule_df.iterrows():
                    if rr['antecedents'] in K and rr['consequents'] in K:
                        cnt += 1
                return cnt
            adopted = _count(rules)
            adopted_high = _count(high_rules)
            total = len(rules)
            total_high = len(high_rules)
        per_unit_date.append({
            'date': d, 'unit_id': u, 'n_keywords': len(K),
            'cost': r['cost'],
            'adopted_all': adopted, 'total_all': total,
            'adopted_high': adopted_high, 'total_high': total_high,
            'adoption_rate_all': round(adopted / total, 4) if total > 0 else 0,
            'adoption_rate_high': round(adopted_high / total_high, 4) if total_high > 0 else 0,
        })

    df = pd.DataFrame(per_unit_date)
    return df


def plot_network_with_solution(rules, plan, out_path, top_edges=50):
    """关联网络图：激活词高亮（红），未激活词（蓝）"""
    import networkx as nx
    apply_style()
    G = nx.Graph()
    activated_kws = set(plan['keyword_id'].astype(int).tolist())
    top = rules.head(top_edges)
    for _, r in top.iterrows():
        a = int(r['antecedents']); b = int(r['consequents'])
        G.add_edge(a, b, weight=float(r['lift']), metric=r.get('metric', 'cosine'))

    fig, ax = plt.subplots(figsize=(14, 10))
    pos = nx.spring_layout(G, k=0.5, seed=42)
    # 节点颜色：激活=red, 未激活=lightblue
    node_colors = ['#E63946' if n in activated_kws else '#A8DADC' for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_size=180, node_color=node_colors, ax=ax,
                           edgecolors='black', linewidths=0.5)
    nx.draw_networkx_edges(G, pos,
                           width=[d['weight'] * 1.5 for _, _, d in G.edges(data=True)],
                           alpha=0.5, edge_color='gray', ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=7, ax=ax)
    ax.set_title(f'Q3 关联网络（MILP 激活词标红，共 {len(activated_kws)} 词激活）', fontsize=12)
    ax.axis('off')
    # 图例
    from matplotlib.patches import Patch
    legend_elems = [
        Patch(facecolor='#E63946', label=f'激活词 ({len([n for n in G.nodes() if n in activated_kws])})'),
        Patch(facecolor='#A8DADC', label=f'未激活词 ({len([n for n in G.nodes() if n not in activated_kws])})'),
    ]
    ax.legend(handles=legend_elems, loc='upper right')
    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'  -> {out_path}')


def main():
    print('=' * 70)
    print('Q3 · A4: 关联规则应用率量化')
    print('=' * 70)

    plan, rules = load_artifacts()
    print(f'\n[输入] MILP 解 {plan.shape[0]} 行（16 天 × ~5 单元）')
    print(f'  关联规则 {rules.shape[0]} 条（cosine 50 + fp_growth 50）')
    print(f'  激活关键词 {plan["keyword_id"].nunique()} 个')
    n_rules_kws = len(np.unique(rules[['antecedents','consequents']].values.flatten()))
    print(f'  规则涉及关键词 {n_rules_kws} 个')

    # ---- 应用率计算 ----
    print('\n[计算] 应用率（按 (date, unit) 维度）')
    adopt_df = compute_adoption(plan, rules)
    print(adopt_df.head(10).to_string(index=False))

    # ---- 保存产物 ----
    print('\n[保存] 应用率 CSV')
    out_csv = os.path.join(TABLES_DIR, 'q3_assoc_adoption.csv')
    adopt_df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'  -> {out_csv}')

    # ---- 汇总统计 ----
    summary = {
        'method': 'cosine + fp_growth 关联规则在 MILP 解中的同日同单元共现率',
        'lift_threshold_high': LIFT_THRESHOLD_HIGH,
        'n_milp_rows': int(plan.shape[0]),
        'n_activated_keywords': int(plan['keyword_id'].nunique()),
        'n_rules_total': int(len(rules)),
        'n_rules_high_confidence': int(len(rules[rules['lift'] >= LIFT_THRESHOLD_HIGH])),
        'adoption_rate_summary': {
            'mean_all': round(float(adopt_df['adoption_rate_all'].mean()), 4),
            'median_all': round(float(adopt_df['adoption_rate_all'].median()), 4),
            'mean_high': round(float(adopt_df['adoption_rate_high'].mean()), 4),
            'median_high': round(float(adopt_df['adoption_rate_high'].median()), 4),
            'max_all': round(float(adopt_df['adoption_rate_all'].max()), 4),
            'max_high': round(float(adopt_df['adoption_rate_high'].max()), 4),
        },
        'interpretation': (
            '应用率 < 0.05 表明关联规则对 MILP 决策影响极小（关联挖掘主要作为辅助信息）；'
            '应用率 ≥ 0.10 表明约束 5 实际触发了同期同单元的关键词共激活。'
        )
    }
    summary_path = os.path.join(TABLES_DIR, 'q3_assoc_adoption_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f'  -> {summary_path}')
    print(f'  应用率（全部）mean={summary["adoption_rate_summary"]["mean_all"]:.4f} '
          f'| median={summary["adoption_rate_summary"]["median_all"]:.4f}')
    print(f'  应用率（高置信）mean={summary["adoption_rate_summary"]["mean_high"]:.4f} '
          f'| median={summary["adoption_rate_summary"]["median_high"]:.4f}')

    # ---- 网络图（叠加解）----
    print('\n[图表] 关联网络图（叠加 MILP 激活词）')
    plot_network_with_solution(rules, plan, os.path.join(FIG_DIR, 'q3_assoc_network_with_solution.png'))

    print('\n' + '=' * 70)
    print('✅ A4 完成')
    print('=' * 70)


if __name__ == '__main__':
    main()
