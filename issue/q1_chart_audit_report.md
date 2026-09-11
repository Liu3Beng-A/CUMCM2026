# Q1 图表与表格专项审计报告

> 审查日期：2026-09-12  
> 审查人：图表可视化独立审查 agent  
> 项目：CUMCM 2026 E 题 · SEM 广告投放策略优化 · 问题一  
> 范围：21 张 PNG + 25 个 CSV/JSON 产物（与项目自评 27 略有差异，因部分 md/json 不计入表格审计）  

---

## 总评分：78 / 100

| 维度 | 分数 | 权重 |
|---|---|---|
| A · 数据准确性 | 21 / 25 | 25% |
| B · 图表文字内容 | 19 / 25 | 25% |
| C · 图表样式 | 18 / 25 | 25% |
| D · 图表作用与引用一致性 | 20 / 25 | 25% |
| **合计** | **78 / 100** | 100% |

**评级**：B（良好）——图表基本可作为论文支撑材料，有少量需要修正的问题（1 处致命不一致、3 处中等缺陷）。与项目自评"二等"区间对齐。

---

## 维度 A · 数据准确性（21 / 25）

### 抽样验证结果（每张图至少 3 个数值）

| 图表 | 抽取数值 | 声明值 | 重算值 | 偏差 | 结论 |
|---|---|---|---|---|---|
| q1_score_breakdown | 出价策略与预算 | 77.6 | 77.6（q1_score.json）| 0% | ✓ |
| q1_score_breakdown | 关键词管理与运用 | 51.6 | 51.6（q1_score.json）| 0% | ✓ |
| q1_score_breakdown | 综合分（标题）| 56.0 | 56.0 | 0% | ✓ |
| q1_score_radar | 出价策略 w=0.3216 | 32.16% | 32.16%（q1_weights.json）| 0% | ✓ |
| q1_score_radar | 关键词管理 w=0.1483 | 14.83% | 14.83% | 0% | ✓ |
| q1_heatmap | 500635396 综合=66.5 | 66.5（图表）| 66.51（plan_scores.csv）| -0.01 | ✓（口径为扣分前）|
| q1_heatmap | 495403620 设计=72.5 | 72.5 | 72.49 | +0.01 | ✓ |
| q1_heatmap | 投放策略与时间 99.6 | 99.6 | 99.57 | +0.03 | ✓ |
| q1_heatmap | 525368335 投放=35.1 | 35.1 | 35.07 | +0.03 | ✓ |
| q1_penalty_compare | 500635396 扣分前 | 66.5 | 66.51 | -0.01 | ✓ |
| q1_penalty_compare | 525368335 扣分前 | 42.5 | 42.46 | +0.04 | ✓ |
| q1_prophet_cost | 总消费额范围 | 0~15000 | daily_full.pkl 月度范围匹配 | OK | ✓ |
| q1_holiday_boxplot | 工作日箱体中位数（消费）| ≈4000 | daily_full.pkl 工作日中位数 ~3906 | +2% | ✓ |
| q1_bootstrap_ci | 春节 01-29 CI | -8511~-2373 | -8510.88~-2372.89 | OK | ✓ |
| q1_bootstrap_ci | 国庆 10-01 CI | -7432~-2292 | -7431.86~-2291.56 | OK | ✓ |
| q1_tornado | 出价策略极差 7.70 | 7.70 | 7.70（sensitivity_summary.csv）| 0% | ✓ |
| q1_tornado | 设计极差 2.18 | 2.18 | 2.18 | 0% | ✓ |
| q1_baseline_rank_scatter | 等权 r=0.9899 | 0.9899 | 0.9899（baseline_corr.csv）| 0% | ✓ |
| q1_baseline_rank_scatter | TOPSIS ρ=0.70 | 0.70 | 0.7 | 0% | ✓ |
| q1_robustness_aug | 春节 CI 2914→2787 | 2914/2787 | 2913.67/2786.81 | OK | ✓ |
| q1_robustness_aug | 综合分汇总 73.2/74.3 | 73.2/74.3 | 73.2/74.3（robustness_score.csv）| 0% | ✓ |
| q1_bounce_clusters | 中跳出-正常词消费占比 | 99.07% | 99.07%（cluster_summary.csv）| 0% | ✓ |
| q1_bounce_clusters | 高跳出词数 | 841 | 841 | 0% | ✓ |
| q1_keyword_management | CPC P90 | 2.37 | 2.371（score_breakdown.csv）| -0.001 | ✓ |
| q1_keyword_management | 跳出率中位数 | 0.826 | ≈0.83（数据估算）| OK | ✓ |

### 扣分点

1. **（-2 分）证据：q1_heatmap.png 标题文字与数值严重不符**  
   子标题第二行写"方案综合得分（**已含 Bootstrap 节日扣分**）"，但实际显示的数值（66.5 / 65.8 / 64.5 / 60.3 / 42.5）是**扣分前**综合分（与 `q1_robustness_score.csv` 完全一致），并非扣分后的 57.28 / 56.60 / 55.26 / 51.08 / 33.23。这是全文最严重的口径错位，可能导致审稿人/读者直接误读为"评级还是 C（一般）"。**建议立即修正**：将子标题改为"方案综合得分（**扣分前**，用于与扣分后对比）"，或在底部横条上叠加扣分后的综合分。

2. **（-1 分）证据：q1_generalization_time_split.png Holt-Winters 预测严重偏低**  
   底部"月度消费额实际 vs 预测"显示：2025-09 实际 vs 预测偏差 +135.0%，2025-11 +446.5%，2025-12 +1380.1%。**1380%** 的偏差意味着 Holt-Winters 在 7-12 月预测上完全失效。论文中"附录 C 泛化验证"引用此图，但未在正文中标注该模型局限。这不是图本身错，而是底层模型的缺陷暴露在了图上——需要在 caption 加 caveat："Holt-Winters 仅训练前 6 个月数据，节日/购物节预测能力有限"。  

3. **（-1 分）证据：q1_generalization_loo_cv.png 隐藏了一个事实问题**  
   图上显示 Spearman ρ = 1.000（排名完美一致），但底层表 `q1_generalization_loo_cv.csv` 中"剔除方案 525368335 后，预测综合分 = -435.14"（实际 41.5）。预测分出现**负值**且与实际分差距巨大，意味着虽然排名正确但预测值无业务含义。图中只展示排名（隐藏绝对值差异），有"误导之嫌"——读者会误以为模型预测也准。**建议**：在图注中加一句"Spearman = 1.000 但预测绝对值不可信（525368335 预测分 -435 vs 实际 41.5）"。

---

## 维度 B · 图表文字内容（19 / 25）

### 文字元素检查表

| 图表 | 标题 | X轴 | Y轴 | 图例 | 中文 | 数字标签 | 阈值线标签 | 完整度 |
|---|---|---|---|---|---|---|---|---|
| q1_score_breakdown | ✓ | ✓ | ✓（评分 0~100）| ✓ | ✓ | ✓ | ✓（C/D 60, D/E 50）| 100% |
| q1_score_radar | ✓ | — | — | — | ✓ | ✓ | — | 90% |
| q1_heatmap | ✗ 口径错误 | ✓ | ✓（评分 0~100）| — | ✓ | ✓ | ✓ | 70% ⚠️ |
| q1_penalty_compare | ✓ | ✓ | ✓（综合分）| ✓ | ✓ | 部分缺 | — | 80% ⚠️ |
| q1_prophet_cost | ✓ | ✓ | ✓（总消费额，无单位）| ✓ | ✓ | — | — | 90% |
| q1_prophet_reg | ✓ | ✓ | ✓（新注册数）| ✓ | ✓ | — | — | 90% |
| q1_holiday_boxplot | ✓ | ✓ | ✓ | — | ✓ | — | — | 100% |
| q1_bootstrap_ci | ✓ | ✓ | ✓（带·无）| ✓ | ✓ | — | ✓（零线）| 95% |
| q1_design_quality | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | 100% |
| q1_keyword_management | ✓ | ✓ | ✓ | ✓ | ✓ | ✓（中位数/P90）| — | 100% |
| q1_bid_strategy | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | 100% |
| q1_time_pattern | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | 95% |
| q1_tornado | ✓ | ✓ | ✓（综合分）| ✓ | ✓ | ✓ | ✓（基准 73.2）| 100% |
| q1_sensitivity_curves | ✓ | ✓（扰动 %）| ✓ | ✓ | ✓ | — | ✓（基准 73.2）| 100% |
| q1_baseline_rank_scatter | ✓ | ✓ | ✓ | ✓ | ✓ | ✓（r/ρ 表）| ✓（y=x）| 100% |
| q1_robustness_aug | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | 100% |
| q1_bounce_clusters | ✓ | ✓（对数刻度）| ✓ | ✓ | ✓ | — | — | 100% |
| q1_bounce_tsne | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | 100% |
| q1_generalization_time_split | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓（季节切分）| 90% |
| q1_generalization_loo_cv | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓（y=x）| 100% |
| q1_generalization_bootstrap | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓（基准标）| 100% |

### 扣分点

1. **（-2 分）证据：q1_heatmap.png 标题"已含 Bootstrap 节日扣分"与实际数值不符**  
   如上所述，标题下方写"已含 Bootstrap 节日扣分"，但图上所有数字（66.5/65.8/64.5/60.3/42.5）均为扣分前。这会严重误导读者，建议立即修正。

2. **（-1 分）证据：q1_penalty_compare.png "扣分后" 数值标签缺失**  
   图例区分了"扣分前 / 扣分后"两类，但**扣分后条形上没有显示具体分值**（如 57.28、56.60 等），仅依赖肉眼对比两条长度。读者难以确认具体扣分值。建议添加数值标签 `f'{score:.2f}'`。

3. **（-1 分）证据：q1_score_breakdown.png 标题与内容范围不一致**  
   标题写"综合评分总览"，但图上画的是 4 个**一级维度评分**（55.8/51.6/77.6/35.8），不是综合评分 56.0 本身。建议标题改为"问题 1：4 维度评分明细（综合分 56.0）"，避免读者误解。

4. **（-1 分）证据：q1_prophet_cost.png Y 轴无单位**  
   Y 轴标签写"总消费额"，但主标题加了"（元）"。建议在 Y 轴标签上补"（元）"或在主标题去掉单位，保持一致。

5. **（-1 分）证据：q1_holiday_boxplot.png 标题"节假日 vs 工作日"与子图分类不符**  
   标题写"节假日 vs 工作日对比分析"，但子图实际分类为"节假日 / 工作日 / 周末"3 类。建议标题改为"节假日 vs 工作日 vs 周末 对比分析"或子图标题加注"3 类别"。

---

## 维度 C · 图表样式（18 / 25）

### 样式检查表

| 图表 | 配色 | 字体 | 布局 | 坐标轴 | 一致性 | 专业感 |
|---|---|---|---|---|---|---|
| q1_score_breakdown | ✓（4 色映射维度）| ✓ | 单图 | ✓ | ✓ | ✓ |
| q1_score_radar | ✓ | ✓ | 单图 | ✓（径向 0~100）| ✓ | ✓ |
| q1_heatmap | ✓（红黄绿）| ✓ | 2x1 含底部条 | ✓（colorbar 0~100）| ✓ | ✓ |
| q1_penalty_compare | ✓（蓝/红）| ✓ | 水平条 | ✓ | ✓ | ✓ |
| q1_prophet_cost | ✓（实际 vs 预测 vs 反事实）| ✓ | 4 子图垂直 | ✓（日期 2025-01~2026-01）| ✓ | ⚠️ 较密 |
| q1_prophet_reg | ✓ | ✓ | 4 子图垂直 | ✓ | ✓ | ⚠️ 较密 |
| q1_holiday_boxplot | ✓（青/紫/橙）| ✓ | 1x2 | ✓ | ✓ | ✓ |
| q1_bootstrap_ci | ✓ | ✓ | 1x2 | ✓（含零线）| ✓ | ⚠️ 节日标签密集 |
| q1_design_quality | ✓（3 色 + 颜色映射）| ✓ | 2x2 | ✓ | ✓ | ✓ |
| q1_keyword_management | ✓ | ✓ | 2x2 | ✓ | ✓ | ✓ |
| q1_bid_strategy | ✓ | ✓ | 2x2 | ✓ | ✓ | ✓ |
| q1_time_pattern | ✓ | ⚠️ **colorbar 1e15 bug** | 2x2 | ✓ | ⚠️ | ✗ 严重 |
| q1_tornado | ✓（4 维度色）| ✓ | 水平条 | ✓ | ✓ | ⚠️ 出价只显示 1 端 |
| q1_sensitivity_curves | ✓（4 曲线色）| ✓ | 单图 | ✓ | ✓ | ✓ |
| q1_baseline_rank_scatter | ✓（3 方法色）| ✓ | 单图 | ✓ | ✓ | ✓ |
| q1_robustness_aug | ✓ | ✓ | 2x2 | ✓ | ✓ | ✓ |
| q1_bounce_clusters | ✓（3 类色）| ✓ | 1x2 | ✓（对数 X）| ✓ | ✓ |
| q1_bounce_tsne | ✓ | ✓ | 单图 | ✓ | ✓ | ✓ |
| q1_generalization_time_split | ✓ | ✓ | 2x1 | ✓ | ✓ | ⚠️ Holt-Winters 偏差大 |
| q1_generalization_loo_cv | ✓（5 方案色）| ✓ | 单图 | ✓ | ✓ | ✓ |
| q1_generalization_bootstrap | ✓ | ✓ | 1x2 | ✓ | ✓ | ✓ |

### 扣分点

1. **（-3 分）致命：q1_time_pattern.png (c) 颜色条 bug**  
   颜色条显示"日期"为 1.745、1.750、1.755，**单位为 1e15**（即 1.745×10¹⁵）。但实际数据是 2025 年日消费额（约 1000-15000 元），不可能达到 1e15 量级。这显然是 colorbar 的 formatter 或归一化 bug，导致图右侧的色标完全无法解读。  
   **建议**：检查 `q1_time_pattern.py` 中 colorbar 的 ticks/locator，将日期（YYYY-MM-DD）格式化为字符串或日期对象。

2. **（-1 分）证据：q1_tornado.png 出价策略仅显示一端**  
   龙卷风图要求每行显示 [低, 高] 两个端点，但"出价策略与预算"行只显示"77.1"，低端点 69.4 缺失（条形从基准线 73.2 直接延伸到 77.1）。这破坏了"龙卷风图"的核心可视化逻辑——读者无法直观看到下行方向的影响范围。  
   **建议**：检查 `q1_sensitivity.py` 中出价行的低端值是否被绘图逻辑过滤掉了。

3. **（-1 分）证据：q1_score_radar.png 权重气泡大小一致**  
   标题暗示"权重气泡（w×800）"，但 4 个角的橙色气泡大小看起来完全相同（按权重比例 w=0.1483/0.2222/0.3079/0.3216 应该有明显视觉差异）。可能是绘图时 scatter 的 size 参数被覆盖或绘图后丢失。  
   **建议**：检查 `q1_plots.py` 中 `scatter` 的 size 参数是否随权重缩放。

4. **（-1 分）证据：q1_bootstrap_ci.png 节日标签密集重叠**  
   37 个节日标签全部展开在 Y 轴，部分相邻节日（如"购物节 2025-03-08"和"购物节 2025-03-15"）几乎贴在同一条线上，视觉上不易区分。  
   **建议**：可考虑用颜色区分节日类型（法定 vs 购物）或只标注关键节日的完整名称。

5. **（-1 分）证据：q1_baseline_rank_scatter.png 标签与散点重叠**  
   排名 1 处 "500635396" 和 "495403620" 标记重叠（500635396 排名 1 在等权和 CRITIC 中，但熵权/TOPSIS 中排名不同），导致部分 Plan ID 文字与标记部分遮挡。  
   **建议**：使用 `adjustText` 库自动避让，或将标签放在散点右侧偏移。

---

## 维度 D · 图表作用与引用一致性（20 / 25）

### 21 张图的作用清晰度

| # | 图表 | 作用一句话 | 论文引用 | 互补性 |
|---|---|---|---|---|
| A1 | q1_score_breakdown | 4 维度评分横向对比 | 图5-8 ✓ | 与雷达互补 |
| A2 | q1_score_radar | 4 维度评分雷达（带权重）| 图5-9 ✓ | 与 breakdown 互补 |
| A3 | q1_heatmap | 5×4 评分矩阵+综合分 | 图5-11 ✓ | 总览维度 |
| A4 | q1_penalty_compare | 扣分前后综合分对比 | 图5-12 ✓ | 与 heatmap 互补 |
| B1 | q1_prophet_cost | 消费额 Prophet 反事实 | 图5-7(b) ✓ | 量级证据 |
| B2 | q1_prophet_reg | 注册量 Prophet 反事实 | 图5-7(b) ✓ | 与 B1 互补 |
| B3 | q1_holiday_boxplot | 节假/工作/周末 分布 | 图5-7 ✓ | 分布证据 |
| B4 | q1_bootstrap_ci | 37 节日 Bootstrap CI | 附录 B ✓ | 显著性证据 |
| C1 | q1_design_quality | 设计质量 4 子图 | 图5-1/5-2 ✓ | 与 5.1.1 对应 |
| C2 | q1_keyword_management | 关键词管理 4 子图 | 图5-3 ✓ | 与 5.1.2 对应 |
| C3 | q1_bid_strategy | 出价策略 4 子图 | 图5-4 ✓ | 与 5.1.3 对应 |
| C4 | q1_time_pattern | 时间规律 4 子图 | 图5-5/5-6 ✓ | 与 5.1.4 对应 |
| D1 | q1_tornado | 权重敏感性龙卷风 | 图5-10 ✓ | 权重稳健性 |
| D2 | q1_sensitivity_curves | 权重敏感性曲线 | 图5-10 ✓ | 与 tornado 互补 |
| D3 | q1_baseline_rank_scatter | 4 方法排名一致性 | 图5-13 ✓ | 方法稳健性 |
| D4 | q1_robustness_aug | 异常日鲁棒性 | 图5-14 ✓ | 数据稳健性 |
| E1 | q1_bounce_clusters | 跳出率聚类散点 | 图5-3(b) ✓ | 关键词分组 |
| E2 | q1_bounce_tsne | TSNE 降维可视化 | 图5-3(b) ✓ | 与 E1 互补 |
| F1 | q1_generalization_time_split | 时间切分泛化 | 附录 C ✓ | 时间维度 |
| F2 | q1_generalization_loo_cv | 留一方案验证 | 附录 C ✓ | 方案维度 |
| F3 | q1_generalization_bootstrap | Bootstrap 泛化误差 | 附录 C ✓ | 统计维度 |

### 多余 / 缺失分析

- **多余**：**无**。21 张图全部在 paper.md 附录 C 或正文 5.1 节引用。
- **缺失**：**无**。paper.md 引用的图（5-1 ~ 5-14 + 附录 B-1）全部存在。
- **重复**：
  - A1 (breakdown) 和 A2 (radar) 都展示 4 维度分，但用不同视觉编码（条形 vs 雷达），有互补性。✓
  - D1 (tornado) 和 D2 (sensitivity_curves) 都展示权重敏感性，但 tornado 离散、curves 连续，有互补性。✓
  - E1 (bounce_clusters) 和 E2 (bounce_tsne) 都是跳出率聚类可视化，散点 vs 降维。✓
  - F1/F2/F3 分别覆盖时间/方案/统计 3 种泛化策略，有互补性。✓
- **互补性整体评估**：良好，无严重冗余。

### 扣分点

1. **（-2 分）证据：q1_generalization_time_split.png 展示了一个"失败"的预测，但论文未充分解释**  
   论文 5.1 节没有显著引用此图（仅附录 C 简单提到）。图上 Holt-Winters 的偏差高达 +1380%，但 caption 只写"7-12月消费额实际 vs 预测"，没有 caveat 说明"Holt-Winters 未考虑节假日，仅作基线对比"。  
   **建议**：在 caption 中加"（注：Holt-Winters 仅训练前 6 个月，未考虑节日/购物节，预测能力有限；本图仅作时间切分泛化能力示意）"。

2. **（-1 分）证据：q1_generalization_loo_cv.png 隐藏了"预测分 = -435"的严重缺陷**  
   论文 caption 仅显示"Spearman ρ = 1.000"，但底层表显示预测综合分出现了**负数**（-435.14）。这意味着虽然排名正确，但模型对某些方案的预测完全没有业务含义。  
   **建议**：在 caption 中加"（注意：预测综合分绝对值不可信；Spearman 仅衡量排名一致性）"。

3. **（-1 分）证据：q1_heatmap.png 与 q1_penalty_compare.png 文字描述互相对照不足**  
   5.1.6(3.1) 节说"底部综合分横条"配合"60/50 评级线"展示扣分后综合分，但 heatmap 底部数值是扣分前 66.5/65.8/64.5/60.3/42.5（落在 C/D 线之上），而 penalty_compare 图的扣分前是同 66.5/65.8/64.5/60.3/42.5（落在 C/D 线之上），扣分后 57.28/56.60/55.26/51.08/33.23（落在 D/E 线）。两个图都展示了扣分前的 4-5 个数值，但论文 caption 写得不够清晰——读者可能需要反复对照。

4. **（-1 分）证据：4 维度分析图（C1-C4）部分子图信息密度过高**  
   例如 q1_design_quality.png (d) 用圆面积表示消费额，但圆的大小比例不明显；q1_keyword_management.png (b) 帕累托曲线在 0~200 关键词处斜率变化剧烈，肉眼难以准确读取 80/20 分界点。  
   **建议**：可考虑为关键标注（如 80/20 分界点）添加更明显的标记线。

---

## TOP-5 必须修复的图表问题（按严重性排序）

1. **【致命】q1_heatmap.png 标题"已含 Bootstrap 节日扣分"与实际数值不符**  
   - 当前：标题写"已含 Bootstrap 节日扣分"，实际数值（66.5/65.8/64.5/60.3/42.5）均为扣分前。  
   - 修复：将子标题第二行改为"方案综合得分（**扣分前**，用于与扣分后对比；扣分后见 q1_penalty_compare.png）"。

2. **【致命】q1_time_pattern.png (c) 颜色条显示 1e15 量级**  
   - 当前：colorbar 显示 1.745、1.750、1.755，标注 1e15。  
   - 修复：检查 `q1_time_pattern.py` colorbar 归一化逻辑；建议改为显示"日期"或"实际数值范围（元）"。

3. **【严重】q1_tornado.png 出价策略仅显示 77.1 一端**  
   - 当前：出价策略与预算行只显示 77.1，低端点 69.4 缺失。  
   - 修复：检查 `q1_sensitivity.py` 中低端值是否被 `~base` 或 `ylim` 过滤掉，确保 [69.4, 77.1] 完整显示。

4. **【严重】q1_generalization_time_split.png Holt-Winters 偏差 1380% 未说明**  
   - 当前：底部图显示 2025-12 月偏差 +1380%，caption 无 caveat。  
   - 修复：在 caption 中加"（Holt-Winters 训练集为前 6 个月，未考虑节日/购物节）"。

5. **【中等】q1_penalty_compare.png 扣分后条形缺数值标签**  
   - 当前：扣分前条形有 66.5/65.8/64.5/60.3/42.5 标签，扣分后条形无标签。  
   - 修复：在每个扣分后条形末端添加数值（57.28/56.60/55.26/51.08/33.23）。

---

## 整体评价

本项目图表集整体水平**良好（78/100）**，可作为 CUMCM 二等竞赛作品的核心支撑。

**优势**：
- 21 张图全部在 paper.md 中有清晰引用，无多余产物；
- 5 大类（综合评分/节日效应/4 维度/辅助分析/聚类/泛化）覆盖完整，互补性强；
- 关键数值与 CSV/JSON 完全一致（如 4 维度评分、5 方案综合分、Bootstrap CI、权重敏感性等均能精确复算）；
- 中文显示无乱码，字体一致，阈值线（C/D=60, D/E=50）跨图统一；
- 配色采用 DIM_COLORS / PLAN_COLORS 双映射系统（蓝/绿/橙/红对应 4 维度），符合学术图表规范。

**主要不足**：
- 1 处致命不一致（heatmap 标题与数值口径冲突），可能直接误导读者；
- 1 处明显 bug（time_pattern colorbar 1e15 量级），影响单图可读性；
- 3 处中等缺陷（tornado 单端显示、time_split 无 caveat、penalty_compare 缺标签）；
- 2 处需要补充 caveat（LOO CV 预测分负值问题）。

**与 CUMCM 国赛标准的差距**：
- **一等（85+）**：图表需无致命/严重问题，且具备创新性可视化（如动态图、交互图）。本项目当前未达到。
- **二等（70-84）**：图表规范，数据准确，引用完整。本项目 78 分正落在此区间，符合二等标准。
- **三等（55-69）**：图表可用，但有可见缺陷。本项目当前问题修正后可稳定在二等水平。

**改进建议**：
1. 立即修复 heatmap 标题与 time_pattern colorbar（致命问题）；
2. 补充 tornado 出价双端显示 + time_split/LOO CV 的 caveat（严重问题）；
3. 在 penalty_compare 添加扣分后数值标签；
4. 考虑为 q1_score_radar 权重气泡的实际大小做对比验证；
5. 论文 5.1 节末尾可加一句"图表局限性说明"，统一处理所有 caveat。

---

## 附录 A · 21 张图快速索引

| # | 文件 | 类别 | 论文引用 | 关键数值 |
|---|---|---|---|---|
| A1 | q1_score_breakdown.png | 评分 | 图5-8 | 55.8/51.6/77.6/35.8 |
| A2 | q1_score_radar.png | 评分 | 图5-9 | 同上 + 权重 22.22/14.83/32.16/30.79% |
| A3 | q1_heatmap.png | 评分 | 图5-11 | 5×4 评分 + 综合 66.5/65.8/64.5/60.3/42.5 |
| A4 | q1_penalty_compare.png | 评分 | 图5-12 | 5 方案扣分前/后 |
| B1 | q1_prophet_cost.png | 节日 | 图5-7(b) | 365 天消费额 Prophet 分解 |
| B2 | q1_prophet_reg.png | 节日 | 图5-7(b) | 365 天注册数 Prophet 分解 |
| B3 | q1_holiday_boxplot.png | 节日 | 图5-7 | 节假日/工作日/周末 分布 |
| B4 | q1_bootstrap_ci.png | 节日 | 附录B-1 | 37 节日 Bootstrap CI (n=100) |
| C1 | q1_design_quality.png | 维度 | 图5-1/5-2 | 5 方案 + 12 单元 + CTR/CPC |
| C2 | q1_keyword_management.png | 维度 | 图5-3 | 有效率 60% + Pareto 80/20 + 跳出率/CPC |
| C3 | q1_bid_strategy.png | 维度 | 图5-4 | CPC 走势 + 月度预算 + 70.3% 上方位 |
| C4 | q1_time_pattern.png | 维度 | 图5-5/5-6 | 日/周/月 + CPC×注册转化率 |
| D1 | q1_tornado.png | 辅助 | 图5-10 | 4 维度 ±20% 扰动 |
| D2 | q1_sensitivity_curves.png | 辅助 | 图5-10 | 4 维度连续扰动曲线 |
| D3 | q1_baseline_rank_scatter.png | 辅助 | 图5-13 | 4 方法 r=0.98+, ρ=0.7-1.0 |
| D4 | q1_robustness_aug.png | 辅助 | 图5-14 | 异常日剔除前后对比 |
| E1 | q1_bounce_clusters.png | 聚类 | 图5-3(b) | 3 类: 249/247/841 词 |
| E2 | q1_bounce_tsne.png | 聚类 | 图5-3(b) | TSNE 降维（k=3, perp=30）|
| F1 | q1_generalization_time_split.png | 泛化 | 附录 C | 7-12 月 Holt-Winters |
| F2 | q1_generalization_loo_cv.png | 泛化 | 附录 C | Spearman ρ=1.0 |
| F3 | q1_generalization_bootstrap.png | 泛化 | 附录 C | 5 方案 + 4 维度 CI (n=100) |

---

## 附录 B · 审查过程记录

### B.1 阅读的源码 / 配置
- `src/plot_style.py`（统一绘图风格）
- `paper/paper.md`（论文主稿 5.1 节 + 附录 C 图表索引）
- `README.md`（总览 + 已知问题清单）

### B.2 阅读的关键表格 / JSON
- `q1_score.json`（综合分 56.0, 4 维度 55.8/51.6/77.6/35.8, 5 方案 57.28/56.60/55.26/51.08/33.23）
- `q1_weights.json`（混合权重 0.2222/0.1483/0.3216/0.3079）
- `q1_plan_scores.csv`（5 方案 × 4 维度）
- `q1_score_breakdown.csv`（9 维度二级指标明细）
- `q1_weights.csv`（业务/CRITIC/混合三套权重）
- `q1_holiday_penalty.json`（4 节日扣分 -12/-4/-4/-10 = -30）
- `q1_bootstrap_ci.csv`（74 个"节日×指标"对的 Bootstrap 显著性）
- `q1_bootstrap_ci_6holidays.csv`（6 代表节日）
- `q1_baseline_corr.csv`（4 方法 r/ρ 对比）
- `q1_sensitivity.csv` / `q1_sensitivity_summary.csv`（权重敏感性）
- `q1_robustness_aug.csv` / `q1_robustness_bootstrap.csv` / `q1_robustness_score.csv`（鲁棒性 3 类）
- `q1_bounce_clusters.csv` / `q1_bounce_cluster_summary.csv`（聚类明细）
- `q1_summary.json`（数据总览）
- `q1_holiday_contribution.csv`（节日贡献分解）
- `q1_baseline_comparison_pre_holiday.csv`（扣分前 baseline）
- `q1_zero_score_diagnosis.csv`（0 分方案诊断）
- `q1_generalization_time_split.csv` / `q1_generalization_loo_cv.csv` / `q1_generalization_bootstrap.csv`（泛化 3 类）

### B.3 阅读的 PNG 图（共 21 张）
类别 A：q1_score_breakdown, q1_score_radar, q1_heatmap, q1_penalty_compare  
类别 B：q1_prophet_cost, q1_prophet_reg, q1_holiday_boxplot, q1_bootstrap_ci  
类别 C：q1_design_quality, q1_keyword_management, q1_bid_strategy, q1_time_pattern  
类别 D：q1_tornado, q1_sensitivity_curves, q1_baseline_rank_scatter, q1_robustness_aug  
类别 E：q1_bounce_clusters, q1_bounce_tsne  
类别 F：q1_generalization_time_split, q1_generalization_loo_cv, q1_generalization_bootstrap  

### B.4 抽样验证的关键比对
- 4 维度分（55.8/51.6/77.6/35.8）vs q1_score.json `dimensions[].score`：✓ 完全一致
- 4 维度权重（22.22/14.83/32.16/30.79%）vs q1_weights.json `mixed_weights`：✓ 完全一致
- 5 方案综合分（57.28/56.60/55.26/51.08/33.23）vs q1_score.json `plan_overall_scores`：✓ 完全一致
- Bootstrap CI 春节 01-29（-8511~-2373）vs q1_bootstrap_ci.csv：✓ 完全一致
- 龙卷风图 出价极差 7.70 vs q1_sensitivity_summary.csv：✓ 完全一致
- baseline_corr 等权 r=0.9899 vs q1_baseline_corr.csv：✓ 完全一致
- robustness 春节 CI 2914→2787 vs q1_robustness_bootstrap.csv：✓ 完全一致
- 聚类消费占比 99.07% vs q1_bounce_cluster_summary.csv：✓ 完全一致
- q1_heatmap 数值（66.5/65.8/64.5/60.3/42.5）vs q1_robustness_score.csv 扣分前列：✓ 完全一致（**但与 caption "已含 Bootstrap 节日扣分" 矛盾**）
- q1_generalization_time_split 12 月偏差 +1380.1% vs q1_generalization_time_split.csv：✓ 一致（**底层模型偏差大**）

### B.5 做出的关键判断（独立打分）
- 总分 78 / 100（B 良好，二等）
- 维度 A（数据准确性）：21 / 25 —— 几乎全部一致，仅 1 处 caption 与数值口径不符
- 维度 B（图表文字内容）：19 / 25 —— 整体清晰，3 处细节缺失
- 维度 C（图表样式）：18 / 25 —— 1 处致命 colorbar bug + 1 处 tornado 单端 + 1 处气泡
- 维度 D（图表作用与引用一致性）：20 / 25 —— 引用完整，但 2 处 caveat 缺失

---

> **审计结束**。本报告作为 Q1 图表与表格专项审计的独立审查意见，不修改任何源代码，仅生成此审计报告文件。建议优先级：致命 2 项立即修复，严重 3 项尽快修复，中等问题可在最终提交前批量修复。