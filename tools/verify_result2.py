"""
S1: Read result2 template and output for Q2 verification
"""
import pandas as pd

# Read template
tpl = pd.read_excel('D:/CUMCM2026Problems/data/raw/attachments/附件2/result2.xlsx', header=None)
print('=== result2 模板 ===')
print(f'shape={tpl.shape}')
print(tpl.to_string())
print()

# Read output
out = pd.read_excel('D:/CUMCM2026Problems/results/excel/result2.xlsx')
print('=== result2 输出 ===')
print(f'shape={out.shape}')
print(f'列名={list(out.columns)}')
print(f'前5行：')
print(out.head().to_string())
print()
print(f'5类计数：')
for c in ['黄金词','重点词','潜力词','问题词','无效词']:
    print(f'  {c}: {out[c].sum()}')
print(f'总行数={len(out)}')

# One-hot check
cls_cols = ['黄金词','重点词','潜力词','问题词','无效词']
sum_row = out[cls_cols].sum(axis=1)
print(f'每行5类之和=1的检验: {(sum_row==1).all()}')
print(f'5类总数={out[cls_cols].sum().sum()}')
