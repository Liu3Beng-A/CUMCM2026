import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
import pandas as pd

root = r'D:\CUMCM2026Problems'

# Find all subdirectories using glob with bytes
import glob

# Find attachment dir
att_dirs = []
for d in glob.glob(os.path.join(root, '*')):
    if os.path.isdir(d) and '附件' in d:
        att_dirs.append(d)

print(f'Found attachment dirs: {att_dirs}')

for att_dir in att_dirs:
    print(f'\n=== {att_dir} ===')
    for item in os.listdir(att_dir):
        full = os.path.join(att_dir, item)
        if os.path.isdir(full):
            print(f'  [DIR] {item}')
            for f in os.listdir(full):
                full_f = os.path.join(full, f)
                if os.path.isfile(full_f):
                    print(f'    {f}: {os.path.getsize(full_f)} bytes')
                    # Read it
                    try:
                        xl = pd.ExcelFile(full_f)
                        for sheet in xl.sheet_names:
                            df = pd.read_excel(full_f, sheet_name=sheet)
                            print(f'      Sheet "{sheet}": shape={df.shape}')
                            print(f'      Columns: {list(df.columns)}')
                            print(f'      前5行:')
                            print(df.head().to_string().replace('\n', '\n      '))
                    except Exception as e:
                        print(f'    Error reading: {e}')
        else:
            print(f'  {item}: {os.path.getsize(full)} bytes')
