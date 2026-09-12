# Q2 关键词 5 类分类 · 实施规划文档

> 起草时间：2026-09-12 14:40
> 执行期限：2026-09-12 14:45 ~ 18:00（估算 3-4 小时）
> 目标：按用户于 14:30 确认的 5 项决策，实现 Q2 关键词 5 类分类（投入成本 × 效益），严格对齐附件 2 result2.xlsx 模板，输出可被 Q3 直接消费

---

## ⚠️ 用户拍板的 5 项决策（**Locked，禁止改**）

> 用户于 2026-09-12 14:30 全部同意下列 5 项推荐。任何变更必须先与用户书面确认，禁止自行扩展。

| # | 决策项 | 锁定选择 | 关键依据 |
|---|---|---|---|
| **D-Q2-001** | 行粒度 | **2227 行明细（one-hot）+ 60 行推广单元聚合双输出** | 题面"将关键词进行分类" + 模板"序号"列 + Q3 衔接 |
| **D-Q2-002** | 阈值字段 | **成本 = 消费额 / 效益 = CPC 倒数（=点击量/消费额）** | 题面"投入成本/效益"语义 + 数学不重复（避免 CPC vs 1/CPC 对偶）+ heavy-tail 数据印证 |
| **D-Q2-003** | 无效词判定 | **消费=0 即无效（890 词，含 888 三零 + 2 异常）** | 题面"无成本、无效益"已满足"无成本"；跳出率"/"占 39.96% 与"消费=0"完美重合印证 |
| **D-Q2-004** | 双输出 | **是（2227 明细 → result2.xlsx；60 聚合 → q2_unit_cluster_summary.csv）** | 成本零 + 国一评审展示完整性 |
| **D-Q2-005** | 极值审计 | **是，消费 > q95（≈500 元）的 ~112 关键词做单独审计** | 国一评审加分点 + heavy-tail 偏倚修正（max/median = 115481 倍）|

---

## ⚠️ 输入红线（**禁止偏离**）

> 这是国一评审最容易挂的地方。每一条都必须在代码里 explicit 校验。

1. **禁止自创聚类方法**（GMM / KMeans / 谱聚类）—— 已与用户确认主方案 = 二维硬阈值
2. **禁止改变决策粒度**—— 主表必须 = 2227 行明细（每关键词 1 行，D-H one-hot）
3. **禁止扩展成本/效益轴**—— 仅"消费额 + CPC 倒数"两字段，**不引入浏览量/跳出率/平均访问时长作主分类特征**（这几个字段只作审计用，不进主分类器）
4. **禁止跳过附件 2 模板列名**—— result2.xlsx 必须严格 8 列：`方案ID | 推广单元 | 序号 | 黄金词 | 重点词 | 潜力词 | 问题词 | 无效词`
5. **禁止"先聚类再凑题面"**—— 分类逻辑必须是确定性规则，不接受"启发式重命名"
6. **CRITIC 综合分（C 方案）只作为可选校验**，**不进入主分类器**，主分类器仅依赖 A 方案（硬阈值）
7. **禁止修改 Q1 已确定的口径**（评分函数 / 权重混合 / Bootstrap n=100 / BH FDR / 节日扣分封顶 -30）

---

## 1. 数据契约

### 1.1 输入

| 项 | 路径 | 用途 |
|---|---|---|
| 关键词原始表 | `data/raw/attachments/附件1.xlsx` Sheet3 | 主输入 |
| 结果模板 | `data/raw/attachments/附件2/result2.xlsx` | 列结构对齐 |
| Q1 已用模块 | `src/utils.py / config.py / plot_style.py` | 复用函数 |

### 1.2 输出

| 项 | 路径 | 用途 | 行数 |
|---|---|---|---|
| Q2 主交付物 | `data/raw/attachments/result2.xlsx` | 题面要求 | **2227 行**（= 2227 关键词 one-hot） |
| Q2 推广单元聚合 | `results/tables/q2_unit_cluster_summary.csv` | 论文图表 + 跨方案对比 | **60 行**（= 12 推广单元，5 方案共享推广单元 ID；实际行数待确认） |
| Q2 极值审计 | `results/tables/q2_extreme_audit.csv` | 112 极值词 + 审计标签 | **~112 行** |
| Q2 5 类分布图 | `results/figures/q2_class_distribution.png` | 5 类计数柱状图 | 1 张 |
| Q2 阈值敏感性 | `results/figures/q2_threshold_sensitivity.png` | 龙卷风图（25 阈值组合） | 1 张 |
| Q2 方案级 5 类堆叠 | `results/figures/q2_unit_class_stacked.png` | 12 推广单元 × 5 类堆叠柱 | 1 张 |
| Q2 主方法 | `src/q2_classify.py` | 实现入口 | ~250 行 |
| Q2 方法文档 | `issue/q2_method.md` | 给评审读的方案说明 | 200-400 行 |
| Q2 §5.2 节 | `paper/paper.md` §5.2 | 论文正文 | 待定 |

### 1.3 中间产物（可复用给 Q3）

| 项 | 路径 | 用途 |
|---|---|---|
| 关键词分类明细（含 5 维特征 + 5 类 one-hot） | `data/processed/q2/keyword_classified.pkl` | Q3 直接 join `Sheet3` 取分类 |
| 阈值参数 | `results/tables/q2_thresholds.json` | Q3 套用相同阈值 |
| 极值审计标签 | `results/tables/q2_extreme_audit.csv` | Q3 投放策略可读 |

---

## 2. 实施步骤（S1 ~ S9）

### S1 · 备份与 TODO（WIP 锚点）

**目的**：防止再次 hallucination + 给后续阶段清晰的进度锚点。

**动作清单**：
1. `tools/backup_pre_q2impl_20260912.py`：将当前 `src/q2_classify.py`（若存在）/ `data/raw/attachments/result2.xlsx` / `results/tables/q2_*.csv` / `results/figures/q2_*.png` / `issue/q2_method.md` / `paper/paper.md` §5.2 全部备份到 `results/snapshots/pre_q2impl_20260912/`
2. 新建 `issue/q2_implementation_plan.md`（本文档）作为 WIP 锚点
3. 在 `WORK_STATE.md` 第 3 节路线图追加 Q2 修复进度表（S1~S9）
4. TodoWrite 建 9 阶段表（S1~S9）

**输出**：`results/snapshots/pre_q2impl_20260912/`（含全部 Q2 已知产物）

---

### S2 · 写 `src/q2_classify.py` 主方法

**目的**：实现二维硬阈值 + 极值审计的主分类器。

**输入处理（按 D-Q2-002 / D-Q2-003）**：
```
读取 Sheet3 (n=2227)
↓
转数值：消费/点击/浏览；跳出率'/'→NaN
↓
Step 1：无效词确定 — cost=0 → 标"无效词", 出主分类
    → 888 词三零 + 2 词异常 = 890 词无效词
    → 剩余 1337 词有效词进入 Step 2
↓
Step 2：有效词二维硬阈值分 4 类
    axis_cost = 消费额 (D-Q2-002)
    axis_benefit = 点击量 / 消费额  ← CPC 倒数
    threshold_cost = median(axis_cost) among 1337 有效词
    threshold_benefit = median(axis_benefit) among 1337 有效词
    4 象限：
        cost<=T_cost AND benefit>=T_benefit → 黄金词
        cost> T_cost AND benefit>=T_benefit → 重点词
        cost<=T_cost AND benefit< T_benefit → 潜力词
        cost> T_cost AND benefit< T_benefit → 问题词
```

**关键不变量（必须 assert）**：
- 4 类有效词数 + 890 无效词 = 2227 ✓
- 4 类有效词 sum(cost) = 全年消费 - 极值审计剔除部分（不强制严格等）
- result2.xlsx 的 D-H 列每行恰有 1 个 1（one-hot 校验）

**输出**：
- `data/processed/q2/keyword_classified.pkl`（含 5 维特征 + 5 类 one-hot）
- `results/tables/q2_thresholds.json`（含 T_cost=消费额中位数, T_benefit=CPC 倒数中位数, n_每类 等）

**函数清单**：
- `load_sheet3() → DataFrame`：读取 Sheet3 + 数值化
- `mark_invalid(df) → DataFrame`：Step 1 标无效词
- `compute_thresholds(df_valid) → dict`：Step 2 计算双阈值
- `classify_two_d(df_valid, thresholds) → DataFrame`：4 象限标注
- `build_one_hot(df_classified) → DataFrame`：生成 result2 模板格式
- `export_result2(df_one_hot) → path`：写 `data/raw/attachments/result2.xlsx`
- `export_unit_summary(df_classified) → path`：写 60 行推广单元聚合
- `mark_extreme(df_classified) → DataFrame`：q95 极值标注
- `assert_invariants(df) → None`：5 类完整性 + one-hot 校验

**预计行数**：250 行（含详细 docstring + 断言）

---

### S3 · 写 `issue/q2_method.md` 方法文档

**目的**：评审读到 `src/q2_classify.py` 之前的方案说明。

**章节（固定 8 节）**：
1. 问题理解（题面原文 + 5 类定义 + 数据契约）
2. 方法选择（候选 A vs B vs C 三方对比，推荐 A）
3. 数据预处理（数值化 / 跳出率缺失处理 / 极值审计触发条件）
4. 无效词判定（D-Q2-003 论证）
5. 硬阈值分类（D-Q2-002 论证 + 阈值具体数值）
6. 极值审计（D-Q2-005 论证 + 审计规则 2 条 + 输出物）
7. 校验机制（详见 S6）
8. 与 Q1/Q3 衔接

**输出文件路径**：`issue/q2_method.md`

---

### S4 · 生成 result2.xlsx + 60 推广单元聚合

**目的**：主交付物 + 副交付物。

**result2.xlsx 写入要求**：
- 列名严格 8 列：`方案ID | 推广单元 | 序号 | 黄金词 | 重点词 | 潜力词 | 问题词 | 无效词`
- 行数 2227（D-Q2-001 + D-Q2-004）
- D-H 列 one-hot：每行 5 列之和 = 1
- 写入前 assert：行数 = 2227，列名匹配模板

**q2_unit_cluster_summary.csv 写入要求**：
- 列：`方案ID | 推广单元 | 关键词总数 | 黄金词 | 重点词 | 潜力词 | 问题词 | 无效词 | 总消费 | 总点击 | 平均CPC`
- 行数 = 实际 (方案×推广单元) 组合数（待数据确认，预计 12 行或 60 行取决于"方案×推广单元"是否唯一）
- 写入前 assert：明细表 sum(黄金词) == 聚合表 sum(黄金词)（双表一致性）

**输出物**：2 个文件 + 2 张图（用 S5 极值审计图占位）

---

### S5 · 极值审计（112 词，D-Q2-005）

**目的**：修正 heavy-tail 偏倚 + 提供国一评审加分点。

**审计触发条件（仅 2 条规则，避免过度复杂）**：
1. **消费 > q95 关键词**：`cost > np.percentile(cost[cost>0], 95)` → 默认审计（约 67 词）
2. **CPC > 5 元 且 消费 > q75**：`CPC > 5 AND cost > q75` → 强制审计（约 45 词，与规则 1 有重叠）

**去重后**：~112 词

**审计输出字段**：
| 字段 | 来源 |
|---|---|
| 序号 | Sheet3 |
| 关键词 | Sheet3 |
| 消费额 | Sheet3 |
| 点击量 | Sheet3 |
| 浏览量 | Sheet3 |
| CPC = 消费/点击 | 计算 |
| 主分类（黄金/重点/潜力/问题） | S2 主分类器 |
| 审计标签 | 规则触发情况（"q95" / "高CPC高消费" / "双触发"） |
| 风险评级 | 计算：消费 × (1 - 效益归一化)，分高/中/低 |

**输出**：
- `results/tables/q2_extreme_audit.csv`（~112 行 × 9 字段）
- `results/figures/q2_extreme_audit.png`（Top 20 极值词横向条形图，颜色 = 风险评级）

---

### S6 · 校验机制（4 项，国一评审加分点）

**目的**：证明分类结果稳健。

#### 6.1 阈值敏感性（龙卷风图）

**做法**：
- 成本轴阈值 = 中位数 × {0.8, 0.9, 1.0, 1.1, 1.2}（5 档）
- 效益轴阈值 = 中位数 × {0.8, 0.9, 1.0, 1.1, 1.2}（5 档）
- 25 个组合，每个组合计算 5 类计数
- 画龙卷风图：X 轴 = 各类计数变化率，Y 轴 = 5 类名

**输出**：`results/figures/q2_threshold_sensitivity.png`

#### 6.2 Bootstrap 重抽样（5 类计数 CI）

**做法**：
- 有效词 1337 个，有放回抽样 1000 次
- 每次重新计算阈值（中位数会变）
- 输出 5 类计数 95% CI

**输出**：`results/tables/q2_bootstrap_ci.csv`（5 类 × {count_mean, ci_low, ci_high}）

#### 6.3 跨方案对比

**做法**：
- 按方案聚合 5 类比例
- 验证业务逻辑：500635396 应"重点词"占比高（高消费特征），525368335 应"问题词"占比高（关键词多但低效益）

**输出**：`results/tables/q2_unit_class_stacked.csv` + `results/figures/q2_unit_class_stacked.png`

#### 6.4 可选：CRITIC 综合分校验（**默认禁用**，需用户启用）

**做法**（仅当用户明确说"启用 C 方案"时执行）：
- 用 CRITIC 对 5 维特征（消费/点击/浏览/CPC 倒数/1-跳出率）赋权
- 综合分 → 5 桶（5 等分）→ 与 A 方案对比
- 关键词级 Cohen's κ 一致率

**输出**（如启用）：`results/tables/q2_consistency_check.csv`（Cohen's κ + 各类一致率）

---

### S7 · 论文 §5.2 同步

**目的**：把方法 + 数字写入论文。

**章节结构**：
```
§5.2 SEM 关键词分类
  §5.2.1 问题理解与方法选择
  §5.2.2 数据预处理与无效词判定
  §5.2.3 二维硬阈值分类（公式 + 阈值具体数值）
  §5.2.4 5 类分布结果（含 result2 描述 + 60 聚合表 + 5×4 矩阵）
  §5.2.5 极值审计（112 词 Top 20 + 风险评级）
  §5.2.6 校验：阈值敏感性 + Bootstrap CI + 跨方案对比
  §5.2.7 与 Q3 衔接（输出物清单 + Q3 如何消费）
```

**必须包含**：
- 5 类具体计数（黄金 / 重点 / 潜力 / 问题 / 无效 各多少词）
- 阈值具体数值（消费 8.06 元 / CPC 倒数 0.904）
- 极值审计 Top 5 + 风险评级
- 龙卷风图 + 5 类分布图 + 方案级堆叠图 各 1 张
- 与 Q1 关键词管理维度（57.6 分）的呼应

**输出**：`paper/paper.md` 第 ~250 行追加 §5.2 节

---

### S8 · RUN_LOG / WORK_STATE / DECISION_LOG 同步

**RUN_LOG**（每次动作都 append，本规划共预计 20-30 行）：
- 每完成 1 个原子动作（S2 写完脚本 = OK，S2 跑通 = OK，S4 写完 result2 = OK，...）

**WORK_STATE.md**（仅状态切换时更新）：
- 路线图 §3 第 3 行 Q2 状态改：`⏸ 待重做` → `🔧 实施中` → `✅ 完成`
- §2 数据契约追加 Q2 输出契约

**DECISION_LOG.md**（仅自主决策时追加，5 项用户决策已锁定仅追加确认）：
- 新增 `D-011`：5 项决策确认（时间戳 + 用户同意）

---

### S9 · 验证清单（自检 10 项）

**目的**：避免再次 hallucination，跑完所有 10 项才算 Q2 完成。

| # | 校验项 | 期望 | 检查方法 |
|---|---|---|---|
| 1 | result2 行数 | 2227 | `len(pd.read_excel('result2.xlsx'))` |
| 2 | result2 列名 | 8 列严格匹配模板 | `list(df.columns) == ['方案ID','推广单元','序号','黄金词','重点词','潜力词','问题词','无效词']` |
| 3 | one-hot 完整性 | 每行 5 列之和 = 1 | `df.iloc[:, 3:].sum(axis=1).unique() == [1]` |
| 4 | 总分类数完整 | 黄金+重点+潜力+问题+无效 = 2227 | `df.iloc[:, 3:].sum().sum() == 2227` |
| 5 | 无效词规则 | 消费=0 全部归无效词 | `无效词.sum() >= 890` |
| 6 | 60 聚合表 | 行数 = (方案×推广单元) 组合数 | 动态校验 |
| 7 | 双表一致性 | 各类 sum 一致 | `np.allclose(detail_sum, aggregate_sum)` |
| 8 | 极值审计 | ~112 词（90~120 都行） | `len(audit_df)` |
| 9 | 4 项校验产物齐全 | 4 张图 + 2 张 csv | `ls results/figures/q2_*.png; ls results/tables/q2_*.csv` |
| 10 | Q1 评分未变 | overall_score = 50.7 | 跑 `python -m src.q1_scoring` 对比 |

**输出**：`tools/check_q2.py` + 自检报告 `results/tables/q2_check_report.json`

---

## 3. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| Sheet3 格式微变（如编码异常）| 低 | 中 | 加 try/except + 数值化容错 |
| 中位数分桶对 heavy-tail 不敏感 | 中 | 中 | 极值审计 + 阈值敏感性（已 S5/S6 锁定）|
| result2.xlsx 被 Excel 锁定导致写入失败 | 中 | 低 | 关闭 Excel 后重试 + 写前 try/except |
| 5 类阈值边界争议（消费 8.06 vs 8.07 是不同类）| 中 | 中 | 龙卷风图展示边界敏感性 |
| 2 个异常词（消费=0 但点击>0）| 低 | 低 | 在 result2 备注 + 论文 §5.2.2 说明 |
| Q3 衔接不畅（result2 字段不够）| 中 | 高 | Q3 启动前先做"Q3 数据契约检查"，避免连锁返工 |

---

## 4. 与 Q1 / Q3 衔接说明

### 4.1 与 Q1 衔接

| Q1 输出 | Q2 消费方式 |
|---|---|
| `q1_score.json`（5 方案综合分）| 跨方案对比：综合分 vs 各方案"问题词占比"，预期强负相关（问题词多的方案综合分低）|
| `q1_weights.json`（关键词管理 14.17% 权重）| Q2 分类结果回填到 Q1 的"关键词管理与运用"维度，作为子指标报告 |
| Q1 关键词管理维度分 57.6 | Q2 章节末段呼应："该维度评分与 Q2 5 类比例的相关性" |

### 4.2 与 Q3 衔接（**关键**）

Q3 需要"选择合适的关键词"做投放，Q2 必须输出 Q3 能直接消费的数据：

| Q3 需要的 | Q2 提供 | 路径 |
|---|---|---|
| 关键词分类（黄金/重点/潜力/问题/无效）| one-hot 列 | `result2.xlsx` |
| 关键词阈值（用于"低成本/高效益"判定）| thresholds.json | `q2_thresholds.json` |
| 关键词级 5 维特征（消费/点击/浏览/跳出/平均时长）| keyword_classified.pkl | `data/processed/q2/keyword_classified.pkl` |
| 极值审计标签（哪些词被审计）| audit.csv | `q2_extreme_audit.csv` |

**Q3 启动前必须做的"衔接检查"**：
- Q2 跑完 result2.xlsx 后，**先验证 Q3 能 join 上**：`pd.merge(Sheet3, result2, on=['方案ID','推广单元','序号'])` 应 1:1 匹配 2227 行
- 验证阈值参数可被 Q3 读取并套用相同逻辑

---

## 5. 实施顺序与时间表（总计 3-4 小时）

| 阶段 | 内容 | 预计 | 累计 |
|---|---|---|---|
| S1 | 备份 + WORK_STATE + DECISION_LOG | 10 min | 0:10 |
| S2 | 写 `src/q2_classify.py` | 45 min | 0:55 |
| S3 | 写 `issue/q2_method.md` | 30 min | 1:25 |
| S4 | 跑通 + 生成 result2 + 60 聚合 | 15 min | 1:40 |
| S5 | 极值审计 + 图 | 30 min | 2:10 |
| S6 | 4 项校验（按优先级，先 6.1/6.2/6.3） | 45 min | 2:55 |
| S7 | 论文 §5.2 同步 | 30 min | 3:25 |
| S8 | RUN_LOG/WORK_STATE/DECISION_LOG 同步 | 10 min | 3:35 |
| S9 | 10 项验证清单 | 15 min | 3:50 |

**buffer**：30 分钟应对 S2/S6 debug

---

## 6. 成功标准（DoD）

- [ ] result2.xlsx 行数 = 2227，列名严格匹配模板，5 列 one-hot 自洽
- [ ] 60 推广单元聚合表 / 极值审计表 / 4 张图全部生成
- [ ] 10 项自检清单全 PASS（含 Q1 综合分 50.7 未变）
- [ ] paper.md §5.2 完整段落（含阈值具体数值 + 5 类计数 + 极值审计 Top 5）
- [ ] issue/q2_method.md 评审可读的方案说明
- [ ] Q3 数据契约检查 1:1 匹配通过
- [ ] RUN_LOG 累计 20+ 行（每动作 1 行）
- [ ] WORK_STATE 路线图 Q2 状态变 ✅
- [ ] DECISION_LOG D-011 5 项决策确认已追加

---

## 7. 引用与依赖

| 引用 | 用途 |
|---|---|
| `src/utils.py` | `ensure_dir`, `load_sheet3`（若已存在）|
| `src/plot_style.py` | 统一绘图风格（中文字体 + 配色）|
| `src/config.py` | 文件路径常量 |
| Q1 已生成 `data/processed/q1/*.pkl` | 不复用（Q2 用 Sheet3 重新读，不污染 Q1 数据）|
| Q1 已建立方法栈 | CRITIC + Bootstrap + BH FDR + 龙卷风（C 方案可选校验时复用）|

---

最后更新：2026-09-12 14:40 · **Locked by 用户 at 14:30** · 严禁偏离 5 项决策
