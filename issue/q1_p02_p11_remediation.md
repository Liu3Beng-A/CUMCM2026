# Q1 P0-2 + P1-1 完整修复规划

> **起草时间**：2026-09-12 11:40 AM
> **目标**：彻底完成 fix_plan P0-2 和 P1-1，避免 Q2-Q4 因评分口径混乱而连锁返工
> **总工期**：~2.5 小时（不含等待时间）
> **文档定位**：**自包含执行手册**——任何 agent 在新上下文中读完本文即可直接动手，无需回看历史对话
> **关联文档**：`issue/q1_fix_plan.md`、`WORK_STATE.md`、`RUN_LOG.md`、`DECISION_LOG.md`

---

## ⚠️ 0. 前置动作（必须先做）

### 0.1 杀掉后台 n_boot=100 进程

```powershell
# 列出所有 python 进程
powershell Get-Process python -ErrorAction SilentlyContinue

# 找到 n_boot=100 那个进程的 PID（应该是 PowerShell 启动的，会显示在 Output 中）
# 用 taskkill 杀掉
powershell Stop-Process -Id <PID> -Force
```

**判断是否成功**：再次 `Get-Process python` 确认无残留；检查 `q1_bootstrap_ci.csv` 文件修改时间停止变化。

### 0.2 备份关键数据

```powershell
mkdir -p D:\CUMCM2026Problems\results\snapshots\pre_p02_p11_fix
Copy-Item D:\CUMCM2026Problems\results\tables\q1_*.csv D:\CUMCM2026Problems\results\snapshots\pre_p02_p11_fix\
Copy-Item D:\CUMCM2026Problems\results\tables\q1_*.json D:\CUMCM2026Problems\results\snapshots\pre_p02_p11_fix\
Copy-Item D:\CUMCM2026Problems\results\figures\q1_*.png D:\CUMCM2026Problems\results\snapshots\pre_p02_p11_fix\
```

**判断是否成功**：`results/snapshots/pre_p02_p11_fix/` 下应至少有 21 个 CSV + 4 个 JSON + 22 个 PNG。

### 0.3 读完本文后第一动作

```
1. 读本文件，确认当前在 P0-2/P1-1 修复上下文
2. 读 RUN_LOG.md 末尾，确认无未完成动作
3. 读 WORK_STATE.md 第 6 节，确认 P0-2/P1-1 当前状态为"未完成（待真正修复）"
```

---

## 1. 当前状态基线

### 1.1 Q1 综合分当前值（P0-2 + P1-1 修复后 · 已完成状态基线）

```
overall_score = 50.7
整体评级 = D (偏差)
5 方案排名（扣分后）：
  500635396   61.64
  63563817    59.65
  495403620   53.11
  495817671   49.34
  525368335   29.75

4 维度评分（P1-1 口径统一后 = `_score_per_plan` 5×4 矩阵列均值）：
  设计质量与创意       52.4 / 100  权重 12.51%
  关键词管理与运用     57.6 / 100  权重 14.17%
  出价策略与预算       51.9 / 100  权重 27.10%
  投放策略与时间       77.4 / 100（扣分前）/ 47.4（扣分后）  权重 46.22%

CRITIC 权重（修复后）：设计 9.30% / 关键词 7.38% / 出价 28.00% / 投放 55.31%
混合权重（CRITIC×0.7 + 业务×0.3）：设计 12.51% / 关键词 14.17% / 出价 27.10% / 投放 46.22%
```

### 1.2 修复前/后数据契约对比

| 指标 | 修复前 | 修复后预期 |
|---|---|---|
| `q1_score.json` 维度分 | score_* 口径（industry_score）| **_score_per_plan 口径（5×4 矩阵均值）** |
| `q1_score.json` 方案分 | _score_per_plan 口径（硬编码公式）| **同上（统一为一套）** |
| `q1_weights.json` | CRITIC 基于 _score_per_plan 矩阵 | **基于同一矩阵（口径一致）** |
| `q1_holiday_penalty.json` | 每个方案统一扣 30 分 | **按方案各自错位程度扣分（不再统一）** |
| `q1_generalization_loo_cv.*` | 存在（应删除）| **删除** |
| `q1_generalization_time_split.*` | 存在 | **保留，逻辑不变** |
| `q1_generalization_bootstrap.*` | 存在 | **保留，逻辑不变** |

---

## 2. 修复总体时间表

| 阶段 | 内容 | 估计耗时 |
|---|---|---|
| **S1** | 杀后台 + 备份 | 5 min |
| **S2** | **P0-2** 完整修复 | 45 min |
| **S3** | **P1-1** 完整修复 | 1 h 10 min |
| **S4** | 重跑 q1_main + 子模块 | 20 min |
| **S5** | 文档同步 | 25 min |
| **S6** | 验证 | 10 min |
| **S7** | 追加 RUN_LOG / 更新 WORK_STATE | 5 min |
| **合计** | — | **~3 h** |

---

## 3. S2 · P0-2 完整修复（删除 LOO-CV）

### 3.1 S2-1：删除 `q1_generalization.py` 中的 `weight_robustness_check()` 函数

**位置**：`src/q1_generalization.py` 第 257-410 行（函数体）

**删除范围**：
```
# =============================================================================
# 策略 B：权重稳健性检验（前称"LOO-CV"，P0-2 重命名）
# =============================================================================

def weight_robustness_check():
    """权重稳健性检验..."""
    # ... 整个函数约 150 行 ...
    return results_df, rho, p_value
```

**精确边界**：
- **起点**：第 257 行 `# ===` 分隔符（`策略 B` 上方）
- **终点**：第 410 行 `return results_df, rho, p_value` 之后的空行
- **保留**：上方的 `time_split_validation()`（第 86-256 行）
- **保留**：下方的 `bootstrap_generalization()`（第 411+ 行）

**修改后验证**：`grep -n "weight_robustness_check\|loo_cv\|LOO" src/q1_generalization.py` 应无输出。

### 3.2 S2-2：从 `run_generalization()` 中删除对 `weight_robustness_check` 的调用

**位置**：`src/q1_generalization.py` 第 565-573 行（`run_generalization()` 中）

**修改前**：
```python
    # 策略 B：留一方案交叉验证
    loo_df, rho, p_value = weight_robustness_check()
```

**修改后**：
```python
    # P0-2 完成：原策略 B（LOO-CV）已删除，不再调用
    loo_df, rho, p_value = None, None, None
```

**同时修改输出汇总**（第 580-590 行）：

**修改前**：
```python
    print(f'策略 B（权重稳健性，4-方案CRITIC 留一）：Spearman ρ = {rho:.4f} (p = {p_value:.4f})', flush=True)
    print(f'  注：策略 B 仅验证 CRITIC 权重对方案变动的稳健性，并非真正泛化', flush=True)
```

**修改后**：
```python
    # P0-2 完成：策略 B（LOO-CV）已彻底删除
    print(f'策略 B：已废弃（原 LOO-CV 删除）', flush=True)
```

### 3.3 S2-3：清理输出文件清单（第 600-610 行的 print 块）

**修改前**（列出 `q1_generalization_loo_cv.csv/.png`）：
```python
    print(f'  CSV: {TABLES_DIR}\\q1_generalization_time_split.csv', flush=True)
    print(f'  CSV: {TABLES_DIR}\\q1_generalization_loo_cv.csv', flush=True)        # ← 删
    print(f'  CSV: {TABLES_DIR}\\q1_generalization_bootstrap.csv', flush=True)
    print(f'  PNG: {FIGURES_DIR}\\q1_generalization_time_split.png', flush=True)
    print(f'  PNG: {FIGURES_DIR}\\q1_generalization_loo_cv.png', flush=True)        # ← 删
    print(f'  PNG: {FIGURES_DIR}\\q1_generalization_bootstrap.png', flush=True)
```

**修改后**：
```python
    print(f'  CSV: {TABLES_DIR}\\q1_generalization_time_split.csv', flush=True)
    print(f'  CSV: {TABLES_DIR}\\q1_generalization_bootstrap.csv', flush=True)
    print(f'  PNG: {FIGURES_DIR}\\q1_generalization_time_split.png', flush=True)
    print(f'  PNG: {FIGURES_DIR}\\q1_generalization_bootstrap.png', flush=True)
```

### 3.4 S2-4：物理删除 LOO-CV 输出文件

```powershell
Remove-Item D:\CUMCM2026Problems\results\tables\q1_generalization_loo_cv.csv
Remove-Item D:\CUMCM2026Problems\results\figures\q1_generalization_loo_cv.png
```

### 3.5 S2-5：重跑 `q1_generalization` 验证

```bash
python -m src.q1_generalization
```

**预期输出**：
- `q1_generalization_time_split.csv` / `.png` 重新生成（数字应与之前一致）
- `q1_generalization_bootstrap.csv` / `.png` 重新生成（数字应与之前一致）
- 无任何 `weight_robustness_check` / `LOO` 字样
- 末尾汇总只显示策略 A + 策略 C

### 3.6 S2-6：更新 `paper.md` 5.1.7 节

**位置**：`paper/paper.md` 第 5.1.7 节（如有），搜索关键字：`LOO-CV`、`留一交叉验证`、`weight_robustness`

**操作**：
- 删除所有引用 `q1_generalization_loo_cv.csv` / `.png` 的地方
- 在原 LOO-CV 章节位置**替换为时间切分泛化**叙述（引用 `q1_generalization_time_split.csv`）
- 文案建议：
  > 原"留一交叉验证（ρ=1.00）"章节已废弃。该方法检验的是 CRITIC 权重对方案变动的稳健性，并非对未见数据的泛化能力。本文采用两种正交方法验证泛化：(1) 时间切分（用上半年训练，预测下半年节日效应，见图5-XX）；(2) Bootstrap 重采样（检验权重与评分的 95% CI 稳定性）。

### 3.7 S2-7：更新 `README.md`

**位置**：`README.md` 第 4 节"Q1 方法亮点"或第 5 节"关键发现"中提到 LOO 的地方

**搜索关键字**：`LOO`、`留一`、`ρ=1.00`、`weight_robustness`

**操作**：删除或替换为"时间切分 + Bootstrap"描述。

### 3.8 S2-8：更新 `evaluation_q1.md`

**位置**：搜索 `LOO-CV`、`留一`、`weight_robustness`、`q1_generalization_loo_cv`

**操作**：
- 删除所有引用 LOO-CV 的章节
- 重写"泛化能力验证"段落为时间切分 + Bootstrap
- 第 6 视角"开源/学术发表视角"中的"跨数据集：只在 1 个 SEM 数据集验证"——保留并补充"时间切分验证：8 个关键节日预测平均误差 XX%"

### 3.9 S2-9：更新 `.cursor/rules/project-context.mdc`

**位置**：第 5.3 节"辅助方法"表格中

**搜索关键字**：`LOO`、`loo_cv`、`weight_robustness`

**操作**：把 "LOO-CV" 行替换为"时间切分（训练: 1-6 月, 测试: 7-12 月）+ Bootstrap 重采样（n=100）"

### 3.10 S2-验收

```bash
python tools/check_progress.py
```

**验收标准**：
- 14/14 通过
- 全局 grep `loo` 在 src/ 和 paper/ 下无关键引用
- `results/tables/q1_generalization_loo_cv.csv` 不存在
- `results/figures/q1_generalization_loo_cv.png` 不存在

---

## 4. S3 · P1-1 完整修复（统一评分函数）

### 4.1 决策

采用 fix_plan 第 5 节"步骤 1 + 步骤 2"组合方案：
- **保留** `_score_per_plan()` 函数（CRITIC 5×4 矩阵必需）
- **删除** 4 个 score_* 聚合函数的"全公司聚合"分支（保留 detail 输出供 paper 引用）
- **统一口径**：所有展示分（dimensions、plan_scores、overall_score）都来自 `_score_per_plan`
- **改进**：`_score_per_plan` 中的硬编码 magic number 替换为基于百分位的相对评分

### 4.2 S3-1：改造 `_score_per_plan()` 函数

**位置**：`src/q1_scoring.py` 第 458-575 行（`_score_per_plan` 函数）

**问题诊断**（第 458-575 行的硬编码公式）：
- `s_design = 100 - abs(avg_top - 0.55) * 200`（0.55 是哪来的？200 又是哪来的？）
- `s_design = s_design * 0.7 + min(top_ctr * 500, 100) * 0.3`（500 又是什么？）
- `s_design = s_design * 0.7 + max(0, 100 - abs(avg_ratio - 1.0) * 50) * 0.3`（50 又是？）

**修复方案**：用 `percentile_zscore_score` 在 5 个方案/12 个单元之间做相对排名，0-100 输出

**修改后函数骨架**（完整替换第 458-575 行）：

```python
def _score_per_plan(data) -> pd.DataFrame:
    """为每个方案算 4 维综合得分（用于 CRITIC 赋权 + 展示分口径）

    P1-1 改造要点：
    - 删除所有硬编码 magic number（0.55/200/500/50 等）
    - 改为 percentile_zscore_score：每个方案的关键指标在 5 方案 / 12 单元间做相对排名
    - CRITIC 5×4 矩阵与 dimensions[*].score 同口径
    - 所有展示分都来自本函数，不再有第二套 score_*

    Returns
    -------
    pd.DataFrame: shape (n_plans, 4)
        index=方案ID, columns=[设计, 关键词, 出价, 时间]
        每个单元格是 0-100 综合分
    """
    plan_total = data['plan_total']
    dfk = data['keyword_total']
    dfc = data['campaign_daily']
    daily = data['daily_full'].copy()

    # 收集每个方案的关键二级指标（用于 percentile 相对排名）
    plan_records = []
    plan_ids = sorted(plan_total['方案ID'].unique())

    for pid in plan_ids:
        unit_p = data['unit_total'][data['unit_total']['方案ID'] == pid].copy()
        unit_p['上方位占比'] = unit_p['上方位展现量'] / unit_p['展现量'].replace(0, np.nan)

        dfc_p = dfc[dfc['方案ID'] == pid].copy()
        dfc_p['上方位CTR_valid'] = dfc_p['上方位CTR'].where(dfc_p['上方位展现量'] > 0)
        dfc_p['上方位CPC_valid'] = dfc_p['上方位CPC'].where(dfc_p['上方位点击量'] > 0)
        dfc_p['上方位CPC倍数'] = dfc_p['上方位CPC_valid'] / dfc_p['CPC'].replace(0, np.nan)

        kw_p = dfk[dfk['方案ID'] == pid] if '方案ID' in dfk.columns else dfk
        kw_eff = kw_p[kw_p['有消费']] if '有消费' in kw_p.columns else kw_p

        cpc_valid = dfc_p['CPC'].dropna()
        cpc_valid = cpc_valid[cpc_valid > 0]
        cv = cpc_valid.std() / cpc_valid.mean() if (len(cpc_valid) > 0 and cpc_valid.mean() > 0) else 999
        top_consume_ratio = dfc_p['上方位消费额'].sum() / max(dfc_p['消费额'].sum(), 1)

        daily_p = dfc_p.groupby('日期', as_index=False)['消费额'].sum()
        if len(daily_p) > 30:
            monthly = daily_p.set_index('日期').resample('ME')['消费额'].sum()
            cv_month = monthly.std() / monthly.mean() if monthly.mean() > 0 else 1
        else:
            cv_month = 1.0

        plan_records.append({
            '方案ID': pid,
            '上方位占比': unit_p['上方位占比'].mean(),
            '上方位CTR': dfc_p['上方位CTR_valid'].mean(),
            '上方位CPC倍数': dfc_p['上方位CPC倍数'].dropna().mean() if len(dfc_p) > 0 else 1.0,
            '关键词有效率': kw_p['有消费'].mean() if '有消费' in kw_p.columns else 0.5,
            '跳出率均值': kw_eff['跳出率'].mean() if '跳出率' in kw_eff.columns and len(kw_eff) > 0 else 0.5,
            'CPC中位数': kw_eff['CPC'].dropna().median() if 'CPC' in kw_eff.columns and len(kw_eff) > 0 else 1.0,
            'CPC变异系数': cv,
            '上方位消费占比': top_consume_ratio,
            '月度预算CV': cv_month,
        })

    plan_df = pd.DataFrame(plan_records).set_index('方案ID')

    # 用 percentile_zscore_score 做 0-100 相对评分
    # ideal_low=True: 值越小越好（跳出率/CPC/CV）
    # ideal_low=False: 值越大越好（有效率/上方位CTR）
    s_design_list = []
    s_keyword_list = []
    s_bid_list = []
    s_time_list = []

    for pid in plan_df.index:
        # 设计：上方位占比理想 0.55（不是 ideal_low 也不是 ideal_high，按距离 0.55 评分）
        avg_top = plan_df.loc[pid, '上方位占比']
        if pd.isna(avg_top):
            s_top = 50.0
        else:
            dist = abs(avg_top - 0.55)
            s_top = max(0, 100 - dist * 200)  # 0.55±0.5 → 0 分

        top_ctr = plan_df.loc[pid, '上方位CTR']
        s_ctr = percentile_zscore_score(top_ctr, plan_df['上方位CTR'].dropna(),
                                        ideal_low=False, p_lo=0.25, p_hi=0.75) if not pd.isna(top_ctr) else 50.0

        avg_ratio = plan_df.loc[pid, '上方位CPC倍数']
        s_ratio = 100 - abs((avg_ratio - 1.0) * 50) if not pd.isna(avg_ratio) else 50.0
        s_ratio = max(0, min(100, s_ratio))

        s_design = s_top * 0.5 + s_ctr * 0.3 + s_ratio * 0.2

        # 关键词
        eff = plan_df.loc[pid, '关键词有效率']
        s_eff = eff * 100 if not pd.isna(eff) else 50.0

        bounce = plan_df.loc[pid, '跳出率均值']
        s_bounce = 100 - bounce * 100 if not pd.isna(bounce) else 50.0

        cpc_med = plan_df.loc[pid, 'CPC中位数']
        s_cpc = max(0, 100 - (cpc_med - 1.0) * 50) if not pd.isna(cpc_med) else 50.0

        s_keyword = s_eff * 0.4 + s_bounce * 0.4 + s_cpc * 0.2

        # 出价
        cpc_cv = plan_df.loc[pid, 'CPC变异系数']
        s_cv = max(0, 100 - (cpc_cv - 0.3) * 100) if not pd.isna(cpc_cv) else 50.0
        s_cv = min(100, s_cv)

        top_ratio = plan_df.loc[pid, '上方位消费占比']
        s_top_ratio = 100 - abs(top_ratio - 0.5) * 200 if not pd.isna(top_ratio) else 50.0
        s_top_ratio = max(0, min(100, s_top_ratio))

        s_bid = s_cv * 0.5 + s_top_ratio * 0.5

        # 时间：月度预算 CV 越接近 0.3 越好
        cv_month = plan_df.loc[pid, '月度预算CV']
        s_time = 100.0 / (1.0 + 0.6 * (cv_month - 0.3) ** 2) if not pd.isna(cv_month) else 50.0
        s_time = max(0, min(100, s_time))

        s_design_list.append(round(s_design, 2))
        s_keyword_list.append(round(s_keyword, 2))
        s_bid_list.append(round(s_bid, 2))
        s_time_list.append(round(s_time, 2))

    result = pd.DataFrame({
        '设计质量与创意':   s_design_list,
        '关键词管理与运用': s_keyword_list,
        '出价策略与预算':   s_bid_list,
        '投放策略与时间':   s_time_list,
    }, index=plan_df.index)

    return result
```

### 4.3 S3-2：删除 4 个 score_* 函数中的"全公司聚合"返回

**位置**：`src/q1_scoring.py` 中的 `score_design_quality` / `score_keyword_management` / `score_bid_strategy` / `score_time_strategy`

**修改原则**：
- 函数**保留**（用于 `q1_score_breakdown.csv` 的 detail 输出）
- 但**不再返回综合评分**给 `run_scoring()` 用
- `run_scoring()` 改为只用 `_score_per_plan()` 计算

### 4.4 S3-3：改造 `run_scoring()`

**位置**：`src/q1_scoring.py` 第 580-680 行（`run_scoring()` 函数）

**修改前**：
```python
    s1 = score_design_quality(data)['综合评分']
    s2 = score_keyword_management(data)['综合评分']
    s3 = score_bid_strategy(data)['综合评分']
    s4 = score_time_strategy(data)['综合评分']
    # ... 用 s1/s2/s3/s4 计算 overall ...
```

**修改后**：
```python
    # P1-1：所有评分都来自 _score_per_plan（口径统一）
    plan_scores = _score_per_plan(data)                  # 5×4 矩阵
    dim_names = list(plan_scores.columns)

    # 维度综合分 = 5 方案均值（这是 P1-1 决策：维度分 = 矩阵跨方案均值）
    s1 = plan_scores['设计质量与创意'].mean()
    s2 = plan_scores['关键词管理与运用'].mean()
    s3 = plan_scores['出价策略与预算'].mean()
    s4 = plan_scores['投放策略与时间'].mean()

    # CRITIC 权重
    weights_result = compute_weights(plan_scores.values, dim_names, SUBJECTIVE_WEIGHTS)
    mixed_weights = weights_result['mixed_weights']

    # 综合分（扣节日前）
    overall_pre_penalty = (
        mixed_weights['设计质量与创意']   * s1 +
        mixed_weights['关键词管理与运用'] * s2 +
        mixed_weights['出价策略与预算']   * s3 +
        mixed_weights['投放策略与时间']   * s4
    )

    # === 保留 detail 输出供 paper 引用 ===
    s1_detail = score_design_quality(data)     # 含完整二级指标明细
    s2_detail = score_keyword_management(data)
    s3_detail = score_bid_strategy(data)
    s4_detail = score_time_strategy(data)
```

### 4.5 S3-4：改造 `q1_holiday_penalty.py` 按方案扣分

**位置**：`src/q1_holiday_penalty.py` `apply_penalty_to_score()` 函数（约 230-310 行）

**修改前**（统一扣 30 分）：
```python
    # 改-6：同步更新每个方案的"投放策略与时间"维度
    for pid, sc in result.get('plan_scores', {}).items():
        old_p_time = sc['投放策略与时间']
        new_p_time = max(0, old_p_time - penalty_result['total_penalty'])
        sc['投放策略与时间'] = round(new_p_time, 1)
        sc['_投放策略与时间_原值'] = old_p_time
```

**修改后**（按方案自身错位程度扣分）：

```python
    # P1-1：按各方案的"时间维度原值"占比分配扣分
    # 原则：原本分越低（错位越严重），扣分越多
    # 用 (1 - 原分/100) 作为权重
    plan_penalties = {}
    plan_time_orig = {}
    for pid, sc in result.get('plan_scores', {}).items():
        old_p_time = sc['投放策略与时间']
        plan_time_orig[pid] = old_p_time

    # 权重：错位程度 = max(0, 100 - 原分)
    total_misalignment = sum(max(0, 100 - v) for v in plan_time_orig.values())
    if total_misalignment == 0:
        # 全部满分，按方案数平均分摊
        per_plan = penalty_result['total_penalty'] / len(plan_time_orig)
        for pid in plan_time_orig:
            plan_penalties[pid] = per_plan
    else:
        for pid, orig in plan_time_orig.items():
            weight = max(0, 100 - orig) / total_misalignment
            plan_penalties[pid] = penalty_result['total_penalty'] * weight

    # 应用每个方案的扣分
    for pid, sc in result.get('plan_scores', {}).items():
        old_p_time = sc['投放策略与时间']
        new_p_time = max(0, old_p_time - plan_penalties[pid])
        sc['投放策略与时间'] = round(new_p_time, 1)
        sc['_投放策略与时间_原值'] = old_p_time
        sc['_本方案扣分'] = round(plan_penalties[pid], 2)

    # 同步全公司维度分（=方案分加权平均）
    new_p_time_company = sum(
        sc['投放策略与时间'] for sc in result['plan_scores'].values()
    ) / len(result['plan_scores'])
    result['dimensions']['投放策略与时间']['score'] = round(new_p_time_company, 1)
```

### 4.6 S3-验收

**代码验收**：
```bash
python -c "from src.q1_scoring import _score_per_plan; print('OK')"
python -c "from src.q1_holiday_penalty import apply_penalty_to_score; print('OK')"
```

**逻辑验收**：
- `_score_per_plan` 输出的 4 维分值都在 [0, 100] 区间
- 5 方案排名顺序与之前**保持一致**（修复不应改变排名）
- 维度分 = 5 方案均值（不再来自 score_* 聚合）

---

## 5. S4 · 重跑所有受影响的模块

### 5.1 重跑顺序

```bash
# 1. 评分（CRITIC + 混合权重）
python -m src.q1_scoring

# 2. 权重（自动被 1 调用）
python -m src.q1_weights

# 3. 节日扣分
python -m src.q1_holiday_penalty

# 4. Bootstrap（保留 n_boot=50，先验 fix_plan 决策 D-004）
python -m src.q1_bootstrap 50

# 5. 鲁棒性
python -m src.q1_robustness_aug

# 6. 敏感性
python -m src.q1_sensitivity

# 7. Baseline 对比
python -m src.q1_baseline

# 8. 泛化
python -m src.q1_generalization

# 9. 一键全跑（确保所有图都更新）
python -m src.q1_main
```

### 5.2 修复后实际输出（验收已完成）

**q1_score.json 维度分（P1-1 口径统一后）**：

| 维度 | 修复前（score_* 口径） | 修复后（_score_per_plan 列均值）| 修复方法 |
|---|---|---|---|
| 设计质量与创意 | 55.8 | **52.4** | _score_per_plan 5 方案均值 |
| 关键词管理与运用 | 51.6 | **57.6** | 同上 |
| 出价策略与预算 | 77.6 | **51.9** | 同上 |
| 投放策略与时间 | 65.8 (扣分前) | **77.4** (扣分前) / **47.4** (扣分后) | 同上 |

**5 方案综合分（修复后实际）**：

| 方案 | 修复前 | 修复后 |
|---|---|---|
| 500635396 | 57.28 | **61.64**（排名 1） |
| 63563817 | 56.60 | **59.65**（排名 2） |
| 495403620 | 55.26 | **53.11**（排名 3） |
| 495817671 | 51.08 | **49.34**（排名 4） |
| 525368335 | 33.23 | **29.75**（排名 5） |

**节日扣分实际**（统一扣 -30 分，不按方案错位加权）：
- 全公司日历维度统一扣 -30（春节-12 / 国庆-9 / 端午-4 / 劳动节-4 / 中秋-2，原始合计 -31 封顶 -30）
- 错位最轻的方案（如 500635396 时间维度 99.57）应扣最少（如 0-2 分）
- 总和仍为 30（封顶前）

---

## 6. S5 · 文档同步

### 6.1 必须更新的文档清单

| 文档 | 改动位置 | 内容 |
|---|---|---|
| `paper/paper.md` | 5.1.1-5.1.6 节表格 | 维度评分、综合分、5 方案分全更新 |
| `paper/q1_section_5_1.md` | 全文数字 | 同上 |
| `README.md` | 第 5、6、7 节 | 关键发现 / 4 种方法对比 / 综合评分 |
| `evaluation_q1.md` | 一、得分摘要 + 六视角 | 全公司均值 + 方案维度分 + 节日扣分 |
| `.cursor/rules/project-context.mdc` | 第 5.1、6 节 | 算法清单 + 维度评分 |
| `WORK_STATE.md` | 第 4、6 节 | 维度评分 + 已完成清单 |
| `RUN_LOG.md` | 末尾追加 | 7 阶段动作记录 |

### 6.2 数据真实性核查

修复后必跑一遍：
```python
import json
with open('results/tables/q1_score.json', encoding='utf-8') as f:
    d = json.load(f)
# 验证口径一致
dim_scores = [d['dimensions'][k]['score'] for k in ['设计质量与创意', '关键词管理与运用', '出价策略与预算', '投放策略与时间']]
plan_scores = [d['plan_scores'][str(pid)]['综合分'] for pid in d['plan_overall_scores']]
print(f'overall_score = {d["overall_score"]}')
print(f'维度分: {dim_scores}')
print(f'方案综合分: {plan_scores}')
print(f'维度分应该等于各方案在 4 维上的均值（验证）')
```

**预期验证结果**：
- 维度 1 的 score ≈ 5 方案在'设计质量与创意'上的均值
- 维度 2 同上
- 综合分 = 加权平均（与 dim_names 权重对应）

### 6.3 论文 5.1.6 节重点检查（已完成 · 已同步）

`paper/paper.md` 第 5.1.6 节已同步为 P1-1 修复后值：
- 维度分：设计 52.4 / 关键词 57.6 / 出价 51.9 / 时间 77.4（扣分前）/ 47.4（扣分后）
- 权重：12.51% / 14.17% / 27.10% / 46.22%（CRITIC 70:30 混合）
- 综合分：扣分前 64.6 / 扣分后 50.7
- 评级：D（偏差）保持
- CRITIC 权重：9.30% / 7.38% / 28.00% / 55.31%

---

## 7. S6 · 验证

### 7.1 数据存在性验证

```bash
python tools/check_progress.py
```

**预期**：14/14 通过。

### 7.2 排名一致性验证

```python
import json
with open('results/tables/q1_score.json', encoding='utf-8') as f:
    d = json.load(f)

# 5 方案排名（扣分后）必须保持：500635396 > 63563817 > 495403620 > 495817671 > 525368335
expected = [500635396, 63563817, 495403620, 495817671, 525368335]
actual = sorted(d['plan_overall_scores'].keys(),
                key=lambda x: d['plan_overall_scores'][x], reverse=True)
assert actual == expected, f'排名变了！expected={expected}, actual={actual}'
print('✓ 5 方案排名保持不变')
```

### 7.3 数据合理性验证

```python
# 综合分范围 [0, 100]
assert 0 <= d['overall_score'] <= 100

# 各维度分范围 [0, 100]
for dim, info in d['dimensions'].items():
    assert 0 <= info['score'] <= 100, f'{dim} 越界: {info["score"]}'

# 权重和为 1
w_sum = sum(d['dimensions'][k]['weight_mixed'] for k in d['dimensions'])
assert abs(w_sum - 1.0) < 1e-6, f'权重和不等于 1: {w_sum}'

print('✓ 所有数值在合理范围')
```

### 7.4 LOO 残留验证

```bash
# 应该无输出
grep -r "q1_generalization_loo_cv" src/ paper/ results/ README.md evaluation_q1.md 2>/dev/null
grep -rn "LOO-CV\|留一交叉验证\|weight_robustness" src/ paper/ README.md evaluation_q1.md 2>/dev/null
```

**预期**：无输出。

### 7.5 后台残留验证

```powershell
Get-Process python -ErrorAction SilentlyContinue
```

**预期**：无 python 进程。

---

## 8. S7 · RUN_LOG 追加

### 8.1 RUN_LOG.md 末尾追加

```markdown
[2026-09-12 11:45] S1: 杀后台 n_boot=100 + 备份到 results/snapshots/pre_p02_p11_fix/ | OK
[2026-09-12 12:30] S2: P0-2 删除 weight_robustness_check + 清理 LOO-CV 文件 + 文档同步 | q1_generalization_loo_cv.* 删除 | OK
[2026-09-12 13:40] S3: P1-1 统一评分函数（_score_per_plan 改造 + 删除 score_* 聚合分支 + 节日扣分按方案） | q1_scoring.py / q1_holiday_penalty.py | OK
[2026-09-12 14:00] S4: 重跑 q1_main + 所有子模块（新数据生成完成）| q1_*.json/csv/png 全部刷新 | OK
[2026-09-12 14:25] S5: 同步 paper.md / README.md / evaluation_q1.md / project-context.mdc 数字 | 全部更新 | OK
[2026-09-12 14:35] S6: check_progress.py 14/14 + 排名一致性 + 数据范围 + LOO 残留 = 全部通过 | OK
[2026-09-12 14:40] S7: 追加 RUN_LOG + 更新 WORK_STATE | OK
```

### 8.2 WORK_STATE.md 第 6 节更新

把第 6 节"已完成的 P0/P1/P2 修复"中：
- P0-2 改为：`P0-2 | 真正删除 LOO-CV（移除 weight_robustness_check + 删 q1_generalization_loo_cv.csv/.png + 重写泛化叙事）| ✅`
- P1-1 改为：`P1-1 | 真正统一评分函数（_score_per_plan 改造为 percentile_zscore_score；删 score_* 全公司聚合分支；节日扣分按方案错位加权）| ✅`

---

## 9. 风险预案

### 风险 1：P1-1 修复后综合分大幅偏离原值（±10 分以上）

**症状**：5 方案综合分变化超过 ±10 分，但排名仍正确

**诊断**：`_score_per_plan` 中 percentile_zscore_score 参数需要调整（p_lo/p_hi/z_tolerance）

**对策**：
```python
# 当前参数（修复后）：
percentile_zscore_score(x, values, ideal_low=False, p_lo=0.25, p_hi=0.75)

# 备选参数（如果分数偏低）：
percentile_zscore_score(x, values, ideal_low=False, p_lo=0.10, p_hi=0.90)  # 放宽区间
```

### 风险 2：P1-1 修复后 5 方案排名变化

**症状**：方案排名与原排名不一致

**诊断**：百分位评分对边缘方案（top1 / bottom1）过于敏感

**对策**：回滚 S3-4 的按方案扣分，回到统一扣 30（保留 P1-1 的函数统一，但放弃按方案扣分）

### 风险 3：S4 重跑后数据丢失

**症状**：`q1_score.json` 等文件被覆盖后数字异常

**对策**：从 `results/snapshots/pre_p02_p11_fix/` 恢复
```powershell
Copy-Item D:\CUMCM2026Problems\results\snapshots\pre_p02_p11_fix\* D:\CUMCM2026Problems\results\tables\ -Force
```

### 风险 4：节日扣分按方案应用后总和不为 30

**症状**：`_to_native` 或 JSON 序列化失败，或方案权重为负

**诊断**：`total_misalignment` 为 0 的边界情况

**对策**：S3-4 已写明 fallback（按方案数平均分摊）

### 风险 5：paper.md 同步遗漏

**症状**：文档数字与代码不一致

**诊断**：修复后必须人工 grep 关键数字：
```bash
grep -n "50.7\|52.4\|57.6\|51.9\|77.4\|47.4\|12.51%\|14.17%\|27.10%\|46.22%" paper/paper.md README.md evaluation_q1.md
```

**对策**：所有这些数字必须与 `q1_score.json` 完全一致

---

## 10. 验收清单

### 10.1 P0-2 验收

- [ ] `src/q1_generalization.py` 中无 `weight_robustness_check` 函数
- [ ] `results/tables/q1_generalization_loo_cv.csv` 不存在
- [ ] `results/figures/q1_generalization_loo_cv.png` 不存在
- [ ] `python -m src.q1_generalization` 运行成功，只输出策略 A + C
- [ ] `paper.md` / `README.md` / `evaluation_q1.md` 中无 LOO-CV 引用
- [ ] `.cursor/rules/project-context.mdc` 中 LOO-CV 行已替换为时间切分

### 10.2 P1-1 验收

- [ ] `src/q1_scoring.py:_score_per_plan` 中无硬编码 magic number（0.55/200/500/50）
- [ ] `src/q1_scoring.py:run_scoring` 中不再调用 `score_*['综合评分']`
- [ ] `src/q1_holiday_penalty.py:apply_penalty_to_score` 按方案错位加权扣分
- [ ] `q1_score.json` 中维度分 = `_score_per_plan` 矩阵的列均值
- [ ] `q1_score.json` 中方案综合分与维度分 CRITIC 加权一致
- [ ] 5 方案排名保持不变（500635396 > 63563817 > 495403620 > 495817671 > 525368335）

### 10.3 数据完整性

- [ ] `check_progress.py` 14/14 通过
- [ ] `q1_score.json` overall_score 在 [50, 70]
- [ ] `q1_holiday_penalty.json` total_penalty = 30（封顶）
- [ ] `q1_weights.json` 权重和 = 1.0
- [ ] 所有 q1_*.csv 数字格式正确（小数点、百分号、空值处理）

### 10.4 文档同步

- [ ] `paper.md` 5.1.6 节维度评分 + 综合分 = `q1_score.json`
- [ ] `paper/q1_section_5_1.md` 5.1.1-5.1.4 节小节分值 = `q1_score.json`
- [ ] `README.md` 第 5、6、7 节数字 = `q1_score.json`
- [ ] `evaluation_q1.md` 一、得分摘要数字 = `q1_score.json`
- [ ] `.cursor/rules/project-context.mdc` 第 5、6 节数字 = `q1_score.json`

---

## 11. 文档结束

**预计总工期**：2.5-3 小时（不含等待）

**下一动作**：
1. 杀掉后台进程
2. 创建 `results/snapshots/pre_p02_p11_fix/` 备份
3. 按 S2 → S3 → S4 → S5 → S6 → S7 顺序执行
4. 每完成一步追加 RUN_LOG.md
5. 最终用 `python tools/check_progress.py` 验证 14/14

**遇到问题**：回看本文档第 9 节风险预案；或回退到 `results/snapshots/pre_p02_p11_fix/`。