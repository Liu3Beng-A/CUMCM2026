import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

print('=== result2.xlsx ===', flush=True)
df = pd.read_excel(r'D:\CUMCM2026Problems\附件\附件2\result2.xlsx')
print(f'Shape: {df.shape}', flush=True)
print(f'Columns RAW:', flush=True)
for c in df.columns:
    print(f'  [{c}] (len={len(c)}) bytes: {c.encode("utf-8")}', flush=True)

print('\n=== result3.xlsx ===', flush=True)
df = pd.read_excel(r'D:\CUMCM2026Problems\附件\附件2\result3.xlsx')
print(f'Shape: {df.shape}', flush=True)
print(f'Columns RAW:', flush=True)
for c in df.columns:
    print(f'  [{c}] (len={len(c)})', flush=True)

print('\n=== result4.xlsx ===', flush=True)
df = pd.read_excel(r'D:\CUMCM2026Problems\附件\附件2\result4.xlsx')
print(f'Shape: {df.shape}', flush=True)
print(f'Columns RAW:', flush=True)
for c in df.columns:
    print(f'  [{c}] (len={len(c)})', flush=True)
