# 📊 图表优化修复追踪表

> **生成时间**：2026-09-12 21:44
> **审查范围**：38 张图（剔除 4 张题面原图）
> **策略**：按 P0 → P1 → P2 → P3 顺序修复，每完成一项标 ✅ 并写入 RUN_LOG

---

## 🔴 P0（必须修复 — 7 项）

| 状态 | # | 文件 | 问题 | 修复方案 |
|------|---|------|------|---------|
| ✅ | P0-1 | `q3_sensitivity.png` | 含 r_reg 扰动（旧版，F1 已替换 v2 但旧图保留）| 删除旧图 + `q3_evaluator.py` 改 out_path 为 `_v1_DEPRECATED` + 新建 `results/figures/README.md` |
| ✅ | P0-2 | `q1_baseline_rank_scatter.png` | tracker 误判（实为 1×1 单图），黄色框与 TOPSIS marker 同色 + 方案 ID 压红线 | 备份 v1 为 DEPRECATED → 重写 `plot_rank_scatter` 为 2×2 子图 + 第 4 子图为 4×4 Spearman ρ 热力图（RdBu_r）|
| ⬜ | P0-3 | `q1_score_radar.png` | 数字标签互相压字 | 数字移到端点外侧 + 加引导线 |
| ⬜ | P0-4 | `q3_assoc_network_with_solution.png` | 78 节点标签密集重叠 | 只标 top-20 激活词，其余隐藏 |
| ⬜ | P0-5 | `q4_factor_correlation.png` | 相关系数 1.00 让色阶视觉单调 | 改用 diverging 色阶 (RdBu_r)，并把完全共线对 (clicks↔browses) 加 ★ 标注 |
| ⬜ | P0-6 | `q4_lambda_robustness.png` | 3 档目标值完全相同（Δ=0）但未强化"决策稳健"信息 | 加标题"决策稳健 Δ=0 元" + 加"全 λ 域目标相同"文字标注 |
| ⬜ | P0-7 | `q3_unit_date_heatmap.png` | 单元 9657930100 占绝对主导，其他单元 0 值难以区分 | 改用 LogNorm 色阶 |

---

## 🟠 P1（强烈建议 — 12 项）

| 状态 | # | 文件 | 问题 | 修复方案 |
|------|---|------|------|---------|
| ⬜ | P1-1 | `q1_design_quality.png` | 子图标签颜色淡 | 加大加粗子图标签 |
| ⬜ | P1-2 | `q1_keyword_management.png` | 标题信息量低 | 改为"5 方案在 5 维指标的相对排名" |
| ⬜ | P1-3 | `q1_bounce_tsne.png` | 0/1/2 命名不业务化 | 改为"低跳出/中跳出/高跳出" + 加大标签字号 |
| ⬜ | P1-4 | `q1_bid_strategy.png` | y 轴"单位：元"位置 | 移到顶部 |
| ⬜ | P1-5 | `q1_score_breakdown.png` | 柱体过矮，趋势不明显 | 加大柱体宽度 + 折线散点放大 |
| ⬜ | P1-6 | `q1_tornado.png` | 缺"基准分 50.7"虚线 | 加虚线 + 标注 |
| ⬜ | P1-7 | `q1_sensitivity_curves.png` | 4 维度线条颜色接近 | 用 tab10 高对比配色 |
| ⬜ | P1-8 | `q1_robustness_aug.png` | 4 子图布局紧 | 调整 spacing |
| ⬜ | P1-9 | `q1_mix_ratio_curve.png` | α=0.7 关键点未高亮 | 加散点 + 虚线 + 数值标注 |
| ⬜ | P1-10 | `q2_class_distribution.png` | 2227 词散点太密 | 改 hexbin 密度图 + 5 类用边框颜色区分 |
| ⬜ | P1-11 | `q2_extreme_audit.png` | 元素过多，视觉噪音 | 拆为 2 图（散点图 + 风险评级表） |
| ⬜ | P1-12 | `q4_uncertainty_distribution.png` | 6 子图分布形态类似 | 加共享 y 轴 + 整体标题解释右偏 |

---

## 🟡 P2（建议修改 — 16 项）

| 状态 | # | 文件 | 问题 | 修复方案 |
|------|---|------|------|---------|
| ⬜ | P2-1 | `q1_prophet_cost.png` | 反事实区间色浅 | 提高阴影透明度 |
| ⬜ | P2-2 | `q1_prophet_reg.png` | 反事实曲线贴近 0 | 加 inset 放大视图 |
| ⬜ | P2-3 | `q1_heatmap.png` | 排名变化不显 | 加排名变化箭头 |
| ⬜ | P2-4 | `q1_penalty_compare.png` | 扣分箭头密 | 改为简洁横条 |
| ⬜ | P2-5 | `q1_baseline_rank_scatter.png` | 同方法 trivial（已并入 P0-2） | — |
| ⬜ | P2-6 | `q1_bounce_clusters.png` | 与 tsne 重叠 | 加二者对比说明文字 |
| ⬜ | P2-7 | `q2_threshold_sensitivity.png` | "15 组合热力图"措辞 | 改为"3×5=15 档阈值组合下的分类数稳定性" |
| ⬜ | P2-8 | `q2_class_pie.png` | 与表格冗余 | 保留作为"视觉快速索引" + 加占总消费% 子标签 |
| ⬜ | P2-9 | `q2_unit_class_stacked.png` | 单元 9811363528 主导 | 改用 100% 堆叠 + 总数副表 |
| ⬜ | P2-10 | `q3_daily_cost.png` | 2/8 月颜色含义不明 | 图例移到右上 + 加文字说明 |
| ⬜ | P2-11 | `q3_unit_date_heatmap.png` | 已并入 P0-7 | — |
| ⬜ | P2-12 | `q3_keyword_cooccurrence.png` | 30×30 密集 | 改 top-15 |
| ⬜ | P2-13 | `q3_sensitivity_v2.png` | W 标签倾斜 | 改水平放置 |
| ⬜ | P2-14 | `q4_unit_date_heatmap.png` | 5/6 单元相同 | 加"5/6 单元 = 610 元/天"标注 |
| ⬜ | P2-15 | `q4_cv_compare.png` | 阈值标签字号小 | 加大字号 |
| ⬜ | P2-16 | `q4_lambda_robustness.png` | 已并入 P0-6 | — |
| ⬜ | P2-17 | `q1_generalization_time_split.png` | 与 bootstrap 重叠 | 合并 |

---

## 🟢 P3（锦上添花 — 3 项）

| 状态 | # | 文件 | 问题 | 修复方案 |
|------|---|------|------|---------|
| ⬜ | P3-1 | `q1_generalization_bootstrap.png` | 置信区间填充过淡 | 加深 alpha |
| ⬜ | P3-2 | `q1_bootstrap_ci.png` | 节日名截断 | 旋转 45° |
| ⬜ | P3-3 | `q1_score_breakdown.png` | 与 radar 重复 | 保留差异部分 |

---

## 📊 进度统计

- P0：0/7 完成
- P1：0/12 完成
- P2：0/16 完成
- P3：0/3 完成
- **合计**：0/38 完成

---

## 🚀 执行顺序（按 ROI）

1. **P0-1** 删除/重命名 q3_sensitivity.png 旧版（30 秒）
2. **P0-2** q1_baseline_rank_scatter 图例修复（5 分钟）
3. **P0-3** q1_score_radar 数字标签修复（5 分钟）
4. **P0-4** q3_assoc_network 节点标签抽样（10 分钟）
5. **P0-5** q4_factor_correlation diverging 色阶（3 分钟）
6. **P0-6** q4_lambda_robustness 决策稳健标注（5 分钟）
7. **P0-7** q3_unit_date_heatmap LogNorm（3 分钟）

预计 P0 全程 30 分钟内完成。

