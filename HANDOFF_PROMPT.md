# 任务移交 · Q3/Q4 实现交接（CUMCM 2026 E 题 · SEM 广告投放策略优化）

---

## 0. 元指令

你正在接手一个**已完成 Q1、Q2 的 CUMCM 2026 E 题建模项目**。前任 agent 已完成：Q1 五方案 CRITIC + 行业阈值评分（综合 50.7/100，含节日扣分）；Q2 二维硬阈值关键词五类分类（result2.xlsx）。**待你完成的是 Q3（2025 16 天投放策略）与 Q4（2026 7 天不确定性投放策略）的实现**。

你不是从零开始：项目已有**事实沉淀**（`.cursor/rules/project-context.mdc`）、**已验证数据契约**（`PoC_REPORT.md`）、**已审定偏差清单**（`BIAS_REPORT.md`）、**已落地方法架构**（`Q3Q4_Method_Architecture.md`）。你的工作是：**在此沉淀之上**完成 Q3/Q4 实施、产出 result3/4.xlsx、对接 §5.3/§5.4 论文文字。

**关键判断准则**：遇到"题面 vs 模板 vs 我以为"的冲突时，**以附件 2 模板列结构为唯一权威**（mdc 红线第 1 条）。题面文字与模板不一致的，按模板落，差异在论文文字中显式说明。

---

## 1. 契约层（不可违反的事实）

### 1.1 数据契约（附件 1，3 sheet 严格列名）

| Sheet | shape | 列（**严格顺序，严格列名，含尾部空格**）| 粒度 |
|---|---|---|---|
| Sheet1 | (2627, 10) | 日期, 方案ID, 推广单元ID, 展现量, 点击量, 消费额, 上方位展现量, 上方位首位展现量, 上方位点击量, 上方位消费额 | 推广单元-日级 |
| Sheet2 | (365, 2) | **日期**(尾部空格), **新注册数**(尾部空格) | 日级（必须 `df.columns.str.strip()`）|
| Sheet3 | (2227, 9) | 序号, 关键词, 方案ID, 推广单元ID, 消费额, 点击量, 浏览量, 跳出率, 平均访问时长 | 关键词-年累计（**无日期列**）|

### 1.2 输出契约（附件 2，模板列结构为唯一权威）

| 输出 | shape | 列（**严格顺序，严格列名**）| 时间范围 | 行粒度 |
|---|---|---|---|---|
| **result2.xlsx**（✅已交付）| (2227, 8) | 方案ID, 推广单元, 序号, **黄金词, 重点词, 潜力词, 问题词, 无效词** | 2025 全年 | 关键词 |
| **result3.xlsx** | (5K~20K, 9) | 日期, 方案ID, 推广单元, 关键词, 投入金额, **预期展位**, 预期点击量, 预期浏览量, 预期注册量 | **2025-02-01~02-08 + 08-01~08-08（16 天）** | 推广单元×关键词×天 |
| **result4.xlsx** | (1K~5K, 9) | **与 result3 列结构 100% 相同** | **2026-09-11~09-17（7 天）** | 推广单元×关键词×天 |

**绝对约束**：
- ❌ 禁止扩展 result3/4 至 11 列（题面"6 个期望值"是文字描述，模板只支持 4 个；6 因子扰动仅用于内部不确定性建模 + 论文 §5.4 文字）
- ❌ 禁止把 result3 时间范围扩到全年 365 天
- ❌ 禁止把决策粒度从"推广单元×关键词×天"降级到"方案×天"
- ❌ 禁止把 4 个预期指标简化为 1 个或 2 个

---

## 2. 沉淀层（已决策 / 已验证 · 无需再讨论）

### 2.1 已锁定的决策（来自 BIAS_REPORT.md 2026-09-12 16:57）

| 决策 ID | 内容 | 出处 |
|---|---|---|
| **D-Q2-001~005** | Q2 5 类规则 = 黄金/重点/潜力/问题/无效；阈值 = 中位数；无效词 = 消费=0；行粒度 = 2227 明细 + 60 聚合 | `issue/q2_implementation_plan.md` |
| **D-Q3Q4-001** | Q4 模板 = result3 同结构，**严格 4 列**（不再讨论 4/6 列之争）| `BIAS_REPORT.md` P0-3 |
| **D-Q3Q4-002** | 决策变量 = **(d, k)**（k 唯一确定方案+推广单元），MILP 规模 14,544（原 174,528 减 92%）| `BIAS_REPORT.md` P1-2 |
| **D-Q3Q4-003** | Q3 预算分段：02 月 13,681.15 元 + 08 月 37,483.78 元（不合并）| `BIAS_REPORT.md` P1-3 |
| **D-Q3Q4-004** | Q4 预算上限 = 2025-09-11~17 实际 23,488.02 元 | `BIAS_REPORT.md` P0-2 |
| **D-Q3Q4-005** | "预期展位"口径 = Sheet1 列 6 "上方位展现量"（top-position impressions，占总展现量 27%）| `BIAS_REPORT.md` P1-1 |
| **D-Q3Q4-006** | Q3 本质 = **历史反事实优化**（非未来预测）；Q4 = 未来预测 + 不确定性 | `BIAS_REPORT.md` P0-1 |
| **D-Q3Q4-007** | "投放模型"三层表达：MILP 公式 + 业务规则摘要 + 关联规则集合 | `BIAS_REPORT.md` P2-2 |
| **D-Q3Q4-008** | **FP-Growth 数据源代理**（**BIAS_v2 新增**）：Sheet1 无关键词列 → 用"推广单元-入选项池（Q2 黄金 ∪ 重点 ∪ 潜力）"代理；论文 §5.3.3 须显式说明 | `Q3Q4_Method_Architecture.md` §2.2 Layer 2 / §12 V2-1 |
| **D-Q3Q4-009** | **Q3 校验改写**（**BIAS_v2 修订**）：旧"历史回放"逻辑矛盾（反事实解 ≠ 实际）→ 改用"代理精度"校验（评估 §2.2.1 代理假设精度，比值 ∈ [0.85, 1.15]）；论文 §5.3.4 加 X vs Y 对比表 | `Q3Q4_Method_Architecture.md` §2.3 / §12 V2-2 |
| **D-Q3Q4-010** | **代理敏感性分析**（**BIAS_v2 新增**）：对 §2.2.1 三个代理比值做 ±30% 缩放扰动（5 档），重解 MILP；通过标准 = 决策变量翻转 < 30% + Top-50 词 overlap ≥ 70%；输出 `q3_proxy_sensitivity.{csv,png}`；论文 §5.3.2 显式声明 | `Q3Q4_Method_Architecture.md` §2.2.2 / §12 V2-3 |
| **D-Q3Q4-011** | **Q4 "2025 年的投入"口径显式声明**（**BIAS_v2 新增**）：取 **2025 同期 23,488.02 元**而非全年 142.59 万元；理由 = 业务场景最相似 + 更严格；论文 §5.4.1 须显式说明 | `Q3Q4_Method_Architecture.md` §3.1 设计原则 6 / §12 V2-4 |

### 2.2 已验证的事实（来自 PoC_REPORT.md 2026-09-12 16:42）

| 事实 | 数值 |
|---|---|
| Sheet3 全年累计 ≈ Sheet1 全年合计 | 1,425,949.81 vs 1,425,949.79（差 < 0.01%）|
| 无效词（890 词）= 消费=0 且 跳出率/访问时长="/" | 100% 重合 |
| Q3 16 天总消费 | **51,164.93 元** |
| Q3 16 天推广单元-日均 | max=2,237.33 / min=1.58（中位 ~500）|
| Q4 同期 7 天（2025-09-11~17）消费 | **23,488.02 元**（日均 3,355.43）|
| Q4 单元-日均 | max=2,721.19 / min=0.00 / 中位 20.86 |
| Sheet1 推广单元级 30 天滚动 CV | 消费 0.46~1.91（中位 0.65）/ 点击 0.45~1.83（中位 0.61）/ 展现 0.33~1.70（中位 0.49）|
| Q3/Q4 入选项池 | 黄金(431) + 重点(238) + 潜力(240) = **909 词**（占 2227 = 40.82%）|

### 2.3 已批准的方法栈（白名单）

- ✅ **MILP via PuLP / OR-Tools**（Q3 决策）
- ✅ **FP-Growth 关联规则**（Q3 业务层）
- ✅ **Two-Stage SP via SAA**（Q4 不确定性）
- ✅ **代理变量法**（Q3 Layer 1.5：关键词-日级 = 推广单元-日级 × 消费占比）
- ✅ **对数正态 / 截断正态**（Q4 扰动分布）
- ✅ **CRITIC + Bootstrap + 龙卷风**（Q1 复用）

❌ **禁止引入**：Transformer / Attention / GAN / DRL / NSGA-II / DRO 求解器 / CPLEX 商业授权

---

## 3. 任务层（你的工作 · 4 个交付物）

### 3.1 数据准备（30 min）

- 读 Sheet1/2/3，生成 `data/processed/q3/` 下的 5 维特征 pkl（2227 词 × 5 维 = 消费/CPC倒数/浏览/1-跳出率/访问时长）
- 严格 strip Sheet2 列名尾部空格
- Sheet3 消费与 Sheet1 校验一致性（应 < 0.01% 差异）

### 3.2 Q3 关联规则挖掘（60 min）

- **算法**：FP-Growth（mlxtend 或自实现）
- **数据源**：Sheet1 (方案-推广单元-日) 重构"每日实际投放关键词集"
- **参数**：min_support=0.05 / min_confidence=0.6
- **输出**：`results/tables/q3_keyword_assoc_rules.csv`（≥ 50 条）+ `results/figures/q3_keyword_assoc_network.png`
- **业务价值**：论文 §5.3.3 显式回答题面"考虑关键词关联关系"

### 3.3 Q3 MILP 决策（90 min）

- **决策变量**：`x[d, k]` ∈ {0,1}、`y[d, k]` ≥ 0（d ∈ {1..16}, k ∈ {909 入选项}）
- **目标函数**：`max Σ (α·r_click + β·r_browse + γ·r_reg) · y[d, k] + δ · 关联应用率`
  - α=0.5, β=0.3, γ=0.2, δ=0.05（论文 §5.3.2 给 3 档敏感性）
- **约束**：见 Q3Q4_Method_Architecture.md §2.3（5 硬 + 1 软）
- **预算**：
  - 02 月段（d ∈ 02-01~08）：∑ y ≤ **13,681.15 元**
  - 08 月段（d ∈ 08-01~08）：∑ y ≤ **37,483.78 元**
  - 推广单元-日：`∑_{k ∈ unit p} y[d, k] ≤ B_unit[p, d]`（Sheet1 实际值）
- **求解器**：PuLP（首选）/ OR-Tools（备选）
- **infeasible fallback**：见 Q3Q4_Method_Architecture.md §2.3 3 级降级
- **输出**：`results/excel/result3.xlsx`（严格 9 列对齐模板）

### 3.4 Q4 不确定性建模 + Two-Stage SP（90 min）

- **6 因子扰动参数化**（Sheet1 推广单元级 30 天滚动 CV，PoC 实证）：
  | 因子 | 分布 | CV 来源 |
  |---|---|---|
  | 竞价 CPC | LogNormal | 消费额/点击量 30 天 CV |
  | 展现量 | LogNormal | Sheet1 展现量 30 天 CV（中位 0.49）|
  | 展现位 | 截断正态 [1,10] | Sheet1 上方位展现量 30 天 CV |
  | 点击量 | LogNormal | Sheet1 点击量 30 天 CV（中位 0.61）|
  | 浏览量 | LogNormal | Sheet1 消费额 CV 代理 |
  | 注册量 | Poisson-Pareto | Sheet2 日级 CV 代理 |
- **预算上限**：**23,488.02 元**（D-Q3Q4-004）
- **求解**：SAA, N=1000 scenarios；λ ∈ {0, 0.5, 1.0} 三档对比
- **输出**：`results/excel/result4.xlsx`（4 列）+ `results/tables/q4_expected_with_ci.csv`（6 期望 + 6 CI）

### 3.5 论文 §5.3/§5.4 文字（90 min）

- §5.3.1：Q3 问题定性（历史反事实优化 vs 未来预测）
- §5.3.2：MILP LaTeX 公式 ≥ 5 行 + 5 约束
- §5.3.3：FP-Growth 关联网络图解读（业务可解释）
- §5.3.4：4 指标反事实估算公式（代理变量法）
- §5.4.1：Q4 6 因子不确定性来源显式标注（每因子 1 行"参数来自 Sheet1/Sheet2 30 天 CV"）
- §5.4.2：**必须文字回答 6 期望值**（即使 Excel 只有 4 列）+ 95% CI
- §5.4.3：λ ∈ {0, 0.5, 1.0} 鲁棒性对比图
- §5.4.4：MILP 公式 + 约束的 LaTeX

---

## 4. 输出契约（交付清单 + 验证点）

### 4.1 文件交付

```
results/excel/result3.xlsx          # 5K-20K 行 × 9 列（严格对齐）
results/excel/result4.xlsx          # 1K-5K 行 × 9 列（严格对齐）
data/processed/q3/keyword_5d.pkl    # 2227 词 × 5 维
data/processed/q3/milp_solution.pkl # 决策变量存档
results/tables/q3_keyword_assoc_rules.csv
results/tables/q3_daily_strategy.csv
results/tables/q3_indicator_summary.csv
results/tables/q4_uncertainty_params.csv
results/tables/q4_expected_with_ci.csv
results/figures/q3_keyword_assoc_network.png
results/figures/q4_uncertainty_distribution.png
results/figures/q4_fan_chart.png
paper/paper.md §5.3 / §5.4 文字
issue/q3_method.md / q4_method.md 实施文档
src/q3_data_prep.py / q3_association.py / q3_milp.py
src/q4_uncertainty.py / q4_solver.py
```

### 4.2 验证点（DoD · 强制）

| # | 验证项 | 通过标准 |
|---|---|---|
| V1 | result3.xlsx 列名 | **严格匹配模板 9 列**，无扩展 |
| V2 | result3 行数 ∈ [5K, 20K] | 通过 |
| V3 | result3 预算守门 | 02 段 ≤ 13,681.15 / 08 段 ≤ 37,483.78 |
| V4 | result3 入选项 100% ∈ 黄金∪重点∪潜力 | 严格相等 |
| V5 | result3 关联规则 ≥ 50 条 | 满足 |
| V6 | result4.xlsx 列名 | **严格 9 列与 result3 同**（D-Q3Q4-001）|
| V7 | result4 期望总预算 ≤ 23,488.02 | 严格 ≤ |
| V8 | 6 因子 KS 检验 p > 0.05 | 每个推广单元分别 KS |
| V9 | λ ∈ {0, 0.5, 1.0} Top 50% 词 overlap ≥ 80% | 鲁棒性 |
| V10 | §5.3/§5.4 LaTeX 公式 ≥ 10 行 | 论文可读性 |
| V11 | RUN_LOG ≥ 30 行（每动作 1 行）| 自动日志 |
| V12 | WORK_STATE Q3/Q4 路线图 ✅ | 状态同步 |

### 4.3 反模式（必须避免）

| 错误 | 后果 |
|---|---|
| 用 GMM/KMeans 替代二维硬阈值 | 偏离题面（Q2 已锁定 5 类规则）|
| 用 NSGA-II 多目标替代单目标 MILP | 解释成本高，偏离"国奖不堆方法"|
| 用 DRO 求解器替代 Two-Stage SP | 公式难懂，偏离可解释原则 |
| 自创 result 列（如 "CPC"、"展现量" 6 列）| **致命**——违反附件 2 模板 |
| 把"预期展位"写成"展现量" | 口径错误（D-Q3Q4-005）|
| 把 Q3 当作未来预测 | 定性错误（D-Q3Q4-006）|
| 用 Sheet3 跨词 CV 替代 Sheet1 推广单元 30 天 CV | 误用统计口径（PoC P1 关键）|
| 跑完 30 分钟才补 RUN_LOG | mdc v3 红线第 11 条 |
| 在 result3 写"投入金额=0"的空投放行 | 浪费行数，模板不要求 |

---

## 5. 工作流（顺序 · 严禁跳步）

```
[Step 0] 通读本提示词 + .cursor/rules/project-context.mdc
[Step 1] 读 PoC_REPORT.md（6 事实已验证）+ BIAS_REPORT.md（10 偏差已修订）
[Step 2] 读 Q3Q4_Method_Architecture.md（654 行，方法架构）
[Step 3] 读 issue/q2_implementation_plan.md（D-Q2-001~005）
[Step 4] 用 pd.read_excel 读附件 2 全部模板，确认列名（**严禁跳过**）
[Step 5] TodoWrite 建任务表
[Step 6] 开始 §3.1 数据准备
[Step 7] §3.2 FP-Growth 关联
[Step 8] §3.3 MILP 求解 result3
[Step 9] §3.4 Two-Stage SP 求解 result4
[Step 10] §3.5 论文 §5.3/§5.4 文字
[Step 11] §4.2 验证点 V1-V12 全部通过
[Step 12] 同步 WORK_STATE / DECISION_LOG
```

**每个 Step 完成立即 append RUN_LOG.md 一行**（格式：`[YYYY-MM-DD HH:MM] **S标识 动作** | 产物 | OK/FAIL`）。

---

## 6. 一句话总结

> 你在做的事 = **用 PuLP MILP 给 Q3 找到 16 天最优投放策略（决策变量 14,544 个，受 02/08 月段预算分段约束），用 SAA 给 Q4 找到 7 天 6 因子扰动下的期望最优策略，两个 result 文件都严格 9 列对齐附件 2 模板**。

---

**项目根目录**：`D:/CUMCM2026Problems`
**Python 入口**：`python -m src.q1_main`（Q1 复用）；`python -m src.q3_milp`（Q3 实施后）；`python -m src.q4_solver`（Q4 实施后）
**关键文件**：
- `.cursor/rules/project-context.mdc`（13 节，含强制流程 + 自动日志规则）
- `Q3Q4_Method_Architecture.md`（方法架构 · 654 行）
- `PoC_REPORT.md`（数据探测 · 196 行）
- `BIAS_REPORT.md`（偏差清单 · 263 行）
- `issue/q2_implementation_plan.md`（Q2 决策 · 392 行）
- `data/raw/attachments/附件2/result{2,3,4}.xlsx`（输出模板）

---

**祝顺利。若发现本提示词与附件 2 模板冲突，以模板为准；若发现本提示词与项目事实沉淀冲突，以最近一次修订日志为准；若有新的工程洞察，append 到 `BIAS_REPORT_v2.md` 而非修改本文档。**
