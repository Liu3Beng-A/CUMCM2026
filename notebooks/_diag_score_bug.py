"""检查 min_max_score 在单值输入下的退化行为。"""
import sys
sys.path.insert(0, r'd:\CUMCM2026Problems')
from src.q1_scoring import min_max_score, percentile_zscore_score
import numpy as np
import pandas as pd

# 1) min_max_score 单值调用
print("=== min_max_score 单值测试 ===")
test_cases = [
    ("有效率 60.04% (理想高)", 0.6004, False),
    ("跳出率 73.4% (理想低)", 0.7343, True),
    ("访问时长 167秒 (理想高)", 167.1, False),
    ("基尼系数 0.405 (理想低)", 0.405, True),
    ("上方位渗透 70.35% (理想高)", 0.7035, False),
    ("高价词占比 3.89% (理想低)", 0.0389, True),
]
for name, val, ideal_low in test_cases:
    s, xmin, xmax = min_max_score([val], ideal_low=ideal_low)
    print(f"  {name}: 输入 {val} → 评分 {s[0]:.1f}  (rng=({xmin},{xmax}))")

# 2) percentile_zscore_score 单值参考分布
print("\n=== percentile_zscore_score 单值参考 ===")
ref = pd.Series([0.7035])
s = percentile_zscore_score(0.7035, ref, ideal_low=False)
print(f"  上方位渗透 70.35%: 评分 {s:.1f}")

# 3) 多值（与方案×日的）正常工作
print("\n=== min_max_score 多值测试 ===")
s, _, _ = min_max_score(np.array([0.038, 0.04, 0.05, 0.039, 0.038, 0.04]), ideal_low=True)
print(f"  6个低价词占比: 评分 {s.round(1)}")

# 4) 检查关键词管理维度的 6 个二级评分
print("\n=== 关键词管理维度 6 个二级评分检查 ===")
print(f"  有效率评分: 0.0      ← 应该约 60 (理想高)")
print(f"  高价词评分: 100.0    ← 应该约 100 (理想低)")
print(f"  跳出率评分: 100.0    ← 应该约 50 (理想低, 73% 是偏差)")
print(f"  高跳出评分: 100.0    ← 应该约 40 (理想低, 40.76% 偏高)")
print(f"  访问时长评分: 0.0    ← 应该约 60 (理想高, 167秒中等)")
print(f"  集中度评分: 100.0    ← 应该约 50 (理想低, 99% 极度集中)")
print(f"  → 当前综合分 66.7 是 6 个默认分数的均值, 失真!")
