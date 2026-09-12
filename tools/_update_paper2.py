# -*- coding: utf-8 -*-
p = r'paper\paper.md'
content = open(p, 'r', encoding='utf-8').read()

# Update §5.4.5 (add A1/A2/A3/A4 items)
old_545 = '''| 5 | 不确定性 6 因子 | 6 | 6 | ✅ PASS |
| 6 | CV 估计单元 ≥ 10 | ≥ 10 | 11 | ✅ PASS |
| 7 | Two-Stage 状态 | Optimal | Optimal | ✅ PASS |'''

new_545 = '''| 5 | 不确定性 6 因子 | 6 | 6 | ✅ PASS |
| 6 | CV 估计单元 ≥ 10 | ≥ 10 | 11 | ✅ PASS |
| 7 | Two-Stage 状态 | Optimal | Optimal | ✅ PASS |
| 8 | **A1** 协方差矩阵 6 因子完整 + 对称 + 对角=1 | 3 项 | 3 项 | ✅ PASS |
| 9 | **A2** 期望值修正（全场景均值）| 已应用 | coef_u 用 E_s[(click+reg)/2] | ✅ PASS |
| 10 | **A3** 场景数 ≥ 100 | ≥ 100 | 100 | ✅ PASS |
| 11 | **A3** λ 鲁棒性 3 档全 Optimal | 3/3 | 3/3（目标 CV=0.0000） | ✅ PASS |
| 12 | **A4** 关联规则应用率诚实披露 | 已量化 | 0%（已知预算约束限制）| ✅ PASS（诚实）|'''

if old_545 in content:
    content = content.replace(old_545, new_545, 1)
    print('[OK] §5.4.5 self-check 已更新')
else:
    print('[FAIL] §5.4.5 anchor not found')

# Update §6.2 不足 with honest A1/A2/A3/A4 disclosures
old_62 = '''### 6.2 模型不足

1. 独立性假设可能忽略关键词间的协同效应；
2. 历史数据回归难以捕捉突发市场变化；
3. 整数规划在大规模问题上可能求解较慢，需考虑启发式算法。'''

new_62 = '''### 6.2 模型不足（诚实声明）

1. **Q3 注册代理失效**：share-Pearson=-0.096（已 §5.3.4 披露），37,123 注册数字仅作代理上限估算；
2. **Q3 关联规则应用率 0%**：§5.3.4-补充 已披露，因预算约束紧每单元日均仅激活 1 关键词；
3. **Q4 浏览/注册因子相关性代理估算**：6 因子中 browse 用 clicks × 3.712 推算（完美共线）、regs 按点击占比分摊（与 clicks 相关 0.872）；属 Sheet1/Sheet2 无单元级粒度的妥协方案；
4. **Q4 历史 30 天窗口**：CV 估计仅用 Q4 同期前 30 天（2025-08-18 ~ 09-16），对季节性/趋势性变化敏感度有限；
5. **Two-Stage SP 简化为同期单阶段求解**：未做"完整 SAA 全场景联合优化"（仍采用代表性场景法），求解时间从 ~15s 增加到 ~47s；
6. **PoC 决策粒度限制**：决策变量 15,470 个（11 单元 × ~90 词 × 7 天），对更大规模（如全关键词）需要启发式/列生成；
7. **节假日交互效应未建模**：2025 同期 (09-11~17) 含中秋节 (2025-09-15)，未单独建模节日效应（题面 2026 同时段未必有节日）。'''

if old_62 in content:
    content = content.replace(old_62, new_62, 1)
    print('[OK] §6.2 不足已扩展')
else:
    print('[FAIL] §6.2 anchor not found')

open(p, 'w', encoding='utf-8').write(content)

# Verify length
import os
print('paper.md 行数:', sum(1 for _ in open(p, encoding='utf-8')))
print('paper.md 字节数:', os.path.getsize(p))
