import re
import os
import pandas as pd

PAPER = 'd:/CUMCM2026Problems/paper/paper.md'

# 1. 抽取 paper.md 中所有文件名引用
with open(PAPER, 'r', encoding='utf-8') as f:
    text = f.read()

# 匹配 backticks 包裹的文件名
pattern = r'`([\w/\\.\-]+\.(?:py|xlsx|csv|json|png|pkl|npy|md|docx))`'
matches = re.findall(pattern, text)

print(f'=== paper.md 中引用的文件：{len(matches)} 处 ===')

# 检查每个文件是否存在
missing = []
existing = []
for m in matches:
    # 跳过论文引用格式如 "Fig.5-1"
    if m.startswith('Fig.'):
        continue
    # 跳过"图 X-Y"格式
    if re.match(r'^图\s*\d', m):
        continue
    # 跳过中文路径
    if any(ord(c) > 127 for c in m):
        continue
    full_path = os.path.join('d:/CUMCM2026Problems', m.replace('/', os.sep))
    if os.path.exists(full_path):
        existing.append(m)
    else:
        # 也试试 data/processed/q3 这种二级目录
        alt_paths = [
            os.path.join('d:/CUMCM2026Problems', m),
            os.path.join('d:/CUMCM2026Problems', 'data/processed', m),
            os.path.join('d:/CUMCM2026Problems', 'data/processed/q3', m),
            os.path.join('d:/CUMCM2026Problems', 'results', m),
        ]
        found = False
        for alt in alt_paths:
            if os.path.exists(alt):
                existing.append(m + ' [ALT: ' + alt.replace('d:/CUMCM2026Problems/', '') + ']')
                found = True
                break
        if not found:
            missing.append(m)

print(f'存在：{len(existing)} 处')
print(f'缺失：{len(missing)} 处')

if missing:
    print('\n=== 缺失文件清单 ===')
    for m in sorted(set(missing)):
        print(f'  - {m}')

# 2. 数据质量核查
print()
print('=== 关键数据再核查 ===')
r3 = pd.read_excel('d:/CUMCM2026Problems/results/excel/result3.xlsx')
r4 = pd.read_excel('d:/CUMCM2026Problems/results/excel/result4.xlsx')

# 检查代理精度
if os.path.exists('d:/CUMCM2026Problems/results/tables/q3_proxy_accuracy.csv'):
    pa = pd.read_csv('d:/CUMCM2026Problems/results/tables/q3_proxy_accuracy.csv')
    print(f'q3_proxy_accuracy.csv shape: {pa.shape}')
    print('代理精度表内容（前 10 行）:')
    print(pa.head(10).to_string(index=False))

# 检查 Q4 uncertainty
if os.path.exists('d:/CUMCM2026Problems/results/tables/q4_two_stage_summary.json'):
    with open('d:/CUMCM2026Problems/results/tables/q4_two_stage_summary.json', 'r', encoding='utf-8') as f:
        ts = json.load(f)
    print(f'\nq4_two_stage_summary.json:')
    print(json.dumps(ts, ensure_ascii=False, indent=2)[:500])

import json
if os.path.exists('d:/CUMCM2026Problems/data/processed/q4/q4_uncertainty_summary.json'):
    with open('d:/CUMCM2026Problems/data/processed/q4/q4_uncertainty_summary.json', 'r', encoding='utf-8') as f:
        us = json.load(f)
    print(f'\nq4_uncertainty_summary.json:')
    print(json.dumps(us, ensure_ascii=False, indent=2)[:500])