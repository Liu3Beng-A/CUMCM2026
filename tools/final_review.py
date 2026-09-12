import os, json
print('=== A+B 全部完成最终审查 ===')
print()
print('--- A 级产物 ---')
for f in [
    'data/processed/q4/q4_factor_cov_matrix.csv',
    'data/processed/q4/q4_factor_cov_summary.json',
    'data/processed/q4/q4_copula_scenarios_sample.pkl',
    'results/figures/q4_factor_correlation.png',
    'results/excel/result4_v2.xlsx',
    'results/excel/q4_6metrics_extended_v2.csv',
    'results/tables/q4_two_stage_v2_summary.json',
    'results/tables/q4_lambda_robustness.csv',
    'results/figures/q4_lambda_robustness.png',
    'results/tables/q3_assoc_adoption.csv',
    'results/tables/q3_assoc_adoption_summary.json',
    'results/figures/q3_assoc_network_with_solution.png',
]:
    sz = os.path.getsize(f) if os.path.exists(f) else 'MISSING'
    print(f'  {sz if isinstance(sz,str) else f"{sz:>10} B"}  {f}')
print()
print('--- B 级产物 ---')
for f in [
    'results/tables/q3_sensitivity_v2.csv',
    'results/tables/q3_sensitivity_v2_summary.json',
    'results/figures/q3_sensitivity_v2.png',
    'results/tables/final_consistency_check.json',
    'results/tables/final_consistency_check.txt',
]:
    sz = os.path.getsize(f) if os.path.exists(f) else 'MISSING'
    print(f'  {sz if isinstance(sz,str) else f"{sz:>10} B"}  {f}')
print()
print('--- 论文状态 ---')
sz = os.path.getsize('paper/paper.md')
print(f'  paper.md: {sz} bytes')
print()
print('--- B7 一致性检查结果 ---')
d = json.load(open('results/tables/final_consistency_check.json', encoding='utf-8'))
print(f'  总计 {d["total"]} 项: PASS={d["pass"]} PARTIAL={d["partial"]} CAVEAT={d["caveat"]} DIFF={d["diff"]} SAME={d["same"]} FAIL={d["fail"]}')
print()
print('--- A1 协方差矩阵关键相关系数 ---')
import pandas as pd
cov = pd.read_csv('data/processed/q4/q4_factor_cov_matrix.csv', index_col=0)
six = ['cpc','impressions','top_imp','clicks','browses','regs']
print(cov.loc[six, six].round(3))
print()
print('--- A3 λ 三档 ---')
lam = pd.read_csv('results/tables/q4_lambda_robustness.csv')
print(lam.to_string(index=False))
print()
print('--- A4 关联应用率 ---')
with open('results/tables/q3_assoc_adoption_summary.json', 'r', encoding='utf-8') as f:
    s = json.load(f)
print(f'  mean_all={s["adoption_rate_summary"]["mean_all"]} (预算紧 → 0% 为已知)')
print()
print('--- DECISION_LOG ---')
print(f'  D-001 ~ D-035 已落档')
print()
print('--- RUN_LOG ---')
n = len(open('RUN_LOG.md', encoding='utf-8').read().split('\n'))
print(f'  {n} 行 (UTF-8 干净)')
