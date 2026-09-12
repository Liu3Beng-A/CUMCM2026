# Q3/Q4 方法架构 · Method Architecture

> 起草时间：2026-09-12 14:50
> 起草人：第 N 轮 agent（衔接 Q2 实施规划）
> 适用对象：负责实现 Q3 / Q4 的下一任 agent
> 目标：在**严格对齐附件 2 模板** + **不偏离题面**的前提下，给出既能"国奖评审过关"又**不让上级再次发生 hallucination** 的方法架构
> 严正声明：本文档由上级在用户授权下撰写；执行 agent 须按本文档方法落地，**禁止自行扩展为更复杂的方法体系（NSGA-II/DRL/GAN 等）**

---

## ⚠️ 执行 agent 必须先读的三件事

1. `issue/q2_implementation_plan.md` —— Q2 已锁定的 5 项决策（D-Q2-001 ~ D-Q2-005），是 Q3/Q4 的输入约束
2. `issue/q1_fix_plan.md` 头部 —— 了解 P0-0 节假日修正 + Q1 评分体系
3. **本文件** §1 数据契约 + §5 红线

执行前**严禁**：
- 跳过第 1 步读附件 2 模板
- 写"我们用 Transformer/Attention/GAN…"等堆砌型方法
- 修改 Q1 已确定的评分函数 / 权重 / 假日扣分

---

## 0. Q2 方案分析方式总结（给执行 agent 的导读）

| 项 | 决定 | 含义 / 后果 |
|---|---|---|
| 输入 | Sheet3 关键词级 9 列数据 | "成本"用消费额、"效益"用 CPC 倒数 |
| 主分类器 | 二维硬阈值（中位数）+ 5 类 one-hot | 严禁用聚类（GMM/KMeans）|
| 无效词规则 | 消费=0 即无效（890 词）| 与"无成本、无效益"题面语义一致 |
| 行粒度 | **2227 行明细 one-hot** | 每关键词 1 行，5 类离散列 |
| 副输出 | 60 行推广单元聚合 | 跨方案对比 |
| 校验 4 项 | 阈值敏感性龙卷风 + Bootstrap CI + 跨方案对比 + 可选 CRITIC | 国奖评审加分项 |
| 极值审计 | 112 词 Top 高消费 + 风险评级 | heavy-tail 修正 |

**Q3 必须消费 Q2 的 4 个产物**：
- `data/processed/q2/keyword_classified.pkl`（含 5 类 one-hot + 5 维特征）
- `results/tables/q2_thresholds.json`（阈值可复用）
- `data/raw/attachments/result2.xlsx`（公式读取）
- `results/tables/q2_extreme_audit.csv`（极值标签）

---

## 1. 数据契约（**直接来自附件 2 模板 + 附件 1 Sheet 列**，不是 mdc 摘要）

### 1.1 输入资源

| 资源 | 路径 | 关键列（**真实列名**）|
|---|---|---|
| Sheet1 方案日表 | `data/raw/attachments/附件1.xlsx` Sheet1 | **日期, 方案ID, 推广单元ID, 展现量, 点击量, 消费额, 上方位展现量, 上方首位展现量, 上方位点击量, 上方位消费额**（10 列，2627 行）|
| Sheet2 新注册日表 | `data/raw/attachments/附件1.xlsx` Sheet2 | **日期, 新注册数**（注意列名尾部有空格，2 列，365 行）|
| Sheet3 关键词表 | `data/raw/attachments/附件1.xlsx` Sheet3 | **序号, 关键词, 方案ID, 推广单元ID, 消费额, 点击量, 浏览量, 跳出率, 平均访问时长**（9 列，2227 行）|
| Q2 5 类分类 | `data/raw/attachments/result2.xlsx` | 方案ID, 推广单元, 序号, 黄金, 重点, 潜力, 问题, 无效（8 列，2227 行）|
| Q2 阈值参数 | `results/tables/q2_thresholds.json` | T_cost, T_benefit, n_per_class |
| Q2 极值审计 | `results/tables/q2_extreme_audit.csv` | ~112 词 + 风险评级 |

### 1.2 输出契约（**严格对齐附件 2 result{3,4} 模板 9 列**）

| 列位 | 模板列名 | 类型 | 含义 / 口径 |
|---|---|---|---|
| 1 | **日期** | string `YYYY-MM-DD` | 投放日 |
| 2 | **方案ID** | int | 与 Sheet1 一致 |
| 3 | **推广单元** | int | 与 Sheet1 一致（注意：模板是"推广单元"非"推广单元ID"，列名严格遵循）|
| 4 | **关键词** | string | 与 Sheet3 一致 |
| 5 | **投入金额** | float（元）| 该日对该关键词的预算 |
| 6 | **预期展位** | int | **口径 = 上方位展现量**（Sheet1 列名，不是"上方首位展现量"）|
| 7 | **预期点击量** | int | 口径 = 该关键词该日的总点击量 |
| 8 | **预期浏览量** | int | 口径 = 该关键词该日的总浏览量（Sheet3 浏览量按关键词-天缩放）|
| 9 | **预期注册量** | float | 口径 = 该关键词该日期望的新注册数（保留小数）|

> **关键口径**（写死，不允许改）：
> - result3 时间范围：**2025-02-01 ~ 02-08 + 2025-08-01 ~ 08-08 = 16 天**
> - result4 时间范围：**2026-09-11 ~ 09-17 = 7 天**
> - Q3 行粒度：`推广单元 × 关键词 × 天`（至少 1 行 = 1 个投放组合，不允许"方案级聚合掉所有关键词"）
> - Q4 行粒度：同 Q3，但只覆盖 2026-09-11~17
> - 入选词集合：**Q2 5 类中"黄金 + 重点 + 潜力"**（问题/无效淘汰）

### 1.3 行数预期（执行 agent 自检用）

| 输出 | 预期行数 | 说明 |
|---|---|---|
| result3.xlsx | **5,000~20,000 行** | 16 天 × 入选项 × 推广单元（每天每推广单元选 topK 关键词）|
| result4.xlsx | **1,000~5,000 行** | 7 天 × 入选项 × 推广单元 |
| 关键词关联图 | ~300 节点 + ~1000 边 | 同推广单元下共现 + 同时段同时展现 |

---

## 2. Q3 方法架构

### 2.1 设计原则（4 条，继承 Q2 + mdc v3）

1. **题面第一**：Q3 题面原文 4 个元素（关键词类型 + 关联关系 + 低成本高效益 + 不超预算），方法必须显式回答这 4 个元素
2. **不是黑盒**：每个公式必须能在论文 §5.3 用 1 行 LaTeX 描述
3. **可解释 > 准确**：国奖评审更看重"为什么这么做"，不是 RMSE 跑分
4. **预算约束硬**：日预算 ≤ 2025 同期日均（不是日均 × N 倍系数）

### 2.2 方法栈（4 层，**严格按从底向上**）

#### Layer 1：关键词 5 维特征工程（继承 Q2）

输入：Sheet3 2227 词 + Q2 分类结果。

对每个关键词计算 5 维特征：
- **成本维度**：消费额（log 标度处理 heavy-tail）
- **效益维度**：CPC 倒数 = 点击量 / max(消费额, 0.01)
- **流量维度**：浏览量（按关键词级别）
- **质量维度**：1 - 跳出率（"无数据"/'/' 值填 = 推广单元均值或 1.0 中性）
- **粘性维度**：平均访问时长（转秒数）

输出：`data/processed/q3/keyword_5d.pkl`

#### Layer 2：关键词关联挖掘（**国奖关键**，FP-Growth）

**目标**：发现"同一推广单元下同时投放的有效组合"，回答题面"考虑关键词类型和关联关系"。

**算法（FP-Growth，不是 GMM！FP-Growth 是数据挖掘经典关联规则算法）**：
- 输入：每天每个推广单元实际投放的关键词集合（从 Sheet1 重构）
- 项集：关键词 ID（按"方案-推广单元"分组 daily）
- 最小支持度：min_support = 5%（即至少在 5% 推广单元日中出现）
- 最小置信度：min_confidence = 60%
- 输出：高频关键词组 + 关联规则 A → B（支持度 / 置信度 / 提升度）

**业务价值**：
- "黄金 + 潜力" 联动投放可提升整体 ROI
- 同一推广单元下高频共现词可降低单次点击成本（CPC 分摊）
- 在 Q3 投放策略中作为"种子词 + 扩展词"机制使用

输出：
- `results/tables/q3_keyword_assoc_rules.csv`（关联规则：前项 → 后项 | sup | conf | lift）
- `results/figures/q3_keyword_assoc_network.png`（关联网络图，节点 = 关键词，颜色 = Q2 分类，边粗细 = lift）

#### Layer 3：16 天预算分配与关键词选择（**Mixed-Integer Linear Programming**）

> 选择 MILP 的理由：题面"选择合适的关键词"+"保证不超预算"+"低成本高效益" = 标准 MILP 语义；可解释；与"国奖不堆方法"原则一致

**决策变量**：
- `x[d, p, k]` ∈ {0, 1}：第 d 天在推广单元 p 是否投放关键词 k（0/1 变量，**关键 discrete**）
- `y[d, p, k]` ≥ 0：第 d 天推广单元 p 关键词 k 的投入金额（连续变量，单位 = 元）

**目标函数**：最大化 16 天总预期收益（点击 / 浏览 / 加权）
```
max  ∑_{d,p,k}  (α·E_click[d,p,k] + β·E_browse[d,p,k] + γ·E_reg[d,p,k]) / max(y[d,p,k], 0.01)
```
其中 α, β, γ 是 3 指标权重（推荐 0.5 / 0.3 / 0.2，注册量是终极目标）。

**约束（4 条硬约束）**：

1. **入选项选择**：仅 Q2 的"黄金+重点+潜力"词可在 x=1（否则 x=0）
   ```
   ∑_d x[d, p, k] ≤ M · 1{k ∈ (黄金∪重点∪潜力)}    ∀ p, k
   ```
2. **推广单元日预算**：y[d,p,k] 对 k 求和 ≤ 该单元 2025 同期日均 × 缩放因子（缺省 1.0）
   ```
   ∑_k y[d, p, k] ≤ B_unit[p, d]    ∀ d, p
   ```
3. **总预算**：∑_{d,p,k} y[d,p,k] ≤ 2025-02-01~08 + 2025-08-01~08 总消费（这是关键硬约束，避免超预算）
4. **关联规则应用**（**Layer 2 输出接入约束**）：
   - 若关联规则 A → B 置信度 > 0.8：A 投放则 B 必须投放（用于强化关联）
   - 若 Q2 标"问题词"：x[d,p,k] = 0

**求解器**：
- 首选 PuLP（纯 Python，易调试，**不要用 CPLEX/Gurobi 商业授权**）
- 备选 OR-Tools（如果 PuLP 性能不够）
- 不接受 NSGA-II/遗传算法/强化学习（**国奖不堆方法**）

**关键简化**（避免维度爆炸）：
- 按推广单元分 12 个独立子问题（MILP 松弛规模从百万降到千级）
- 每个推广单元独立优化后再做"全局 sum 不超预算"的可行性校验（必要时缩放各单元解）

输出：
- `results/tables/q3_daily_strategy.csv`（16 天 × 12 推广单元 × 入选项）
- `data/raw/attachments/result3.xlsx`（按 row-level 模板格式输出）
- `data/processed/q3/milp_solution.pkl`（含决策变量，便于反事实）

#### Layer 4：四指标预测（**确定性预测**，Q3 是 baseline，Q4 再加不确定性）

对每个被选中的 (d, p, k) 组合（x[d,p,k]=1），用历史比值法给出 4 个指标预测：

| 指标 | 公式 | 输入 |
|---|---|---|
| 预期展位 | `y[d,p,k] · (历史上方位展现量/消费额) · 关键词规模系数` | Sheet1 上方位展现量/消费额 的推广单元日均值 |
| 预期点击量 | `y[d,p,k] · (历史点击量/消费额)` | Sheet1 点击量/消费额 |
| 预期浏览量 | `y[d,p,k] · (浏览量/消费额)_关键词历史` | Sheet3 浏览量/消费额 |
| 预期注册量 | `y[d,p,k] · (新注册数/消费额)_方案日均` | Sheet2 / Sheet1 整合 |

> **简化但有效**：所有比值用"2025 同窗口"（2025-02-01~08 与 2025-08-01~08）实际数据算术平均，作为常数；不做时间序列外推（理由：题面只 16 天，历史太短做 ARIMA/Prophet 没意义）

**鲁棒性修正**（避免 overconfidence）：
- 对每个比值乘以 0.85 折扣（防系统性高估）
- 对极端值做 95th 截尾（防 heavy-tail 偏倚）
- 提供"上界 vs 下界"两套预测，给论文 §5.3.4

输出：
- `data/raw/attachments/result3.xlsx`（4 个预期列 + 投入金额）
- `results/tables/q3_indicator_summary.csv`（4 指标总量统计）

### 2.3 校验机制（4 项，**国奖评审加分**）

| 校验 | 做法 | 通过标准 |
|---|---|---|
| **预算守门** | sum(投入金额) ≤ 2025-02+2025-08 实际消费 | 严格 ≤（不留 buffer） |
| **历史回放** | 用 2025 全年数据做 backtest：把 Q3 的投入金额方案套到 2025 实际产出，看是否接近实际 | 预测点击数 / 实际点击数 ∈ [0.85, 1.15] |
| **入选项准入** | 100% 入选词 ∈ 黄金∪重点∪潜力，0% 包含问题或无效词 | 严格相等 |
| **关联应用率** | 关联规则中"强制共现"的覆盖率（即 满足 conf>0.8 规则的词组比例）| ≥ 60% |

### 2.4 输出物清单（Q3 实施 agent 交付）

| 产出 | 路径 | 行/字段数 |
|---|---|---|
| result3.xlsx（主交付）| `data/raw/attachments/result3.xlsx` | 5K-20K 行 × 9 列 |
| 5 维特征 pkl | `data/processed/q3/keyword_5d.pkl` | 2227 × 5+ |
| 关联规则 csv | `results/tables/q3_keyword_assoc_rules.csv` | ~100-200 行 |
| 关联网络图 png | `results/figures/q3_keyword_assoc_network.png` | 1 张 |
| MILP 求解 pkl | `data/processed/q3/milp_solution.pkl` | 16 × 12 × K |
| 每日策略 csv | `results/tables/q3_daily_strategy.csv` | 同 result3.xlsx |
| 4 指标汇总 | `results/tables/q3_indicator_summary.csv` | 16 × 9 矩阵 |
| §5.3 论文节 | `paper/paper.md` §5.3 | ~150-200 行 |
| q3_method.md | `issue/q3_method.md` | ~300 行 |
| q3_data_prep.py | `src/q3_data_prep.py` | ~150 行 |
| q3_association.py | `src/q3_association.py` | ~80 行 |
| q3_milp.py | `src/q3_milp.py` | ~250 行 |

---

## 3. Q4 方法架构

> Q4 = Q3 baseline + 不确定性扰动 + 期望值估计 + 区间

### 3.1 设计原则

1. **不是凭空随机**：6 个扰动因子必须从 2025 实际数据估计分布参数（不能用任意 Beta 分布凑数）
2. **期望 + 区间**：每个 (d,p,k) 输出 6 个指标的期望值 + 95% CI
3. **预算与 Q3 同等约束**：≤ 2025 同期（不是 ≤ 2025 全年）
4. **方法显式可解释**：Two-Stage SP（不是 DRO/DRL）

### 3.2 不确定性参数化（**关键，不许拍脑袋**）

**6 个扰动因子与历史数据来源**：

| 扰动因子 | 来源 | 估计方法 | 分布假设 |
|---|---|---|---|
| 竞价（CPC）| Sheet3 关键词级 消费/点击 跨 2025 全年的变异 | 滑动窗口 30 天 CV | 对数正态 LogNormal(μ, σ)|
| 展现量 | Sheet1 推广单元日级 展现量 | 滑动窗口 30 天 CV | 对数正态 |
| 展现位 | Sheet1 推广单元日级 上方位展现量 | 同上 | 截断正态（在 [1, 10]）|
| 点击量 | Sheet1 推广单元日级 点击量 | 同上 | 对数正态 |
| 浏览量 | Sheet3 关键词级 浏览量 | 同上 | 对数正态 |
| 注册量 | Sheet2 日期级 新注册数 + Sheet1 分配 | 同上 + 泊松近似 | Poisson-Pareto 混合 |

> **工程实现**：每个 (p, k) 对每个因子计算
> - 历史序列：[x_1, x_2, ..., x_T]
> - 滑动 CV = std(x[t-30+1:t]) / mean(x[t-30+1:t])
> - 取中位数作为分布参数

输出：
- `results/tables/q4_uncertainty_params.csv`（每推广单元 × 每关键词 × 6 因子）
- `results/figures/q4_uncertainty_distribution.png`（6 张子图：6 因子的经验分布）

### 3.3 优化：两阶段随机规划 Two-Stage SP（**不是 DRO**）

**为什么选 Two-Stage SP**：
- DRO（distributionally robust optimization）解释成本太高，评委不爱看公式
- 简单 SAA（sample average approximation）太天真，6 因子联合扰动下不可行
- Two-Stage SP 是工业界经典："第一阶段策略 + 第二阶段补足"

**决策变量**：
- 第一阶段（here-and-now）：`y[d,p,k]` ∈ {0, 1} 二元（投不投），同 Q3
- 第二阶段（wait-and-see）：`z[d,p,k,ξ]` ∈ ℝ+ 在场景 ξ 下补足金额

**目标函数**：最小化最坏期望成本（不超预算的前提下最大化期望收益；或等价的最大化期望收益）
```
max  E_ξ [收益(d,p,k, ξ)] - λ · Var_ξ [收益]
```
其中 λ 是风险厌恶系数（推荐 λ=0.5，给出 3 个对比：λ=0/0.5/1.0）。

**约束**：
1. 第一阶段：x[d,p,k], y[d,p,k] 同 Q3
2. 第二阶段：scenario-s 收益预测 ≤ 投入预算 + scenario-s 补足（不允许超）
3. 期望总预算 ≤ 2025 同期（不是每个 scenario 都强约束）

**求解**：Monte Carlo 采样 N=1000 个场景，SAA 近似 + 还原到 MILP。
- 起步：每个场景独立解 Q3 的 MILP，再加权聚合
- 进阶：用 SDDP（stochastic dual dynamic programming）—— **可选，仅当 SAA 时间超过 30 分钟才用**

### 3.4 6 个指标的期望 + CI

输出每个 (d,p,k) 的：
- 6 个期望值 = Sample mean over 1000 scenarios
- 6 个 95% CI = Sample percentile [2.5%, 97.5%]
- 6 个标准差（用于灵敏度分析）

输出：
- `data/raw/attachments/result4.xlsx`（按 row-level 模板格式输出 6 期望值）
- `results/tables/q4_expected_with_ci.csv`（6 期望 + 6 CI × 7 天 × 推广单元 × 关键词）
- `results/figures/q4_fan_chart.png`（展示每个指标 7 天的 fan chart，含期望 + 95% 区间）

### 3.5 校验机制（4 项）

| 校验 | 做法 | 通过标准 |
|---|---|---|
| **分布校准** | 用 KS 检验验证 6 因子经验分布拟合 | p > 0.05（不能 reject）|
| **期望守门** | 期望总投入 ≤ 2025 同期 | 严格 ≤ |
| **鲁棒性** | 改 λ ∈ {0, 0.5, 1.0} 看投入策略是否稳定 | Top 50% 词集合 overlap ≥ 80% |
| **不确定性传播** | 6 指标 CV 加权 vs 总 CV | 总收益 CV ∈ [0.10, 0.50]（不过分散）|

### 3.6 输出物清单（Q4 实施 agent 交付）

| 产出 | 路径 |
|---|---|
| result4.xlsx | `data/raw/attachments/result4.xlsx` |
| 不确定性参数 | `results/tables/q4_uncertainty_params.csv` |
| 不确定性分布图 | `results/figures/q4_uncertainty_distribution.png` |
| 期望+CI 长表 | `results/tables/q4_expected_with_ci.csv` |
| Fan chart | `results/figures/q4_fan_chart.png` |
| §5.4 论文节 | `paper/paper.md` §5.4 |
| q4_method.md | `issue/q4_method.md` |
| q4_data_prep.py | `src/q4_data_prep.py` |
| q4_uncertainty.py | `src/q4_uncertainty.py` |
| q4_solver.py | `src/q4_solver.py` |

---

## 4. 国奖加分点（**4 项，不堆方法，只强化业务价值 + 模型可解释**）

| 加分点 | 在哪一章节 | 为什么是国奖 |
|---|---|---|
| **关键词关联网络图**（不只是统计分布）| Q3 §5.3.3 | 业务可解释（SEM 投放经理能直接读图决策）+ 题目"关联关系"语义落实 |
| **MILP 目标函数 + 约束的 LaTeX 公式** | Q3 §5.3.2 | 评委看公式比看代码重要 + 模型严谨 |
| **6 因子不确定性来源显式标注**（每张图标注"参数来自 Sheet1/Sheet3 历史 30 天 CV"）| Q4 §5.4.1 | 不是黑盒随机，是基于实际数据 |
| **鲁棒性 3 档 λ 对比图**（λ=0 vs 0.5 vs 1.0）| Q4 §5.4.4 | 评委喜欢看"参数敏感性 + 鲁棒性结论" |

---

## 5. 给执行 agent 的红线（**继承 mdc v3 + Q2 规划**）

1. ❌ **禁止自创输出格式**——result3/4 列名 = 9 列严格对齐附件 2
2. ❌ **禁止扩展时间范围**——result3 = 16 天 / result4 = 7 天
3. ❌ **禁止改变决策粒度**——必须 = 推广单元 × 关键词 × 天
4. ❌ **禁止引入未在本文档的方法**（Transformer/Attention/DRL/GAN/NSGA-II/CPLEX）
5. ❌ **禁止把 4 指标简化为 1 指标**——4 列必须都写
6. ❌ **禁止使用商业求解器商业授权**——PuLP/OR-Tools 是首选
7. ❌ **禁止自创随机分布假设**——必须从历史 30 天 CV 派生
8. ❌ **禁止修改 Q1 / Q2 已确定的口径**——评分函数 / 权重 / 假日扣分 / 5 类规则 / 阈值
9. ❌ **禁止跳过读附件 2 模板**——每次跑前先 re-read 一次
10. ❌ **禁止"做了一堆动作但忘了写 RUN_LOG"**——每动作 1 行

**允许的方法栈白名单**：
- ✅ FP-Growth（关联规则挖掘）
- ✅ MILP via PuLP / OR-Tools
- ✅ Two-Stage SP via SAA / SDDP（可选）
- ✅ CRITIC + Bootstrap + 龙卷风（从 Q1 复用）
- ✅ 对数正态 / 截断正态 / 泊松拟合

---

## 6. 执行顺序（S1-S9，继承 Q2 规划风格）

| 阶段 | 内容 | 时间预算 |
|---|---|---|
| **S1** | 备份当前 + WORK_STATE/DECISION_LOG 同步 Q3/Q4 任务 | 10 min |
| **S2** | 读附件 2 模板 + Sheet1/2/3 + 5 维特征 pkl 准备 | 30 min |
| **S3** | 写 `src/q3_data_prep.py` + 5 维特征 pkl | 45 min |
| **S4** | 写 `src/q3_association.py` + 关联网络图 + 规则 csv | 60 min |
| **S5** | 写 `src/q3_milp.py`（MILP 公式 + PuLP 实现）| 90 min |
| **S6** | 跑通 result3.xlsx + 4 校验 | 45 min |
| **S7** | 写 `issue/q3_method.md` + `paper/paper.md` §5.3 | 90 min |
| **S8** | Q4 启动：不确定性参数化 + Two-Stage SP | 90 min |
| **S9** | §5.4 + 所有校验 + DoD | 60 min |
| **总计** | | **9 小时 ≈ 1 上午** |

---

## 7. DoD（成功标准）

### Q3 完成判定
- [ ] result3.xlsx 行数 ∈ [5K, 20K]，9 列名严格对齐
- [ ] 预算 ≤ 2025 同期（不留 buffer）
- [ ] 入选项 100% 来自黄金+重点+潜力
- [ ] 关联网络图输出 + 关联规则 csv ≥ 50 条
- [ ] MILP 求解时间 < 10 分钟
- [ ] 4 个指标历史回放比率 ∈ [0.85, 1.15]
- [ ] §5.3 论文节有 LaTeX 公式 ≥ 5 行
- [ ] q3_method.md 评审可读

### Q4 完成判定
- [ ] result4.xlsx 行数 ∈ [1K, 5K]，6 期望列齐全
- [ ] 6 因子 KS 检验 p > 0.05
- [ ] 期望总预算 ≤ 2025 同期
- [ ] λ ∈ {0, 0.5, 1.0} Top 词集合 overlap ≥ 80%
- [ ] §5.4 论文节含不确定性来源标注 + 鲁棒性对比
- [ ] q4_method.md 评审可读

### 通用（继承 Q2）
- [ ] RUN_LOG 30+ 行
- [ ] WORK_STATE Q3/Q4 路线图状态 ✅
- [ ] DECISION_LOG D-012/D-013 决策追加

---

## 8. 与 Q1 / Q2 衔接 / 不要做的修改

- **不能改**：Q1 综合分 50.7、Q1 4 维度权重、Q1 节日扣分
- **不能改**：Q2 5 类规则（黄金/重点/潜力/问题/无效）
- **不能改**：Q2 阈值定义（中位数分桶）
- **能改**：result3/4 产出物命名（除 schema 外不影响 Q1/Q2）
- **能改**：MILP 目标函数权重 α/β/γ（但需在 §5.3 显式说明）
- **能改**：λ 风险厌恶系数（要在 §5.4 显示 3 档对比）

---

## 9. 引用

| 引用 | 用途 |
|---|---|
| `issue/q2_implementation_plan.md` | Q2 5 项锁定决策 + D-Q2-001~005 |
| `issue/q1_fix_plan.md` | P0-0 节假日修正 + Q1 评分链路 |
| `src/utils.py` | 加载 Sheet / 数据读 |
| `src/plot_style.py` | 统一绘图 |
| `data/processed/q2/keyword_classified.pkl` | Q3 必备输入 |
| `results/tables/q2_thresholds.json` | Q3 可选参考（不强引用）|

---

最后更新：2026-09-12 14:50 · 用于 Q3/Q4 实施交接 · 严禁偏离红线 §5
