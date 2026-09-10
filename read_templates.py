import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

# 查看所有结果模板
for fname in ['result2.xlsx', 'result3.xlsx', 'result4.xlsx']:
    path = rf'D:\CUMCM2026Problems\附件\附件2\{fname}'
    print(f'\n===== {fname} =====')
    try:
        xl = pd.ExcelFile(path)
        print(f'Sheets: {xl.sheet_names}')
        for sh in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sh)
            print(f'\n--- {sh} ---')
            print(f'shape: {df.shape}')
            print(f'columns: {list(df.columns)}')
            print(df.head(3).to_string())
    except Exception as e:
        print(f'err: {e}')
