# WORK STATE · CUMCM 2026 E 题 · 长期运行进度跟踪

> **这是本仓库的"长期记忆"**。无论上下文如何滚动，第一动作 = 读这个文件。
> 由主 agent 维护，每完成一步追加更新。

---

## 0. 当前状态（一句话）

**阶段**：全部 Q1 + Q2 + Q3 + Q4 完成；论文数字已同步；check_progress 14/14 通过；待交付总结
**时间锚点**：2026-09-12 11:30 UTC+8
**关键结果**：综合分 56.0 / 100（扣分前 65.3；扣分 -30 封顶，节日分解：春节 -12 / 劳动 -4 / 端午 -4 / 国庆 -9 / 中秋 -2）

---

## 1. 完整路线图（5 Phase + 终）

| Phase | 内容 | 状态 | 关键产出 |
|-------|------|------|----------|
| 0 | 4 层 context 防护 | ✅ 完成 | WORK_STATE / DECISION_LOG / RUN_LOG / check_progress.py |
| 1 | Q1 7 项修复（评审报告对应）| ✅ 完成 | 统一评分 / Bootstrap / BH FDR / 时间切分 / 权重敏感性 |
| 2 | 完整 Bootstrap（n_boot=100, FDR 校正）| ✅ 完成 | q1_bootstrap_ci.csv (37 节日) + q1_holiday_penalty.json (-30) |
| 3 | Q2 关键词分类（GMM + BIC）| ✅ 完成 | result2.xlsx + q2_keyword_classification.csv (K=8, 5 类) |
| 4 | Q3 投放策略优化（MILP + NSGA-II）| ✅ 完成 | result3.xlsx + q3_daily_strategy.csv (+21.60%) |
| 5 | Q4 不确定性优化（SAA + DRO + 后悔）| ✅ 完成 | result4.xlsx + q4_strategy_comparison.csv (DRO 3.39%) |
| 终 | 论文数字同步 | ✅ 完成 | paper.md 全部数字统一 + Q2/Q3/Q4 附录追加 |

---

## 2. 数据契约（关键，防出错）

- **原始**：`data/raw/attachments/附件1.xlsx`（3 sheet：方案日表 / 新注册 / 关键词表）
- **Q1 中间产物**：`data/processed/q1/*.pkl`
  - `keyword_total.pkl` (2227 行)
  - `unit_total.pkl` (12 行)
  - `plan_total.pkl` (5 行)
  - `plan_daily.pkl` (1825 行 = 5 方案 × 365 天)
  - `daily_full.pkl`
  - `campaign_daily.pkl` (365 行)
- **Q1 输出**：
  - `results/tables/q1_score.json` (overall_score=56.0)
  - `results/tables/q1_weights.json`
  - `results/tables/q1_holiday_penalty.json` (-30, 5 节日)
  - `results/tables/q1_bootstrap_ci.csv`
- **Q2 输出**：
  - `results/tables/q2_keyword_classification.csv` (2227 行)
  - `results/tables/q2_cluster_summary.csv` (8 聚类 → 5 业务类)
  - `data/raw/attachments/result2.xlsx`
- **Q3 输出**：
  - `results/tables/q3_daily_strategy.csv` (5 × 365 = 1825 行)
  - `results/tables/q3_pareto_front.csv` (60 个 Pareto 解)
  - `results/tables/q3_plan_summary.csv` (5 方案汇总)
  - `data/raw/attachments/result3.xlsx`
- **Q4 输出**：
  - `results/tables/q4_daily_strategy.csv`
  - `results/tables/q4_strategy_comparison.csv` (4 策略 × 期望/标准差/worst-case/regret%)
  - `data/raw/attachments/result4.xlsx`

---

## 3. 自主决策清单（已固化）

| ID | 决策 | 选择 | 理由 |
|----|------|------|------|
| D-001 | Q2 分类器 | GMM + BIC | 比硬阈值更鲁棒，BIC 是客观准则 |
| D-002 | Q3 优化器 | MILP + NSGA-II Pareto | 工业级 + 多目标，国一亮点 |
| D-003 | Q4 优化器 | DRO (Wasserstein) + SAA + 后悔分析 | 国赛前沿，理论深度 |
| D-004 | Bootstrap n_boot | 100（Bench 显示 1000 不可行）| 兼顾精度和速度 |
| D-005 | 节日扣分封顶 | -30 | 已与现状一致 |
| D-006 | 权重混合比例 | 70:30（CRITIC:业务）| 与 q1_weights.json 一致 |
| D-007 | Q2 K | BIC 选 K=8（最优 BIC）| 不是拍脑袋 K=5 |

---

## 4. 4 维度评分与权重（最终）

| 维度 | 评分 | 权重 |
|---|---|---|
| 设计质量与创意 | 55.8 / 100 | 22.22% |
| 关键词管理与运用 | 51.6 / 100 | 14.83% |
| 出价策略与预算 | 77.6 / 100 | 32.16% |
| 投放策略与时间 | 65.8 / 100 | 30.79% |

**5 个方案最终排名（含扣分）**：

| 方案 | 综合分 |
|---|---|
| 500635396 | 57.28 |
| 63563817 | 56.60 |
| 495403620 | 55.26 |
| 495817671 | 51.08 |
| 525368335 | 33.23 |

---

## 5. Q3/Q4 关键结果速览

**Q3 MILP**：85,313 → 103,742 (+21.60%)

| 方案 | 原消费(元) | 最优消费(元) | 变化 | 平均 r* |
|------|-----------|-------------|------|---------|
| 63563817 | 15,225 | 16,258 | +6.8% | 0.78 |
| 495403620 | 215,831 | 212,513 | -1.5% | 1.18 |
| 495817671 | 171,870 | 180,957 | +5.3% | 1.10 |
| 500635396 | 841,527 | 776,630 | **-7.7%** | 1.18 |
| 525368335 | 181,497 | 239,592 | **+32.0%** | 0.98 |

**Q4 4 策略对比（K=200 ±20% 高斯扰动）**：

| 策略 | 期望注册数 | 标准差 | worst-case | regret % |
|------|-----------|--------|-----------|----------|
| baseline (r=1) | 85,347 | 781 | 83,407 | 0.00 |
| nominal (Q3 MILP) | 103,853 | 1,260 | 100,171 | 3.55 |
| **SAA** | **103,873** | 1,259 | 100,284 | 3.45 |
| **DRO** | 103,783 | 1,262 | 100,261 | **3.39** |

---

## 6. 已完成的 P0/P1/P2 修复（评审报告对应）

| ID | 内容 | 状态 |
|----|------|------|
| P0-1 | 统一 Bootstrap（q1_bootstrap.py 公共别名 + q1_robustness_aug.py 复用）| ✅ |
| P0-2 | LOO 重命名为 weight_robustness_check（明确非泛化）| ✅ |
| P0-3 | Prophet 残差 Z-Score 替代 8月 Z-Score（异常日 8/21 → 3/19, Z=4.877）| ✅ |
| P1-1 | 明确 _score_per_plan vs score_* 两套路径（加 docstring）| ✅ |
| P1-4 | CRITIC:业务 比例敏感性（极差 3.97, 6.16%, 评估'稳健'）| ✅ |
| P1-5 | BH FDR 校正（apply_fdr_correction + 节日扣分启用 FDR）| ✅ |
| P1-6 | requirements.txt 生成 | ✅ |
| P2-1 | 龙卷风图扰动后权重无上限约束 | 论文叙事补充 |

---

## 7. 下一动作（如再开新上下文）

1. 第一动作：`python tools/check_progress.py` → 确认 14/14 通过
2. 看 `RUN_LOG.md` 末尾 → 知道上次做到哪
3. 看 `evaluation_q1.md` → 知道当前评估结论
4. 看 `paper/paper.md` 末尾 → 知道论文最新状态

如要继续工作：
- 检查 `issue/` 下是否还有未处理的 P1/P2 项
- 检查 `paper/paper.md` 是否需要补充 5.2 / 5.3 / 5.4 节正文（目前只有附录 X 速览）
- 检查 Word 版本 `paper/SEM广告投放策略优化_论文框架.docx` 是否同步
