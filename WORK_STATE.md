# WORK STATE · CUMCM 2026 E 题 · 长期运行进度跟踪

> **这是本仓库的"长期记忆"**。无论上下文如何滚动，**第一动作 = 读这个文件 + 读题面 PNG + 读附件 2 模板**。
> 由主 agent 维护，每完成一步追加更新。

---

## 0. 当前状态（一句话）

**阶段**：Q1 P0/P1/P2 全修复完成（综合分 50.7 / 100，D 级）；**Q2 已完成 + 6 项数学稳健性验证**（10/10 PASS，2026-09-12）；Q3/Q4 幻觉事故已清理，按真实题面重做待规划。
**时间锚点**：2026-09-12 13:30 UTC+8
**关键结果**：Q1 综合分 50.7 / 100（扣分前 64.6；扣分 -30 封顶）

---

## 0.1 幻觉事故清理进度（2026-09-12 13:25）

> **事故**：前 agent 在 Q2/Q3/Q4 完全无视附件 2 `result{2,3,4}.xlsx` 模板，自创 GMM+MILP+NSGA-II+SAA+DRO 等高大上方案。决策粒度（全 365 天/方案级）/ 时间范围 / 列结构 / 预测指标全部错位。
> **根因**：之前的 `.cursor/rules/project-context.mdc` 只列了题面图路径，**没有强调"每次对话必读附件 2 模板"**，且未列出附件 2 模板列结构。
> **应对**：彻底清理 + 备份 + mdc 加入强约束。

| S | 阶段 | 状态 | 关键产物 |
|---|------|------|----------|
| S1 | 创建 `results/snapshots/hallucination_v1_20260912/` + 备份 29 个错位产物 | ✅ | snapshot 含 src q2/q3/q4、result2/3/4.xlsx、q2/q3/q4 csv/png、q2/q3/q4 method.md、paper.md、WORK_STATE/RUN_LOG/DECISION_LOG、tools/check_q2.py |
| S2 | 更新 `project-context.mdc` v2：加「⚠️ 强制流程」+ 附件 2 模板列结构 + Q2/Q3/Q4 真实题面摘要 + 事故记录 | ✅ | `.cursor/rules/project-context.mdc` 367 行（v2 18,425 bytes）|
| S3 | 备份 v2 mdc 到 `results/snapshots/mdc_v2_with_must_read_20260912/` | ✅ | snapshot 18,425 bytes |
| S4 | 彻底删除 25 个错位产物 | ✅ | 删除：src q2/q3/q4 代码 + 27 个 results/data/issue/tools 产物（result2_new.xlsx 首次删除被 Excel 锁住，用户关闭后重试成功）|
| S5 | 还原 paper.md §5.2-5.4 占位（"待重做"）+ 摘要/DECISION_LOG 关键词/B.21-23 表 | ✅ | paper.md 703 行 |
| S6 | 同步 WORK_STATE.md / RUN_LOG.md / DECISION_LOG.md | ✅ | 当前文件 + DECISION_LOG.md D-010 + RUN_LOG.md 4 条 |
| S7 | 验证清理完整（列出所有 Q2/Q3/Q4 文件） | ⏸ 进行中 | 用户即将验证 |

---

## 0.2 Q1 P0-2 + P1-1 修复进度（保持历史记录）

| S | 阶段 | 状态 | 关键产物 |
|---|------|------|----------|
| S1 | 杀后台 + 备份 | ✅ 完成 | PID 5680 killed; snapshot 在 `results/snapshots/pre_p02_p11_fix/` |
| S2 | P0-2 完整修复 | ✅ 完成 | LOO 输出文件删除 + paper/INDEX/WORK_STATE 去引用 + bug 修复 (avg_score_ci_width → avg_score_ci) |
| S3 | P1-1 完整修复 | ✅ 完成 | _score_per_plan 改 percentile_zscore_score + score_* 标记 details-only + run_scoring 统一为 dim_scores_from_per_plan |
| S4 | 重跑 q1_scoring + q1_holiday_penalty + q1_baseline | ✅ 完成 | q1_score.json: 50.7/D; q1_weights.json: 12.51/14.17/27.10/46.22% |
| S5 | 文档同步 | ✅ 完成 | paper.md / README.md / evaluation_q1.md / q1_section_5_1.md / project-context.mdc 全部更新 |
| S6 | 验证（check_progress 14/14）| ✅ 完成 | 排名 500635396 > 63563817 > 495403620 > 495817671 > 525368335 保持；评级 D 保持；范围 [0,100] 全过 |
| S7 | RUN_LOG 追加 + WORK_STATE 更新 | ✅ 完成 | - |

---

## 0.3 P1-1 修复前后对比

| 维度 | 修复前（score_* 口径）| 修复后（_score_per_plan 列均值）| 变化 |
|---|---|---|---|
| 设计质量与创意 | 55.8 | 52.4 | -3.4 |
| 关键词管理与运用 | 51.6 | 57.6 | +6.0 |
| 出价策略与预算 | 77.6 | 51.9 | -25.7 |
| 投放策略与时间 | 65.8 (扣分前) / 35.8 | 77.4 (扣分前) / 47.4 | +11.6 / +11.6 |
| 综合分（扣分前）| 65.3 | 64.6 | -0.7 |
| 综合分（扣分后）| 56.0 (D) | **50.7 (D)** | **-5.3** |
| CRITIC 权重（混合）| 22.22/14.83/32.16/30.79% | **12.51/14.17/27.10/46.22%** | 时间维度权重大幅上升（CRITIC 自动识别为最高权重） |
| 5 方案排名 | 500635396 > 63563817 > 495403620 > 495817671 > 525368335 | **完全一致** | ✓ 排名未变 |
| 评级 | D (偏差) | **D (偏差)** | ✓ 评级未变 |

---

## 0.4 P0-2 修复动作清单

1. ✅ 删除 `results/tables/q1_generalization_loo_cv.csv`
2. ✅ 删除 `results/figures/q1_generalization_loo_cv.png`
3. ✅ paper.md 第 B.20 行 "LOO-CV" → "time split + bootstrap"
4. ✅ INDEX.md 第 59/117/134 行 "留一 / loo_cv" 删除
5. ✅ WORK_STATE.md 第 144 行 "LOO 重命名" → "LOO 删除"
6. ✅ q1_generalization.py bug 修复：`avg_score_ci_width` → `avg_score_ci`（NameError）
7. ✅ src/q1_generalization.py docstring 保留 "P0-2 完成" 标记（说明性文字，非代码逻辑）

---

## 1. 完整路线图（5 Phase + 终）

| Phase | 内容 | 状态 | 关键产出 |
|-------|------|------|----------|
| 0 | 4 层 context 防护 | ✅ 完成 | WORK_STATE / DECISION_LOG / RUN_LOG / check_progress.py |
| 1 | Q1 7 项修复（评审报告对应）| ✅ 完成 | 统一评分 / Bootstrap / BH FDR / 时间切分 / 权重敏感性 |
| 2 | 完整 Bootstrap（n_boot=100, FDR 校正）| ✅ 完成 | q1_bootstrap_ci.csv (37 节日) + q1_holiday_penalty.json (-30) |
| 3 | **Q2 关键词分类** | ✅ **完成 + 6 项稳健性分析**（2026-09-12 14:18，10/10 自检 PASS）| 主交付物 `results/excel/result2.xlsx` 2227 行严格 8 列对齐附件 2 模板 + 5 类计数 黄金431/重点238/潜力240/问题428/无效890 + 推广单元聚合表 12 行 + 极值审计 105 词（v1 + v2 业务阈值版）+ 4 张图（5 类分布/阈值敏感性/极值审计/推广单元堆叠）+ 6 项稳健性（阈值3对比/字段稳健性 Cohen κ/审计 v2/ghost_browsing/三零词细分/汇总报告）|
| 4 | **Q3 投放策略优化** | ⏸ **待重做**（**幻觉事故清理完成 2026-09-12**）| 真实需求：2025-02-01~08 + 2025-08-01~08 共 16 天；决策粒度 推广单元×关键词×天；预算 ≤2025 同期；预测 4 指标（展位/点击/浏览/注册）|
| 5 | **Q4 不确定性优化** | ⏸ **待重做**（**幻觉事故清理完成 2026-09-12**）| 真实需求：2026-09-11~17 共 7 天；决策粒度 推广单元×关键词×天；6 因素不确定性（竞价/展现/展现位/点击/浏览/注册）；预测 6 个期望值 |
| 终 | 论文数字同步 | ⏸ 待 Phase 3-5 完成后 | paper.md §5.2/5.3/5.4 全补 |

---

## 2. 数据契约（Q1 已确定，Q2-Q4 待重做）

- **原始**：`data/raw/attachments/附件1.xlsx`（3 sheet：方案日表 / 新注册 / 关键词表）
- **Q1 中间产物**：`data/processed/q1/*.pkl`（已生成）
- **Q1 输出**（已确定）：
  - `results/tables/q1_score.json` (overall_score=50.7，D 级偏差)
  - `results/tables/q1_weights.json` (mixed_weights: 12.51% / 14.17% / 27.10% / 46.22%)
  - `results/tables/q1_holiday_penalty.json` (-30 封顶)
  - `results/tables/q1_bootstrap_ci.csv` (37 节日 × 100 次 + BH FDR)
- **Q2 输出**（✅ 已完成 + 6 项稳健性分析）：`results/excel/result2.xlsx`（严格对齐 `data/raw/attachments/附件2/result2.xlsx` 模板列，统一汇总至 `results/excel/`）+ 6 项稳健性产物：`q2_thresholds_compare.json` / `q2_field_robustness.csv` / `q2_extreme_audit_v2.csv` / `q2_zero_keyword_breakdown.csv` / `q2_robustness_report.json` / pkl 新增 `异常标记` 列
- **Q3 输出**（⏸ 待重做）：`results/excel/result3.xlsx`（严格对齐 `data/raw/attachments/附件2/result3.xlsx` 模板列）
- **Q4 输出**（⏸ 待重做）：`results/excel/result4.xlsx`（严格对齐 `data/raw/attachments/附件2/result4.xlsx` 模板列）

---

## 3. 自主决策清单（保留有效决策，作废错位决策）

| ID | 决策 | 选择 | 状态 |
|----|------|------|------|
| D-001 | Q2 分类器 | 二维硬阈值（成本×效益中位数）| ✅ 有效；2026-09-12 14:18 加 6 项稳健性证据 |
| D-002 | Q3 优化器 | 待规划（关键词级 LP/LP+启发式）| ⏸ 备选 D-002 已作废（MILP+NSGA-II）|
| D-003 | Q4 优化器 | 待规划（DRO/Robust LP）| ⏸ 备选 D-003 已作废（SAA+DRO+后悔）|
| D-004 | Bootstrap n_boot | 100 | ✅ 有效（Q1 仍用）|
| D-005 | 节日扣分封顶 | -30 | ✅ 有效（Q1 仍用）|
| D-006 | 权重混合比例 | 70:30（CRITIC:业务）| ✅ 有效（Q1 仍用）|
| D-015 | Q2 字段选择 | (成本=消费额, 效益=CPC倒数) 锁定 | ✅ 2026-09-12 15:30 经 4 组合 Cohen κ 验证（其他 3 组合 κ=0.003~0.294 接近随机）|
| D-016 | Q2 阈值口径 | 均匀中位数（不消费加权）| ✅ 2026-09-12 15:30 验证消费加权导致 T_cost=6.97 万元，分类失效 |
| D-017 | 极值审计风险评级 | 业务阈值（消费>1万=高/5000-1万=中/<5000=低）| ✅ 2026-09-12 15:30 替代原统计分位（105 词全聚集"高"）|
| D-018 | 极值类型分类 | 重点词=保留型 / 问题词=削减型 | ✅ 2026-09-12 15:30（业务语义清晰：加码 vs 削减）|
| D-019 | 异常词标记 | ghost_browsing / potential_revival / truly_dead | ✅ 2026-09-12 15:30（实际：ghost=2 / revival=0 / dead=888）|
| D-020 | Q2 重做完成（+6 项稳健性） | 6 项稳健性 + thresholds.json 加 robustness 字段 | ✅ 2026-09-12 15:30 |
| D-007 | Q2 K | —（已作废）| ❌ 原 D-007 是"GMM K=8"——全部作废 |
| D-008 | Q2 特征维度 | —（已作废）| ❌ 原 D-008 是"5 维（GMM 特征）"——全部作废 |
| D-009 | Q2 命名启发式 | —（已作废）| ❌ 原 D-009 是"GMM 5 优先级命名启发式"——全部作废 |
| D-010 | 幻觉事故清理 | 彻底清理 + 备份 + mdc 强化 | ✅ 2026-09-12 13:25 执行 |

---

## 4. Q1 4 维度评分与权重（最终 · P1-1 口径统一后）

> **P1-1 口径**：维度分 = `_score_per_plan` 5×4 矩阵列均值；权重 = CRITIC + 业务 70:30 混合

| 维度 | 评分 | 权重 |
|---|---|---|
| 设计质量与创意 | 52.4 / 100 | 12.51% |
| 关键词管理与运用 | 57.6 / 100 | 14.17% |
| 出价策略与预算 | 51.9 / 100 | 27.10% |
| 投放策略与时间 | 47.4 / 100（原值 77.4） | 46.22% |

5 个方案最终排名（含扣分）：

| 方案 | 综合分 |
|---|---|
| 500635396 | 61.64 |
| 63563817  | 59.65 |
| 495403620 | 53.11 |
| 495817671 | 49.34 |
| 525368335 | 29.75 |

---

## 5. Q3/Q4 关键结果（**幻觉事故已清理**）

> ⚠️ 以下 Q3/Q4 数据是**幻觉版**（决策粒度错：方案×天，应为关键词×天；时间范围错：365 天，应为 16 天 / 7 天），已彻底清理，备份 `hallucination_v1_20260912/`，**禁止用于真实提交**。

**幻觉版 Q3 MILP**：85,313 → 103,742 (+21.60%)【仅作历史记录，禁止引用】

**幻觉版 Q4 4 策略对比（DRO 3.39%）**【仅作历史记录，禁止引用】

---

## 6. 已完成的 P0/P1/P2 修复（评审报告对应）

| ID | 内容 | 状态 |
|----|------|------|
| P0-1 | 统一 Bootstrap | ✅ |
| P0-2 | 删除 LOO-CV | ✅ |
| P0-3 | Prophet 残差 Z-Score 替代 8月 Z-Score | ✅ |
| P1-1 | 统一评分函数（_score_per_plan 列均值口径）| ✅ |
| P1-4 | CRITIC:业务 比例敏感性 | ✅ |
| P1-5 | BH FDR 校正 | ✅ |
| P1-6 | requirements.txt 生成 | ✅ |
| P2-1 | 龙卷风图扰动后权重无上限约束 | ✅ |

---

## 7. 下一动作（如再开新上下文）

### ⚠️ 强制第一动作（mdc v2 新增约束）

1. **读题面图 2 张 PNG**：`paper/figures/raw_attachments/problem_pages/page_{1,2}.png`
2. **读附件 2 模板 3 个 xlsx**：`data/raw/attachments/附件2/result{2,3,4}.xlsx`
3. **读 .cursor/rules/project-context.mdc**：看「⚠️ 强制流程」节 + 「Q2/Q3/Q4 真实题面摘要」节
4. **读本 WORK_STATE.md 第 0.1 节**：事故教训
5. **不要看 `results/snapshots/hallucination_v1_20260912/`**：作为事故证据保留，**禁止参考其代码**！

### 后续流程

- ✅ Q2 已完成 + 6 项稳健性分析（10/10 自检 PASS，2026-09-12 14:18）
- 检查 `issue/q2_method.md`（**已确认：用户说论文/方法文档先不做**）
- 检查 `paper/paper.md` §5.2（**已确认：用户说论文先不做**）
- 按真实题面规划 Q3（2025-02-01~08 + 2025-08-01~08 共 16 天，关键词×天，预算约束）
- 按真实题面规划 Q4（2026-09-11~17 共 7 天，关键词×天，6 因素不确定性）
