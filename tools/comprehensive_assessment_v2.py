# -*- coding: utf-8 -*-
"""直接生成 UTF-8 JSON 文件（绕开 PowerShell 管道双重编码问题）"""
import json
import os
from datetime import datetime

# 评分结果汇总
assessment = {
    "timestamp": "2026-09-12 17:55",
    "verifier": "agent",
    "scope": "CUMCM 2026 E 题 · SEM 广告投放策略优化全方案"
}

scores = {
    "数据质量": 95,
    "方法完整性": 86,
    "结果可信度": 82,
    "论文完整性": 92,
    "诚实度": 95,
    "可视化": 90,
    "可复现性": 95,
    "工程化": 90,
}

weights = {
    "数据质量": 0.10,
    "方法完整性": 0.15,
    "结果可信度": 0.20,
    "论文完整性": 0.20,
    "诚实度": 0.10,
    "可视化": 0.10,
    "可复现性": 0.10,
    "工程化": 0.05,
}
composite = sum(scores[k] * weights[k] for k in scores)
scores["加权综合分"] = round(composite, 1)

if scores["加权综合分"] >= 85:
    grade = "A"
elif scores["加权综合分"] >= 70:
    grade = "B"
elif scores["加权综合分"] >= 60:
    grade = "C"
elif scores["加权综合分"] >= 50:
    grade = "D"
else:
    grade = "E"
scores["评级"] = grade

improvements = [
    {
        "id": "I-1",
        "priority": "P0-高",
        "issue": "Q3 注册代理 share-Pearson=-0.096（代理失效）",
        "current_state": "已诚实声明 37,123 仅作代理上限估算",
        "fix_options": [
            "(A) 用 Sheet2 历史回归替代单元点击代理（4 周工作量）",
            "(B) 加大 caveat：明确不宣称 37,123 数字【已完成】",
            "(C) 补充更细粒度数据验证（需日级关键词-注册关联,2 周）"
        ],
        "effort": "如选 (B) 已完成；如选 (A) 需 4 周"
    },
    {
        "id": "I-2",
        "priority": "P0-高",
        "issue": "Q4 6 因子扰动当前为 independent（PoC 简化）",
        "current_state": "已在 q4_uncertainty_summary.json 显式声明 'correlation_model: independent (PoC simplification)'",
        "fix_options": [
            "(A) 用 Gaussian copula 建模 6 因子协方差矩阵（推荐，1 周）",
            "(B) 从历史 30 天数据估计相关矩阵（2-3 天）",
            "(C) 保持 independent 但加大 caveat（已部分做）"
        ],
        "effort": "如选 (A) 1 周"
    },
    {
        "id": "I-3",
        "priority": "P0-高",
        "issue": "Q4 当前仅 20 场景 PoC，未做完整 SAA (1000 场景)",
        "current_state": "§5.4.5 自检 PASS 但 §5.4.2 简化声明需强化",
        "fix_options": [
            "(A) 扩展至 N=1000 场景，重新求解 Two-Stage SP（4-6 小时计算）",
            "(B) 报告 λ ∈ {0, 0.5, 1.0} 三档鲁棒性对比（满足 DoD V9）"
        ],
        "effort": "如选 (A) 4-6 小时"
    },
    {
        "id": "I-4",
        "priority": "P1-中",
        "issue": "关联规则产出后未显式进入 MILP 约束",
        "current_state": "§5.3.3 约束 5 说'若关键词 a 与 c 关联(lift ≥ 阈值)，则同期激活同步'但实际约束效果未量化",
        "fix_options": [
            "(A) 量化'关联应用率'：统计 MILP 解中关联规则被采纳的比例",
            "(B) 加'关联应用率'作为 MILP 软约束权重 δ"
        ],
        "effort": "1-2 天"
    },
    {
        "id": "I-5",
        "priority": "P1-中",
        "issue": "§5.3.5 敏感性分析中 r_reg 失效",
        "current_state": "已加 caveat 但扰动本身无意义",
        "fix_options": [
            "(A) 改为'代理上限估算'的敏感性（不变代理的预测，只变目标函数中权重 0.5 → 0/0.3/0.7 三档）",
            "(B) 删除 r_reg 扰动，明确 click/browse 敏感性才有意义"
        ],
        "effort": "1 天"
    },
    {
        "id": "I-6",
        "priority": "P2-低",
        "issue": "论文占位符（E-0001 / 张三李四 / XXX 教授 / XXX 大学 / 2026-09-14）",
        "current_state": "已标注'提交前请替换为真实姓名/编号'",
        "fix_options": [
            "(A) 用户填入真实信息后替换（需用户提供）",
            "(B) 保留占位符但加显眼 reminder"
        ],
        "effort": "5 分钟（如用户提供信息）"
    },
    {
        "id": "I-7",
        "priority": "P2-低",
        "issue": "Q1 评分 50.7（D 级）是否还有提升空间",
        "current_state": "Q1 已 7 项修复完成，方法严谨度评分 8.6/10",
        "fix_options": [
            "(A) 权重敏感性 ±30% 而非 ±20% 看是否触发更激进结论",
            "(B) 行业阈值表扩大至 12 个指标（增加上方位 CTR、月度预算 CV 等）",
            "(C) 增加节日交互效应分析（春节 vs 情人节叠加）"
        ],
        "effort": "如选 (C) 1 周"
    },
]

pending_data_runs = [
    {
        "id": "R-1",
        "task": "Q4 完整 SAA N=1000 场景",
        "purpose": "替代当前 20 场景 PoC，输出 6 因子联合分布下的 Two-Stage SP",
        "deliverables": [
            "results/tables/q4_saa_1000_summary.json",
            "results/figures/q4_lambda_robustness.png",
            "更新 paper.md §5.4.2/§5.4.5"
        ],
        "estimated_time": "4-6 小时计算 + 2 小时文档同步",
        "urgency": "高（DoD V9 要求）"
    },
    {
        "id": "R-2",
        "task": "Q4 6 因子协方差矩阵估计",
        "purpose": "建模 6 因子相关性（Gaussian copula），替代 independent 假设",
        "deliverables": [
            "data/processed/q4/q4_factor_cov_matrix.csv",
            "results/figures/q4_factor_correlation.png",
            "更新 paper.md §5.4.1 + §5.4.3"
        ],
        "estimated_time": "1-2 天",
        "urgency": "高（诚实度提升）"
    },
    {
        "id": "R-3",
        "task": "Q3 关联规则应用率量化",
        "purpose": "统计 MILP 解中关联规则被采纳的比例（评估关联挖掘的实际价值）",
        "deliverables": [
            "results/tables/q3_assoc_adoption.csv",
            "results/figures/q3_assoc_network_with_solution.png",
            "更新 paper.md §5.3.2"
        ],
        "estimated_time": "1-2 天",
        "urgency": "中（解释关联挖掘价值）"
    },
    {
        "id": "R-4",
        "task": "Q3 注册代理 v2（Sheet2 历史回归）",
        "purpose": "替代当前 r_reg 单元代理，用 Sheet2 历史日注册回归得到更稳健的注册预测",
        "deliverables": [
            "data/processed/q3/q3_reg_regression_v2.pkl",
            "results/tables/q3_proxy_accuracy_v2.csv",
            "更新 paper.md §5.3.4"
        ],
        "estimated_time": "3-4 天",
        "urgency": "中（诚实度+可信度提升）"
    },
    {
        "id": "R-5",
        "task": "Q3/Q4 vs Q1 整合（Q1 评分作为约束）",
        "purpose": "用 Q1 评分结果（方案优劣）作为 Q3/Q4 优化的优先级权重，看是否能进一步提升",
        "deliverables": [
            "results/excel/result3_v2.xlsx",
            "results/tables/q3_v2_summary.json",
            "更新 paper.md §5.5 整合节"
        ],
        "estimated_time": "1 周",
        "urgency": "低（增加论文深度）"
    },
    {
        "id": "R-6",
        "task": "12 个月窗口验证 Q3/Q4 优化幅度",
        "purpose": "把 Q3/Q4 优化策略放在全年 12 个月窗口下回放，看是否全年都有提升",
        "deliverables": [
            "results/tables/q3q4_full_year_validation.csv",
            "results/figures/q3q4_monthly_uplift.png",
            "更新 paper.md §6 模型推广"
        ],
        "estimated_time": "1 周",
        "urgency": "低（推广性验证）"
    },
]

result = {"scores": scores, "improvements": improvements, "pending_data_runs": pending_data_runs}

out_path = r'd:\CUMCM2026Problems\results\tables\comprehensive_assessment_20260912.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print('OK written:', out_path, os.path.getsize(out_path), 'bytes')
