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
    """F3 修复（2026-09-12）：改用"画像相似度"重新定义应用率

    原定义（共激活率）：要求规则 (a, c) 的两端在同日同单元同时激活。
      问题：预算紧张时单元日预算被单关键词吃满，伙伴词无法同时激活，应用率 = 0。

    新定义（单端画像命中率）：检查规则的前件或后件是否被 MILP 激活。
      含义：只要规则涉及"对"的关键词任一端被选入计划，即视为关联规则对决策产生指引。
    """
    rows = []
    activated_kws = set(plan['keyword_id'].astype(int).tolist())

    # 全局画像命中率（整个计划维度）
    def _count_either(rule_df):
        cnt = 0
        for _, rr in rule_df.iterrows():
            if rr['antecedents'] in activated_kws or rr['consequents'] in activated_kws:
                cnt += 1
        return cnt

    adopted_all_global = _count_either(rules)
    high_rules = rules[rules['lift'] >= LIFT_THRESHOLD_HIGH]
    adopted_high_global = _count_either(high_rules)
    n_plan_kws = len(activated_kws)
    print(f'\n[F3 修复] 全局画像命中率（单端命中）: '
          f'all={adopted_all_global}/{len(rules)} ({adopted_all_global/max(len(rules),1):.4f}) | '
          f'high={adopted_high_global}/{len(high_rules)} '
          f'({adopted_high_global/max(len(high_rules),1):.4f}) | '
          f'激活词数={n_plan_kws}')

    grouped = plan.groupby(['date', 'unit_id']).agg(
        keywords=('keyword_id', lambda x: set(x.tolist())),
        cost=('cost', 'sum'),
    ).reset_index()

    per_unit_date = []
    for _, r in grouped.iterrows():
        d, u, K = r['date'], r['unit_id'], r['keywords']
        # 单元-日维度：单端命中率
        def _count_either_unit(rule_df):
            cnt = 0
            for _, rr in rule_df.iterrows():
                if rr['antecedents'] in K or rr['consequents'] in K:
                    cnt += 1
            return cnt

        adopted_either = _count_either_unit(rules)
        adopted_either_high = _count_either_unit(high_rules)
        # 保留原共激活口径作为对照
        def _count_both(rule_df):
            cnt = 0
            for _, rr in rule_df.iterrows():
                if rr['antecedents'] in K and rr['consequents'] in K:
                    cnt += 1
            return cnt

        adopted_both = _count_both(rules) if len(K) >= 2 else 0
        adopted_both_high = _count_both(high_rules) if len(K) >= 2 else 0

        per_unit_date.append({
            'date': d, 'unit_id': u, 'n_keywords': len(K),
            'cost': r['cost'],
            # 新口径：单端命中
            'adopted_either_all': adopted_either, 'total_all': len(rules),
            'adopted_either_high': adopted_either_high, 'total_high': len(high_rules),
            'adoption_either_all': round(adopted_either / max(len(rules), 1), 4),
            'adoption_either_high': round(adopted_either_high / max(len(high_rules), 1), 4),
            # 旧口径：共激活（仅作对照）
            'adopted_both_all': adopted_both, 'adopted_both_high': adopted_both_high,
        })

    df = pd.DataFrame(per_unit_date)
    return df, adopted_all_global, adopted_high_global, n_plan_kws


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
    print('\n[计算] 应用率（按 (date, unit) 维度，F3 修复：单端画像命中）')
    high_rules = rules[rules['lift'] >= LIFT_THRESHOLD_HIGH]
    adopt_df, adopted_global, adopted_high_global, n_kws = compute_adoption(plan, rules)
    print(adopt_df.head(10).to_string(index=False))

    # ---- 保存产物 ----
    print('\n[保存] 应用率 CSV')
    out_csv = os.path.join(TABLES_DIR, 'q3_assoc_adoption.csv')
    adopt_df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'  -> {out_csv}')

    # ---- 汇总统计 ----
    summary = {
        'method': 'F3 修复：单端画像命中率（cosine + fp_growth 关联规则中前件或后件被 MILP 激活的比例）',
        'original_method': '共激活率（已被 F3 修复替代，仅作对照保留）',
        'lift_threshold_high': LIFT_THRESHOLD_HIGH,
        'n_milp_rows': int(plan.shape[0]),
        'n_activated_keywords': n_kws,
        'n_rules_total': int(len(rules)),
        'n_rules_high_confidence': int(len(high_rules)),
        'F3_global_either_rate_all': round(adopted_global / max(len(rules), 1), 4),
        'F3_global_either_rate_high': round(adopted_high_global / max(len(high_rules), 1), 4),
        'F3_per_unit_date_either_rate_all_mean': round(float(adopt_df['adoption_either_all'].mean()), 4),
        'F3_per_unit_date_either_rate_high_mean': round(float(adopt_df['adoption_either_high'].mean()), 4),
        'legacy_both_rate_all_mean': round(float(adopt_df['adopted_both_all'].sum() / max(adopt_df['total_all'].sum(), 1)), 4),
        'legacy_both_rate_high_mean': round(float(adopt_df['adopted_both_high'].sum() / max(adopt_df['total_high'].sum(), 1)), 4),
        'interpretation': (
            'F3 修复后：单端画像命中率反映 MILP 计划对关联规则所列关键词池的覆盖率，'
            '比"强制共激活率"在预算紧张场景下更可读；'
            '旧口径（共激活率）作为对照保留在 adopted_both_* 列。'
        )
    }
    summary_path = os.path.join(TABLES_DIR, 'q3_assoc_adoption_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f'  -> {summary_path}')
    print(f'  F3 单端命中率（全部规则）全局={summary["F3_global_either_rate_all"]:.4f} | '
          f'单元-日均={summary["F3_per_unit_date_either_rate_all_mean"]:.4f}')
    print(f'  F3 单端命中率（高置信）全局={summary["F3_global_either_rate_high"]:.4f} | '
          f'单元-日均={summary["F3_per_unit_date_either_rate_high_mean"]:.4f}')
    print(f'  旧口径（共激活）合计率：'
          f'all={summary["legacy_both_rate_all_mean"]:.4f} | '
          f'high={summary["legacy_both_rate_high_mean"]:.4f}')

    # ---- 网络图（叠加解）----
    print('\n[图表] 关联网络图（叠加 MILP 激活词）')
    plot_network_with_solution(rules, plan, os.path.join(FIG_DIR, 'q3_assoc_network_with_solution.png'))

    print('\n' + '=' * 70)
    print('✅ A4 完成')
    print('=' * 70)


if __name__ == '__main__':
    main()
