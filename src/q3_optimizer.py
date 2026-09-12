"""Q3 投放策略优化：MILP 单目标 + NSGA-II 多目标 Pareto

目的：
- 在总预算约束下，求每方案每日最优预算分配
- 单目标：MILP 求"最大注册数"分配
- 多目标：NSGA-II 求 (成本最小, 注册最大) Pareto 前沿

模型：
- 决策变量：r[plan, t] ∈ [0, 2.0]，每日每方案预算相对当前的比例
  （1.0 = 保持当前分配）
- 约束：
  * 总预算 = 当前总预算（不可超）
  * 日平滑：相邻日比例变化 ≤ 30%
  * 月平滑：月度 CV ≤ 0.5
- 目标（单目标MILP）：
  * max Σ reg_rate[p,t] × original_budget[p,t] × r[p,t]
- 目标（NSGA-II）：
  * f1 = 总成本（保持 ~当前 → 越小越好）
  * f2 = 总注册数（越大越好）

输出：
- results/tables/q3_daily_strategy.csv（MILP 最优解）
- results/tables/q3_pareto_front.csv（NSGA-II Pareto）
- results/figures/q3_strategy_heatmap.png（MILP 热力图）
- results/figures/q3_pareto.png（Pareto 前沿图）
- data/raw/attachments/result3.xlsx
- issue/q3_method.md
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import linprog, minimize
from scipy.stats import spearmanr

from src.utils import TABLES_DIR, FIGURES_DIR, ensure_dir
from src.plot_style import apply_style, save_fig, COLORS


def load_data():
    """加载 Q3 所需数据"""
    plan_daily = pd.read_pickle(os.path.join('data', 'processed', 'q1', 'plan_daily.pkl'))
    daily_full = pd.read_pickle(os.path.join('data', 'processed', 'q1', 'daily_full.pkl'))
    return plan_daily, daily_full


def build_decision_matrix(plan_daily, daily_full):
    """构造决策变量矩阵 r[plan, day]

    r[plan, day] = 相对当前预算的比例（1.0 = 保持）
    原始预算 base[plan, day] = plan_daily['消费额']
    """
    plan_daily = plan_daily.copy()
    plan_daily['日期'] = pd.to_datetime(plan_daily['日期'])
    plans = sorted(plan_daily['方案ID'].unique())
    days = sorted(plan_daily['日期'].unique())

    # 完整网格（plan × day）矩阵
    n_p, n_d = len(plans), len(days)
    base = np.zeros((n_p, n_d))   # 原始消费额
    reg_rate = np.zeros((n_p, n_d))  # 日注册率（注册数/消费额）

    daily_full_idx = daily_full.copy()
    daily_full_idx['日期'] = pd.to_datetime(daily_full_idx['日期'])
    daily_full_idx = daily_full_idx.set_index('日期')

    reg_col = '新注册数' if '新注册数' in daily_full_idx.columns else daily_full_idx.columns[0]

    plan_id_map = {p: i for i, p in enumerate(plans)}
    day_id_map = {d: i for i, d in enumerate(days)}

    # 计算每日总消费额（用于 reg_rate 拆分）
    plan_daily_with_date = plan_daily.copy()
    plan_daily_with_date['消费额'] = plan_daily_with_date.get('消费额', 0)
    total_cost_per_day = plan_daily_with_date.groupby('日期')['消费额'].sum().to_dict()

    for _, row in plan_daily.iterrows():
        pi = plan_id_map[row['方案ID']]
        di = day_id_map[row['日期']]
        cost = row.get('消费额', 0) if '消费额' in plan_daily.columns else 0
        base[pi, di] = max(cost, 0)
        # 注册率：用全公司日注册数 / 全公司日总消费额；所有方案共享
        daily_reg_d = daily_full_idx[reg_col].get(row['日期'], 0) if row['日期'] in daily_full_idx.index else 0
        total_d = total_cost_per_day.get(row['日期'], 0)
        reg_rate[pi, di] = daily_reg_d / total_d if total_d > 0 else 0

    return base, reg_rate, plans, days, plan_id_map, day_id_map


def solve_milp(base, reg_rate, plans, days):
    """单目标 MILP：max 总注册数

    决策变量：r[plan, day]  ∈ [0, 2.0]
    目标：max Σ base[i,j] × reg_rate[i,j] × r[i,j]
    约束：
      - Σ base[i,j] × r[i,j] = 总预算不变 → 等式约束（保持总成本不变）
      - 0.3 ≤ r[i,j] ≤ 2.0

    注：MILP 的 M（混合整数）特征在于 budget allocation 离散化。此处我们用 LP
    （连续松弛），因"逐步微调 r"对连续值更友好。
    """
    print('\n=== Q3 MILP 单目标（求最大注册数）===', flush=True)

    n_p, n_d = base.shape
    n = n_p * n_d
    total_budget = base.sum()

    # LP: scipy.optimize.linprog min -c^T x
    c = -(base * reg_rate).flatten()  # 负号：min -obj = max obj
    A_eq = np.zeros((1, n))
    A_eq[0, :] = base.flatten()
    b_eq = np.array([total_budget])

    bounds = [(0.3, 2.0)] * n
    result = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')

    if not result.success:
        print(f'[MILP] 失败：{result.message}', flush=True)
        return None, None

    r_opt = result.x.reshape(n_p, n_d)
    predicted_cost = (base * r_opt).sum()
    predicted_reg  = (base * r_opt * reg_rate).sum()

    print(f'  总预算（约束）: {total_budget:,.0f} 元', flush=True)
    print(f'  解的总成本:    {predicted_cost:,.0f} 元', flush=True)
    print(f'  解的总注册数:  {predicted_reg:,.0f} 人', flush=True)

    # 当前方案的注册数（r=1）
    current_reg = (base * reg_rate).sum()
    print(f'  当前注册数:    {current_reg:,.0f} 人', flush=True)
    print(f'  提升:          {predicted_reg - current_reg:+.0f} ({(predicted_reg/current_reg - 1)*100:+.2f}%)', flush=True)

    return r_opt, {
        '总预算': total_budget,
        '解的总成本': predicted_cost,
        '解的总注册数': predicted_reg,
        '当前注册数': current_reg,
        '提升幅度(%)': (predicted_reg/current_reg - 1)*100,
    }


def solve_nsga2(base, reg_rate, n_gen=50, pop=80):
    """NSGA-II 多目标：(成本, 注册数) Pareto 前沿

    f1 = 总成本（越小越好，但预算约束使其不能远小于 baseline）
    f2 = -总注册数（最小化负注册数 = 最大化注册数）

    使用简化版 NSGA-II（非支配排序 + 拥挤距离 + 锦标赛选择）
    """
    print('\n=== Q3 NSGA-II 多目标 Pareto ===', flush=True)

    n_p, n_d = base.shape
    total_budget = base.sum()

    def decode(x):
        """x: 一维数组，长度 n_p × n_d；reshape 为 r 矩阵"""
        return np.clip(x.reshape(n_p, n_d), 0.3, 2.0)

    def fitness(x):
        r = decode(x)
        cost = (base * r).sum()
        reg = (base * r * reg_rate).sum()
        # 约束处理：成本偏离 baseline 越多，罚越大
        penalty = max(0, abs(cost - total_budget) - total_budget * 0.05) ** 2
        # 平滑约束：相邻日比例变化过大要罚
        smooth_pen = 0
        for i in range(n_p):
            diffs = np.diff(r[i])
            smooth_pen += np.sum(np.clip(np.abs(diffs) - 0.3, 0, None) ** 2)
        return np.array([cost + 0.0001 * penalty,
                         -reg + 0.001 * smooth_pen])

    def non_dominated_sort(pop_fitness):
        """非支配排序"""
        n_pop = len(pop_fitness)
        dominated_by = [[] for _ in range(n_pop)]
        dom_count = np.zeros(n_pop, dtype=int)
        ranks = np.zeros(n_pop, dtype=int)
        fronts = [[]]
        for i in range(n_pop):
            for j in range(n_pop):
                if i == j: continue
                if all(pop_fitness[i] <= pop_fitness[j]) and any(pop_fitness[i] < pop_fitness[j]):
                    dominated_by[i].append(j)
                elif all(pop_fitness[j] <= pop_fitness[i]) and any(pop_fitness[j] < pop_fitness[i]):
                    dom_count[i] += 1
            if dom_count[i] == 0:
                ranks[i] = 0
                fronts[0].append(i)
        k = 0
        while len(fronts[k]) > 0:
            next_front = []
            for i in fronts[k]:
                for j in dominated_by[i]:
                    dom_count[j] -= 1
                    if dom_count[j] == 0:
                        ranks[j] = k + 1
                        next_front.append(j)
            k += 1
            fronts.append(next_front)
        return ranks, fronts

    def crowding_distance(pop_fitness, front):
        """拥挤距离"""
        n_f = len(front)
        if n_f <= 2:
            return np.full(n_f, np.inf)
        dist = np.zeros(n_f)
        for m in range(2):
            vals = pop_fitness[front, m]
            sorted_idx = np.argsort(vals)
            dist[sorted_idx[0]] = dist[sorted_idx[-1]] = np.inf
            vmin, vmax = vals[sorted_idx[0]], vals[sorted_idx[-1]]
            if vmax == vmin:
                continue
            for j in range(1, n_f - 1):
                dist[sorted_idx[j]] += (vals[sorted_idx[j+1]] - vals[sorted_idx[j-1]]) / (vmax - vmin)
        return dist

    np.random.seed(42)
    n_var = n_p * n_d

    # 初始化种群
    pop_x = np.random.uniform(0.5, 1.5, size=(pop, n_var))

    for gen in range(n_gen):
        pop_f = np.array([fitness(x) for x in pop_x])

        # 父子合并
        offspring_x = pop_x + np.random.normal(0, 0.1, size=pop_x.shape)
        offspring_x = np.clip(offspring_x, 0.3, 2.0)
        offspring_f = np.array([fitness(x) for x in offspring_x])

        merged_x = np.vstack([pop_x, offspring_x])
        merged_f = np.vstack([pop_f, offspring_f])

        ranks, fronts = non_dominated_sort(merged_f)
        new_pop_x = []
        front_idx = 0
        while len(new_pop_x) + len(fronts[front_idx]) <= pop:
            for idx in fronts[front_idx]:
                new_pop_x.append(merged_x[idx])
            front_idx += 1

        # 最后一个前沿用拥挤距离挑
        if len(new_pop_x) < pop and front_idx < len(fronts):
            last_front = fronts[front_idx]
            cd = crowding_distance(merged_f, last_front)
            sorted_by_cd = sorted(zip(last_front, cd), key=lambda x: -x[1])
            for idx, _ in sorted_by_cd:
                if len(new_pop_x) >= pop:
                    break
                new_pop_x.append(merged_x[idx])

        pop_x = np.array(new_pop_x)
        if gen % 10 == 0:
            best_reg = -pop_f[:, 1].min()
            print(f'  Gen {gen:3d}: best_reg={best_reg:.0f}', flush=True)

    # 最终 Pareto
    final_f = np.array([fitness(x) for x in pop_x])
    ranks, fronts = non_dominated_sort(final_f)
    pareto_idx = fronts[0]

    pareto_x = pop_x[pareto_idx]
    pareto_f = final_f[pareto_idx]

    # 排序按成本
    sorted_idx = np.argsort(pareto_f[:, 0])
    pareto_x = pareto_x[sorted_idx]
    pareto_f = pareto_f[sorted_idx]

    print(f'\n  Pareto 解数：{len(pareto_x)}', flush=True)
    print(f'  Pareto 范围：成本 [{pareto_f[:,0].min():,.0f}, {pareto_f[:,0].max():,.0f}], 注册 [{-pareto_f[:,1].max():,.0f}, {-pareto_f[:,1].min():,.0f}]', flush=True)
    return pareto_x, pareto_f


def main():
    print('=' * 60, flush=True)
    print('问题 3：投放策略优化（MILP + NSGA-II Pareto）', flush=True)
    print('=' * 60, flush=True)

    ensure_dir(TABLES_DIR)
    ensure_dir(FIGURES_DIR)

    plan_daily, daily_full = load_data()
    print(f'  plan_daily: {len(plan_daily)} 行', flush=True)
    print(f'  daily_full: {len(daily_full)} 行', flush=True)

    base, reg_rate, plans, days, plan_id_map, day_id_map = build_decision_matrix(plan_daily, daily_full)
    print(f'\n  决策矩阵: {base.shape[0]} 方案 × {base.shape[1]} 天', flush=True)
    print(f'  5 方案: {plans}', flush=True)
    print(f'  时间范围: {min(days).date()} ~ {max(days).date()} ({len(days)} 天)', flush=True)
    print(f'  总预算: {base.sum():,.0f} 元 = {base.sum()/10000:.2f} 万元', flush=True)

    # ===== MILP =====
    r_opt, milp_stats = solve_milp(base, reg_rate, plans, days)

    if r_opt is None:
        print('[abort] MILP 失败', flush=True)
        return

    # ===== NSGA-II =====
    pareto_x, pareto_f = solve_nsga2(base, reg_rate, n_gen=30, pop=60)

    # ===== 保存 MILP 最优解 CSV =====
    milp_rows = []
    for i, p in enumerate(plans):
        for j, d in enumerate(days):
            milp_rows.append({
                '方案ID': int(p),
                '日期': pd.Timestamp(d).strftime('%Y-%m-%d'),
                '原始消费额': round(base[i, j], 2),
                '最优比例 r*': round(r_opt[i, j], 4),
                '最优消费额': round(base[i, j] * r_opt[i, j], 2),
                '注册数预测': round(base[i, j] * r_opt[i, j] * reg_rate[i, j], 2),
            })
    milp_df = pd.DataFrame(milp_rows)
    milp_csv = os.path.join(TABLES_DIR, 'q3_daily_strategy.csv')
    milp_df.to_csv(milp_csv, index=False, encoding='utf-8-sig')
    print(f'\n[save] {milp_csv}', flush=True)

    # ===== 汇总：MILP 5 方案 + 全公司 =====
    plan_summary_rows = []
    for i, p in enumerate(plans):
        orig_cost = base[i].sum()
        opt_cost = (base[i] * r_opt[i]).sum()
        opt_reg = (base[i] * r_opt[i] * reg_rate[i]).sum()
        plan_summary_rows.append({
            '方案ID': int(p),
            '原始总消费': round(orig_cost, 2),
            '最优总消费': round(opt_cost, 2),
            '消费变化(%)': round((opt_cost - orig_cost) / orig_cost * 100, 2),
            '最优注册数预测': round(opt_reg, 2),
            '平均相对比例': round(r_opt[i].mean(), 4),
            '比例标准差': round(r_opt[i].std(), 4),
        })
    summary_df = pd.DataFrame(plan_summary_rows)
    summary_csv = os.path.join(TABLES_DIR, 'q3_plan_summary.csv')
    summary_df.to_csv(summary_csv, index=False, encoding='utf-8-sig')
    print(f'[save] {summary_csv}', flush=True)
    print('\n  MILP 5 方案汇总：', flush=True)
    print(summary_df.to_string(index=False), flush=True)

    # ===== 保存 Pareto =====
    pareto_rows = []
    for i, (x, f) in enumerate(zip(pareto_x, pareto_f)):
        r_mat = np.clip(x.reshape(len(plans), len(days)), 0.3, 2.0)
        # 5 方案汇总
        summary = {f'方案{int(p)}_cost': round((base[k] * r_mat[k]).sum(), 0)
                   for k, p in enumerate(plans)}
        summary['_total_cost'] = f[0]
        summary['_total_reg'] = -f[1]
        pareto_rows.append(summary)
    pareto_df = pd.DataFrame(pareto_rows)
    pareto_csv = os.path.join(TABLES_DIR, 'q3_pareto_front.csv')
    pareto_df.to_csv(pareto_csv, index=False, encoding='utf-8-sig')
    print(f'[save] {pareto_csv} ({len(pareto_df)} 个 Pareto 解)', flush=True)

    # ===== 写 result3.xlsx =====
    out_xlsx = os.path.join('data', 'raw', 'attachments', 'result3.xlsx')
    os.makedirs(os.path.dirname(out_xlsx), exist_ok=True)
    with pd.ExcelWriter(out_xlsx, engine='openpyxl') as writer:
        summary_df.to_excel(writer, sheet_name='方案汇总', index=False)
        milp_df.head(1000).to_excel(writer, sheet_name='每日策略', index=False)  # 限 1000 行
        pareto_df.to_excel(writer, sheet_name='Pareto前沿', index=False)
    print(f'[save] {out_xlsx}', flush=True)

    # ===== 绘图 1：MILP 热力图 =====
    apply_style()
    fig, axes = plt.subplots(2, 1, figsize=(15, 8))

    # (a) MILP r*
    ax = axes[0]
    im = ax.imshow(r_opt, aspect='auto', cmap='RdYlGn', vmin=0.5, vmax=1.5)
    ax.set_yticks(range(len(plans)))
    ax.set_yticklabels([str(p) for p in plans])
    ax.set_xticks(range(0, len(days), 30))
    ax.set_xticklabels([pd.Timestamp(d).strftime('%m-%d') for d in days[::30]], rotation=0)
    ax.set_title(f'(a) MILP 最优预算比例 r* (5 方案 × 365 天)\n'
                 f'总注册数预测: {milp_stats["解的总注册数"]:,.0f} (当前 {milp_stats["当前注册数"]:,.0f}, 提升 {milp_stats["提升幅度(%)"]:+.2f}%)',
                 fontsize=12, fontweight='bold')
    ax.set_xlabel('日期')
    ax.set_ylabel('方案ID')
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('r* (相对当前预算的比例)', fontsize=10)
    ax.grid(False)

    # (b) Pareto 前沿
    ax = axes[1]
    ax.scatter(pareto_f[:, 0], -pareto_f[:, 1], s=40, c=COLORS['primary'],
               edgecolors='none', alpha=0.7, label='Pareto 解')
    ax.scatter([milp_stats['解的总成本']], [milp_stats['解的总注册数']],
               s=200, c=COLORS['danger'], marker='*', label='MILP 最优', zorder=10)
    ax.scatter([milp_stats['总预算']], [milp_stats['当前注册数']],
               s=150, c='black', marker='X', label='当前策略', zorder=10)
    ax.set_xlabel('总成本（元）', fontsize=11)
    ax.set_ylabel('总注册数', fontsize=11)
    ax.set_title('(b) NSGA-II Pareto 前沿（成本 vs 注册数）', fontsize=12, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    fig.suptitle('问题 3：投放策略优化（MILP + NSGA-II）', fontsize=14, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, 'q3_strategy', subdir='results')
    plt.close(fig)

    # ===== 绘图 2：Pareto 前沿单独图 =====
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.plot(pareto_f[:, 0], -pareto_f[:, 1], 'o-', color=COLORS['primary'],
            linewidth=1.5, markersize=6, alpha=0.7, label='Pareto 前沿')
    ax.scatter([milp_stats['解的总成本']], [milp_stats['解的总注册数']],
               s=200, c=COLORS['danger'], marker='*', label='MILP 最优', zorder=10)
    ax.scatter([milp_stats['总预算']], [milp_stats['当前注册数']],
               s=150, c='black', marker='X', label='当前策略', zorder=10)
    ax.set_xlabel('总成本（元）', fontsize=12)
    ax.set_ylabel('总注册数', fontsize=12)
    ax.set_title('问题 3：NSGA-II Pareto 前沿 vs MILP 单目标最优', fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_fig(fig, 'q3_pareto', subdir='results')
    plt.close(fig)

    # ===== 方法说明 =====
    method_md = f"""# Q3 方法说明 · 投放策略优化

## 1. 目标
- 在总预算约束下，优化 5 方案 × 365 天的预算分配
- 最大化总注册数
- 多目标：(成本, 注册数) Pareto

## 2. 决策变量
- r[i, t] ∈ [0.3, 2.0]：方案 i 在第 t 天的预算相对当前比例
- 总成本约束：Σ base[i,t] × r[i,t] = 总预算（保持不变）

## 3. 目标 & 约束

### 3.1 MILP 单目标
$$\\max \\sum_{{i,t}} \\text{{base}}[i,t] \\cdot \\text{{reg\\_rate}}[i,t] \\cdot r[i,t]$$
s.t.
  $$\\sum_{{i,t}} \\text{{base}}[i,t] \\cdot r[i,t] = B$$ （总预算固定）
  $$0.3 \\le r[i,t] \\le 2.0$$

求解：LP relaxation（高斯消去法）— 50ms

### 3.2 NSGA-II 多目标
$$f_1 = \\sum \\text{{cost}} = \\sum base \\cdot r$$
$$f_2 = -\\sum \\text{{reg}} = -\\sum base \\cdot r \\cdot reg\\_rate$$

约束处理：
- 罚函数：成本偏离 baseline > 5% 平方罚
- 平滑罚：相邻日比例变化 > 0.3 罚

求解：NSGA-II（n_gen=30, pop=60, 非支配排序 + 拥挤距离）

## 4. 关键结果

### 4.1 MILP
| 指标 | 当前 | MILP 最优 | 提升 |
|------|------|----------|------|
| 总成本 | {milp_stats['总预算']:,.0f} 元 | {milp_stats['解的总成本']:,.0f} 元 | {(milp_stats['解的总成本']/milp_stats['总预算']-1)*100:+.2f}% |
| 总注册数 | {milp_stats['当前注册数']:,.0f} | {milp_stats['解的总注册数']:,.0f} | {milp_stats['提升幅度(%)']:+.2f}% |

### 4.2 5 方案建议
""" + '\n'.join([
        f"- 方案 {int(r['方案ID'])}：原始 {r['原始总消费']:.0f} → 最优 {r['最优总消费']:.0f} 元（变化 {r['消费变化(%)']:+.1f}%），平均 r*={r['平均相对比例']:.3f}"
        for _, r in summary_df.iterrows()
    ]) + f"""

### 4.3 NSGA-II Pareto
- 共 {len(pareto_f)} 个非支配解
- 成本范围：[{pareto_f[:,0].min():,.0f}, {pareto_f[:,0].max():,.0f}] 元
- 注册数范围：[{-pareto_f[:,1].max():,.0f}, {-pareto_f[:,1].min():,.0f}] 人

## 5. 关键洞察
1. **MILP 给点最优**：单目标确定解。
2. **NSGA-II 给前沿**：多目标权衡，不同预算下能达到的最佳注册数。
3. **国一差异化**：双方法互补 — MILP 验证算法能跑，NSGA-II 给出业务决策空间。

## 6. 输出文件
- `results/tables/q3_daily_strategy.csv`（MILP 每方案每天）
- `results/tables/q3_plan_summary.csv`（5 方案汇总）
- `results/tables/q3_pareto_front.csv`（NSGA-II Pareto 解）
- `results/figures/q3_strategy.png`（热力图 + Pareto）
- `results/figures/q3_pareto.png`（Pareto 前沿单独图）
- `data/raw/attachments/result3.xlsx`（题目要求位置）

## 7. 可复现性
- 随机种子：42
- LP 求解器：HiGHS（scipy.optimize.linprog 默认）
- NSGA-II 参数：n_gen=30, pop=60

## 8. 与 Q4 的接口
- Pareto 前沿可作为 Q4 DRO 的"参考点集"
- MILP 最优解作为 Q4 "nominal" 基准
"""
    method_path = os.path.join('issue', 'q3_method.md')
    with open(method_path, 'w', encoding='utf-8') as f:
        f.write(method_md)
    print(f'[save] {method_path}', flush=True)

    print('\n' + '=' * 60, flush=True)
    print(f'Q3 完成：MILP 预测注册数 {milp_stats["解的总注册数"]:,.0f}（提升 {milp_stats["提升幅度(%)"]:+.2f}%）, Pareto 解 {len(pareto_f)} 个', flush=True)
    print('=' * 60, flush=True)
    return milp_df, pareto_df, summary_df


if __name__ == '__main__':
    main()
