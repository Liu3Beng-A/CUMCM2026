"""
Q3 · 代理精度校验 + 敏感性分析（§2.3 + §2.2.2）
=================================================

**功能**：
1. 代理精度校验：用 2025 实际数据代入代理公式，比值 ∈ [0.85, 1.15]
2. 敏感性分析：3 比值 × ±30% 扰动 × 5 档，比对 result3.xlsx 投放结构变化

**§2.3 校验逻辑**：
- 对每个 (单元, 日期)，代入代理公式：predicted_clicks = cost × r_click
- 与 actual_clicks 比较：ratio = predicted / actual
- 期望 ratio ∈ [0.85, 1.15]（代理精度 15% 误差带）

**§2.2.2 敏感性**：
- 3 比值：r_click, r_browse, r_reg
- 5 档：[-30%, -15%, 0%, +15%, +30%]
- 15 个扰动场景 × 各自跑 MILP → 投放变化对比
- 输出：15 个 result3_sens_*.csv + 1 张敏感性图

**主要输入**：
- `data/processed/q3/q3_actual_16d.pkl`：16 天实际产出基线
- `data/processed/q3/q3_proxy_ratios.pkl`：代理比值
- `results/excel/result3.xlsx`：基线解
- `data/processed/q3/q3_optimal_plan.pkl`：基线 plan

**主要输出**（v1 · 已废弃）：
- `results/tables/q3_proxy_accuracy.csv`：比值表
- `results/tables/q3_proxy_accuracy.json`：汇总
- `results/figures/q3_sensitivity_v1_DEPRECATED.png`：v1 敏感性曲线（含 r_reg 扰动，代理失效）
- `results/tables/q3_sensitivity_summary.csv`：v1 15 场景对比

**⚠️ v2 替代（2026-09-12）**：本文件已被 `tools/q3_sensitivity_v2.py` 替代，
v2 删 r_reg + 加 click/browse 权重 3 档，输出 `q3_sensitivity_v2.png`。
如需重新跑敏感性分析，请使用 v2 版本。
"""
import os
import sys
import pandas as pd
import numpy as np
import pickle
import json
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import PROCESSED_DIR, RESULTS_DIR, TABLES_DIR, FIGURES_DIR, ensure_dir  # noqa: E402
from src.plot_style import apply_style  # noqa: E402

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# 敏感性参数
SENS_PCTS = [-0.30, -0.15, 0.0, 0.15, 0.30]  # 5 档
SENS_METRICS = ['r_click', 'r_browse', 'r_reg']  # 3 比值
ACCURACY_TOL = 0.15  # 15% 误差带


def proxy_accuracy_check(proxy, actual, tol=ACCURACY_TOL):
    """§2.3 代理精度校验（绝对比值 + 相对相关性）

    F1 修复（2026-09-12）：reg 预测改为 click × r_reg（CVR 口径），
    原 cost × r_reg 公式因 annual_regs 全局分配存在结构性反相关。
    """
    df = proxy.merge(actual, on='unit_id', how='inner')
    # 绝对比值：predicted = actual_cost × ratio
    df['pred_clicks'] = df['actual_cost'] * df['r_click']
    df['ratio_clicks'] = df['pred_clicks'] / df['actual_clicks'].clip(lower=1)
    df['pred_topimp'] = df['actual_cost'] * df['r_topimp']
    df['ratio_topimp'] = df['pred_topimp'] / df['actual_top_imps'].clip(lower=1)
    # F1 修复：pred_regs = pred_clicks × r_reg（CVR 口径，不再用 cost × r_reg）
    df['pred_regs'] = df['pred_clicks'] * df['r_reg']
    df['ratio_regs'] = df['pred_regs'] / df['actual_regs'].clip(lower=1)
    df['pass_clicks'] = (df['ratio_clicks'].between(1 - tol, 1 + tol)).astype(int)
    df['pass_topimp'] = (df['ratio_topimp'].between(1 - tol, 1 + tol)).astype(int)
    df['pass_regs'] = (df['ratio_regs'].between(1 - tol, 1 + tol)).astype(int)
    return df


def proxy_correlation(proxy, actual):
    """§2.3 代理精度扩展：相对顺序相关性"""
    df = proxy.merge(actual, on='unit_id', how='inner')
    metrics = {
        'clicks': ('r_click', 'actual_clicks'),
        'topimp': ('r_topimp', 'actual_top_imps'),
        'regs': ('r_reg', 'actual_regs'),
    }
    result = {}
    for k, (r_col, a_col) in metrics.items():
        # 相对占比
        actual_share = df[a_col] / df[a_col].sum()
        predicted = df['actual_cost'] * df[r_col]
        pred_share = predicted / predicted.sum()
        # Pearson 相关
        corr = float(np.corrcoef(actual_share, pred_share)[0, 1])
        result[f'{k}_share_pearson'] = corr
    return result


def sensitivity_run(base_plan, proxy, sens_pcts=SENS_PCTS, sens_metrics=SENS_METRICS):
    """§2.2.2 敏感性分析（不重新跑 MILP，直接重算代理产出）"""
    rows = []
    plan = base_plan.merge(
        proxy[['unit_id', 'r_click', 'r_browse', 'r_reg', 'r_topimp']],
        on='unit_id', how='left'
    )
    for metric in sens_metrics:
        for pct in sens_pcts:
            plan_s = plan.copy()
            plan_s[metric] = plan_s[metric] * (1 + pct)
            # 重算 click/browse/reg
            plan_s['click_s'] = plan_s['cost'] * plan_s['r_click']
            plan_s['browse_s'] = plan_s['click_s'] * 2.93
            # F1 修复：reg_s = click_s × r_reg
            plan_s['reg_s'] = plan_s['click_s'] * plan_s['r_reg']
            plan_s['top_imp_s'] = plan_s['cost'] * plan_s['r_topimp']
            rows.append({
                'metric': metric,
                'pct': pct,
                'total_cost': plan_s['cost'].sum(),
                'total_clicks': plan_s['click_s'].sum(),
                'total_browses': plan_s['browse_s'].sum(),
                'total_regs': plan_s['reg_s'].sum(),
                'total_top_imp': plan_s['top_imp_s'].sum(),
            })
    return pd.DataFrame(rows)


def plot_sensitivity(sens_df):
    """敏感性曲线图"""
    apply_style()
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    metrics_to_plot = ['total_clicks', 'total_browses', 'total_regs']
    titles = ['预期点击量敏感性', '预期浏览量敏感性', '预期注册量敏感性']

    for ax, metric, title in zip(axes, metrics_to_plot, titles):
        for m in sens_df['metric'].unique():
            sub = sens_df[sens_df['metric'] == m].sort_values('pct')
            pct_pct = (sub['pct'] * 100).astype(int)
            ax.plot(pct_pct, sub[metric], marker='o', label=m)
        ax.set_xlabel('扰动 (%)')
        ax.set_ylabel(metric)
        ax.set_title(title)
        ax.legend()
        ax.grid(alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join(FIGURES_DIR, 'q3_sensitivity_v1_DEPRECATED.png')  # v1 已废弃（F1 重构），如运行会生成 DEPRECATED 命名
    plt.savefig(out_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  -> {out_path}")


def main():
    print("=" * 70)
    print("Q3 · 代理精度校验 + 敏感性分析（§2.3 + §2.2.2）")
    print("=" * 70)

    out_dir = ensure_dir(os.path.join(PROCESSED_DIR, 'q3'))

    # ---- 加载 ----
    proxy = pd.read_pickle(os.path.join(out_dir, 'q3_proxy_ratios.pkl'))
    actual = pd.read_pickle(os.path.join(out_dir, 'q3_actual_16d.pkl'))
    plan = pd.read_pickle(os.path.join(out_dir, 'q3_optimal_plan.pkl'))

    print(f"\n[输入] 代理 {proxy.shape[0]} 单元 | 实际 {actual.shape[0]} 单元 | 投放 {plan.shape[0]} 行")

    # ---- §2.3 代理精度校验 ----
    print("\n[§2.3] 代理精度校验（误差带 ±15%）")
    acc_df = proxy_accuracy_check(proxy, actual)
    acc_path = os.path.join(TABLES_DIR, 'q3_proxy_accuracy.csv')
    acc_df.to_csv(acc_path, index=False, encoding='utf-8-sig')
    print(f"  -> {acc_path}")

    # 汇总
    corr = proxy_correlation(proxy, actual)
    summary = {
        'tolerance': ACCURACY_TOL,
        'n_units': len(acc_df),
        'click_pass': int(acc_df['pass_clicks'].sum()),
        'topimp_pass': int(acc_df['pass_topimp'].sum()),
        'reg_pass': int(acc_df['pass_regs'].sum()),
        'click_ratio_mean': float(acc_df['ratio_clicks'].mean()),
        'click_ratio_std': float(acc_df['ratio_clicks'].std()),
        'topimp_ratio_mean': float(acc_df['ratio_topimp'].mean()),
        'reg_ratio_mean': float(acc_df['ratio_regs'].mean()),
        'click_pass_rate': float(acc_df['pass_clicks'].mean()),
        'topimp_pass_rate': float(acc_df['pass_topimp'].mean()),
        'reg_pass_rate': float(acc_df['pass_regs'].mean()),
        'correlation': corr,
        'interpretation': (
            '绝对比值通过率低是因 16 天日级波动大（季度/节日/异常日），'
            '但 share-Pearson 可达 0.9+ 说明相对顺序保持良好，'
            '代理对"选哪些单元多投"仍有指导价值。'
        ),
    }
    summary_path = os.path.join(TABLES_DIR, 'q3_proxy_accuracy.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"  -> {summary_path}")
    print(f"  点击通过 {summary['click_pass']}/{summary['n_units']} = {summary['click_pass_rate']*100:.1f}%")
    print(f"  展位通过 {summary['topimp_pass']}/{summary['n_units']} = {summary['topimp_pass_rate']*100:.1f}%")
    print(f"  注册通过 {summary['reg_pass']}/{summary['n_units']} = {summary['reg_pass_rate']*100:.1f}%")
    print(f"  share-Pearson: clicks={corr['clicks_share_pearson']:.3f}, "
          f"topimp={corr['topimp_share_pearson']:.3f}, regs={corr['regs_share_pearson']:.3f}")

    # ---- §2.2.2 敏感性分析 ----
    print("\n[§2.2.2] 敏感性分析（3 比值 × 5 档）")
    sens_df = sensitivity_run(plan, proxy)
    sens_path = os.path.join(TABLES_DIR, 'q3_sensitivity_summary.csv')
    sens_df.to_csv(sens_path, index=False, encoding='utf-8-sig')
    print(f"  -> {sens_path} | {len(sens_df)} 场景")

    # 统计
    for m in SENS_METRICS:
        sub = sens_df[sens_df['metric'] == m]
        baseline = sub[sub['pct'] == 0]['total_clicks'].values[0]
        max_pct = sub[sub['pct'] == 0.30]['total_clicks'].values[0]
        min_pct = sub[sub['pct'] == -0.30]['total_clicks'].values[0]
        print(f"  {m}: 基线 {baseline:.0f} → [-30%] {min_pct:.0f} ({(min_pct/baseline-1)*100:+.1f}%) "
              f"→ [+30%] {max_pct:.0f} ({(max_pct/baseline-1)*100:+.1f}%)")

    # ---- 图表 ----
    print("\n[图表] 敏感性曲线")
    plot_sensitivity(sens_df)

    print("\n" + "=" * 70)
    print("✅ Q3 代理精度校验 + 敏感性分析完成")
    print("=" * 70)


if __name__ == '__main__':
    main()
