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
| `logs/` | 运行日志、PDF 抽取文本等中间产物 | — |

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

### 正式代码（15 个 Q1 模块 + 5 个公共）

| 文件 | 作用 |
|------|------|
| `q1_main.py` | Q1 主流程入口 |
| `q1_data_prep.py` | 数据预处理：从原始附件生成 Q1 聚合数据 |
| `q1_analysis.py` | 综合分析模块（设计/关键词/出价/时间/假日） |
| `q1_collect_summary.py` | 收集汇总指标到 `q1_summary.json` |
| `q1_plots.py` | 除 Prophet 外所有图表绘制 |
| `q1_write.py` | Q1 论文文字稿生成 |
| `q1_weights.py` | 权重优化（熵权法/层次分析） |
| `q1_scoring.py` | 方案打分核心逻辑 |
| `q1_baseline.py` | 5 种基线方法对比 |
| `q1_bootstrap.py` | Bootstrap 置信区间 |
| `q1_evaluation_scenarios.py` | 场景化评估 |
| `q1_generalization.py` | 留一 / 时序切分泛化验证 |
| `q1_robustness_aug.py` | 数据增强鲁棒性 |
| `q1_sensitivity.py` | 参数敏感性 |
| `q1_holiday_penalty.py` | 节假日惩罚项 |
| `q1_prophet.py` | Prophet 趋势预测 |
| `q1_heatmap.py` | 相关性热力图 |
| `q1_bounce_cluster.py` | 跳出率聚类分析 |
| `q1_diagnose_zero_score.py` | 0 分方案诊断 |
| `config.py` | 全局配置（路径、常量） |
| `utils.py` | 工具函数（路径、字体） |
| `data_loader.py` | 原始附件加载 + 上游清洗 |
| `plot_style.py` | 统一绘图风格 |
| `build_paper.py` | 从 Markdown 生成 docx |
| `__init__.py` | 包标记 |

### `_archive/`（一次性 / 调试脚本）

不再维护，仅历史归档：

- `00_read_attachments.py` — 初次读取附件的探查脚本
- `boot.py` — 早期 bootstrapping 测试
- `font_diag.py` / `font_fix.py` / `test_cn.py` — 中文字体调试
- `check_daily.py` / `debug_dfc.py` — 数据诊断
- `pdf_to_images.py` — PDF → PNG 抽取（已用，结果在 `paper/figures/raw_attachments/`）
- `read_e_pdf.py` / `read_e_v2.py` — PDF 文本提取（已用，结果在 `logs/`）
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

### `figures/` — 分析图表（约 22 张 PNG）
```
q1_heatmap.png              相关性热力图
q1_prophet_reg.png          Prophet 注册量预测
q1_prophet_cost.png         Prophet 消费额预测
q1_bid_strategy.png         出价策略示意
q1_holiday_boxplot.png      节假日分布
q1_penalty_compare.png      惩罚项对比
q1_bounce_clusters.png      跳出率聚类
q1_time_pattern.png         时序模式
q1_baseline_rank_scatter.png 基线排名散点
q1_score_breakdown.png      评分拆解
q1_score_radar.png          评分雷达图
q1_keyword_management.png   关键词管理
q1_design_quality.png       设计质量评估
q1_robustness_aug.png       数据增强鲁棒性
q1_bootstrap_ci.png         Bootstrap 置信区间
q1_generalization_time_split.png   时序切分
q1_generalization_loo_cv.png       留一交叉验证
q1_generalization_bootstrap.png    泛化 bootstrap
q1_sensitivity_curves.png   敏感性曲线
q1_tornado.png              龙卷风图
q1_eval_fuzzy_heatmap.png   模糊评估热力图
q1_eval_entropy_weights_compare.png  熵权对比
```

### `tables/` — 表格与中间产物
```
q1_weights.{csv,json}                权重结果
q1_score.{json,csv}                  方案得分
q1_score_breakdown.csv               评分拆解明细
q1_plan_scores.csv                   各方案得分
q1_baseline_comparison.csv           基线方法对比
q1_baseline_corr.csv                 基线相关系数
q1_bootstrap_ci.csv                  Bootstrap CI
q1_generalization_{loo_cv,time_split,bootstrap}.csv  泛化验证
q1_robustness_{aug,bootstrap,score}.csv              鲁棒性
q1_sensitivity.csv / _summary.csv    敏感性分析
q1_holiday_contribution.csv          节假日贡献
q1_holiday_penalty.json              节假日惩罚
q1_bounce_clusters.csv / _summary.csv 跳出率聚类
q1_bounce_interpretation.md          跳出率解读
q1_eval_entropy_{ranking,weights}.csv 熵权评估
q1_eval_fuzzy_scores.csv             模糊评分
q1_eval_score_compare.csv            评分方法对比
q1_zero_score_diagnosis.csv          0 分方案诊断
q1_summary.json                      综合指标汇总
```

## `issue/`

| 文件 | 用途 |
|------|------|
| `issue_q1.md` | Q1 问题理解、模型假设、约束条件 |
| `issue_q1_methods.md` | Q1 方法选择对比 |

## `logs/`

运行历史日志与 PDF 抽取文本。

## 入口推荐

- **复现 Q1 全流程**：`python src/q1_main.py`（依赖 `data/processed/q1/*.pkl` 已存在；如不存在先跑 `q1_data_prep.py`）
- **查看最终论文**：打开 `paper/SEM投放策略优化_终稿.docx`
- **了解模型假设**：先看 `issue/issue_q1.md`

## 忽略规则

见 `.gitignore`：
- `__pycache__/`、`*.pyc`
- `logs/*.log`
- `data/processed/{campaign,keyword,registration}_main.pkl`（上游缓存，每次重建）
