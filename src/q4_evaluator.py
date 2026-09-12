"""
Q4 · Two-Stage Stochastic Programming + 生成 result4.xlsx
========================================================

**锁定决策（D-Q3Q4-024 / PoC_REPORT §2.2-§2.3）**：
- 7 天预测期：2026-09-11~17
- 同期预算上限：23,488.02 元
- 决策：第一阶段（here-and-now）选单元×关键词组合；第二阶段（wait-and-see）日级调整
- 不确定性：6 因子 × CV（历史 30 天单元级估计）

**简化（PoC）**：
- 决策粒度：单元 × 关键词 × 天 = (11 × ~75 × 7) ≈ 5,775 变量
- 目标：max E[收益] = max Σ_t Σ_u Σ_k (r_click + r_reg) × x[u,k,t] × ξ[u,t]
- 期望值 = 基础值 × (1 + N(0, CV))，独立扰动简化
- 输出 result4.xlsx：严格 9 列对齐附件 2 模板 + 6 因子期望值（隐式在 4 输出列 + 投入金额）

**主要输入**：
- `data/processed/q4/q4_same_period_2025.pkl`：同期实际
- `data/processed/q4/q4_unit_cv.pkl`：不确定性 CV
- `data/processed/q2/keyword_classified.pkl`：909 词

**主要输出**：
- `data/processed/q4/q4_optimal_plan.pkl`：最优解
- `results/excel/result4.xlsx`：严格 9 列对齐附件 2 模板
- `results/excel/q4_6metrics_extended.csv`：6 因子期望值（额外补充）
- `results/tables/q4_two_stage_summary.json`：求解状态 + 期望值
- `results/figures/q4_uncertainty_distribution.png`：6 因子 CV 分布
"""
import os
import sys
import pandas as pd
import numpy as np
import pickle
import json
import time
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import PROCESSED_DIR, RESULTS_DIR, TABLES_DIR, FIGURES_DIR, EXCEL_DIR, ensure_dir  # noqa: E402

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.plot_style import apply_style  # noqa: E402

try:
    import pulp
    HAS_PULP = True
except ImportError:
    HAS_PULP = False


# Two-Stage SP 参数
N_SCENARIOS = 20          # 场景数（PoC：20）
MAX_KEYWORDS_PER_UNIT_DATE = 25  # 强制分散
UNCERTAINTY_FACTORS = ['cpc', 'impressions', 'top_imp_pos', 'clicks', 'browses', 'regs']


def sample_scenarios(cv_df, n_scenarios=N_SCENARIOS, seed=42):
    """采样 N_SCENARIOS 个场景，每场景是 11 单元 × 6 因子 的乘子矩阵"""
    rng = np.random.RandomState(seed)
    units = sorted(cv_df['unit_id'].unique())
    scenarios = []
    for s in range(n_scenarios):
        # 6 因子乘子：对数正态分布（CV 转为 sigma）
        mults = {}
        for fac in UNCERTAINTY_FACTORS:
            cv_col = f'cv_{fac}'
            # 对数正态参数：sigma = sqrt(log(1+CV²))
            sigmas = np.log1p(cv_df.set_index('unit_id').loc[units, cv_col].values ** 2) ** 0.5
            # 乘子 = exp(N(-σ²/2, σ))
            mults[fac] = np.exp(rng.normal(-sigmas**2 / 2, sigmas))
        scenarios.append({
            'units': units,
            'mults': mults,
        })
    return scenarios


def solve_two_stage_sp(cv_df, scenarios, budget, kw_per_unit, proxy_dict):
    """Two-Stage SP 求解"""
    if not HAS_PULP:
        print("❌ PuLP 未安装")
        return None

    print(f"\n[Two-Stage SP] 场景数={len(scenarios)} | 预算={budget:.2f} 元")

    units = sorted(set(u for s in scenarios for u in s['units']))
    dates = [f"2026-09-{d:02d}" for d in range(11, 18)]  # 7 天

    # 决策变量：(unit, kw) first-stage 激活 + (unit, kw, date) second-stage 投入
    # 简化：每单元每关键词固定 7 天投入，仅调整单元×日期分配

    # 决策变量 x[unit, kw, date]
    var_keys = []
    for u in units:
        for k in kw_per_unit.get(u, []):
            for d in dates:
                var_keys.append((u, int(k), d))
    var_keys = list(set(var_keys))
    var_idx = {v: i for i, v in enumerate(var_keys)}
    n_var = len(var_keys)
    print(f"  决策变量数 = {n_var}")

    # 取代表性场景（场景 0）做确定性优化
    s0 = scenarios[0]
    prob = pulp.LpProblem('Q4_TwoStage', pulp.LpMaximize)

    x = pulp.LpVariable.dicts('x', range(n_var), lowBound=0, cat='Continuous')
    y = pulp.LpVariable.dicts('y', range(n_var), lowBound=0, upBound=1, cat='Binary')

    # kw_max_cost (big-M)
    kw_max_cost = max(kw_pool_proxy.values()) if kw_pool_proxy else 1000
    M = kw_max_cost * 1.5

    # 目标：场景 0 下最大化收益
    s0_mults = s0['mults']
    s0_units = list(s0['units'])
    coef = {}
    for u in units:
        if u in proxy_dict:
            p = proxy_dict[u]
        else:
            p = {'r_click': 0.5, 'r_browse': 1.0, 'r_reg': 0.5}
        c_base = 0.4 * p['r_click'] + 0.1 * p['r_browse'] + 0.5 * p['r_reg']
        # 场景 0 扰动（若 u 不在 s0_units 中则用 1.0）
        try:
            ui = s0_units.index(u)
            click_mult = s0_mults['clicks'][ui]
            reg_mult = s0_mults['regs'][ui]
        except ValueError:
            click_mult = reg_mult = 1.0
        coef[u] = c_base * (click_mult + reg_mult) / 2

    prob += pulp.lpSum(coef.get(v[0], 0.5) * x[i] for i, v in enumerate(var_keys)), 'value'

    # 总预算
    prob += pulp.lpSum(x[i] for i in range(n_var)) <= budget, 'budget'

    # big-M
    for i in range(n_var):
        prob += x[i] <= M * y[i], f'bigM_{i}'

    # 强制分散
    for u in units:
        ub_daily = budget / 7 / 11 * 2  # 简单均分上浮 2×
        for d in dates:
            idx_list = [var_idx[v] for v in var_keys if v[0] == u and v[2] == d]
            if not idx_list:
                continue
            prob += (
                pulp.lpSum(x[i] for i in idx_list) <= ub_daily,
                f'unit_{u}_date_{d}'
            )
            prob += (
                pulp.lpSum(y[i] for i in idx_list) <= MAX_KEYWORDS_PER_UNIT_DATE,
                f'unit_{u}_date_{d}_kws'
            )

    # 求解
    t0 = time.time()
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=60)
    status = prob.solve(solver)
    print(f"  状态 = {pulp.LpStatus[status]} | 目标 = {pulp.value(prob.objective):.2f} | "
          f"时间 = {time.time() - t0:.2f}s")

    # 提取解
    rows = []
    for i, v in enumerate(var_keys):
        cost = x[i].value()
        if cost is None or cost < 0.01:
            continue
        u, k, d = v
        # 期望值（场景平均）
        exp_clicks = np.mean([s['mults']['clicks'][s['units'].index(u)] for s in scenarios])
        exp_top = np.mean([s['mults']['top_imp_pos'][s['units'].index(u)] for s in scenarios])
        exp_browses = np.mean([s['mults']['browses'][s['units'].index(u)] for s in scenarios])
        exp_regs = np.mean([s['mults']['regs'][s['units'].index(u)] for s in scenarios])
        exp_cpc = np.mean([s['mults']['cpc'][s['units'].index(u)] for s in scenarios])
        exp_imp = np.mean([s['mults']['impressions'][s['units'].index(u)] for s in scenarios])
        # 用基线 proxy × cost × 期望乘子
        p = proxy_dict.get(u, {'r_click': 0.5, 'r_browse': 1.0, 'r_reg': 0.5, 'r_topimp': 0.27})
        click = cost * p['r_click'] * exp_clicks
        browse = click * 3.712 * exp_browses
        reg = cost * p['r_reg'] * exp_regs
        top_imp = cost * p['r_topimp'] * exp_top
        rows.append({
            'date': d, 'unit_id': u, 'keyword_id': k, 'cost': cost,
            'exp_cpc': cost * exp_cpc / max(click, 1),  # CPC = cost/clicks
            'exp_impressions': cost / max(cost * exp_cpc / max(click, 1) * exp_imp, 1) * exp_imp,
            'exp_top_imp': top_imp,
            'exp_clicks': click,
            'exp_browses': browse,
            'exp_regs': reg,
        })
    return pd.DataFrame(rows)


def plot_uncertainty_dist(cv_df):
    """6 因子 CV 分布图"""
    apply_style()
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    factors = UNCERTAINTY_FACTORS
    for ax, fac in zip(axes.flat, factors):
        cv_col = f'cv_{fac}'
        if cv_col in cv_df.columns:
            ax.hist(cv_df[cv_col], bins=10, color='#2E86AB', alpha=0.7, edgecolor='black')
            ax.axvline(cv_df[cv_col].mean(), color='red', linestyle='--',
                       label=f'mean={cv_df[cv_col].mean():.3f}')
            ax.set_title(f'CV[{fac}] 分布', fontsize=11)
            ax.set_xlabel('CV')
            ax.set_ylabel('单元数')
            ax.legend()
            ax.grid(alpha=0.3)
    plt.suptitle('Q4 · 6 因子不确定性 CV 分布（11 单元 × 历史 30 天）', fontsize=13)
    plt.tight_layout()
    out_path = os.path.join(FIGURES_DIR, 'q4_uncertainty_distribution.png')
    plt.savefig(out_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  -> {out_path}")


def main():
    print("=" * 70)
    print("Q4 · Two-Stage SP + 生成 result4.xlsx（PoC 修订）")
    print("=" * 70)

    if not HAS_PULP:
        print("❌ PuLP 未安装")
        return

    out_dir = ensure_dir(os.path.join(PROCESSED_DIR, 'q4'))
    excel_dir = ensure_dir(EXCEL_DIR)

    # ---- 加载 ----
    cv_df = pd.read_pickle(os.path.join(out_dir, 'q4_unit_cv.pkl'))
    same_period = pd.read_pickle(os.path.join(out_dir, 'q4_same_period_2025.pkl'))
    budget = pd.read_pickle(os.path.join(out_dir, 'q4_budget_ceiling.pkl'))['budget'].iloc[0]

    kw_pool = pd.read_pickle(os.path.join(PROCESSED_DIR, 'q2', 'keyword_classified.pkl'))
    # kw_pool 列名：方案ID, 推广单元ID, 成本, 点击, 浏览, ...
    kw_pool_renamed = kw_pool.rename(columns={
        '推广单元ID': 'unit_id', '成本': 'kw_cost',
        '点击': 'kw_clicks', '浏览': 'kw_browses',
    })
    kw_per_unit = kw_pool_renamed.groupby('unit_id')['关键词'].apply(set).to_dict()

    # 代理比值：用同期数据（已含 reg 分配）重算 r_reg
    same_period_ratios = same_period.groupby('unit_id').agg(
        cost=('cost', 'sum'),
        clicks=('clicks', 'sum'),
        regs=('regs', 'sum'),
        browses=('browses', 'sum'),
        top_imp=('top_imp', 'sum'),
    ).reset_index()
    same_period_ratios['r_click'] = same_period_ratios['clicks'] / same_period_ratios['cost'].clip(lower=0.01)
    same_period_ratios['r_reg'] = same_period_ratios['regs'] / same_period_ratios['cost'].clip(lower=0.01)
    same_period_ratios['r_browse'] = same_period_ratios['browses'] / same_period_ratios['cost'].clip(lower=0.01)
    same_period_ratios['r_topimp'] = same_period_ratios['top_imp'] / same_period_ratios['cost'].clip(lower=0.01)
    proxy_dict = same_period_ratios.set_index('unit_id')[
        ['r_click', 'r_browse', 'r_reg', 'r_topimp']
    ].to_dict('index')

    # 全局变量（用于 solve_two_stage_sp）
    global kw_pool_proxy
    kw_pool_proxy = kw_pool_renamed.set_index(kw_pool_renamed['关键词'].astype(int))['kw_cost'].to_dict()

    print(f"\n[输入] CV 矩阵 {cv_df.shape} | 同期 {same_period.shape[0]} 行 | "
          f"预算 {budget:.2f} 元")

    # ---- Step 1: 不确定性 CV 图 ----
    print("\n[Step 1] CV 分布图")
    plot_uncertainty_dist(cv_df)

    # ---- Step 2: 场景采样 ----
    print("\n[Step 2] 场景采样")
    scenarios = sample_scenarios(cv_df, N_SCENARIOS)
    print(f"  采样 {len(scenarios)} 场景")

    # ---- Step 3: Two-Stage SP 求解 ----
    print("\n[Step 3] Two-Stage SP 求解")
    plan_df = solve_two_stage_sp(cv_df, scenarios, budget, kw_per_unit, proxy_dict)
    if plan_df is None:
        return

    plan_df.to_pickle(os.path.join(out_dir, 'q4_optimal_plan.pkl'))
    print(f"  -> q4_optimal_plan.pkl | {len(plan_df)} 行")

    # ---- Step 4: 生成 result4.xlsx（严格 9 列对齐附件 2）----
    print("\n[Step 4] 生成 result4.xlsx（严格 9 列）")
    kw_to_plan = kw_pool.set_index(kw_pool['关键词'].astype(int))['方案ID'].astype(int).to_dict()

    result4 = pd.DataFrame({
        '日期': plan_df['date'],
        '方案ID': plan_df['keyword_id'].map(
            kw_pool_renamed.set_index(kw_pool_renamed['关键词'].astype(int))['方案ID'].astype(int).to_dict()
        ),
        '推广单元': plan_df['unit_id'],
        '关键词': plan_df['keyword_id'],
        '投入金额': plan_df['cost'].round(2),
        '预期展位': plan_df['exp_top_imp'].round(0).astype(int),
        '预期点击量': plan_df['exp_clicks'].round(0).astype(int),
        '预期浏览量': plan_df['exp_browses'].round(0).astype(int),
        '预期注册量': plan_df['exp_regs'].round(0).astype(int),
    })

    result4_path = os.path.join(excel_dir, 'result4.xlsx')
    result4.to_excel(result4_path, index=False)
    print(f"  -> {result4_path} | {len(result4)} 行")
    print(f"  列对齐附件 2: {list(result4.columns) == ['日期', '方案ID', '推广单元', '关键词', '投入金额', '预期展位', '预期点击量', '预期浏览量', '预期注册量']}")

    # ---- Step 5: 额外 q4_6metrics_extended.csv（6 因子期望值）----
    ext_cols = ['date', 'unit_id', 'keyword_id', 'cost',
                'exp_cpc', 'exp_impressions', 'exp_top_imp',
                'exp_clicks', 'exp_browses', 'exp_regs']
    ext = plan_df[ext_cols].rename(columns={
        'date': '日期', 'unit_id': '推广单元', 'keyword_id': '关键词',
        'cost': '投入金额', 'exp_cpc': '期望竞价', 'exp_impressions': '期望展现量',
        'exp_top_imp': '期望展现位', 'exp_clicks': '期望点击量',
        'exp_browses': '期望浏览量', 'exp_regs': '期望注册量',
    })
    ext_path = os.path.join(excel_dir, 'q4_6metrics_extended.csv')
    ext.to_csv(ext_path, index=False, encoding='utf-8-sig')
    print(f"  -> {ext_path} | 6 因子扩展输出")

    # ---- Step 6: 求解汇总 ----
    summary = {
        'method': 'Two-Stage Stochastic Programming (scenario 0 optimization)',
        'n_scenarios': N_SCENARIOS,
        'budget': float(budget),
        'n_units': int(cv_df.shape[0]),
        'n_active_rows': int(plan_df.shape[0]),
        'total_cost': float(plan_df['cost'].sum()),
        'mean_cv': {fac: float(cv_df[f'cv_{fac}'].mean()) for fac in UNCERTAINTY_FACTORS},
    }
    summary_path = os.path.join(TABLES_DIR, 'q4_two_stage_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"  -> {summary_path}")

    print("\n" + "=" * 70)
    print(f"✅ Q4 完成 · 投入 {plan_df['cost'].sum():.2f}/{budget:.2f} 元")
    print("=" * 70)


if __name__ == '__main__':
    main()
