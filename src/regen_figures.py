"""定向刷新 q1_score.json 评级 + 4 张过期图

步骤：
1. q1_scoring.run_scoring() → q1_score.json（grade='C' 扣分前 65.3）
2. q1_holiday_penalty.apply_penalty_to_score() → q1_score.json（grade='D' 扣分后 56.0）
3. 4 张图按 q1_score.json 重画
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

import json

print('[regen] Step 1/3  q1_scoring → 65.3 / C ...', flush=True)
from src.q1_scoring import run_scoring
result = run_scoring()

print('\n[regen] Step 2/3  q1_holiday_penalty → 56.0 / D ...', flush=True)
from src.q1_holiday_penalty import apply_penalty_to_score
new_overall = apply_penalty_to_score()

with open(r'd:\CUMCM2026Problems\results\tables\q1_score.json', 'r', encoding='utf-8') as f:
    sc = json.load(f)
print(f'[regen]   overall_score = {sc["overall_score"]}', flush=True)
print(f'[regen]   grade         = {sc["grade"]}', flush=True)

print('\n[regen] Step 3/3  重画 4 张图（grade="D (偏差)"）...', flush=True)
from src.q1_plots import fig_score_radar, fig_score_breakdown
fig_score_radar(sc)
fig_score_breakdown(sc)
print('[regen]   ✓ q1_score_radar.png', flush=True)
print('[regen]   ✓ q1_score_breakdown.png', flush=True)

from src.q1_heatmap import fig_heatmap
fig_heatmap()
print('[regen]   ✓ q1_heatmap.png', flush=True)
print('[regen]   ✓ q1_penalty_compare.png', flush=True)

print('\n[regen] 完成。grade="D (偏差)" / 56.0 / 4 张图全部刷新。', flush=True)