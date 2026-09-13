"""
Q4 · Two-Stage Stochastic Programming + 生成 result4.xlsx
========================================================

**锁定决策（D-Q3Q4-024 / PoC_REPORT §2.2-§2.3）**：
- 7 天预测期：2026-09-11~17
- 同期预算上限：23,488.02 元
- 决策：第一阶段（here-and-now）选单元×关键词组合；第二阶段（wait-and-see）日级调整
- 不确定性：6 因子 × CV（历史 31 天单元级估计，截止 09-10，无目标期泄漏）

**F4 修复（2026-09-13）· 真正 SAA**：
- 目标函数改为 max Σ_u c_base[u] × E[(click_mult + reg_mult)/2] × x[u,k,t]
- 即对所有 N_SCENARIOS 个场景的扰动乘子取平均后做线性优化（线性模型下等价于 SAA）
- c_base[u] = p['r_click']（与 Q3 P0-4 修复后口径一致）

**简化（PoC）**：
- 决策粒度：单元 × 关键词 × 天 = (11 × ~75 × 7) ≈ 5,775 变量
- 不确定性乘子：对数正态分布（CV 转 σ，6 因子独立扰动，PoC 简化）
- 期望值（后验 SAA 估计）：cost × proxy × E[乘子]

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
# P2-2 FIX (2026-09-13)：场景数从 20 提升至 1000
#   SAA 收敛率 O(1/√N)：N=20 → SE=σ/4.47；N=1000 → SE=σ/31.6
#   N=1000 是学界标准的 SAA 配置（N=20 偏少）
#   预算约束紧绑时，决策几乎不变，但 CV/置信区间精度提升 7 倍
N_SCENARIOS = 1000
MAX_KEYWORDS_PER_UNIT_DATE = 25  # 强制分散
# P2-5 FIX (2026-09-13)：单单元预算占比上限（防 HHI 过高）
#   与 Q3 一致：UNIT_MAX_SHARE = 0.40（目标 HHI ≤ 0.25）
#   Q3 实测：cap=0.40 → HHI=0.36（原 0.51），预算利用率 70%
UNIT_MAX_SHARE = 0.40  # 单单元预算 ≤ 总预算的 40%
UNCERTAINTY_FACTORS = ['cpc', 'impressions', 'top_imp_pos', 'clicks', 'browses', 'regs']

# T3 修复（2026-09-13）：预测期日期集中管理，与 q4_data_prep.py 同源
Q4_PRED_DATES = [f"2026-09-{d:02d}" for d in range(11, 18)]  # 预测 7 天


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


def solve_two_stage_sp(cv_df, scenarios, budget, kw_per_unit, proxy_dict,
                       browse_click_ratio=None, kw_max_cost_dict=None,
                       cvr_7d=0.07):
    """Two-Stage SP 求解（SAA 形式：全场景加权期望目标）

    F4 修复（2026-09-13）：原版只取场景 0 的乘子做优化，其余 19 个场景仅用于后验。
    现改为 SAA：目标函数对所有 N_SCENARIOS 个场景的乘子取均值，
    即 max Σ_u c_base[u] × E[(click_mult_s + reg_mult_s)/2] × x[u,k,t]
    其中 c_base[u] = proxy_dict[u]['r_click']（与 Q3 P0-4 修复一致）

    T3 修复（同时）：browse_click_ratio 与 kw_max_cost_dict 改为显式参数传入

    D-V2-002 修复（同时）：cvr_7d 显式传入，注册报数口径 = 同期 7 天实测 CVR
      默认 0.07（与 Q3 的 0.0700 同量级），由调用方从 same_period 数据计算覆盖
    """
    if not HAS_PULP:
        print("❌ PuLP 未安装")
        return None

    print(f"\n[Two-Stage SP · SAA] 场景数={len(scenarios)} | 预算={budget:.2f} 元")

    units = sorted(set(u for s in scenarios for u in s['units']))
    dates = Q4_PRED_DATES  # 用模块常量（不再硬编码）

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

    prob = pulp.LpProblem('Q4_TwoStage_SAA', pulp.LpMaximize)

    x = pulp.LpVariable.dicts('x', range(n_var), lowBound=0, cat='Continuous')
    y = pulp.LpVariable.dicts('y', range(n_var), lowBound=0, upBound=1, cat='Binary')

    # big-M 从显式参数取（不再依赖全局 kw_pool_proxy）
    if kw_max_cost_dict:
        kw_max_cost = max(kw_max_cost_dict.values())
    else:
        kw_max_cost = 1000.0
    M = kw_max_cost * 1.5

    # ===== F4 修复：SAA 目标系数 =====
    # 对每个单元，先把每个场景的扰动乘子 (click_mult_s, reg_mult_s) 取平均，
    # 再与 c_base[u]（= r_click）相乘，得到线性目标系数 coef[u]
    # coef[u] = c_base[u] × E[(click_mult_s + reg_mult_s) / 2]
    n_scenarios = len(scenarios)
    s0_units = list(scenarios[0]['units'])
    unit_to_idx_in_scenarios = {u: i for i, u in enumerate(s0_units)}

    # proxy 全局均值作为 fallback（删除 0.27 常数）
    proxy_mean = {
        'r_click': float(np.mean([v['r_click'] for v in proxy_dict.values()]))
                    if proxy_dict else 0.5,
        'r_reg': float(np.mean([v.get('r_reg', 0.07) for v in proxy_dict.values()]))
                  if proxy_dict else 0.07,
        'r_topimp': float(np.mean([v.get('r_topimp', 1.0) for v in proxy_dict.values()]))
                    if proxy_dict else 1.0,
        'r_imp': float(np.mean([v.get('r_imp', 1.0) for v in proxy_dict.values()]))
                  if proxy_dict else 1.0,
    }

    coef = {}
    for u in units:
        # c_base 与 Q3 P0-4 修复一致：直接用 r_click
        c_base = proxy_dict.get(u, proxy_mean).get('r_click', proxy_mean['r_click'])

        if u in unit_to_idx_in_scenarios:
            ui = unit_to_idx_in_scenarios[u]
            mean_click_mult = float(np.mean([s['mults']['clicks'][ui] for s in scenarios]))
            mean_reg_mult = float(np.mean([s['mults']['regs'][ui] for s in scenarios]))
        else:
            mean_click_mult = 1.0
            mean_reg_mult = 1.0
        coef[u] = c_base * (mean_click_mult + mean_reg_mult) / 2

    print(f"  [F4 修复] 目标函数 = max Σ c_base[u] × E[(click_mult + reg_mult)/2] × x")
    print(f"    c_base 取自 proxy.r_click | S={n_scenarios} 场景平均 | 与 Q3 P0-4 口径一致")

    prob += pulp.lpSum(coef.get(v[0], proxy_mean['r_click']) * x[i]
                       for i, v in enumerate(var_keys)), 'expected_value'

    # 总预算（F2 修复 2026-09-12：减去 0.10 元浮点缓冲，确保 sum(cost) ≤ 23,488.02）
    budget_strict = budget - 0.10  # 留 0.10 元给 CBC 浮点累计误差
    prob += pulp.lpSum(x[i] for i in range(n_var)) <= budget_strict, 'budget'

    # P2-5 FIX (2026-09-13)：单单元预算占比上限（防 HHI 过高）
    #   Σ_{k,t in unit u} x[i] ≤ UNIT_MAX_SHARE × budget
    #   12 单元 × 15% = 180%（理论上允许 6-7 单元满负荷），实际稀疏解会自然下降
    print(f"  [P2-5 约束] 单单元预算占比上限 = {UNIT_MAX_SHARE*100:.0f}%")
    for u in units:
        idx_list_u = [var_idx[v] for v in var_keys if v[0] == u]
        if not idx_list_u:
            continue
        prob += (
            pulp.lpSum(x[i] for i in idx_list_u) <= UNIT_MAX_SHARE * budget,
            f'unit_share_cap_{u}'
        )

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

    # 提取解 + 后验期望值（SAA 估计）
    # 后验每个单元的乘子期望（用于报告 6 因子）
    exp_mults = {}
    for u in units:
        if u in unit_to_idx_in_scenarios:
            ui = unit_to_idx_in_scenarios[u]
            exp_mults[u] = {
                fac: float(np.mean([s['mults'][fac][ui] for s in scenarios]))
                for fac in UNCERTAINTY_FACTORS
            }
        else:
            exp_mults[u] = {fac: 1.0 for fac in UNCERTAINTY_FACTORS}

    rows = []
    for i, v in enumerate(var_keys):
        cost = x[i].value()
        if cost is None or cost < 0.01:
            continue
        u, k, d = v
        em = exp_mults[u]
        p = proxy_dict.get(u, proxy_mean)

        # 点击：cost × r_click × 期望乘子
        click = cost * p['r_click'] * em['clicks']
        # 注册 FIX（2026-09-13）：用全局 cvr_7d 校准注册报数
        reg = click * cvr_7d
        # 浏览 FIX（2026-09-13）：browse = cost × r_browse × em['browses']（无双重计数）
        #   修复前（BUG）：browse = click × browse_click_ratio × em['browses']
        #     其中 click = cost × r_click × em['clicks']
        #     browse_click_ratio = 总浏览/总点击（≈3.71）
        #     → browse = cost × r_click × em['clicks'] × browse_click_ratio × em['browses']
        #     → em['clicks'] 和 browse_click_ratio 同时出现，导致双重计数（browse/click 比例偏大）
        #   正确公式：browse = cost × r_browse × em['browses']
        #     r_browse = 总浏览/总成本（年度浏览/成本比）
        #     em['browses'] = SAA均值浏览乘子（browses因子独立扰动）
        #     → browse = 总浏览 × em['browses']（逻辑清晰，无重复因子）
        browse = cost * p['r_browse'] * em['browses']
        # 上方位：cost × r_topimp × 期望乘子
        top_imp = cost * p['r_topimp'] * em['top_imp_pos']
        # ===== T3 修复：直接定义 exp_cpc / exp_impressions（不再代数混乱）=====
        # CPC = cost / clicks（清晰定义）
        exp_cpc = cost / max(click, 1e-6)
        # impressions = cost × r_imp × 期望乘子（r_imp 从同期数据计算 = imp/cost）
        if 'r_imp' in p:
            exp_imp = cost * p['r_imp'] * em['impressions']
        else:
            # fallback: 由 clicks 反推 imp（imp = clicks / CTR）
            ctr = p['r_click'] / max(p.get('r_imp', p['r_click']), 1e-6)
            exp_imp = click / max(ctr, 1e-6)

        rows.append({
            'date': d, 'unit_id': u, 'keyword_id': k, 'cost': cost,
            'exp_cpc': exp_cpc,
            'exp_impressions': exp_imp,
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
    # T3 修复（2026-09-13）：补 r_imp = impressions/cost（删除原硬编码 r_topimp=0.27 fallback）
    same_period_ratios = same_period.groupby('unit_id').agg(
        cost=('cost', 'sum'),
        clicks=('clicks', 'sum'),
        regs=('regs', 'sum'),
        browses=('browses', 'sum'),
        top_imp=('top_imp', 'sum'),
        impressions=('impressions', 'sum'),
    ).reset_index()
    same_period_ratios['r_click'] = same_period_ratios['clicks'] / same_period_ratios['cost'].clip(lower=0.01)
    same_period_ratios['r_reg'] = same_period_ratios['regs'] / same_period_ratios['cost'].clip(lower=0.01)
    same_period_ratios['r_browse'] = same_period_ratios['browses'] / same_period_ratios['cost'].clip(lower=0.01)
    same_period_ratios['r_topimp'] = same_period_ratios['top_imp'] / same_period_ratios['cost'].clip(lower=0.01)
    same_period_ratios['r_imp'] = same_period_ratios['impressions'] / same_period_ratios['cost'].clip(lower=0.01)
    proxy_dict = same_period_ratios.set_index('unit_id')[
        ['r_click', 'r_browse', 'r_reg', 'r_topimp', 'r_imp']
    ].to_dict('index')

    # T3 修复（2026-09-13）：浏览/点击比从同期数据计算（删除原硬编码 3.712）
    browse_click_ratio = float(same_period['browses'].sum() / max(same_period['clicks'].sum(), 1))
    print(f"  [T3 修复] 浏览/点击比 = {browse_click_ratio:.3f}（同期实测）")

    # D-V2-002 修复（2026-09-13）：注册报数口径 = 同期 7 天实测 CVR
    #   p['r_reg'] = unit_regs/unit_cost（单元级 regs/cost，0.066~0.126）不可用于"click × CVR"口径报数
    #   cvr_7d = total_actual_regs / total_actual_clicks（同期 7 天实测，与 Q3 16 天口径同类）
    cvr_7d = float(same_period['regs'].sum() / max(same_period['clicks'].sum(), 1))
    print(f"  [D-V2-002 修复] 同期 7 天 CVR = {cvr_7d:.4f}（同期实际："
          f"regs={same_period['regs'].sum():.0f} / clicks={same_period['clicks'].sum():.0f}）")

    # T3 修复（2026-09-13）：kw_max_cost 作为显式 dict 传给求解函数（不再用 global kw_pool_proxy）
    kw_max_cost_dict = kw_pool_renamed.set_index(
        kw_pool_renamed['关键词'].astype(int)
    )['kw_cost'].to_dict()
    print(f"  [T3 修复] kw_max_cost_dict 已构造（{len(kw_max_cost_dict)} 词）")

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
    plan_df = solve_two_stage_sp(
        cv_df, scenarios, budget, kw_per_unit, proxy_dict,
        browse_click_ratio=browse_click_ratio,
        kw_max_cost_dict=kw_max_cost_dict,
        cvr_7d=cvr_7d,  # D-V2-002：注册报数口径 = 同期 7 天实测 CVR
    )
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
        # F4 + P2-2 修复（2026-09-13）：SAA 场景数已升级至 N_SCENARIOS
        'method': f'Two-Stage Stochastic Programming (SAA, S={N_SCENARIOS} scenarios in objective)',
        'objective_formula': 'max Σ_u c_base[u] × E[(click_mult_s + reg_mult_s)/2] × x',
        'c_base_definition': 'c_base[u] = proxy.r_click (consistent with Q3 P0-4 fix)',
        'n_scenarios': N_SCENARIOS,
        'budget': float(budget),
        'n_units': int(cv_df.shape[0]),
        'n_active_rows': int(plan_df.shape[0]),
        'total_cost': float(plan_df['cost'].sum()),
        'mean_cv': {fac: float(cv_df[f'cv_{fac}'].mean()) for fac in UNCERTAINTY_FACTORS},
        'browse_click_ratio': float(browse_click_ratio),
        'cvr_7d': float(cvr_7d),  # D-V2-002：同期 7 天实测 CVR（注册报数口径）
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
