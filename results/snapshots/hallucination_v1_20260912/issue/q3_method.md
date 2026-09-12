# Q3 方法说明 · 投放策略优化

## 1. 目标
- 在总预算约束下，优化 5 方案 × 365 天的预算分配
- 最大化总注册数
- 多目标：(成本, 注册数) Pareto

## 2. 决策变量
- r[i, t] ∈ [0.3, 2.0]：方案 i 在第 t 天的预算相对当前比例
- 总成本约束：Σ base[i,t] × r[i,t] = 总预算（保持不变）

## 3. 目标 & 约束

### 3.1 MILP 单目标
$$\max \sum_{i,t} \text{base}[i,t] \cdot \text{reg\_rate}[i,t] \cdot r[i,t]$$
s.t.
  $$\sum_{i,t} \text{base}[i,t] \cdot r[i,t] = B$$ （总预算固定）
  $$0.3 \le r[i,t] \le 2.0$$

求解：LP relaxation（高斯消去法）— 50ms

### 3.2 NSGA-II 多目标
$$f_1 = \sum \text{cost} = \sum base \cdot r$$
$$f_2 = -\sum \text{reg} = -\sum base \cdot r \cdot reg\_rate$$

约束处理：
- 罚函数：成本偏离 baseline > 5% 平方罚
- 平滑罚：相邻日比例变化 > 0.3 罚

求解：NSGA-II（n_gen=30, pop=60, 非支配排序 + 拥挤距离）

## 4. 关键结果

### 4.1 MILP
| 指标 | 当前 | MILP 最优 | 提升 |
|------|------|----------|------|
| 总成本 | 1,425,950 元 | 1,425,950 元 | +0.00% |
| 总注册数 | 85,313 | 103,742 | +21.60% |

### 4.2 5 方案建议
- 方案 63563817：原始 15225 → 最优 16258 元（变化 +6.8%），平均 r*=0.775
- 方案 495403620：原始 215831 → 最优 212513 元（变化 -1.5%），平均 r*=1.185
- 方案 495817671：原始 171870 → 最优 180957 元（变化 +5.3%），平均 r*=1.096
- 方案 500635396：原始 841527 → 最优 776630 元（变化 -7.7%），平均 r*=1.178
- 方案 525368335：原始 181497 → 最优 239592 元（变化 +32.0%），平均 r*=0.980

### 4.3 NSGA-II Pareto
- 共 60 个非支配解
- 成本范围：[1,352,155, 2,246,029] 元
- 注册数范围：[82,485, 96,454] 人

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
