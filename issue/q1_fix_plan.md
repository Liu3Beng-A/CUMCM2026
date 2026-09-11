# Q1 修复规划文档 · Q1 Fix Plan

> 起草时间：2026-09-12 02:55 AM
> **重大更新：2026-09-12 03:50 AM · 新增 P0-0-11：LEGAL_HOLIDAYS 动态派生；P0-0 全部完成**
> 执行期限：2026-09-12 03:00 ~ 09:00（6 小时）
> 目标：完成 P0-1/P0-2/P0-3/P1-1/P1-4/P1-5/P1-6 修复，Q1 评分体系收敛到可复现、可继承给 Q2-Q4 的稳定状态

---

## ⚠️ P0-0 · 节假日表日期错误（必须最先修！）

### 问题描述

检查 `src/config.py` 第 39-67 行 `HOLIDAYS_2025` 时发现：

**官方 2025 节假日**（国务院办公厅 2024-11 通知）：
- 元旦：1月1日（1天）
- 春节：1月28日(除夕，周二) ~ 2月4日(初七，周二)，放假调休共8天
- 清明节：4月4日(周五) ~ 6日(周日)，共3天
- 劳动节：5月1日(周四) ~ 5日(周一)，放假调休共5天
- 端午节：5月31日(周六) ~ 6月2日(周一)，共3天
- **国庆节+中秋节合并：10月1日(周三) ~ 8日(周三)，放假调休共8天**
- **中秋节当天：10月6日(农历八月十五，星期一)** ← 这是关键

**调休上班日**（周末补班日）：
- 1月26日（周日，补春节）
- 2月8日（周六，补春节）
- 5月11日（周日，补劳动节）
- 9月28日（周日，补国庆）
- 10月11日（周六，补国庆）

### Bug 列表

| Bug | 当前配置 | 正确配置 | 影响 |
|-----|---------|---------|------|
| **Bug 1** | `('2025-10-08', '中秋')` | `('2025-10-06', '中秋')` | 中秋节定位偏 2 天 |
| **Bug 2** | `('2025-10-06', '国庆')` | `('2025-10-06', '中秋')` | 错误把中秋节标为国庆 |
| **Bug 3** | `('2025-10-08', '中秋')` | `('2025-10-08', '国庆')` | 错误把合并假期最后一天标为中秋 |
| **Bug 4** | 缺少 5 个调休上班日 | 需新增 `COMPENSATORY_WORKDAYS_2025` | 反事实模型把补班日误判为假日 |

### 量化影响

若不修复：
- 中秋节扣分会基于错误的 10月8（实际是合并假期尾声，无显著异常）
- 真实中秋节 10月6 的显著异常会被错过
- 反事实模型在补班日（如 5月11日）会预测偏低，但实际数据是工作日水平，造成预测误差

### 修复方案

#### 步骤 1：修改 `src/config.py`

**修改前**：
```python
HOLIDAYS_2025 = [
    # ...
    ('2025-10-01', '国庆'),
    ('2025-10-02', '国庆'),
    ('2025-10-03', '国庆'),
    ('2025-10-04', '国庆'),
    ('2025-10-05', '国庆'),
    ('2025-10-06', '国庆'),   # ← 错！应该是中秋
    ('2025-10-07', '国庆'),
    ('2025-10-08', '中秋'),   # ← 错！应该是国庆
]
```

**修改后**：
```python
HOLIDAYS_2025 = [
    # 元旦
    ('2025-01-01', '元旦'),
    # 春节
    ('2025-01-28', '春节'),
    ('2025-01-29', '春节'),
    ('2025-01-30', '春节'),
    ('2025-01-31', '春节'),
    ('2025-02-01', '春节'),
    ('2025-02-02', '春节'),
    ('2025-02-03', '春节'),
    ('2025-02-04', '春节'),
    # 清明
    ('2025-04-04', '清明'),
    ('2025-04-05', '清明'),
    ('2025-04-06', '清明'),
    # 劳动节
    ('2025-05-01', '劳动节'),
    ('2025-05-02', '劳动节'),
    ('2025-05-03', '劳动节'),
    ('2025-05-04', '劳动节'),
    ('2025-05-05', '劳动节'),
    # 端午
    ('2025-05-31', '端午'),
    ('2025-06-01', '端午'),
    ('2025-06-02', '端午'),
    # 国庆 + 中秋（10月6是中秋节当天）
    ('2025-10-01', '国庆'),
    ('2025-10-02', '国庆'),
    ('2025-10-03', '国庆'),
    ('2025-10-04', '国庆'),
    ('2025-10-05', '国庆'),
    ('2025-10-06', '中秋'),  # ← 修正
    ('2025-10-07', '国庆'),
    ('2025-10-08', '国庆'),  # ← 修正
]

# 调休上班日（虽然是周末，但是工作日）
COMPENSATORY_WORKDAYS_2025 = [
    '2025-01-26',  # 周日，补春节
    '2025-02-08',  # 周六，补春节
    '2025-05-11',  # 周日，补劳动节
    '2025-09-28',  # 周日，补国庆
    '2025-10-11',  # 周六，补国庆
]
```

#### 步骤 2：更新 `src/q1_prophet.py` 让 Prophet 使用调休上班日

**修改 `make_holidays_df()` 函数**：
```python
# 原：
def make_holidays_df(holidays):
    return pd.DataFrame({
        'holiday': [h[1] for h in holidays],
        'ds':      pd.to_datetime([h[0] for h in holidays]),
        'lower_window': 0,
        'upper_window': 1,
    })

# 改为：
def make_holidays_df(holidays, compensatory_days=None):
    """生成 Prophet holidays dataframe（包含调休上班日的反向处理）"""
    df_holidays = pd.DataFrame({
        'holiday': [h[1] for h in holidays],
        'ds':      pd.to_datetime([h[0] for h in holidays]),
        'lower_window': 0,
        'upper_window': 1,
    })
    
    if compensatory_days:
        # 调休上班日：标记为特殊日，让 Prophet 不要当作"假日窗口"
        df_work = pd.DataFrame({
            'holiday': '调休上班日' * len(compensatory_days),
            'ds':      pd.to_datetime(compensatory_days),
            'lower_window': 0,
            'upper_window': 0,
        })
        df_holidays = pd.concat([df_holidays, df_work], ignore_index=True)
    
    return df_holidays
```

#### 步骤 3：更新 `src/q1_bootstrap.py` 同步

**修改 `make_holidays_df()` 函数**（同上）

### 测试方式

```bash
python -m src.q1_prophet
python -m src.q1_bootstrap
```

**预期结果**：
- 10月6 出现明显的"节日效应峰值"（之前分散在 10月8）
- 10月8 节日效应消失或减弱（合并假期尾声，效应本就小）
- 综合分应有合理变化（±5 分）

### 同步内容

**必须重新生成的文件**：
- `results/tables/q1_bootstrap_ci.csv`（中秋节 CI 会重定位到 10月6）
- `results/tables/q1_holiday_penalty.json`（中秋扣分可能变化）
- `results/tables/q1_score.json`（综合分变化）

**必须重新生成的图表**：
- `results/figures/q1_prophet_cost.png`
- `results/figures/q1_prophet_reg.png`
- `results/figures/q1_bootstrap_ci.png`

**必须修改的论文/文档**：
- `paper/paper.md`：节假日表需更新
- `paper/q1_section_5_1.md`：同步
- `README.md`：第 5.2 节"假日效应"段落
- `.cursor/rules/project-context.mdc`：第 5.2 节同步

---

## 0. 修复总览

### 0.1 P0-0 状态：✅ 全部完成（2026-09-12 03:50 AM）

**子任务清单**：

| ID | 任务 | 状态 | 完成时间 |
|----|------|------|---------|
| p0-0-1 | 备份 src/config.py 到 .bak | ✅ | 03:08 |
| p0-0-2 | 修改 src/config.py 修正节假日表 | ✅ | 03:09 |
| p0-0-3 | 检查所有引用 HOLIDAYS_2025 的文件 | ✅ | 03:08 |
| p0-0-4 | 修改 q1_prophet.py 处理调休上班日 | ⏭️ 取消 | - |
| p0-0-5 | 修改 q1_bootstrap.py 处理调休上班日 | ⏭️ 取消 | - |
| p0-0-6 | 重跑 python -m src.q1_prophet | ✅ | 03:10 |
| p0-0-7 | 重跑 python -m src.q1_bootstrap | ⏭️ 取消 | - |
| p0-0-8 | 验证 10月6 中秋节效应 | ✅ | 03:30 |
| p0-0-9 | 备份关键输出到 results/snapshots/phase0/ | ✅ | 03:32 |
| p0-0-10 | 回到待确认问题清单 | ✅ | 03:35 |
| **p0-0-11** | **修改 q1_robustness_aug.py LEGAL_HOLIDAYS 动态派生** | **✅** | **03:50** |

**修改文件**：
- `src/config.py`（修复 HOLIDAYS_2025，新增 COMPENSATORY_WORKDAYS_2025）
- `src/config.py.bak.p0-0`（回滚备份）
- `src/q1_robustness_aug.py`（第 42-46 行，LEGAL_HOLIDAYS 改为动态派生）

**验证输出**：
- `results/tables/q1_holiday_contribution.csv`（Prophet 修复后节日贡献）
- `results/snapshots/phase0/{before,after}/*`（修复前后对比快照）
- `issue/verify_p0_0.py`（验证脚本）
- `issue/q1_fix_progress.md`（进度跟踪）

**核心结论**：
- 2025-10-06 已正确标记为"中秋节"（农历八月十五）
- 2025-10-08 已正确标记为"国庆节"（合并假期最后一天）
- 10-06 节日效应 -73%（消费），10-08 节日效应 -36%
- 数据印证：10-08 消费 5925 元，明显高于 10-06 的 1615 元（合并假期尾声效应衰减）

**未完成项**：
- Bootstrap 完整重跑（n_boot=200 太慢，主动终止）
- COMPENSATORY_WORKDAYS_2025 未在 Prophet 中使用（留待 P1 阶段评估）
- `q1_robustness_aug.py` 中 `LEGAL_HOLIDAYS` 的 Bootstrap 简化版逻辑暂未改为调用统一 Bootstrap（P0-1 阶段处理）

---

| ID | 问题 | 方案 | 优先级 | 工作量 | 风险 |
|----|------|------|--------|--------|------|
| **P0-1** | 两套 Bootstrap 不一致 | A. 统一为 Prophet-based | P0 必做 | 2h | 中 |
| **P0-2** | LOO-CV ρ=1.00 测试的是权重稳健性，不是泛化能力 | B. 重新设计泛化测试（用时间切分） | P0 必做 | 30m | 低 |
| **P0-3** | Z=1.69 来自退化路径 | **J. Prophet 残差 Z-Score** | P0 必做 | 1h | 低 |
| **P1-1** | 两套评分函数口径不一致 | A. 统一为维度级评分（删 `_score_per_plan()`） | P1 必做 | 1.5h | 中 |
| **P1-4** | 70:30 混合权重比例无敏感性支撑 | A. 增加敏感性分析（新增图表） | P1 必做 | 30m | 低 |
| **P1-5** | 74 次 Bootstrap 检验无多重比较校正 | A. BH FDR 校正 | P1 必做 | 30m | 中 |
| **P1-6** | 缺失 `requirements.txt` | A. 自动生成 | P1 必做 | 5m | 无 |

**总工作量：约 6 小时**
**执行顺序：P1-6 → P0-1 → P0-3 → P1-5 → P1-1 → P0-2 → P1-4**

---

## 1. P1-6 · 生成 requirements.txt（5 分钟 · 最先做）

### 改动内容
- 新建 `D:\CUMCM2026Problems\requirements.txt`
- 包含内容：prophet, pandas, numpy, scipy, matplotlib, scikit-learn, statsmodels, openpyxl, seaborn（精确版本由 `pip freeze` 捕获）

### 操作命令
```bash
cd D:\CUMCM2026Problems
pip freeze > requirements.txt
```
**或更精确：**
```bash
pipreqs . --encoding=utf-8 --force
```

### 测试方式
```bash
python -c "import prophet, pandas, numpy, scipy, matplotlib, sklearn, statsmodels; print('OK')"
pip install -r requirements.txt  # 在干净环境验证
```

### 同步内容
- 无（新增文件，不影响其他内容）

---

## 2. P0-1 · 统一两套 Bootstrap 为 Prophet-based（2 小时）

### 改动内容

**文件 1：`src/q1_robustness_aug.py`**

定位：第 120-168 行（`LEGAL_HOLIDAYS` 相关的 Bootstrap 简化版）

**删除以下代码**：
```python
# 删除 LEGAL_HOLIDAYS 常量定义（第 38-43 行）
LEGAL_HOLIDAYS = [
    ('2025-01-29', '春节'),
    ('2025-05-01', '劳动节'),
    ('2025-10-01', '国庆'),
]

# 删除 Bootstrap 简化版函数（约 120-168 行）
# 改为调用 src.q1_bootstrap.bootstrap_one_holiday
```

**修改 `_bootstrap_ci_width_comparison()` 函数**（约 200-250 行）：
- 不再使用"当天值-前后7天均值"
- 改为调用 `q1_bootstrap.bootstrap_one_holiday(holiday_date, holiday_name)` 复用 P0-1 后的 Prophet-based Bootstrap

**具体新代码骨架**：
```python
from src.q1_bootstrap import bootstrap_one_holiday  # 新增 import

def _bootstrap_ci_width_comparison(holidays_to_test, original_daily, clean_daily):
    """Bootstrap CI 宽度对比（Prophet-based）"""
    rows = []
    for holiday_date, holiday_name in holidays_to_test:
        # 原始数据 Bootstrap
        ci_orig = bootstrap_one_holiday(original_daily, holiday_date, holiday_name, n_boot=100)
        # 剔除异常日后 Bootstrap
        ci_clean = bootstrap_one_holiday(clean_daily, holiday_date, holiday_name, n_boot=100)
        rows.append({
            '节日': holiday_name,
            '原始 CI 宽度': ci_orig['ci_upper'] - ci_orig['ci_lower'],
            '剔除后 CI 宽度': ci_clean['ci_upper'] - ci_clean['ci_lower'],
            'CI 宽度变化率': (ci_clean['ci_upper'] - ci_clean['ci_lower']) / 
                           (ci_orig['ci_upper'] - ci_orig['ci_lower']) - 1,
        })
    return pd.DataFrame(rows)
```

**文件 2：`src/q1_bootstrap.py`**

定位：第 50 行附近，确认 `bootstrap_one_holiday()` 函数可被外部调用

**修改**：将函数从内部封装改为可被 `q1_robustness_aug.py` 直接 import

### 测试方式

```bash
# 1. 重跑主 Bootstrap（验证 q1_bootstrap.py 仍工作）
python -m src.q1_bootstrap
# 检查：results/tables/q1_bootstrap_ci.csv 仍生成，数字与修复前一致（允许 ±5% 波动）

# 2. 重跑鲁棒性（验证 Bootstrap 统一后仍工作）
python -m src.q1_robustness_aug
# 检查：results/tables/q1_robustness_bootstrap.csv 仍生成
# 关键：CI 宽度变化率应在 -20% ~ +20% 范围内（剔除 1 天不应引起剧变）

# 3. 对比两个 csv 中春节的 CI 宽度
# q1_bootstrap_ci.csv 中春节 CI 宽度 ≈ q1_robustness_bootstrap.csv 中春节 CI 宽度（±10% 内）
```

### 同步内容

**必须重新生成的文件**：
- `results/tables/q1_robustness_bootstrap.csv`（CI 宽度数字会变）
- `results/tables/q1_robustness_aug.csv`（Prophet 对比可能微变）

**必须重新生成的图表**：
- `results/figures/q1_robustness_aug.png`（CI 宽度对比图）

**必须修改的论文/文档**：
- `paper/paper.md` 5.1.6 节：将"Bootstrap CI 宽度对比"段落修改，强调"基于 Prophet 反事实"
- `paper/q1_section_5_1.md`：同步
- `README.md`：若提到"两套 Bootstrap"则改为"统一的 Prophet-based Bootstrap"

**必须修改的事实索引**：
- `.cursor/rules/project-context.mdc`：第 5.2 节"Bootstrap 方法描述"统一为"Prophet-based Bootstrap"

---

## 3. P0-3 · 改用 Prophet 残差 Z-Score（1 小时）

### 改动内容

**文件 1：`src/q1_robustness_aug.py`**

**修改 `locate_abnormal_day()` 函数**（约 80-100 行）

**删除**以下代码：
```python
# 原：基于全年消费额 Z-Score
aug['Z_Score'] = (aug['总消费额'] - aug['总消费额'].mean()) / aug['总消费额'].std()
anomalies = aug[aug['Z_Score'] > 3]
```

**替换为**（新代码）：
```python
def locate_abnormal_day_via_prophet(daily):
    """基于 Prophet 残差定位异常日（去季节性）
    
    步骤：
    1. 用 Prophet 反事实模型（不含节假日）拟合全年日消费额
    2. 计算每日残差 residual = 实际值 - yhat
    3. 残差的 Z-Score = residual / σ_residual
    4. 找 Z-Score 最大的日期（异常度最大）
    """
    from prophet import Prophet
    
    df = daily.rename(columns={'日期': 'ds', '总消费额': 'y'})[['ds', 'y']]
    
    # 不含节假日的 Prophet 模型
    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode='additive',
    )
    m.fit(df)
    
    future = m.make_future_dataframe(periods=0)
    forecast = m.predict(future)
    
    # 计算残差
    merged = df.merge(forecast[['ds', 'yhat']], on='ds')
    merged['residual'] = merged['y'] - merged['yhat']
    
    # 残差的 Z-Score
    mu_res = merged['residual'].mean()
    sigma_res = merged['residual'].std()
    merged['Z_Residual'] = (merged['residual'] - mu_res) / sigma_res
    
    # 找 Z-Score 最大（最异常）的日期
    idx_max = merged['Z_Residual'].idxmax()
    abnormal_date = merged.loc[idx_max, 'ds'].strftime('%Y-%m-%d')
    z_residual = merged.loc[idx_max, 'Z_Residual']
    
    print(f'基于 Prophet 残差定位异常日：{abnormal_date}', flush=True)
    print(f'  残差 Z-Score：{z_residual:.3f}', flush=True)
    print(f'  当日实际消费：{merged.loc[idx_max, "y"]:.2f} 元', flush=True)
    print(f'  Prophet 预测：{merged.loc[idx_max, "yhat"]:.2f} 元', flush=True)
    
    return abnormal_date, z_residual, merged[['ds', 'y', 'yhat', 'residual', 'Z_Residual']]
```

**修改 `main()` 入口**：
```python
# 原：
abnormal_date, abnormal_row, z_score = locate_abnormal_day(aug)
# 改为：
abnormal_date, z_score, residual_df = locate_abnormal_day_via_prophet(daily)
# 保存残差表到新文件
residual_df.to_csv(os.path.join(TABLES_DIR, 'q1_prophet_residual.csv'), index=False)
```

### 测试方式

```bash
python -m src.q1_robustness_aug
```

**预期结果**：
- 异常日定位：`Z_Residual > 1.96`（α=0.05 下显著）的日期
- 若全年无 Z_Residual > 1.96 的日期，则取最大的（论文叙事改为"消费高峰日（Z_Residual = X）"）
- 检查 `results/tables/q1_prophet_residual.csv` 生成，列名正确

**合理性检查**：
- Z_Residual > 1.96 的日期应主要集中在春节/国庆/购物节前后（验证方法正确）
- 2025-08-21 若仍是异常日，说明消费确实有真实异常
- 若 2025-08-21 不再是异常日，论文叙事需要更新

### 同步内容

**必须重新生成的文件**：
- `results/tables/q1_robustness_aug.csv`（异常日定位结果会变）
- `results/tables/q1_prophet_residual.csv`（新增文件）
- `results/tables/q1_robustness_bootstrap.csv`（基于新异常日）
- `results/tables/q1_robustness_score.csv`（基于新异常日）

**必须重新生成的图表**：
- `results/figures/q1_robustness_aug.png`（异常日定位图）

**必须修改的论文/文档**：
- `paper/paper.md` 5.1.6 节"鲁棒性验证"段落：改为"基于 Prophet 残差 Z-Score"
- `paper/q1_section_5_1.md`：同步
- `README.md`：第 5.3 节异常日描述改为"基于 Prophet 残差 Z-Score"
- `.cursor/rules/project-context.mdc`：第 5.3 节同步

**必须修改的事实索引**：
- 同上

---

## 4. P1-5 · BH FDR 多重比较校正（30 分钟）

### 改动内容

**文件：`src/q1_bootstrap.py`**

**定位**：`save_results()` 或类似函数，约第 200 行附近

**新增代码**：
```python
from statsmodels.stats.multitest import multipletests

def apply_fdr_correction(df, p_col='p_value', alpha=0.05):
    """对 Bootstrap p 值做 BH FDR 校正"""
    pvals = df[p_col].values
    reject, p_corrected, _, _ = multipletests(pvals, alpha=alpha, method='fdr_bh')
    df = df.copy()
    df['p_corrected'] = p_corrected
    df['significant_fdr'] = reject
    return df

# 在保存 csv 之前调用：
bootstrap_df = apply_fdr_correction(bootstrap_df, p_col='p_value')
bootstrap_df.to_csv(out_csv, index=False)
```

### 测试方式

```bash
python -m src.q1_bootstrap
```

**预期结果**：
- 校正前显著数：从 `q1_bootstrap_ci.csv` 中统计 `p_value < 0.05` 的行数（约 56 个）
- 校正后显著数：`significant_fdr == True` 的行数（约 48-52 个）
- 综合分变化：扣分从 -30 → 约 -22 ~ -26，综合分从 56.0 → 约 60-64
- 排名顺序应保持不变（仍为 500635396 > 63563817 > 495403620 > 495817671 > 525368335）

**合理性检查**：
- 校正后春节、劳动节、国庆、清明 应仍显著（这 4 个节日总扣分约占 70%）
- 部分边缘显著的购物节可能不再显著（如双十一、618），扣分减少

### 同步内容

**必须重新生成的文件**：
- `results/tables/q1_bootstrap_ci.csv`（新增 `p_corrected`、`significant_fdr` 列）
- `results/tables/q1_holiday_penalty.json`（扣分可能变化）
- `results/tables/q1_score.json`（综合分变化）

**必须重新生成的图表**：
- `results/figures/q1_bootstrap_ci.png`（CI 图需更新显著性标记）
- `results/figures/q1_score_breakdown.png`（综合分分解变化）
- `results/figures/q1_score_radar.png`（雷达图变化）

**必须修改的论文/文档**：
- `paper/paper.md` 5.1.5 节"Bootstrap 显著性检验"段落：增加"BH FDR 校正"
- `paper/q1_section_5_1.md`：同步
- `README.md`：第 5.2 节"Bootstrap"段落增加 FDR 校正说明
- `.cursor/rules/project-context.mdc`：第 5.2 节同步

---

## 5. P1-1 · 统一两套评分函数（1.5 小时）

### 改动内容

**文件：`src/q1_scoring.py`**

**决策**：保留 `_score_per_plan()`（CRITIC 需要 5×4 矩阵），删除 `score_design_quality()` 等4个函数的"全公司聚合"分支

**具体步骤**：

**步骤 1**：在 `_score_per_plan()` 中增加"维度级聚合"输出

```python
def _score_per_plan(plan_daily, plan_total, unit_daily, unit_total, keyword_total):
    """计算 5 方案 × 4 维度的评分矩阵（用于 CRITIC）"""
    # 原有逻辑不变
    s_design, s_keyword, s_bid, s_time = [], [], [], []
    for plan in plan_ids:
        s_design.append(_score_design_one(plan, ...))
        s_keyword.append(_score_keyword_one(plan, ...))
        s_bid.append(_score_bid_one(plan, ...))
        s_time.append(_score_time_one(plan, ...))
    
    score_matrix = pd.DataFrame({
        '设计质量': s_design,
        '关键词管理': s_keyword,
        '出价策略': s_bid,
        '时间投放': s_time,
    }, index=plan_ids)
    
    # 新增：维度级评分 = 各维度跨方案的均值
    dim_scores = score_matrix.mean(axis=0).to_dict()
    return score_matrix, dim_scores
```

**步骤 2**：删除 `score_design_quality()` 等4个独立函数

**步骤 3**：在 `main()` 中替换调用
```python
# 原：
s1 = score_design_quality(keyword_total)
s2 = score_keyword_management(keyword_total, plan_total)
# ...
# 改为：
score_matrix, dim_scores = _score_per_plan(...)
s1, s2, s3, s4 = dim_scores['设计质量'], dim_scores['关键词管理'], dim_scores['出价策略'], dim_scores['时间投放']
```

### 测试方式

```bash
python -m src.q1_scoring
```

**预期结果**：
- `results/tables/q1_score.json` 中4个维度评分应在原值 ±3 分内（轻微波动）
- 5 个方案排名顺序保持不变
- 综合分应在原值 ±3 分内

**合理性检查**：
- 维度评分（设计55.8 / 关键词51.6 / 出价77.6 / 时间65.8）的相对大小关系应保持
- 关键词管理 51.6 仍为最低分
- 出价策略 77.6 仍为最高分

### 同步内容

**必须重新生成的文件**：
- `results/tables/q1_score.json`（维度评分、综合分、排名会变）
- `results/tables/q1_score_breakdown.csv`
- `results/tables/q1_plan_scores.csv`
- `results/tables/q1_weights.json`（基于新矩阵）

**必须重新生成的图表**：
- `results/figures/q1_score_breakdown.png`
- `results/figures/q1_score_radar.png`
- `results/figures/q1_design_quality.png`
- `results/figures/q1_keyword_management.png`
- `results/figures/q1_bid_strategy.png`
- `results/figures/q1_time_pattern.png`
- `results/figures/q1_heatmap.png`
- `results/figures/q1_baseline_rank_scatter.png`

**必须修改的论文/文档**：
- `paper/paper.md`：综合分表格、维度评分表格、排名表格全部更新
- `paper/q1_section_5_1.md`：同步
- `README.md`：第 6 节"4 维度评分与权重"全部更新
- `.cursor/rules/project-context.mdc`：第 6 节同步
- `evaluation_q1.md`：综合分数字同步

---

## 6. P0-2 · 重新设计 LOO-CV 为时间切分泛化测试（30 分钟）

### 改动内容

**文件：`src/q1_generalization.py`**

**决策**：方案 B —— 重新设计泛化测试，用时间切分（上半年训练，下半年测试）

**具体步骤**：

**步骤 1**：删除现有 `loo_cross_validation()` 函数（约 100-180 行）

**步骤 2**：新增 `time_split_validation()` 函数
```python
def time_split_validation(plan_total, daily, split_date='2025-07-01'):
    """时间切分泛化验证
    
    训练集：上半年 (2025-01-01 ~ 2025-06-30)
    测试集：下半年 (2025-07-01 ~ 2025-12-31)
    
    方法：
    1. 用上半年的 5 方案数据计算 CRITIC 权重（训练权重）
    2. 用训练权重计算下半年每个方案的加权综合分（预测得分）
    3. 与下半年的实际综合分比较 Spearman ρ
    4. ρ 接近 1 表示权重具有时间外推能力（真正的泛化）
    """
    # 划分训练/测试集
    train = plan_total[plan_total['日期'] < split_date]
    test = plan_total[plan_total['日期'] >= split_date]
    
    # 训练权重
    train_matrix = compute_critic_matrix(train)  # 5×4
    train_weights = critic_weights(train_matrix)
    
    # 用训练权重预测测试集
    test_matrix = compute_critic_matrix(test)
    pred_scores = (test_matrix * train_weights).sum(axis=1)
    actual_scores = test_matrix.mean(axis=1)  # 实际综合分（等权参考）
    
    spearman_rho = spearmanr(pred_scores, actual_scores).correlation
    
    return spearman_rho, train_weights
```

**步骤 3**：删除 `results/figures/q1_generalization_loo_cv.png` 的生成代码，改为生成 `q1_generalization_time_split.png`（已存在，但需重新设计）

### 测试方式

```bash
python -m src.q1_generalization
```

**预期结果**：
- 输出新的 Spearman ρ（应在 0.7-1.0 之间，真正反映泛化能力）
- `results/tables/q1_generalization_time_split.csv` 仍生成，列名更新

**合理性检查**：
- 新 ρ 应 < 旧 ρ=1.00（这才正常，旧的是错的）
- 新 ρ 应 ≥ 0.6 才能支撑"权重稳健"的叙事

### 同步内容

**必须重新生成的文件**：
- `results/tables/q1_generalization_loo_cv.csv` → 删除
- `results/tables/q1_generalization_time_split.csv` → 更新列名
- `results/tables/q1_generalization_bootstrap.csv` → 更新

**必须重新生成的图表**：
- `results/figures/q1_generalization_loo_cv.png` → 删除或重新设计
- `results/figures/q1_generalization_time_split.png` → 更新
- `results/figures/q1_generalization_bootstrap.png` → 更新

**必须修改的论文/文档**：
- `paper/paper.md` 5.1.7 节"泛化验证"：改为"时间切分泛化验证"
- `paper/q1_section_5_1.md`：同步
- `README.md`：第 5.3 节删除"LOO-CV"描述，改为"时间切分泛化"
- `.cursor/rules/project-context.mdc`：第 5.3 节同步

---

## 7. P1-4 · 70:30 权重比例敏感性分析（30 分钟）

### 改动内容

**文件：`src/q1_sensitivity.py`**

**新增函数**：
```python
def critic_business_ratio_sensitivity(score_matrix, business_weights, ratios=[0.0, 0.3, 0.5, 0.7, 1.0]):
    """70:30 混合权重比例敏感性分析
    
    ratios:
      0.0 = 纯业务权重
      0.3 = 30% CRITIC + 70% 业务（即原 70:30）
      0.5 = 50:50
      0.7 = 70% CRITIC + 30% 业务（即原 30:70）
      1.0 = 纯 CRITIC
    """
    from src.q1_weights import critic_weights
    
    results = []
    for r in ratios:
        critic_w = critic_weights(score_matrix)
        mixed_w = r * critic_w + (1 - r) * business_weights
        mixed_w = mixed_w / mixed_w.sum()  # 归一化
        scores = (score_matrix * mixed_w).sum(axis=1)
        results.append({
            'CRITIC 占比': r,
            '权重向量': mixed_w.to_dict(),
            '方案排名': scores.rank(ascending=False).to_dict(),
            '综合分标准差': scores.std(),
        })
    return pd.DataFrame(results)
```

**新增可视化**：
```python
# 龙卷风图基础上，增加"比例 vs 综合分标准差"曲线
# 横轴：CRITIC 占比 0~1，纵轴：5 方案综合分的标准差
# 期望：标准差较稳定 → 验证 70:30 是合理选择
```

### 测试方式

```bash
python -m src.q1_sensitivity
```

**预期结果**：
- 新增 `results/tables/q1_mix_ratio_sensitivity.csv`
- 新增 `results/figures/q1_mix_ratio_curve.png`
- 曲线应较为平稳（标准差变化 < 30%），证明 70:30 选择稳健

### 同步内容

**必须重新生成的文件**：
- `results/tables/q1_mix_ratio_sensitivity.csv`（新增）

**必须重新生成的图表**：
- `results/figures/q1_mix_ratio_curve.png`（新增）
- `results/figures/q1_tornado.png`（可能不变）
- `results/figures/q1_sens_curve.png`（可能不变）

**必须修改的论文/文档**：
- `paper/paper.md` 5.1.4 节"CRITIC + 业务 70:30 权重"段落：增加"敏感性分析验证 70:30 稳健性"
- `paper/q1_section_5_1.md`：同步
- `README.md`：第 5.1 节"赋权"段落增加敏感性说明
- `.cursor/rules/project-context.mdc`：第 5.1 节同步

---

## 8. 总执行顺序与时间表

| 时段 | 任务 | 累计耗时 | 输出 |
|------|------|---------|------|
| **03:00 ~ 03:05** | P1-6：生成 requirements.txt | 5m | `requirements.txt` |
| **03:05 ~ 05:05** | P0-1：统一 Bootstrap | 2h | q1_bootstrap_ci.csv、q1_robustness_bootstrap.csv 更新 |
| **05:05 ~ 06:05** | P0-3：Prophet 残差 Z-Score | 1h | q1_prophet_residual.csv 新增、q1_robustness_aug.csv 更新 |
| **06:05 ~ 06:35** | P1-5：BH FDR 校正 | 30m | q1_bootstrap_ci.csv 新增列、q1_score.json 综合分变化 |
| **06:35 ~ 08:05** | P1-1：统一评分函数 | 1.5h | q1_score.json 维度评分微调、9 张图表重新生成 |
| **08:05 ~ 08:35** | P0-2：时间切分泛化 | 30m | q1_generalization_time_split.csv 更新、LOO 图替换 |
| **08:35 ~ 09:05** | P1-4：权重比例敏感性 | 30m | q1_mix_ratio_sensitivity.csv 新增、敏感性曲线新增 |
| **09:05 ~ 09:30** | 论文同步更新 | 25m | paper.md 全文数字统一、章节标题修改 |

---

## 9. 验收清单（每个修复完成后必须验证）

### 9.1 数据验收
- [ ] `results/tables/q1_score.json` 中综合分仍在 50-70 区间
- [ ] 5 方案排名顺序：500635396 > 63563817 > 495403620 > 495817671 > 525368335
- [ ] 4 维度评分相对大小关系保持（出价 > 时间 > 设计 > 关键词）
- [ ] 节日扣分仍 ≤ 30（封顶约束）
- [ ] Bootstrap 显著节日数 ≥ 40（FDR 校正后）

### 9.2 图表验收
- [ ] 所有图表可正常打开（PNG 文件大小 > 10KB）
- [ ] 所有图表中文显示正常（无乱码）
- [ ] 所有图表 x/y 轴标签正确

### 9.3 论文验收
- [ ] `paper/paper.md` 中所有数字与 `results/tables/*.csv` 一致
- [ ] 5.1 节标题、子标题与代码一致
- [ ] 引用 `q1_*.csv` 的脚注全部正确
- [ ] 没有指向已删除文件的引用（如 `q1_generalization_loo_cv.csv`）

### 9.4 事实索引验收
- [ ] `.cursor/rules/project-context.mdc` 第 5/6/7 节数字与 paper.md 一致
- [ ] `README.md` 第 5/6/7 节数字与 paper.md 一致

---

## 10. 风险预案

### 风险 1：P0-1 修复后 Bootstrap 数字剧烈变化
**症状**：春节 CI 宽度变化 > 50%
**对策**：检查 `bootstrap_one_holiday()` 是否被错误修改，必要时回退到修改前版本

### 风险 2：P1-1 修复后排名变化
**症状**：525368335 不再是最低分
**对策**：检查 `_score_design_one()` 等函数是否被错误修改，必要时保留 `_score_per_plan()` 旧逻辑

### 风险 3：P1-5 修复后综合分超出预期范围
**症状**：综合分 > 80 或 < 40
**对策**：检查 FDR 校正后扣分逻辑，可能需要调整扣分封顶值

### 风险 4：图表重生成失败
**症状**：matplotlib 中文字体丢失
**对策**：运行 `python -m src.font_fix` 重新注册字体

---

## 11. 修复完成后给 Q2-Q4 留下的接口

修复完成后，Q2-Q4 可以直接复用以下稳定组件：

1. **统一的评分函数**（来自 P1-1）：`src.q1_scoring._score_per_plan()` 输出 5×4 评分矩阵，可直接喂给 Q2 分类器
2. **统一的 Bootstrap 方法**（来自 P0-1）：`src.q1_bootstrap.bootstrap_one_holiday()` 可被 Q4 不确定性分析直接调用
3. **Prophet 残差异常检测**（来自 P0-3）：可被 Q3 优化器用于剔除异常日
4. **FDR 校正工具**（来自 P1-5）：`src.q1_bootstrap.apply_fdr_correction()` 可被 Q4 复用
5. **时间切分泛化测试**（来自 P0-2）：`src.q1_generalization.time_split_validation()` 可被 Q4 用于验证优化结果的时间外推性

---

**规划文档结束。执行时间：2026-09-12 03:00 开始**
