import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'd:\CUMCM2026Problems\results\tables\q1_score.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
print(f'综合评分: {d["overall_score"]}', flush=True)
print(f'评级: {d["grade"]}', flush=True)
for cat, info in d['dimensions'].items():
    print(f'  {cat}: {info["score"]} (w={info["weight"]})', flush=True)
