# 仓库索引

2026 年全国大学生数学建模竞赛 E 题项目仓库结构索引。详细问题建模过程见 `paper/`。

---

## 顶层目录

| 目录 | 用途 | 进入方式 |
|------|------|----------|
| `data/` | 原始数据和处理后数据 | — |
| `src/` | 所有源代码（按问题分文件） | 见下 |
| `paper/` | 论文写作（Markdown + docx 终稿） | — |
| `results/` | 分析产出（图表 + 表格） | — |
| `issue/` | 问题分析、建模假设、待解决问题清单 | — |
| `notebooks/` | EDA 探索性脚本 | — |

## `data/`

```
data/
├── raw/
│   └── attachments/           ← 附件原始数据（唯一来源）
│       ├── 附件1.xlsx
│       └── 附件2/
│           ├── result2.xlsx
│           ├── result3.xlsx
│           └── result4.xlsx
└── processed/
    ├── campaign_main.pkl        ┐
    ├── keyword_main.pkl         ├ 加载清洗后上游缓存（已 .gitignore）
    ├── registration_main.pkl    ┘  src/data_loader.py::load_processed('main') 会读
    └── q1/                      ← Q1 专用聚合数据
        ├── daily_full.pkl
        ├── daily_full_no_aug.pkl
        ├── campaign_daily.pkl
        ├── unit_daily.pkl / unit_total.pkl
        ├── plan_daily.pkl / plan_total.pkl / plan_daily_no_reg.pkl
        └── keyword_total.pkl
```

## `src/`

### 正式代码（24 个 Q1/Q2/Q3/Q4 模块 + 5 个公共 + 1 个 build_paper）

| 文件 | 作用 |
|------|------|
| `q1_main.py` | Q1 主流程入口 |
| `q1_data_prep.py` | 数据预处理：从原始附件生成 Q1 聚合数据 |
| `q1_weights.py` | CRITIC + 业务 70:30 混合权重 |
| `q1_scoring.py` | 方案打分核心（_score_per_plan 5×4 矩阵 + 行业阈值细节） |
| `q1_baseline.py` | 4 种基线方法对比（等权 / 熵权 / TOPSIS / CRITIC）|
| `q1_bootstrap.py` | Bootstrap 显著性（全量 37 节日 × 100 次 + BH FDR） |
| `q1_generalization.py` | 时序切分 + Bootstrap 泛化验证（已删除 LOO-CV，P0-2） |
| `q1_prophet.py` | Prophet 反事实假日分析 |
| `q1_holiday_penalty.py` | 节日聚合显著性扣分（-30 封顶，原始 -31） |
| `q1_sensitivity.py` | 龙卷风 + 敏感性曲线 + CRITIC/业务 比例敏感性 |
| `q1_robustness_aug.py` | 异常日（2025-08-21）鲁棒性 |
| `q1_bounce_cluster.py` | 跳出率 KMeans 聚类（含 TSNE 可视化） |
| `q1_heatmap.py` | 5×4 方案-维度热力图 |
| `q1_penalty_compare.py` | 扣分前 vs 扣分后综合分对比图（集成在 q1_plots） |
| `q1_plots.py` | 主图集合（除 Prophet 外所有图） |
| `q1_analysis.py` | 综合分析模块（设计/关键词/出价/时间/假日） |
| `q1_write.py` | Q1 论文文字稿生成 |
| `q1_collect_summary.py` | 收集汇总指标到 `q1_summary.json` |
| `q1_evaluation_scenarios.py` | 场景化评估 |
| `q1_diagnose_zero_score.py` | 0 分方案诊断 |
| `q2_classify.py` | Q2 关键词 5 类分类（GMM + BIC K=8） |
| `q3_optimizer.py` | Q3 投放策略优化（MILP + NSGA-II Pareto） |
| `q4_uncertainty.py` | Q4 不确定性优化（SAA + DRO + 后悔分析） |
| `regen_figures.py` | 全图重生成辅助脚本 |
| `config.py` | 全局配置（路径、常量、节假日表） |
| `utils.py` | 工具函数（路径、字体） |
| `data_loader.py` | 原始附件加载 + 上游清洗 |
| `plot_style.py` | 统一绘图风格 |
| `font_fix.py` | 中文字体注册 |
| `build_paper.py` | 从 Markdown 生成 docx |
| `__init__.py` | 包标记 |

### `_archive/`（一次性 / 调试脚本）

不再维护，仅历史归档：

- `00_read_attachments.py` — 初次读取附件的探查脚本
- `boot.py` — 早期 bootstrapping 测试
- `font_diag.py` / `font_fix.py` / `test_cn.py` — 中文字体调试
- `check_daily.py` / `debug_dfc.py` — 数据诊断
- `pdf_to_images.py` — PDF → PNG 抽取（已用，结果在 `paper/figures/raw_attachments/`）
- `read_e_pdf.py` / `read_e_v2.py` — PDF 文本提取（一次性）
- `read_templates.py` / `read_templates_v2.py` — Word 模板解析
- `main.py` / `show_score.py` — 早期入口（已被 `q1_main.py` 取代）
- `q2_classify.py` / `q3_optimizer.py` / `q4_uncertainty.py` — 占位脚本

## `paper/`

| 文件 | 说明 |
|------|------|
| `paper.md` | 完整论文 Markdown 草稿 |
| `q1_section_5_1.md` | 第 5.1 节（Q1 详细建模）单独维护版本 |
| `SEM投放策略优化_终稿.docx` | 最终 docx 稿件（用 `build_paper.py` 生成） |
| `figures/raw_attachments/problem_pages/` | 题目原文 PNG（`page_1.png`, `page_2.png`） |

## `results/`

### `figures/` — 分析图表（21 张 Q1 + 4 张 Q2/Q3/Q4）
```
q1_heatmap.png              5×4 方案-维度热力图 + 综合分横条
q1_prophet_reg.png          Prophet 注册量预测（反事实）
q1_prophet_cost.png         Prophet 消费额预测（反事实）
q1_bid_strategy.png         出价策略示意
q1_holiday_boxplot.png      节假日 vs 工作日注册量分布
q1_penalty_compare.png      扣分前 vs 扣分后综合分对比
q1_bounce_clusters.png      跳出率 KMeans 聚类（中心散点）
q1_bounce_tsne.png          跳出率聚类 TSNE 降维可视化
q1_time_pattern.png         时序模式（月度/周度/日度）
q1_baseline_rank_scatter.png 基线 4 方法排名一致性散点（含 Pearson/Spearman）
q1_score_breakdown.png      评分拆解（4 维度）
q1_score_radar.png          5 方案评分雷达图
q1_keyword_management.png   关键词管理（有效率/跳出率/CPC/集中度）
q1_design_quality.png       设计质量评估（单元上方位占比）
q1_robustness_aug.png       数据增强鲁棒性（异常日剔除前后）
q1_bootstrap_ci.png         Bootstrap 置信区间（37 节日）
q1_generalization_time_split.png   时序切分（训练上半年 / 测试下半年）
q1_generalization_bootstrap.png    泛化 Bootstrap 重采样
q1_sensitivity_curves.png   敏感性曲线
q1_tornado.png              龙卷风图（权重 ±20% 扰动）
q1_mix_ratio_curve.png      CRITIC:业务 比例敏感性曲线
q2_gmm_clusters.png         Q2 GMM 8 类聚类散点（合并 5 业务类）
q3_strategy.png             Q3 每日预算分配与预期注册量
q3_pareto.png               Q3 NSGA-II Pareto 前沿
q4_strategy_comparison.png  Q4 4 策略对比 + Monte Carlo 注册量分布
```

### `tables/` — 表格与中间产物
```
# Q1 输出（20+ csv/json）
q1_weights.{csv,json}                权重结果（CRITIC + 业务 70:30 混合）
q1_score.json                        综合评分 + 4 维度评分 + 5 方案综合分（含扣分）
q1_score_breakdown.csv               评分拆解明细（含 P1-1 口径 details）
q1_plan_scores.csv                   5 方案 × 4 维度评分矩阵（_score_per_plan）
q1_baseline_corr.csv                 4 方法相关系数（Pearson + Spearman）
q1_baseline_comparison_pre_holiday.csv 扣分前 baseline 对比
q1_bootstrap_ci.csv                  全量 37 节日 Bootstrap CI + BH FDR
q1_bootstrap_ci_6holidays.csv        6 代表节日 Bootstrap 子集
q1_generalization_time_split.csv     泛化验证（时序切分）
q1_generalization_bootstrap.csv      泛化验证（Bootstrap 重采样）
q1_robustness_aug.csv                异常日 Prophet 鲁棒性
q1_robustness_bootstrap.csv          异常日 Bootstrap CI 宽度对比
q1_robustness_score.csv              异常日评分鲁棒性
q1_sensitivity.csv / _summary.csv    权重敏感性扫描
q1_mix_ratio_sensitivity.csv         CRITIC:业务 比例敏感性
q1_holiday_contribution.csv          节假日贡献量化
q1_holiday_penalty.json              节假日惩罚（-30 封顶，原始 -31）
q1_bounce_clusters.csv / _summary.csv 跳出率聚类
q1_prophet_residual.csv              Prophet 残差（异常日定位用）
q1_zero_score_diagnosis.csv          0 分方案诊断
q1_summary.json                      综合指标汇总

# Q2 输出
q2_keyword_classification.csv         2227 关键词 5 类分类（GMM + BIC K=8）
q2_cluster_summary.csv                8 聚类 → 5 业务类映射

# Q3 输出
q3_daily_strategy.csv                 5 方案 × 365 天最优预算分配
q3_pareto_front.csv                   60 个 Pareto 非支配解
q3_plan_summary.csv                   5 方案最优汇总

# Q4 输出
q4_daily_strategy.csv                 2026-09-11~17 每日最优策略
q4_strategy_comparison.csv            4 策略 × 期望/标准差/worst-case/regret
```

## `issue/`

| 文件 | 用途 |
|------|------|
| `issue_q1.md` | Q1 问题理解、模型假设、约束条件 |
| `issue_q1_methods.md` | Q1 方法选择对比（4 方向） |
| `q1_fix_plan.md` | Q1 修复规划文档（P0-0 ~ P1-6，含节假日表修正、评分统一等） |
| `q1_code_review_report.md` | Q1 评审报告 + P0/P1 问题清单 |
| `q1_p02_p11_remediation.md` | P0-2 + P1-1 完整修复执行手册（S1-S7 七阶段） |

## 入口推荐

- **复现 Q1 全流程**：`python src/q1_main.py`（依赖 `data/processed/q1/*.pkl` 已存在；如不存在先跑 `q1_data_prep.py`）
- **查看最终论文**：打开 `paper/SEM投放策略优化_终稿.docx`
- **了解模型假设**：先看 `issue/issue_q1.md`

## 忽略规则

见 `.gitignore`：
- `__pycache__/`、`*.pyc`
- `data/processed/{campaign,keyword,registration}_main.pkl`（上游缓存，每次重建）
