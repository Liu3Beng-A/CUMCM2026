# -*- coding: utf-8 -*-
p = r'paper\paper.md'
content = open(p, 'r', encoding='utf-8').read()

# Update §5.3.4 (add A4 finding)
old_534 = '若需更可信的注册预测，应补充日级关键词-注册关联数据。'
new_534 = '''若需更可信的注册预测，应补充日级关键词-注册关联数据。

**5.3.4-补充 · 关联规则应用率量化**（B 级补强）：MILP 解中 §5.3.3 约束 5 "关联词同期激活" 的实际触发率。统计方法：MILP 解 89 行（16 天 × 12 单元）中按 (date, unit) 分组，每组激活关键词集合与 `q3_keyword_assoc_rules.csv`（100 条规则：cosine 50 + fp_growth 50）做交集，统计同时出现 2 词的规则数。

**结果**：89 个 (date, unit) 组中，**每组均仅激活 1 个关键词**（预算极紧，每单元日均预算约 23488.02/7/11 ≈ 305 元，单词单价即占满），导致应用率 = **0%**（高置信规则 lift≥0.7 应用率同为 0%）。

**诚实披露**：本节是关联挖掘的"实际价值边界"。关联规则作为"知识发现"仍具价值（识别相似关键词画像），但作为 MILP 硬约束在当前预算约束下未触发任何同期共激活。详见 `results/tables/q3_assoc_adoption.csv`（89 行详细表）+ `q3_assoc_adoption_summary.json`（汇总统计）+ `q3_assoc_network_with_solution.png`（关联网络图，红色节点为激活词）。

**含义**：
- 若需触发关联约束，需放宽"每单元日均预算"或加入"多元化目标"（除点击外加权关联多样性）。
- 实际投放中，因预算紧张，运营商也会理性选择"集中投入最优词"而非"分散关联词"，这与代理求解的策略一致。'''

if old_534 in content:
    content = content.replace(old_534, new_534, 1)
    print('[OK] §5.3.4 A4 补充已插入')
else:
    print('[FAIL] §5.3.4 anchor not found')

# Update §5.3.5 (B6 重构)
old_535 = '#### 5.3.5 敏感性分析（§2.2.2）\n\n3 比值 × 5 档（±30%, ±15%, 0%） = 15 场景：\n- r_click ±30%：点击量 ±30%（线性放大，share-Pearson=0.983 代理可信）\n- r_browse ±30%：浏览量 ±30%\n- r_reg ±30%：**注册代理失效**（share-Pearson=-0.096）→ 扰动无实际意义，仅作为说明性测试\n\n详见 `results/tables/q3_sensitivity_summary.csv` 与 `results/figures/q3_sensitivity.png`。'

new_535 = '''#### 5.3.5 敏感性分析（§2.2.2 · B6 重构）

**重构前**（v1）：3 比值 × ±30% 扰动 = 15 场景（含 **r_reg**，但 share-Pearson=-0.096 代理失效 → 扰动无意义）

**重构后**（v2）：
1. **代理比值扰动**（删 r_reg）：r_click / r_browse × 5 档（±30%, ±15%, 0%）= **10 场景**
2. **目标函数权重 3 档**（新增）：仅 click/browse 权重变化（删除 reg 代理），MILP 重新求解
   - W=(1.0, 0.0)：纯 click 目标
   - W=(0.7, 0.3)：click 主导
   - W=(0.3, 0.7)：browse 主导

**结果摘要**：

| 类别 | 场景数 | 主要结论 |
|---|---|---|
| 代理比值扰动（删 r_reg）| 10 | r_click ±30% → 点击量 ±30%（线性放大，share-Pearson=0.983 代理可信）；r_browse ±30% → 浏览量 ±30%（browse = click × 2.93） |
| 目标函数权重 3 档 | 3 | 三档下结果相同（投入 51,165 元，点击 54,200 次）→ **决策稳健**：候选集由"高 r_click 关键词"主导，browse 权重变化不影响排序 |

详见 `results/tables/q3_sensitivity_v2.csv`（13 场景）+ `q3_sensitivity_v2_summary.json` + `q3_sensitivity_v2.png`。

**诚实声明**：r_reg 扰动从 §5.3.5 中**永久删除**（注册代理失效，扰动只会放大噪声）。原 `q3_sensitivity_summary.csv` 仅作历史保留。'''

if old_535 in content:
    content = content.replace(old_535, new_535, 1)
    print('[OK] §5.3.5 B6 重构已替换')
else:
    print('[FAIL] §5.3.5 anchor not found')

# Update §5.4.2 (A1+A2+A3)
old_542 = '''**简化（PoC）**：
- **第一阶段**（here-and-now）：选单元×关键词激活（二值 $y_{d,u,k}$）
- **第二阶段**（wait-and-see）：日级投入分配（连续 $x_{d,u,k}$）
- **场景采样**：20 个场景（PoC 简化，未做 SAA）
- **目标**：场景 0 下最大化期望收益

**决策变量**：$x_{d,u,k} \\in \\mathbb{R}^+$（每单元每关键词每天投入）

**目标函数**：
$$\\max \\sum_{d,u,k} \\mathrm{coef}_{u,s_0} \\cdot x_{d,u,k}$$
$$\\mathrm{coef}_{u,s_0} = (0.4 r^{\\text{click}}_u + 0.1 r^{\\text{browse}}_u + 0.5 r^{\\text{reg}}_u) \\cdot \\frac{\\xi^{\\text{click}}_{u,s_0} + \\xi^{\\text{reg}}_{u,s_0}}{2}$$

其中 $\\xi^{\\text{click}}_{u,s_0}, \\xi^{\\text{reg}}_{u,s_0}$ 为场景 0 下单元 $u$ 的点击/注册乘子。

**约束**：
1. **总预算**：$\\sum x_{d,u,k} \\le 23{,}488.02$
2. **big-M**：$x_{d,u,k} \\le M \\cdot y_{d,u,k}$
3. **强制分散**：每 (单元, 日期) ≤ 25 关键词
4. **日预算上限**：每单元每日 ≤ $\\frac{23{,}488.02}{7 \\times 11} \\times 2$

**求解器**：PuLP + CBC
- 决策变量：**15,470** 个
- 求解时间：~15s
- 状态：**Optimal**
- 目标值：23,631.91'''

new_542 = '''**A1+A2+A3 升级**（vs 原 PoC）：
- **A1 协方差建模**：原独立假设（PoC 简化）→ **Spearman 相关矩阵 + Gaussian copula 采样**（基于历史 30 天 330 个样本估算，6 因子矩阵见 `data/processed/q4/q4_factor_cov_matrix.csv`）。**主要相关性**：clicks↔regs=0.872, impressions↔top_imp=0.810, impressions↔clicks=0.767；cpc 与其他因子相关性弱（<0.35）。
- **A2 期望值修正**：原仅用场景 0 计算 coef → **全场景均值** $\\mathrm{coef}_u = c_{\\text{base}} \\cdot \\mathbb{E}_s[(\\xi^{\\text{click}}_{u,s} + \\xi^{\\text{reg}}_{u,s}) / 2]$
- **A3 场景数 + λ 鲁棒性**：20 场景 → **100 场景**（满足 DoD V9）；**λ ∈ {0.0, 0.5, 1.0} 三档鲁棒性扫描**（λ 权衡"期望值"vs"方差"）

**第一阶段**（here-and-now）：选单元×关键词激活（二值 $y_{d,u,k}$）
**第二阶段**（wait-and-see）：日级投入分配（连续 $x_{d,u,k}$）
**场景采样**：100 场景（Gaussian copula，6 因子相关结构）
**目标**：max 全场景期望收益

**决策变量**：$x_{d,u,k} \\in \\mathbb{R}^+$（每单元每关键词每天投入）

**目标函数（λ 形式）**：
$$\\max \\mathbb{E}_s\\left[\\sum_{d,u,k} \\mathrm{coef}_{u,s} \\cdot x_{d,u,k}\\right] - \\lambda \\cdot \\mathrm{std}_s\\left[\\sum_{d,u,k} \\mathrm{coef}_{u,s} \\cdot x_{d,u,k}\\right]$$

其中：
$$\\mathrm{coef}_{u} = (0.4 r^{\\text{click}}_u + 0.1 r^{\\text{browse}}_u + 0.5 r^{\\text{reg}}_u) \\cdot \\frac{\\mathbb{E}_s[\\xi^{\\text{click}}_{u,s}] + \\mathbb{E}_s[\\xi^{\\text{reg}}_{u,s}]}{2}$$

**约束**：
1. **总预算**：$\\sum x_{d,u,k} \\le 23{,}488.02$（工程硬约束放宽至 ≤ 23,488.10 预留 PuLP/CBC 浮点精度）
2. **big-M**：$x_{d,u,k} \\le M \\cdot y_{d,u,k}$
3. **强制分散**：每 (单元, 日期) ≤ 25 关键词
4. **日预算上限**：每单元每日 ≤ $\\frac{23{,}488.02}{7 \\times 11} \\times 2$

**求解器**：PuLP + CBC
- 决策变量：**15,470** 个
- 场景数：**100**
- 求解时间：~47s/λ 档（共 3 档 × 47s ≈ 141s）
- 状态：**Optimal**（3 档均）
- 目标值（期望值口径）：**33,803** 元（vs 原独立假设 32,830 元，提升 +3%）

**λ 三档鲁棒性结果**：

| λ | 目标值 | 总投入 | 激活行数 | 求解时间 |
|---|---|---|---|---|
| 0.0 | 33,803.08 | 23,488.02 | 39 | 47.1s |
| 0.5 | 33,803.08 | 23,488.02 | 39 | 47.2s |
| 1.0 | 33,803.08 | 23,488.02 | 39 | 47.1s |

**结论**：λ 三档目标值稳定（CV=0.0000），决策对风险偏好不敏感（候选集由预算上限主导）。详见 `results/tables/q4_lambda_robustness.csv` + `q4_lambda_robustness.png`。

**主输出**：`results/excel/result4_v2.xlsx`（39 行，严格 9 列对齐附件 2）+ `q4_6metrics_extended_v2.csv`（6 因子期望值扩展）+ `q4_two_stage_v2_summary.json`。'''

if old_542 in content:
    content = content.replace(old_542, new_542, 1)
    print('[OK] §5.4.2 A1+A2+A3 升级已替换')
else:
    print('[FAIL] §5.4.2 anchor not found')

open(p, 'w', encoding='utf-8').write(content)
print('done')
