# -*- coding: utf-8 -*-
"""
Q3 · B6: §5.3.5 敏感性重构（删 r_reg 扰动 + 加 click/browse 权重三档）
========================================================================
**原 §5.3.5**：3 比值 × ±30% 扰动 = 15 场景（含 r_reg，**代理失效**）
**重构后**：
  - 删 r_reg 扰动（代理失效，扰动无意义）
  - 保留 r_click / r_browse ±30% 扰动 = 10 场景
  - 新增 click/browse 权重 3 档（objective 函数权重，非代理比值）：
    * (1.0, 0.0) - 纯 click 目标
    * (0.7, 0.3) - click 主导
    * (0.3, 0.7) - browse 主导

**输出**：
  results/tables/q3_sensitivity_v2.csv
  results/tables/q3_sensitivity_v2_summary.json
  results/figures/q3_sensitivity_v2.png
"""
import os, sys, json
import pandas as pd
import numpy as np
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

# 灵敏度参数
RATIO_PCTS = [-0.30, -0.15, 0.0, 0.15, 0.30]
RATIO_METRICS = ['r_click', 'r_browse']  # 删除 r_reg（代理失效）
WEIGHT_SCENARIOS = [
    {'name': 'W=(1.0,0.0)', 'w_click': 1.0, 'w_browse': 0.0},
    {'name': 'W=(0.7,0.3)', 'w_click': 0.7, 'w_browse': 0.3},
    {'name': 'W=(0.3,0.7)', 'w_click': 0.3, 'w_browse': 0.7},
]


def ratio_sensitivity(plan, proxy):
    """代理比值 ±30% 扰动（删 r_reg）"""
    rows = []
    plan_merged = plan.merge(
        proxy[['unit_id', 'r_click', 'r_browse', 'r_reg', 'r_topimp']],
        on='unit_id', how='left'
    )
    for metric in RATIO_METRICS:
        for pct in RATIO_PCTS:
            plan_s = plan_merged.copy()
            plan_s[metric] = plan_s[metric] * (1 + pct)
            plan_s['click_s'] = plan_s['cost'] * plan_s['r_click']
            plan_s['browse_s'] = plan_s['click_s'] * 2.93
            plan_s['reg_s'] = plan_s['cost'] * plan_s['r_reg']  # reg 不变（不参与灵敏度）
            plan_s['top_imp_s'] = plan_s['cost'] * plan_s['r_topimp']
            rows.append({
                'scenario_type': 'ratio_pct',
                'metric': metric,
                'pct': pct,
                'label': f'{metric}_pct={pct:+.0%}',
                'total_cost': plan_s['cost'].sum(),
                'total_clicks': plan_s['click_s'].sum(),
                'total_browses': plan_s['browse_s'].sum(),
                'total_regs': plan_s['reg_s'].sum(),
                'total_top_imp': plan_s['top_imp_s'].sum(),
            })
    return pd.DataFrame(rows)


def weight_sensitivity(plan, proxy):
    """目标函数权重敏感性（重新求解 MILP）"""
    import pulp

    rows = []
    for scen in WEIGHT_SCENARIOS:
        print(f'\n  --- 权重 {scen["name"]} ---')
        prob = pulp.LpProblem(f'Q3_sens_{scen["name"]}', pulp.LpMaximize)

        candidates = [(row['keyword_id'], row['unit_id'], row['date'], row['cost'])
                      for _, row in plan.iterrows() if row['cost'] > 0.01]
        # 重新构建决策变量
        x = pulp.LpVariable.dicts('x', range(len(candidates)), lowBound=0, cat='Continuous')

        # 代理收益系数
        proxy_dict = proxy.set_index('unit_id')[['r_click', 'r_browse', 'r_reg', 'r_topimp']].to_dict('index')

        coef = {}
        for i, (k, u, d, c) in enumerate(candidates):
            p = proxy_dict.get(u, {'r_click': 0.5, 'r_browse': 1.0, 'r_reg': 0.5, 'r_topimp': 0.27})
            # 仅 click 和 browse 权重变化（删 reg 代理）
            coef[i] = scen['w_click'] * p['r_click'] + scen['w_browse'] * p['r_browse']

        prob += pulp.lpSum(coef[i] * x[i] for i in range(len(candidates))), 'value'

        # 总预算约束
        total_budget = 51164.93
        prob += pulp.lpSum(x[i] for i in range(len(candidates))) <= total_budget, 'budget'

        # 每个候选的上限（基线 cost）
        for i, (k, u, d, c) in enumerate(candidates):
            prob += x[i] <= c, f'cap_{i}'

        solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=60)
        status = prob.solve(solver)

        # 计算结果
        total_cost = sum(x[i].value() or 0 for i in range(len(candidates)))
        total_clicks = 0
        total_browses = 0
        total_regs = 0
        for i, (k, u, d, c) in enumerate(candidates):
            xv = x[i].value() or 0
            p = proxy_dict.get(u, {'r_click': 0.5, 'r_browse': 1.0, 'r_reg': 0.5, 'r_topimp': 0.27})
            total_clicks += xv * p['r_click']
            total_browses += xv * p['r_click'] * 2.93
            total_regs += xv * p['r_reg']

        rows.append({
            'scenario_type': 'weight',
            'metric': 'objective_weights',
            'pct': 0,
            'label': scen['name'],
            'w_click': scen['w_click'],
            'w_browse': scen['w_browse'],
            'total_cost': total_cost,
            'total_clicks': total_clicks,
            'total_browses': total_browses,
            'total_regs': total_regs,
            'total_top_imp': sum((x[i].value() or 0) * proxy_dict.get(c[1], {}).get('r_topimp', 0.27)
                                  for i, c in enumerate(candidates)),
        })
    return pd.DataFrame(rows)


def plot_sensitivity(df):
    """2 子图：ratio_pct（左）+ weight（右）"""
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 左：ratio_pct 曲线
    ratio_df = df[df['scenario_type'] == 'ratio_pct'].copy()
    ratio_df['pct_pct'] = (ratio_df['pct'] * 100).astype(int)
    ax = axes[0]
    for m in ratio_df['metric'].unique():
        sub = ratio_df[ratio_df['metric'] == m].sort_values('pct_pct')
        ax.plot(sub['pct_pct'], sub['total_clicks'] / sub['total_clicks'].max() * 100,
                marker='o', label=m)
    ax.set_xlabel('代理比值扰动 (%)')
    ax.set_ylabel('归一化点击量 (% of max)')
    ax.set_title('代理比值敏感性（已删 r_reg）')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.axhline(100, color='gray', linestyle=':', alpha=0.5)

    # 右：weight 柱状
    weight_df = df[df['scenario_type'] == 'weight'].copy()
    ax = axes[1]
    x_pos = np.arange(len(weight_df))
    width = 0.35
    ax.bar(x_pos - width/2, weight_df['total_clicks'], width, label='total_clicks', color='#2E86AB')
    ax.bar(x_pos + width/2, weight_df['total_browses'], width, label='total_browses', color='#A23B72')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(weight_df['label'], rotation=15)
    ax.set_ylabel('量级')
    ax.set_title('目标函数权重 3 档对比（click/browse 仅）')
    ax.legend()
    ax.grid(alpha=0.3, axis='y')

    plt.suptitle('Q3 · 敏感性分析 v2（删 r_reg + 权重 3 档）', fontsize=12)
    plt.tight_layout()
    out_path = os.path.join(FIG_DIR, 'q3_sensitivity_v2.png')
    plt.savefig(out_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'  -> {out_path}')


def main():
    print('=' * 70)
    print('Q3 · B6: §5.3.5 敏感性重构')
    print('=' * 70)

    proxy = pd.read_pickle(os.path.join(PROC_Q3, 'q3_proxy_ratios.pkl'))
    plan = pd.read_pickle(os.path.join(PROC_Q3, 'q3_optimal_plan.pkl'))
    print(f'\n[输入] 代理 {proxy.shape[0]} 单元 | plan {plan.shape[0]} 行')

    # ---- Part 1: 代理比值扰动（删 r_reg）----
    print('\n[Part 1] 代理比值扰动（删 r_reg 后 2 比值 × 5 档 = 10 场景）')
    ratio_df = ratio_sensitivity(plan, proxy)
    print(f'  生成 {len(ratio_df)} 场景')

    # ---- Part 2: 目标函数权重 3 档 ----
    print('\n[Part 2] 目标函数权重 3 档（重新跑 MILP）')
    weight_df = weight_sensitivity(plan, proxy)
    print(f'  生成 {len(weight_df)} 场景')

    # ---- 合并 + 保存 ----
    print('\n[合并 + 保存]')
    df = pd.concat([ratio_df, weight_df], ignore_index=True)
    out_csv = os.path.join(TABLES_DIR, 'q3_sensitivity_v2.csv')
    df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'  -> {out_csv} | {len(df)} 场景')

    summary = {
        'method': '代理比值扰动（r_click/r_browse，删 r_reg） + 目标函数权重 3 档',
        'n_ratio_scenarios': int(len(ratio_df)),
        'n_weight_scenarios': int(len(weight_df)),
        'ratio_metrics': RATIO_METRICS,
        'ratio_pcts': RATIO_PCTS,
        'weight_scenarios': [s['name'] for s in WEIGHT_SCENARIOS],
        'improvement_vs_v1': '删 r_reg 扰动（代理失效无意义）+ 引入 click/browse 权重敏感性',
        'weight_scenarios_summary': {
            s['name']: {
                'total_cost': round(float(weight_df[weight_df['label'] == s['name']]['total_cost'].iloc[0]), 2),
                'total_clicks': round(float(weight_df[weight_df['label'] == s['name']]['total_clicks'].iloc[0]), 0),
                'total_browses': round(float(weight_df[weight_df['label'] == s['name']]['total_browses'].iloc[0]), 0),
                'total_regs': round(float(weight_df[weight_df['label'] == s['name']]['total_regs'].iloc[0]), 0),
            } for s in WEIGHT_SCENARIOS
        }
    }
    summary_path = os.path.join(TABLES_DIR, 'q3_sensitivity_v2_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f'  -> {summary_path}')

    print('\n  权重 3 档对比：')
    for s in WEIGHT_SCENARIOS:
        sub = weight_df[weight_df['label'] == s['name']].iloc[0]
        print(f'    {s["name"]}: 投入 {sub["total_cost"]:.0f}, '
              f'点击 {sub["total_clicks"]:.0f}, 浏览 {sub["total_browses"]:.0f}')

    # ---- 图表 ----
    print('\n[图表] 敏感性 v2 图')
    plot_sensitivity(df)

    print('\n' + '=' * 70)
    print('[OK] B6 完成')
    print('=' * 70)


if __name__ == '__main__':
    main()
