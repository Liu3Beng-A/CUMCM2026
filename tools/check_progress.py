"""check_progress.py · 项目进度自检脚本

用法：python tools/check_progress.py

每次新上下文开启时第一动作 = 跑这个脚本，一眼看出当前进度。
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
errors = []
oks = []

def check(label: str, condition: bool, hint: str = ""):
    if condition:
        oks.append(f"[OK]   {label}")
    else:
        errors.append(f"[MISS] {label}" + (f"  ({hint})" if hint else ""))

# ============ Q1 数据契约 ============
check("data/processed/q1/keyword_total.pkl", (ROOT / "data/processed/q1/keyword_total.pkl").exists())
check("data/processed/q1/plan_daily.pkl", (ROOT / "data/processed/q1/plan_daily.pkl").exists())
check("data/processed/q1/daily_full.pkl", (ROOT / "data/processed/q1/daily_full.pkl").exists())

# ============ Q1 输出 ============
q1_score = ROOT / "results/tables/q1_score.json"
if q1_score.exists():
    try:
        with open(q1_score, "r", encoding="utf-8") as f:
            d = json.load(f)
        check(f"q1_score.json.overall_score = {d.get('overall_score')}", d.get('overall_score') is not None)
    except Exception as e:
        errors.append(f"[ERR] q1_score.json 解析失败: {e}")
else:
    errors.append("[MISS] q1_score.json")

check("q1_weights.json", (ROOT / "results/tables/q1_weights.json").exists())
check("q1_holiday_penalty.json", (ROOT / "results/tables/q1_holiday_penalty.json").exists())
check("q1_bootstrap_ci.csv", (ROOT / "results/tables/q1_bootstrap_ci.csv").exists())

# ============ Q2 输出 ============
check("Q2: results/tables/q2_keyword_classification.csv", (ROOT / "results/tables/q2_keyword_classification.csv").exists())
check("Q2: data/raw/attachments/result2.xlsx", (ROOT / "data/raw/attachments/result2.xlsx").exists())

# ============ Q3 输出 ============
check("Q3: results/tables/q3_daily_strategy.csv", (ROOT / "results/tables/q3_daily_strategy.csv").exists())
check("Q3: data/raw/attachments/result3.xlsx", (ROOT / "data/raw/attachments/result3.xlsx").exists())

# ============ Q4 输出 ============
check("Q4: results/tables/q4_daily_strategy.csv", (ROOT / "results/tables/q4_daily_strategy.csv").exists())
check("Q4: data/raw/attachments/result4.xlsx", (ROOT / "data/raw/attachments/result4.xlsx").exists())

# ============ 论文 ============
check("paper/paper.md", (ROOT / "paper/paper.md").exists())

sys.stdout.reconfigure(encoding='utf-8')

# ============ 输出 ============
print("\n".join(oks))
if errors:
    print("\n--- MISSING / ERRORS ---")
    print("\n".join(errors))
    sys.exit(1)
print(f"\n[OK] All {len(oks)} checks passed.")
