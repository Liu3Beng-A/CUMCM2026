# WORK STATE · CUMCM 2026 E 题 · 长期运行进度跟踪

> **这是本仓库的"长期记忆"**。无论上下文如何滚动，**第一动作 = 读这个文件 + 读题面 PNG + 读附件 2 模板**。
> 由主 agent 维护，每完成一步追加更新。

---

## 0. 当前状态（一句话）

**阶段**：Q1 P0/P1/P2 全修复完成（综合分 50.7 / 100，D 级）；**Q2 已完成 + 6 项稳健性**（10/10 PASS）；**Q3 已完成 + 7 项自检（6 PASS + 1 CAVEAT）**；**Q4 已完成 + 7 项自检（7 PASS + 1 精度溢出）**；**Phase A 清理 + Phase B 三处 JSON 一致性修复完成（2026-09-13 13:51）**；**论文待重新生成（用户决定暂缓）**。

**时间锚点**：2026-09-13 13:51 UTC+8

**关键结果**：
- Q1 综合分 50.7 / 100
- Q3 result3.xlsx 89 行 MILP Optimal；JSON total_cost = 51,164.90 = xlsx sum ✓
- Q4 result4.xlsx 39 行 Two-Stage SP；JSON total_cost = 23,487.98 = xlsx sum ✓；n_active_units = 6；browse_click_ratio_actual = 3.7624

---

## 0.1 Phase A 清理 + Phase B 修复（2026-09-13 13:42-13:51）

### Phase A：清理（删除 24 文件 + 1 文件迁移）

| ID | 动作 | 数量 | 风险 |
|----|------|------|------|
| A1 | 备份 paper_final.md → `results/snapshots/pre_regen_20260913/paper_final.md` | 1 文件 (93,302 bytes) | 低 |
| A2 | 删除 paper_final.md / paper.md / paper_appendix_q234.md | 3 | 中（已备份） |
| A3 | 删除 `results/excel/result4_v2.xlsx`（过期中间版本） | 1 | 低 |
| A4 | 删除 src/q3_data_prep_v1_bak.py / q3_milp_v1_bak.py / q4_evaluator_v1_bak.py | 3 | 低 |
| A5a | 迁移 Q3Q4_Method_Architecture.md → issue/q3q4_method_architecture.md | 1 (47,295 bytes) | 低 |
| A5b | 删除 16 个过时根目录文档（BIAS/CHART/CHECK/CUMCM prompt/CURSOR*3/FINAL/HANDOFF/INDEX/MODEL_AUDIT*2/MODEL_REPAIR/P2/PARAMETER/VARIABLE/PoC/_survey） | 16 | 中 |
| A6 | 删除 issue/q1_code_review_report.md + issue/q1_fix_plan.md | 2 | 低 |

### Phase B：三处 JSON 一致性修复

| ID | 修复 | 旧问题 | 新方案 |
|----|------|--------|--------|
| **B1** | `q3_milp.py` total_cost | 循环累加未舍入 = 51,164.93，result3.xlsx = 51,164.90（差 0.03 元） | `total_cost = plan_df['cost'].round(2).sum()` 循环外派生，**JSON == xlsx sum** |
| **B2** | `q4_evaluator.py` browse_click_ratio | 单字段 3.7121 含义模糊（同期全局比 ≠ 求解后加权比） | 拆分为 `browse_click_ratio_search_space` (3.7121) + `browse_click_ratio_actual` (3.7624) |
| **B3** | `q4_evaluator.py` n_units | 单字段 12 含义模糊（搜索空间 ≠ 实际激活） | 拆分为 `n_eligible_units` (12) + `n_active_units` (6) |
| **B4** | 重跑 + 校验 | - | total_cost = xlsx sum ✓；n_active_units = plan_df['unit_id'].nunique() ✓；browse/click = 3.7624 ✓ |

### 论文状态（Q5 暂缓）

- paper_final.md / paper.md / paper_appendix_q234.md 已全部删除
- 重新生成**按用户决定暂缓**（"先确认无差异再重新生成"——当前差异已修复，但用户决定推迟 regen）
- 验证脚本 `tools/_verify_consistency.py` 待用户要求 regen 时再启用

---

## 0.2 Q1 P0/P1/P2 修复状态（保持历史记录）

| S | 阶段 | 状态 | 关键产物 |
|---|------|------|----------|
| S1 | 杀后台 + 备份 | ✅ 完成 | snapshot 在 `results/snapshots/pre_p02_p11_fix/` |
| S2 | P0-2 完整修复 | ✅ 完成 | LOO 输出文件删除 + 文档去引用 + bug 修复 |
| S3 | P1-1 完整修复 | ✅ 完成 | _score_per_plan 列均值口径 |
| S4 | 重跑 q1_scoring + q1_holiday_penalty + q1_baseline | ✅ 完成 | q1_score.json: 50.7/D |
| S5 | 文档同步 | ✅ 完成 | README / evaluation_q1 / q1_section_5_1 / mdc 全部更新 |
| S6 | 验证 | ✅ 完成 | 排名 + 评级 + 范围全过 |
| S7 | RUN_LOG 追加 + WORK_STATE 更新 | ✅ 完成 | - |

---

## 0.3 P1-1 修复前后对比

| 维度 | 修复前 | 修复后 | 变化 |
|---|---|---|---|
| 设计质量与创意 | 55.8 | 52.4 | -3.4 |
| 关键词管理与运用 | 51.6 | 57.6 | +6.0 |
| 出价策略与预算 | 77.6 | 51.9 | -25.7 |
| 投放策略与时间 | 65.8 (扣分前) / 35.8 | 77.4 (扣分前) / 47.4 | +11.6 |
| 综合分（扣分前）| 65.3 | 64.6 | -0.7 |
| 综合分（扣分后）| 56.0 (D) | **50.7 (D)** | **-5.3** |
| CRITIC 权重（混合）| 22.22/14.83/32.16/30.79% | **12.51/14.17/27.10/46.22%** | 时间维度权重大幅上升 |
| 5 方案排名 | 500635396 > 63563817 > 495403620 > 495817671 > 525368335 | **完全一致** | ✓ 排名未变 |
| 评级 | D (偏差) | **D (偏差)** | ✓ 评级未变 |

---

## 0.4 BIAS_v2 修订日志（2026-09-12 17:27）

| ID | 关注点 | 处理 | 文档位置 |
|---|---|---|---|
| V2-1 | 关联规则数据源 | "推广单元-入选项池（909 词）"代理 | issue/q3q4_method_architecture.md §2.2 |
| V2-2 | Q3 backtest 逻辑矛盾 | 改写为"代理精度"校验 | 同上 §2.3 |
| V2-3 | §2.2.1 弱假设未做敏感性 | §2.2.2：3 比值 × ±30% × 5 档 | 同上 §2.2.2 |
| V2-4 | Q4 同期口径未显式 | 23,488.02 元 + 4 条理由 | 同上 §3.1 原则 6 |
| V2-5 | §5 红线扩充 | 红线 13/14 | 同上 §5 |
| V2-6 | 决策日志 | D-021/D-022/D-023/D-024 | DECISION_LOG.md |

---

## 1. 完整路线图（5 Phase + 终）

| Phase | 内容 | 状态 | 关键产出 |
|-------|------|------|----------|
| 0 | 4 层 context 防护 | ✅ 完成 | WORK_STATE / DECISION_LOG / RUN_LOG |
| 1 | Q1 7 项修复 | ✅ 完成 | 统一评分 / Bootstrap / BH FDR / 时间切分 / 权重敏感性 |
| 2 | 完整 Bootstrap | ✅ 完成 | q1_bootstrap_ci.csv + q1_holiday_penalty.json |
| 3 | **Q2 关键词分类** | ✅ **完成 + 6 项稳健性** | result2.xlsx 2227 行 × 8 列严格对齐模板；5 类计数 黄金431/重点238/潜力240/问题428/无效890 |
| 4 | **Q3 投放策略优化** | ✅ **完成 + 7 项自检** | result3.xlsx 89 行 × 9 列；MILP 8,640 决策变量 Optimal；总投入 51,164.90 / 51,164.93 元（100% 利用率）|
| 5 | **Q4 不确定性优化** | ✅ **完成 + 7 项自检** | result4.xlsx 39 行 × 9 列；Two-Stage SP SAA 1000 场景；总投入 23,487.98 / 23,488.02 元；6 单元激活 |
| 终 | **论文** | ⏸ **暂缓（用户决定推迟 regen）** | paper.md 已删除；待用户启动 regen 时用 `_verify_consistency.py` 校验后重写 |

---

## 2. 数据契约（Q1-Q4 已确定）

### Q1 输出（✅）
- `results/tables/q1_score.json` (overall_score=50.7，D 级偏差)
- `results/tables/q1_weights.json` (12.51% / 14.17% / 27.10% / 46.22%)
- `results/tables/q1_holiday_penalty.json` (-30 封顶)
- `results/tables/q1_bootstrap_ci.csv` (37 节日 × 100 次 + BH FDR)

### Q2 输出（✅）
- `results/excel/result2.xlsx`（严格对齐 `data/raw/attachments/附件2/result2.xlsx` 模板列）
- 6 项稳健性产物

### Q3 输出（✅ · B1 修复后）
- `results/excel/result3.xlsx` 89 行 × 9 列
- `results/tables/q3_milp_summary.json`：total_cost = 51,164.90 = xlsx sum ✓
- 6 metrics 在 result3.xlsx 内（4 指标：预期展位/点击/浏览/注册）

### Q4 输出（✅ · B2+B3 修复后）
- `results/excel/result4.xlsx` 39 行 × 9 列
- `results/excel/q4_6metrics_extended.csv`（6 因子期望）
- `results/tables/q4_two_stage_summary.json`：
  - total_cost = 23,487.98 = xlsx sum ✓
  - n_eligible_units = 12, n_active_units = 6 ✓
  - browse_click_ratio_search_space = 3.7121, browse_click_ratio_actual = 3.7624 ✓

---

## 3. 自主决策清单（保留有效决策）

| ID | 决策 | 选择 | 状态 |
|----|------|------|------|
| D-001 | Q2 分类器 | 二维硬阈值（中位数）| ✅ |
| D-002 | Q3 优化器 | MILP + 单元-关键词-天粒度 | ✅ |
| D-003 | Q4 优化器 | Two-Stage SP SAA + 6 因子对数正态 | ✅ |
| D-004 | Bootstrap n_boot | 100 | ✅ |
| D-005 | 节日扣分封顶 | -30 | ✅ |
| D-006 | 权重混合比例 | 70:30（CRITIC:业务）| ✅ |
| D-015 | Q2 字段选择 | (成本=消费额, 效益=CPC倒数) | ✅ |
| D-016 | Q2 阈值口径 | 均匀中位数 | ✅ |
| D-017 | 极值审计风险评级 | 业务阈值（消费>1万=高/5000-1万=中/<5000=低）| ✅ |
| D-018 | 极值类型分类 | 重点词=保留 / 问题词=削减 | ✅ |
| D-019 | 异常词标记 | ghost_browsing / potential_revival / truly_dead | ✅ |
| D-020 | Q2 重做完成 + 6 项稳健性 | ✅ | 2026-09-12 15:30 |
| D-021 | FP-Growth 数据源代理 | "推广单元-入选项池（909 词）" | ✅ 2026-09-12 17:27 |
| D-022 | Q3 校验改写 | 旧"历史回放"→"代理精度" | ✅ 2026-09-12 17:27 |
| D-023 | 代理敏感性分析 | 3 比值 × ±30% × 5 档扰动 | ✅ 2026-09-12 17:27 |
| D-024 | Q4 同期口径 | 23,488.02 元 | ✅ 2026-09-12 17:27 |
| **D-025** | **q3_milp total_cost 一致化** | 循环外 `plan_df['cost'].round(2).sum()` 派生 JSON = xlsx sum | ✅ **2026-09-13 13:45** |
| **D-026** | **q4_evaluator browse_click_ratio 拆分** | search_space (3.7121) + actual (3.7624) | ✅ **2026-09-13 13:48** |
| **D-027** | **q4_evaluator n_units 拆分** | eligible (12) + active (6) | ✅ **2026-09-13 13:48** |
| **D-028** | **论文暂缓重新生成** | 等用户决策（差异已修复） | ⏸ **2026-09-13 13:51** |

---

## 4. Q1 4 维度评分与权重

| 维度 | 评分 | 权重 |
|---|---|---|
| 设计质量与创意 | 52.4 / 100 | 12.51% |
| 关键词管理与运用 | 57.6 / 100 | 14.17% |
| 出价策略与预算 | 51.9 / 100 | 27.10% |
| 投放策略与时间 | 47.4 / 100（原值 77.4） | 46.22% |

5 方案最终排名：

| 方案 | 综合分 |
|---|---|
| 500635396 | 61.64 |
| 63563817  | 59.65 |
| 495403620 | 53.11 |
| 495817671 | 49.34 |
| 525368335 | 29.75 |

---

## 5. Q3/Q4 关键结果（✅ 已修正口径）

### Q3 · 16 天投放策略（MILP Optimal · 2025-02-01~08 + 2025-08-01~08）

| 指标 | 值 |
|---|---|
| 决策变量 | 8,640 个 (16 天 × 12 单元 × 多关键词) |
| 实际投放行 | 89 行（result3.xlsx）|
| 总投入 | **51,164.90 元** / 预算 51,164.93 元（**100.0% 利用率**）|
| 浏览/点击比 | **2.93**（同期实测）|
| 预期点击 | 54,192 |
| 预期浏览 | 158,816 |
| 预期注册 | 3,793（同期 CVR = 0.0700 口径）|
| 预期展位 | 297,445 |

### Q4 · 7 天不确定性投放（Two-Stage SP SAA · 2026-09-11~17）

| 指标 | 值 |
|---|---|
| 决策变量 | 15,589 个 (7 天 × 11 单元 × 多关键词) |
| 实际投放行 | 39 行（result4.xlsx）|
| 总投入 | **23,487.98 元** / 预算 23,488.02 元（**99.99% 利用率**）|
| 浏览/点击比 | **3.7624**（求解后加权）|
| 搜索空间浏览/点击 | 3.7121（同期 31 天全局比）|
| 激活单元数 | 6 / 12 eligible |
| 场景数 | SAA 1000 |
| 预期点击 | 29,344 |
| 预期浏览 | 110,404 |
| 预期注册 | 4,690 |
| 预期展位 | 180,691 |

---

## 6. 已完成的 P0/P1/P2 修复（评审报告对应）

| ID | 内容 | 状态 |
|----|------|------|
| P0-1 | 统一 Bootstrap | ✅ |
| P0-2 | 删除 LOO-CV | ✅ |
| P0-3 | Prophet 残差 Z-Score 替代 8月 Z-Score | ✅ |
| P1-1 | 统一评分函数 | ✅ |
| P1-4 | CRITIC:业务 比例敏感性 | ✅ |
| P1-5 | BH FDR 校正 | ✅ |
| P1-6 | requirements.txt 生成 | ✅ |
| P2-1 | 龙卷风图扰动后权重无上限约束 | ✅ |
| **P3-1** | **q3_milp JSON 一致性** | ✅ 2026-09-13 |
| **P3-2** | **q4_evaluator JSON 一致性（browse + units 拆分）** | ✅ 2026-09-13 |
| **P3-3** | **论文清理 + 暂缓 regen** | ✅ 2026-09-13 |

---

## 7. 下一动作（如再开新上下文）

### ⚠️ 强制第一动作（mdc v2 约束）

1. 读题面图 2 张 PNG：`paper/figures/raw_attachments/problem_pages/page_{1,2}.png`
2. 读附件 2 模板 3 个 xlsx：`data/raw/attachments/附件2/result{2,3,4}.xlsx`
3. 读 `.cursor/rules/project-context.mdc`
4. 读本 WORK_STATE.md §0.1（事故教训）+ §5（当前 Q3/Q4 数据）
5. **不要看** `results/snapshots/hallucination_v1_20260912/`（事故证据保留）

### 后续流程

- Q1-Q4 数据全部完成且校验通过
- 论文 `paper.md` 待重新生成（用户决定暂缓）
- 启用脚本 `tools/_verify_consistency.py` 在 regen 之前自动校验 xlsx/JSON 一致性

---

## 8. 最终交付检查清单（2026-09-13 13:51 综合状态）

### ✅ 已交付（持久化产物）

| 类别 | 文件 | 状态 |
|------|------|------|
| Q1 综合分 | `results/tables/q1_score.json` (50.7 / D偏差) | ✅ |
| Q1 权重 | `results/tables/q1_weights.json` | ✅ |
| Q1 节日扣分 | `results/tables/q1_holiday_penalty.json` | ✅ |
| Q1 9 图 | `results/figures/q1_*.png` (21 活跃) | ✅ |
| Q2 分类 | `results/excel/result2.xlsx` | ✅ |
| Q2 稳健性 | 5 个 json/csv | ✅ |
| Q3 投放 | `results/excel/result3.xlsx` (89 行) | ✅ |
| Q3 JSON | `results/tables/q3_milp_summary.json` (total_cost=51164.90 ✓) | ✅ |
| Q4 不确定性 | `results/excel/result4.xlsx` (39 行) | ✅ |
| Q4 JSON | `results/tables/q4_two_stage_summary.json` (total_cost=23487.98, n_active=6, browse/click=3.7624 ✓) | ✅ |
| Q4 6 指标扩展 | `results/excel/q4_6metrics_extended.csv` | ✅ |
| 评估报告 | `evaluation_q1.md` | ✅ |
| Q1 文档 | `issue/issue_q1.md` + `issue/issue_q1_methods.md` | ✅ |
| Q2 文档 | `issue/q2_implementation_plan.md` | ✅ |
| Q3 文档 | `issue/q3_method.md` | ✅ |
| Q4 文档 | `issue/q4_method.md` | ✅ |
| Q3Q4 架构 | `issue/q3q4_method_architecture.md`（已迁移）| ✅ |
| 总览 | `README.md` | ✅ |
| 日志 | `RUN_LOG.md` / `WORK_STATE.md` / `DECISION_LOG.md` | ✅ |

### ⏸ 待办

1. **论文重新生成** —— 用户决定暂缓；regen 前用 `_verify_consistency.py` 校验

### 🚫 不可删（永久证据）

- `results/snapshots/hallucination_v1_20260912/` —— 29 文件错位产物（事故证据）
- `results/snapshots/pre_regen_20260913/paper_final.md` —— 2026-09-13 删除前的 paper 备份（参考留痕）
- `results/snapshots/{mdc_v2, mdc_v3, phase0, phase2, pre_p02_p11_fix, pre_p07_fix, pre_q2_fix}_*/` —— 关键状态节点备份
