# Q1 解决方案审查报告

> 审查日期：2026-09-11
> 审查人：独立审查 agent
> 项目：CUMCM 2026 E 题 · SEM 广告投放策略优化 · 问题一

---

## 总评分：74 / 100

| 维度 | 分数 | 权重 |
|---|---|---|
| A · 科学性与合理性 | 19 / 25 | 25% |
| B · 产物与数据一致性 | 23 / 25 | 25% |
| C · 产物与算法匹配度 | 16 / 25 | 25% |
| D · 写作质量与可复现性 | 16 / 25 | 25% |
| **合计** | **74 / 100** | 100% |

评级：**良好（建议小修）**

---

## 维度 A · 科学性与合理性（19 / 25）

### 优点
1. **评分体系完整、维度划分合理**：4 维度（设计质量 / 关键词管理 / 出价策略 / 投放时间）+ 9 行业阈值二级指标的混合框架，对应 SEM 行业真实业务链条。
2. **赋权方法兼顾客观与可解释**：CRITIC（变异+冲突）+ 业务 70:30 混合是合理选择，避免纯 AHP 主观性过强和纯熵权忽略相关性的问题。
3. **节日效应建模方法扎实**：Prophet 反事实 + Bootstrap 重采样（n=100/节日）共做 74 个"节日×指标"对，显著率 75.7%。
4. **辅助方法齐全**：龙卷风、敏感性曲线、异常值鲁棒性、KMeans 聚类、4 种方法对比（等权 / 熵权 / TOPSIS / CRITIC），且 Pearson ≥ 0.98 + Spearman ≥ 0.7 验证排序稳健。
5. **方案评分排名稳定**：5 方案在 4 种方法下排名完全一致（500635396 > 63563817 > 495403620 > 495817671 > 525368335）。

### 扣分点
1. **（-2 分）CRITIC 实现细节与论文描述有出入**：论文表 5.1.6 写"CRITIC 权重 = 设计 0.20 / 关键词 0.07 / 出价 0.32 / 投放 0.42"，但 `q1_weights.json` 实际 critic_weights 为 0.2317 / 0.0832 / 0.3523 / 0.3327。两套数字差异过大（关键词 0.07 vs 0.0832 接近 19% 偏差），论文文字与产物不一致。
2. **（-2 分）节日效应"显著负贡献"的方向解读过于绝对**：Bootstrap 证明的是"窗口期与窗口前后的差异"，但论文直接扣 30 分（封顶），相当于对每个方案的"时间维度"统一扣满，没有考虑不同方案的差异。扣分链路对全公司日历生效，但综合分却是逐方案独立计算——扣分规则与综合分计算口径存在耦合不清。
3. **（-1 分）"节日效应"扣分规则封顶 -30 但 4 个法定节日原始扣分求和恰好 -30 巧合**：春节 -12 + 国庆 -10 + 清明 -4 + 劳动 -4 = -30 恰好等于封顶值，意味着封顶实际未生效。论文未说明这是巧合还是设计意图。
4. **（-1 分）Z-Score 异常检测的"基准口径"选择未充分论证**：2025-08-21 异常日 Z=1.69 是基于"8 月内"统计（mean=5326, std=2519），论文未说明为何不用全年口径（全年口径 Z=2.14），且全年口径下 Z=2.14 实际高于 Z>2 的常规异常阈值。

---

## 维度 B · 产物与数据一致性（23 / 25）

### 抽样验证结果（11 个关键数值）

| 数值 | 声明值 | 重算值 | 偏差 | 结论 |
|---|---|---|---|---|
| 全年消费 | 142.59 万元 | 1,425,949.79 元 = 142.5950 万元 | +0.005 | ✓ |
| 展现量 | 22.58M | 22,580,381 = 22.5804M | +0.0004M | ✓ |
| 点击量 | 834,815 | 834,815 | 0 | ✓ |
| 注册数 | 85,313 | 85,313 | 0 | ✓ |
| 注册转化率（总量） | 10.22% | 85313/834815 = 10.219% | 0 | ✓ |
| 注册转化率（日均算术平均）| 11.40% | 0.114024 | 0 | ✓ |
| 异常日消费（8/21） | 9575.18 元 | 9575.18 元 | 0 | ✓ |
| 异常日 Z-Score | 1.69（8 月口径）| 1.6865（8 月）/ 2.1362（全年） | 0 | ✓（口径有歧义）|
| 4 维度权重 | 22.22% / 14.83% / 32.16% / 30.79% | 0.2222 / 0.1483 / 0.3216 / 0.3079 | 0 | ✓ |
| Bootstrap n_boot | 全部 = 100 | 全部 n_boot_valid=100 | 0 | ✓ |
| 节日扣分（按聚合）| -12/-10/-4/-4 = -30 | -12/-10/-4/-4 = -30 | 0 | ✓ |
| 5 方案综合分（扣分后）| 57.28/56.60/55.26/51.08/33.23 | 57.28/56.60/55.26/51.08/33.23 | 0 | ✓ |

### 关键综合分验证（重要）

| 口径 | 论文声明 | 实际计算 | 偏差 | 结论 |
|---|---|---|---|---|
| 扣分前综合分 | 65.3 | 用实际权重 (0.2222/0.1483/0.3216/0.3079) + 扣分前 4 维度分 (55.8/51.6/77.6/65.8) = 65.27 | -0.03 | ✓（舍入差）|
| 含节日扣分综合分 | 56.0 | 用实际权重 + 扣分后 4 维度分 (55.8/51.6/77.6/35.8) = 56.03 | +0.03 | ✓（舍入差）|

### 扣分点
1. **（-1 分）异常日 Z-Score 的口径不清晰**：论文同时存在"Z=1.69（8 月口径）"和"Z>3 才是典型异常"两个表述，但未说明用 8 月口径的理由。建议统一为全年口径 Z=2.14 加上"未达 Z>3 显著阈值"的说明。
2. **（-1 分）q1_score.json 中"投放策略与时间"维度得分"原值 65.8"在多处不一致**：
   - paper.md 表格写"投放策略与时间 评分（扣分前）65.8"
   - paper.md 表格写"设计质量与创意 69.0 / 关键词管理与运用 66.7 / 出价策略与预算 86.3"
   - q1_score.json 实际："设计 55.8 / 关键词 51.6 / 出价 77.6 / 投放 35.8（扣分后）"
   - q1_summary.json 综合评分 段："设计 60.9 / 关键词 56.9 / 出价 83.6 / 投放 65.8"（用主观权重 0.2/0.3/0.25/0.25 的旧版本）
   - 三个文件的 4 维度分完全对不上。

---

## 维度 C · 产物与算法匹配度（16 / 25）

### 交叉验证表

| 算法 | 产物 | 是否存在 | 是否匹配 | 问题描述 |
|---|---|---|---|---|
| CRITIC 赋权 | `q1_weights.json` + `q1_weights.csv` | ✓ | ⚠️ | 论文文字描述 CRITIC 权重 0.20/0.07/0.32/0.42，文件实际 0.2317/0.0832/0.3523/0.3327 |
| 百分位+Z-Score 双轨 | `q1_score.json` | ✓ | ✓ | — |
| 行业阈值绝对评分 | `q1_score.json` | ✓ | ✓ | 9 个阈值表完整 |
| 4 种方法对比 | `q1_baseline_comparison_pre_holiday.csv` + `q1_baseline_corr.csv` + `q1_baseline_rank_scatter.png` | ✓ | ⚠️ | paper.md 5.1.7 的 4 套 baseline 分数与实际 CSV 不一致（声明 64.94 / 实际 66.51 等）|
| Prophet 反事实 | `q1_prophet_cost.png` + `q1_prophet_reg.png` | ✓ | ✓ | — |
| Bootstrap 显著性 | `q1_bootstrap_ci.csv`（74 行）+ `q1_bootstrap_ci.png` | ✓ | ✓ | 全部 n_boot_valid=100，无截断 |
| 节日扣分 | `q1_holiday_penalty.json` | ✓ | ✓ | 4 个扣分明细完整 |
| 龙卷风 / 敏感性 | `q1_tornado.png` + `q1_sensitivity_curves.png` + `q1_sensitivity.csv` + `q1_sensitivity_summary.csv` | ✓ | ⚠️ | paper.md 表"出价 极差 7.77 / 相对变化 10.70%"与实际 q1_sensitivity_summary.csv"出价 极差 7.7 / 相对变化 10.51%"不一致；paper.md 表"扰动后评分范围 [68.7, 76.5]"与实际 [69.39, 77.09] 不一致 |
| 5×4 热力图 | `q1_heatmap.png` | ✓ | ✓ | — |
| 跳出率聚类 | `q1_bounce_clusters.csv` + `q1_bounce_clusters.png` + `q1_bounce_tsne.png` | ✓ | ✓ | — |
| 异常值鲁棒性 | `q1_robustness_{aug,bootstrap,score}.csv` + `q1_robustness_aug.png` | ✓ | ⚠️ | paper.md 5.1.7 表中"综合评分 73.2 / 74.3 / CI 宽度 2914 / 2787"实际 CSV 值 73.2 / 74.3 / 2913.67 / 2786.81 一致 ✓；但 paper.md 表注"基于旧 Bootstrap 输出（n_boot≈84-90）"与 q1_bootstrap_ci.csv 实际全 100 矛盾 |
| 论文 5.1 节文字稿 | `paper/q1_section_5_1.md` | ✗ | ✗ | **文件不存在**，但被 `project-context.mdc` 文档索引和 `q1_robustness_aug.py` 代码 `append_paper_section()` 引用。实际由 `paper/q1_solution_record.md` 取代 |

### 已发现的不一致（按严重性排序）

1. **【严重】论文 5.1.6 表中 4 维度评分与 q1_score.json 不一致**：paper.md 表 5.1.6（"各维度诊断"）写 设计 69.0 / 关键词 66.7 / 出价 86.3 / 投放 65.8；但 q1_score.json 实际是 55.8 / 51.6 / 77.6 / 35.8。这是 **paper.md 的内部版本**（可能是更早的主观权重版），与最新 CRITIC 混合赋权版的产物脱节。

2. **【严重】paper.md 5.1.7 baseline 表与 q1_baseline_comparison_pre_holiday.csv 不一致**：声明 CRITIC=64.94/等权=62.43/熵权=82.37/TOPSIS=70.43；实际 CSV 为 66.51/65.50/70.33/56.92。这是另一份早期版本 baseline 输出。

3. **【中等】paper.md CRITIC 权重描述与 q1_weights.json 不一致**：论文文字"设计 0.20 / 关键词 0.07 / 出价 0.32 / 投放 0.42" vs 实际 critic_weights 0.2317 / 0.0832 / 0.3523 / 0.3327。

4. **【中等】paper.md 5.1.6 混合权重在论文内自相矛盾**：text "设计 0.20 / 关键词 0.14 / 出价 0.30 / 投放 0.37" vs 同表 "0.199 / 0.136 / 0.296 / 0.369" vs 实际 q1_weights.json "0.2222 / 0.1483 / 0.3216 / 0.3079"——**论文同一节出现 3 套不同权重数字**。

5. **【中等】paper.md 5.1.7 表注与实际 Bootstrap 输出矛盾**：注释写"基于旧 Bootstrap 输出（n_boot≈84-90）"，但实际 q1_bootstrap_ci.csv 全部 n_boot_valid=100。这是论文撰写时未同步更新注释。

6. **【中等】q1_summary.json 综合评分段使用主观权重 0.2/0.3/0.25/0.25**：与 q1_score.json 的 CRITIC 混合权重不一致；overall=66.6 与 paper.md 综合分 65.3/56.0 不匹配。看起来是历史遗留产物。

7. **【轻微】paper.md 5.1.7 表"日级指标"列顺序**：声明的 [日级]指标实际产出顺序是 月度 CV / 日 CPC 中位数 / 注册转化率 / 8 月消费占比，论文表格顺序正确。

---

## 维度 D · 写作质量与可复现性（16 / 25）

### 优点
1. **论文结构清晰**：5.1 节有"问题→方法→结果→结论"完整链条，包含数据→指标→评分→反事实→敏感性→鲁棒性→优化建议。
2. **可复现性较好**：`python -m src.q1_main` 一键运行，模块化清晰（15 个独立脚本），所有 PNG 都有标题和坐标轴标签。
3. **辅助文档完整**：README.md、evaluation_q1.md、issue/issue_q1.md 三层文档齐全。
4. **图表丰富**：21 张 q1_*.png 覆盖评分、权重、节日、敏感性、聚类等多角度。
5. **字体兼容**：font_fix.py 处理中文显示问题。

### 扣分点
1. **（-3 分）paper.md 同一节存在多处自相矛盾的数字**（详见维度 C）：4 维度评分、CRITIC 权重、混合权重、baseline 分数——评审专家读到这些不一致会严重质疑方案可信度。
2. **（-2 分）paper.md 引用的文件 `q1_section_5_1.md` 不存在**：被 `project-context.mdc` 第 90、198 行和 `q1_robustness_aug.py` 的 `append_paper_section()` 函数引用，但实际未生成。实际文字稿是 `paper/q1_solution_record.md`，但 paper.md 没有引用它。
3. **（-1 分）paper.md 5.1 节包含 Q2/Q3/Q4 的占位符（图 5-8 / 5-9 / 5-10 / 5-11）**：这些图表属于其他问题，但在 Q1 章节末尾出现"5.2.3 关键词五分类 / 5.3 / 5.4"等跨节内容，且表格 5-1 数据全部是【待填】，作为"问题一审查"看到这些未填充内容会扣印象分。
4. **（-1 分）README.md 与 paper.md 部分数值不一致**：README.md 综合分修复后是 56.0，paper.md 也是 56.0，一致；但 README.md 第 5 节"Bootstrap 显著负贡献节日"与 paper.md 表 5.1.5 略有差异（README 只写"春节、劳动节、国庆各扣 15 分"，但 paper.md 实际扣 12/10/4/4 = 30 而非 45）。
5. **（-1 分）`evaluation_q1.md` 与 paper.md 在权重表述上不一致**：evaluation_q1.md 表中说 "500635396 设计 43.22 / 关键词 69.73 / 出价 49.46 / 时间 99.57"，但 paper.md 表 5.1.6 的 4 维度分是"69.0 / 66.7 / 86.3 / 65.8"。这是 **维度级评分 vs 方案级评分的混淆**——维度级分是各维度的全公司汇总分，方案级分是单个方案的分，evaluation_q1.md 表头没区分。
6. **（-1 分）`paper.md` 的"摘要"段落提到"问题四给出 2026 年 9 月 11-17 日的最优投放策略"，但 Q4 在审查范围内未交付**——Q4 章节只有占位符，作为 Q1 审查不应受影响，但全文可见 Q2/Q3/Q4 大量【待填】会让评委对项目完成度有疑虑。

---

## TOP-5 必须修复的问题（按严重性排序）

1. **【致命】paper.md 5.1.6 表与 q1_score.json 的 4 维度评分不一致**（设计 69.0 vs 55.8，关键词 66.7 vs 51.6，出价 86.3 vs 77.6）。论文用旧版本的维度分（主观权重 0.2/0.3/0.25/0.25），与最新 CRITIC 混合赋权版的 q1_score.json 完全对不上。**必须修复**：把 paper.md 表 5.1.6 改为 q1_score.json 的实际值，并解释为何出价维度分从 86.3 变为 77.6（可能与 industry_score 修复 bug 有关）。

2. **【严重】paper.md CRITIC 权重和混合权重数字与 q1_weights.json 实际值不一致**（CRITIC：文字 0.20/0.07/0.32/0.42 vs 文件 0.2317/0.0832/0.3523/0.3327；混合权重：文字 0.20/0.14/0.30/0.37、表 0.199/0.136/0.296/0.369、文件 0.2222/0.1483/0.3216/0.3079——三套数字！）。**必须修复**：把 paper.md 5.1.6 的权重表改为 q1_weights.json 的实际值。

3. **【严重】paper.md 5.1.7 baseline 表与 q1_baseline_comparison_pre_holiday.csv 不一致**（声明 CRITIC=64.94 / 等权=62.43 / 熵权=82.37 / TOPSIS=70.43；实际 66.51 / 65.50 / 70.33 / 56.92）。**必须修复**：把 paper.md 表 5.1.7 baseline 部分改为 baseline_comparison_pre_holiday.csv 实际值。

4. **【中等】paper.md 引用的 `paper/q1_section_5_1.md` 不存在**。被 `project-context.mdc` 第 90/198 行和 `q1_robustness_aug.py` `append_paper_section()` 引用。**必须修复**：要么生成该文件（运行 q1_robustness_aug.py 会生成），要么删除所有引用、把文档索引改为 `paper/q1_solution_record.md`。

5. **【中等】paper.md 5.1.7 表注与实际 Bootstrap n_boot 不一致**（注释"基于旧 Bootstrap 输出（n_boot≈84-90）"，但 q1_bootstrap_ci.csv 实际全 100）。**必须修复**：删除该表注或更新为"基于最新 Bootstrap 输出（n_boot=100）"。

### 附加改进建议（按价值密度排序）

- **【轻微】Z-Score 异常检测口径**：建议统一用全年口径 Z=2.14，并补充说明"未达 Z>3 显著阈值，作为敏感性测试用例"。
- **【轻微】q1_summary.json 综合评分段**：使用主观权重 0.2/0.3/0.25/0.25，与最新 CRITIC 混合权重不一致；建议重跑或删除该段。
- **【轻微】paper.md "摘要"段**：提到 Q4 的 2026 年 9 月投放策略，作为 Q1 论文应当只讲 Q1 范围内的结论；或者删除摘要里 Q4 的部分，或者补充 Q2/Q3/Q4 已完成的部分。
- **【轻微】README.md 第 5 节**：写"Bootstrap 显著负贡献节日：春节、劳动节、国庆各扣 15 分（p<0.001），合计 -30 分封顶"——但实际是 春节 -12 / 国庆 -10 / 清明 -4 / 劳动 -4，不是 3 个节日各扣 15 分。建议改为 4 个节日，扣分明细与 paper.md 一致。

---

## 整体评价

Q1 方案在**方法论框架**上是本科竞赛的高水平作品：CRITIC + 业务 70:30 混合赋权、百分位 + Z-Score 双轨评分、Prophet 反事实 + Bootstrap 显著性分级扣分、4 种方法对比 + 龙卷风 + 异常值鲁棒性——方法密度足够覆盖 CUMCM 国赛一等奖门槛。

**主要优点**：
- 评分体系完整、9 个行业阈值二级指标覆盖 SEM 全链路；
- 节日效应建模（Prophet + Bootstrap + 显著性 + 扣分链路）自洽、可解释；
- 4 种方法对比 + Pearson ≥ 0.98 + Spearman ≥ 0.7 验证排序稳健；
- 异常值鲁棒性检验（剔除 2025-08-21 前后对比）结论可信；
- 数据真实性核查（142.59 万元、22.58M、10.22% 等）全部通过验证；
- 工程化典范：`python -m src.q1_main` 一键运行，模块化清晰。

**主要风险**：
- **论文与产物多处不一致**（4 维度评分、CRITIC 权重、混合权重、baseline 分数、Bootstrap 注释）——这是评审中最致命的扣分点，会让评委对方案可信度产生严重怀疑；
- **q1_section_5_1.md 引用但不存在**——文档索引断裂；
- **Z-Score 异常检测口径**未在论文中说明为何用 8 月而非全年。

**与 CUMCM 国赛评审标准的差距**：
- 框架与方法已达国一水平；
- 但写作一致性（论文 vs 产物）有 3-5 处需要立即修复；
- 综合 74 分（良好），小修后可达到 80+（良好上等），修复论文一致性后可冲 85+（优秀）。

---

## 附录 · 审查过程记录

### 读过的文件（按路径）

**索引与背景**：
- `d:\CUMCM2026Problems\.cursor\rules\project-context.mdc`
- `d:\CUMCM2026Problems\README.md`
- `d:\CUMCM2026Problems\issue\issue_q1.md`
- `d:\CUMCM2026Problems\issue\issue_q1_methods.md`

**论文与技术素材**：
- `d:\CUMCM2026Problems\paper\paper.md`（重点 5.1.5 / 5.1.6 / 5.1.7 节）
- `d:\CUMCM2026Problems\paper\q1_solution_record.md`（前 100 行）
- `d:\CUMCM2026Problems\evaluation_q1.md`

**代码（按数据流顺序）**：
- `d:\CUMCM2026Problems\src\q1_data_prep.py`
- `d:\CUMCM2026Problems\src\q1_weights.py`
- `d:\CUMCM2026Problems\src\q1_scoring.py`
- `d:\CUMCM2026Problems\src\q1_baseline.py`
- `d:\CUMCM2026Problems\src\q1_bootstrap.py`
- `d:\CUMCM2026Problems\src\q1_holiday_penalty.py`
- `d:\CUMCM2026Problems\src\q1_robustness_aug.py`
- `d:\CUMCM2026Problems\src\q1_plots.py`

**产物（数据 + 图表）**：
- `d:\CUMCM2026Problems\data\processed\q1\daily_full.pkl`
- `d:\CUMCM2026Problems\data\processed\q1\plan_total.pkl`
- `d:\CUMCM2026Problems\data\processed\q1\plan_daily.pkl`
- `d:\CUMCM2026Problems\data\processed\q1\keyword_total.pkl`
- `d:\CUMCM2026Problems\results\tables\q1_score.json`
- `d:\CUMCM2026Problems\results\tables\q1_weights.json`
- `d:\CUMCM2026Problems\results\tables\q1_holiday_penalty.json`
- `d:\CUMCM2026Problems\results\tables\q1_bootstrap_ci.csv`
- `d:\CUMCM2026Problems\results\tables\q1_baseline_comparison_pre_holiday.csv`
- `d:\CUMCM2026Problems\results\tables\q1_baseline_corr.csv`
- `d:\CUMCM2026Problems\results\tables\q1_plan_scores.csv`
- `d:\CUMCM2026Problems\results\tables\q1_sensitivity_summary.csv`
- `d:\CUMCM2026Problems\results\tables\q1_robustness_aug.csv`
- `d:\CUMCM2026Problems\results\tables\q1_robustness_bootstrap.csv`
- `d:\CUMCM2026Problems\results\tables\q1_robustness_score.csv`
- `d:\CUMCM2026Problems\results\tables\q1_summary.json`
- `d:\CUMCM2026Problems\results\figures\` 全部 21 张 PNG 文件

### 跑过的命令 / 验证脚本

- `python issue\audit_verify.py` — 验证 11 个关键基础数值
- `python issue\audit_verify2.py` — 验证 Z-Score / Bootstrap / baseline_corr / sensitivity
- `python issue\audit_verify3.py` — 验证综合分（扣分前 / 扣分后）/ 4 维度分 / 5 方案排名
- `python issue\audit_verify4.py` — 验证 paper.md 5.1.7 表与 robustness CSV 一致性 / baseline 一致性
- `Get-ChildItem results\figures` — 列出所有 PNG 验证引用存在
- `Get-ChildItem paper` — 验证 q1_section_5_1.md 不存在（**关键发现**）

### 关键验证结果汇总

- ✓ 11 个基础数值（消费/展现/点击/注册/转化率/异常日/权重/扣分/方案分）全部通过验证
- ✓ Bootstrap 全部 n_boot_valid=100，与声明一致
- ✓ Pearson/Spearman 全部一致
- ✓ 5 方案最终排名完全一致（500635396 > 63563817 > 495403620 > 495817671 > 525368335）
- ✗ paper.md 5.1.6 表 4 维度评分与 q1_score.json 不一致
- ✗ paper.md CRITIC 权重 / 混合权重与 q1_weights.json 不一致
- ✗ paper.md 5.1.7 baseline 表与 baseline_comparison_pre_holiday.csv 不一致
- ✗ paper.md 引用的 q1_section_5_1.md 不存在
- ✗ q1_summary.json 综合评分段使用旧版主观权重，与最新 CRITIC 混合权重不一致

---

> **审查完成时间**：2026-09-11
> **审查结论**：方案整体水平为良好（74/100），方法论框架扎实、数据真实性核查全部通过；但写作一致性和论文-产物对齐需修复 5 处后才能达到优秀。
