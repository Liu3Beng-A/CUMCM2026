import os, json
def listing(p):
    if not os.path.exists(p):
        return 'NOT EXIST'
    if os.path.isfile(p):
        return f'{os.path.getsize(p):>10} bytes  {p}'
    out = []
    for f in sorted(os.listdir(p)):
        full = os.path.join(p, f)
        if os.path.isfile(full):
            out.append(f'{os.path.getsize(full):>10}  {f}')
        elif os.path.isdir(full):
            out.append(f'{"<DIR>":>10}  {f}/')
    return '\n'.join(out)

print('=== results/excel/ ===')
print(listing(r'd:\CUMCM2026Problems\results\excel'))
print()
print('=== results/tables/q4* ===')
print(listing(r'd:\CUMCM2026Problems\results\tables'))
print()
print('=== results/figures/q4* ===')
print(listing(r'd:\CUMCM2026Problems\results\figures'))
print()
print('=== data/processed/q4 (新加) ===')
print(listing(r'd:\CUMCM2026Problems\data\processed\q4'))

# 验证 q4_factor_cov_matrix.csv
import pandas as pd
cov = pd.read_csv(r'd:\CUMCM2026Problems\data\processed\q4\q4_factor_cov_matrix.csv', index_col=0)
print()
print('=== A1 协方差矩阵 (6 因子) ===')
six = ['cpc','impressions','top_imp','clicks','browses','regs']
print(cov.loc[six, six].round(3))

# 验证 result4_v2.xlsx
print()
print('=== A3 result4_v2.xlsx ===')
r = pd.read_excel(r'd:\CUMCM2026Problems\results\excel\result4_v2.xlsx')
print('行数:', len(r), '| 列对齐:', list(r.columns) == ['日期','方案ID','推广单元','关键词','投入金额','预期展位','预期点击量','预期浏览量','预期注册量'])
print('投入:', round(r['投入金额'].sum(), 2), '/ 23488.02')

# 验证 λ 鲁棒性
print()
print('=== A3 λ 三档对比 ===')
print(pd.read_csv(r'd:\CUMCM2026Problems\results\tables\q4_lambda_robustness.csv').to_string(index=False))

# 验证 A4
print()
print('=== A4 关联应用率 ===')
adopt = pd.read_csv(r'd:\CUMCM2026Problems\results\tables\q3_assoc_adoption.csv')
print('日期-单元组:', len(adopt), '| 平均每组关键词:', adopt['n_keywords'].mean())
print('n_keywords 直方:')
print(adopt['n_keywords'].value_counts().sort_index().to_string())
print('应用率（全部）:', adopt['adoption_rate_all'].mean(), '| max:', adopt['adoption_rate_all'].max())
print('应用率（高置信）:', adopt['adoption_rate_high'].mean(), '| max:', adopt['adoption_rate_high'].max())

with open(r'd:\CUMCM2026Problems\results\tables\q3_assoc_adoption_summary.json','r',encoding='utf-8') as f:
    s = json.load(f)
print()
print('A4 summary:')
print(json.dumps(s['adoption_rate_summary'], indent=2, ensure_ascii=False))
