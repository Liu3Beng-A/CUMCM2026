"""项目说明文档 - E题：SEM广告投放策略

## 项目结构

```
D:\CUMCM2026Problems\
├── 附件/                      原始附件（用户上传，不要改动）
│   ├── 附件1.xlsx             2025年SEM投放数据
│   └── 附件2/                 结果模板
│       ├── result2.xlsx       问题2的输出模板
│       ├── result3.xlsx       问题3的输出模板
│       └── result4.xlsx       问题4的输出模板
│
├── data/
│   ├── raw/
│   │   └── 附件_原始备份/      原始附件的副本
│   └── processed/              清洗后的数据（parquet格式）
│
├── src/                       核心代码模块
│   ├── __init__.py
│   ├── utils.py               路径、中文字体、绘图风格
│   ├── config.py              业务常量配置
│   ├── data_loader.py         数据加载与基础指标
│   ├── q1_analysis.py         问题1：合理性分析 + 规律 + 假日效应
│   ├── q2_classify.py         问题2：关键词五分类
│   ├── q3_optimizer.py        问题3：投放优化模型
│   ├── q4_uncertainty.py       问题4：不确定性优化
│   └── plot_style.py          统一绘图风格
│
├── notebooks/                  探索性分析（Jupyter / .py 脚本）
│   ├── 01_eda_summary.py       EDA总结
│   ├── 02_q1_analysis.ipynb
│   └── ...
│
├── results/                   输出结果
│   ├── figures/               图表PNG
│   ├── tables/                中间表格CSV
│   └── excel/                 最终题目要求的xlsx
│       ├── result2.xlsx
│       ├── result3.xlsx
│       └── result4.xlsx
│
├── paper/                     论文相关
│   ├── figures/               论文插图（高分辨率）
│   └── paper.md               论文草稿（Markdown）
│
├── main.py                    一键运行入口
├── setup_dirs.py              目录初始化脚本
└── README.md                  本文件
```

## 工作流程

1. **初始化**：运行 `python setup_dirs.py`
2. **加载数据**：`from src.data_loader import load_raw_data`
3. **问题1**：`python -m src.q1_analysis`
4. **问题2**：`python -m src.q2_classify`
5. **问题3**：`python -m src.q3_optimizer`
6. **问题4**：`python -m src.q4_uncertainty`

## 数据说明

### 附件1
- **Sheet1**：投放方案与消费记录（2627条 / 全年）
- **Sheet2**：每天新注册用户数（365条）
- **Sheet3**：关键词统计数据（2227个关键词）

### 关键指标
- CPC（Cost Per Click）= 消费额 / 点击量
- CTR（Click-Through Rate）= 点击量 / 展现量
- 上方位占比 = 上方位展现量 / 展现量
- 注册转化率 = 新注册数 / 点击量（按天聚合估算）

## 五个核心方案

| 方案ID | 角色 |
|--------|------|
| 500635396 | 主力方案（占消费59%） |
| 495403620 | 次主力（15%） |
| 525368335 | 第三梯队（13%） |
| 495817671 | 第三梯队（12%） |
| 63563817  | 长尾方案（1%） |

## 进度

- [x] 项目结构搭建
- [x] 数据加载模块
- [ ] 问题1：合理性分析 + 规律 + 假日效应
- [ ] 问题2：关键词分类
- [ ] 问题3：投放优化
- [ ] 问题4：不确定性优化
