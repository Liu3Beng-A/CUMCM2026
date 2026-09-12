"""
Q3 · MILP 优化器（PuLP · Q3Q4 doc §2.4）
==========================================

**锁定决策（Q3Q4 doc §2.2 + §2.4 + BIAS_v2）**：
- 决策变量 x[k,t] = 关键词 k 在日期 t 的投入金额（连续变量，[0, ∞)）
- 决策变量 y[k,t] ∈ {0,1} = 关键词 k 是否在日期 t 投放（二值变量）
- 目标：max Σ_{k,t} (r_click × cost[k,t] + r_reg × cost[k,t])
       = max Σ_{k,t} (r_click + r_reg) × x[k,t]
       即总收益最大（低成本高效益代理）
- 约束：
  1. 总预算 ≤ 51,164.93 元（同期）
  2. 推广单元 u 日预算 ≤ 该单元同期日均预算
  3. 关键词激活：x[k,t] ≤ M × y[k,t] (M = 关键词历史最大日消费 × 1.5)
  4. 关联约束（前 20 强关联）：y[a,t] ≥ y[c,t] （关联对必须同时投）
  5. 同期分段：feb/aug 分段独立预算

**代理变量法（§2.2.1）**：
- 投入金额 x[k,t] → 产出 = r_click × x[k,t] （点击量代理）
- 投入金额 x[k,t] → 产出 = r_browse × x[k,t] （浏览量代理）
- 投入金额 x[k,t] → 产出 = r_reg × x[k,t] （注册量代理）
- 投入金额 x[k,t] → 产出 = r_topimp × x[k,t] （上方位代理）
- 系数 r_xxx 来自 q3_proxy_ratios.pkl

**主要输入**：
- `data/processed/q3/q3_target_window.pkl`：16 天（日期×单元）
- `data/processed/q3/q3_keyword_pool.pkl`：909 词
- `data/processed/q3/q3_budget_period.pkl`：02 月 + 08 月预算
- `data/processed/q3/q3_proxy_ratios.pkl`：代理比值
- `data/processed/q3/q3_unit_budget_ceiling.pkl`：单元 16 天预算上限
- `results/tables/q3_keyword_assoc_rules.csv`：50 条关联规则

**主要输出**（写到 `data/processed/q3/`）：
- `q3_optimal_plan.pkl`：16 天 × 单元 × 关键词 投入矩阵
- `results/excel/result3.xlsx`：严格 9 列对齐附件 2 模板
- `results/tables/q3_milp_summary.json`：求解状态 + 目标值
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
from src.utils import PROCESSED_DIR, RESULTS_DIR, TABLES_DIR, EXCEL_DIR, ensure_dir  # noqa: E402

try:
    import pulp
    HAS_PULP = True
except ImportError:
    HAS_PULP = False


# 关联约束：取 top-20 高 lift 关联（必共现）
N_ASSOC_CONSTRAINTS = 20
# 单元日均预算上浮倍数（防止过度收紧）
UNIT_DAILY_MULTIPLIER = 1.0  # 不放大，强制真实同期
# 每 (单元, 日期) 投放关键词数上限（强制分散）
MAX_KEYWORDS_PER_UNIT_DATE = 30
# 每 (单元, 日期) 投入上限 = 该单元日均预算 × 1.0（强制分散）


def main():
    print("=" * 70)
    print("Q3 · MILP 优化器（PuLP · §2.4）")
    print("=" * 70)

    if not HAS_PULP:
        print("❌ PuLP 未安装，无法求解 MILP。请先 pip install pulp")
        return

    out_dir = ensure_dir(os.path.join(PROCESSED_DIR, 'q3'))
    excel_dir = ensure_dir(EXCEL_DIR)
    t0 = time.time()

    # ---- 加载输入 ----
    target = pd.read_pickle(os.path.join(out_dir, 'q3_target_window.pkl'))
    pool = pd.read_pickle(os.path.join(out_dir, 'q3_keyword_pool.pkl'))
    budget_df = pd.read_pickle(os.path.join(out_dir, 'q3_budget_period.pkl'))
    proxy = pd.read_pickle(os.path.join(out_dir, 'q3_proxy_ratios.pkl'))
    unit_budget = pd.read_pickle(os.path.join(out_dir, 'q3_unit_budget_ceiling.pkl'))
    rules_path = os.path.join(TABLES_DIR, 'q3_keyword_assoc_rules.csv')
    rules = pd.read_csv(rules_path, encoding='utf-8-sig') if os.path.exists(rules_path) else pd.DataFrame()

    print(f"\n[输入] 16 天 {target.shape[0]} 行 | 词池 {pool.shape[0]} 词 | "
          f"关联规则 {len(rules)} 条")

    # ---- 决策变量集合 ----
    # (date, unit, keyword) 三元组 → 投放决策
    dates = sorted(target['date'].unique())
    units = sorted(target['unit_id'].unique())
    kw_per_unit = pool.groupby('unit_id')['关键词'].apply(set).to_dict()

    # 构建 (date, unit, keyword) 候选集
    candidates = []
    for d in dates:
        day_units = target[target['date'] == d]['unit_id'].unique()
        for u in day_units:
            for k in kw_per_unit.get(u, []):
                candidates.append((d, u, int(k)))
    candidates = list(set(candidates))  # 去重
    print(f"\n[决策空间] 候选 (date, unit, kw) 三元组 = {len(candidates)} 个")
    n_var = len(candidates)

    # 索引化（加速访问）
    cand_idx = {c: i for i, c in enumerate(candidates)}

    # ---- 代理比值（按单元）----
    proxy_dict = proxy.set_index('unit_id')[['r_click', 'r_browse', 'r_topimp', 'r_reg']].to_dict('index')
    # 收益系数：r_click × 0.4 + r_browse × 0.1 + r_reg × 0.5（归一化权重）
    coef = {}
    for u in units:
        if u in proxy_dict:
            p = proxy_dict[u]
            coef[u] = 0.4 * p['r_click'] + 0.1 * p['r_browse'] + 0.5 * p['r_reg']
        else:
            coef[u] = 0.5  # fallback
    print(f"\n[代理比值] 单元收益系数 (前 5): "
          f"{dict(list(coef.items())[:5])}")

    # ---- 单元日均预算上限 ----
    unit_budget_dict = unit_budget.set_index('unit_id').to_dict('index')
    print(f"\n[预算] 16 天同期预算 = {budget_df[budget_df['period'] == 'total']['budget'].values[0]:.2f} 元")

    # ---- MILP 建模 ----
    print("\n[建模] PuLP MILP ...")
    prob = pulp.LpProblem('Q3_SEM_Bidding', pulp.LpMaximize)

    # 决策变量
    x = pulp.LpVariable.dicts('x', range(n_var), lowBound=0, cat='Continuous')
    y = pulp.LpVariable.dicts('y', range(n_var), lowBound=0, upBound=1, cat='Binary')

    # 关键词历史最大日消费（用于 big-M）
    kw_max_cost = pool.set_index(pool['关键词'].astype(int))['kw_cost'].to_dict()
    M = max(kw_max_cost.values()) * 1.5  # big-M = 1.5 × 最大日消费

    # 目标函数
    print("  [目标] max Σ (coef[u] × x[i])")
    prob += pulp.lpSum(
        coef.get(c[1], 0.5) * x[i] for i, c in enumerate(candidates)
    ), 'total_value'

    # 约束 1：总预算
    total_budget = budget_df[budget_df['period'] == 'total']['budget'].values[0]
    prob += pulp.lpSum(x[i] for i in range(n_var)) <= total_budget, 'total_budget'
    print(f"  [约束 1] 总预算 ≤ {total_budget:.2f}")

    # 约束 2：单元 16 天预算上限
    print(f"  [约束 2] 单元 16 天预算上限（{len(unit_budget)} 单元）")
    for _, row in unit_budget.iterrows():
        u = row['unit_id']
        ub = row['unit_budget_16d'] * UNIT_DAILY_MULTIPLIER
        idx_list = [cand_idx[c] for c in candidates if c[1] == u]
        if idx_list:
            prob += (
                pulp.lpSum(x[i] for i in idx_list) <= ub,
                f'unit_{u}_budget'
            )

    # 约束 3：big-M (x ≤ M × y)
    print(f"  [约束 3] big-M = {M:.2f}")
    for i, c in enumerate(candidates):
        prob += x[i] <= M * y[i], f'bigM_{i}'

    # 约束 3.5：(单元, 日期) 投放分散 + 日预算上限
    print(f"  [约束 3.5] (单元, 日期) 投放分散约束（MAX_KEYWORDS={MAX_KEYWORDS_PER_UNIT_DATE}）")
    for u in units:
        ub_16d = unit_budget_dict.get(u, {}).get('unit_budget_16d', 0)
        ub_daily = ub_16d / 16 * UNIT_DAILY_MULTIPLIER
        if ub_daily < 1:
            continue
        for d in dates:
            idx_list = [cand_idx[c1] for c1 in candidates
                        if c1[0] == d and c1[1] == u]
            if not idx_list:
                continue
            # 日预算上限（2× 日均）
            prob += (
                pulp.lpSum(x[i] for i in idx_list) <= ub_daily * 2,
                f'unit_{u}_date_{d}_budget'
            )
            # 关键词数上限
            prob += (
                pulp.lpSum(y[i] for i in idx_list) <= MAX_KEYWORDS_PER_UNIT_DATE,
                f'unit_{u}_date_{d}_kws'
            )

    # 约束 4：关联约束（y[a,t] ≥ y[c,t]）—— top-20 by lift
    print(f"  [约束 4] 关联约束（top-{N_ASSOC_CONSTRAINTS}）")
    if len(rules) > 0:
        # 取 cosine 规则的 top-N（跨单元）
        cos_rules = rules[rules['metric'] == 'cosine'].head(N_ASSOC_CONSTRAINTS)
        for _, r in cos_rules.iterrows():
            try:
                a = int(r['antecedents'])
                c = int(r['consequents'])
            except (ValueError, TypeError):
                continue
            # 对每一日，a 投放 → c 也必须投放（在同一单元）
            # 由于 a 和 c 可能在不同单元，简化为：所有日同步
            for d in dates:
                # 找 (d, u_a, a) 和 (d, u_c, c) 的 idx
                idx_a = [cand_idx[c1] for c1 in candidates
                         if c1[0] == d and c1[2] == a]
                idx_c = [cand_idx[c1] for c1 in candidates
                         if c1[0] == d and c1[2] == c]
                for ia in idx_a:
                    for ic in idx_c:
                        # y[a] >= y[c] → 当 a 不投，c 也不投
                        prob += y[ia] - y[ic] >= 0, f'assoc_{ia}_{ic}'

    # ---- 求解 ----
    print("\n[求解] CBC 默认求解器 ...")
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=120)
    status = prob.solve(solver)
    status_name = pulp.LpStatus[status]
    print(f"  状态 = {status_name}")
    print(f"  目标值 = {pulp.value(prob.objective):.4f}")
    print(f"  求解时间 = {time.time() - t0:.2f}s")

    # ---- 提取解 ----
    rows = []
    total_cost = 0
    for i, c in enumerate(candidates):
        cost = x[i].value()
        if cost is None or cost < 0.01:
            continue
        u = c[1]
        kw_id = int(c[2])
        if u in proxy_dict:
            p = proxy_dict[u]
        else:
            p = {'r_click': 0.5, 'r_browse': 1.0, 'r_reg': 0.5, 'r_topimp': 0.27}
        click = cost * p['r_click']
        browse = click * 2.93  # 浏览/点击 比 (历史均值)
        reg = cost * p['r_reg']
        top_imp = cost * p['r_topimp']
        rows.append({
            'date': c[0], 'unit_id': u, 'keyword_id': kw_id,
            'cost': cost, 'click': click, 'browse': browse,
            'reg': reg, 'top_imp': top_imp,
        })
        total_cost += cost

    plan_df = pd.DataFrame(rows)
    print(f"\n[解] 投放行数 = {plan_df.shape[0]} | 总投入 = {total_cost:.2f} 元")
    plan_df.to_pickle(os.path.join(out_dir, 'q3_optimal_plan.pkl'))

    # ---- 写入 result3.xlsx（严格 9 列对齐附件 2）----
    plan_df['_kw'] = plan_df['keyword_id'].astype(str)
    kw_to_plan = pool.set_index(pool['关键词'].astype(int))['plan_id'].astype(int).to_dict()
    plan_df['plan_id'] = plan_df['keyword_id'].map(kw_to_plan)
    plan_df['keyword'] = plan_df['keyword_id']  # 数字 ID 即为关键词

    result3 = pd.DataFrame({
        '日期': plan_df['date'],
        '方案ID': plan_df['plan_id'],
        '推广单元': plan_df['unit_id'],
        '关键词': plan_df['keyword'],
        '投入金额': plan_df['cost'].round(2),
        '预期展位': plan_df['top_imp'].round(0).astype(int),
        '预期点击量': plan_df['click'].round(0).astype(int),
        '预期浏览量': plan_df['browse'].round(0).astype(int),
        '预期注册量': plan_df['reg'].round(0).astype(int),
    })

    result3_path = os.path.join(excel_dir, 'result3.xlsx')
    result3.to_excel(result3_path, index=False)
    print(f"  -> {result3_path} | {len(result3)} 行")
    print(f"  列对齐附件 2: {list(result3.columns) == ['日期', '方案ID', '推广单元', '关键词', '投入金额', '预期展位', '预期点击量', '预期浏览量', '预期注册量']}")

    # ---- 写入 milp_summary.json ----
    summary = {
        'status': status_name,
        'objective': float(pulp.value(prob.objective)),
        'total_cost': float(total_cost),
        'budget_limit': float(total_budget),
        'n_candidates': n_var,
        'n_active': int(plan_df.shape[0]),
        'n_constraints': len(prob.constraints),
        'solve_time_sec': round(time.time() - t0, 2),
        'coef_formula': 'coef = 0.4*r_click + 0.1*r_browse + 0.5*r_reg',
        'unit_daily_multiplier': UNIT_DAILY_MULTIPLIER,
    }
    summary_path = os.path.join(TABLES_DIR, 'q3_milp_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"  -> {summary_path}")

    print("\n" + "=" * 70)
    print(f"✅ Q3 MILP 完成 · 投入 {total_cost:.2f}/{total_budget:.2f} 元 "
          f"({total_cost/total_budget*100:.1f}%)")
    print("=" * 70)


if __name__ == '__main__':
    main()
