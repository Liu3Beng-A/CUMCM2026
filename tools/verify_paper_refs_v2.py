import re
import os
import json
import pandas as pd

PAPER = 'd:/CUMCM2026Problems/paper/paper.md'

with open(PAPER, 'r', encoding='utf-8') as f:
    text = f.read()

# 匹配 backticks 包裹的文件名
pattern = r'`([\w/\\.\-]+\.(?:py|xlsx|csv|json|png|pkl|npy|md|docx))`'
matches = re.findall(pattern, text)

# 过滤：跳过明显不是文件的（如代码片段）
def is_real_file_ref(m):
    if m.startswith('Fig.'):
        return False
    if any(ord(c) > 127 for c in m):
        return False
    # 必须有扩展名
    if '.' not in m:
        return False
    return True

real_refs = [m for m in matches if is_real_file_ref(m)]
print(f'=== paper.md 中真实文件引用：{len(real_refs)} 处 ===\n')

missing = []
existing = []
PROJECT_ROOT = 'd:/CUMCM2026Problems'

# 真实路径候选
def find_file(rel_path):
    """尝试多个候选位置"""
    candidates = [
        os.path.join(PROJECT_ROOT, rel_path),
        os.path.join(PROJECT_ROOT, 'results', rel_path),
        os.path.join(PROJECT_ROOT, 'results/figures', rel_path),
        os.path.join(PROJECT_ROOT, 'results/tables', rel_path),
        os.path.join(PROJECT_ROOT, 'results/excel', rel_path),
        os.path.join(PROJECT_ROOT, 'data/processed', rel_path),
        os.path.join(PROJECT_ROOT, 'data/processed/q1', rel_path),
        os.path.join(PROJECT_ROOT, 'data/processed/q2', rel_path),
        os.path.join(PROJECT_ROOT, 'data/processed/q3', rel_path),
        os.path.join(PROJECT_ROOT, 'data/processed/q4', rel_path),
        os.path.join(PROJECT_ROOT, 'src', rel_path),
        os.path.join(PROJECT_ROOT, 'paper', rel_path),
        os.path.join(PROJECT_ROOT, 'issue', rel_path),
        os.path.join(PROJECT_ROOT, 'tools', rel_path),
        os.path.join(PROJECT_ROOT, 'results/snapshots', rel_path),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

for m in sorted(set(real_refs)):
    found = find_file(m)
    if found:
        existing.append((m, found))
    else:
        missing.append(m)

print(f'存在：{len(existing)} 处')
print(f'缺失：{len(missing)} 处')

if missing:
    print('\n=== 真实缺失文件清单 ===')
    for m in sorted(set(missing)):
        print(f'  - {m}')
else:
    print('\n[OK] 所有引用文件均存在')

# 数据质量核查
print()
print('=== 关键数据再核查 ===')
r3 = pd.read_excel('d:/CUMCM2026Problems/results/excel/result3.xlsx')
r4 = pd.read_excel('d:/CUMCM2026Problems/results/excel/result4.xlsx')
r2 = pd.read_excel('d:/CUMCM2026Problems/results/excel/result2.xlsx')

print(f'Q2 result2: shape={r2.shape}, 列={list(r2.columns)}')
print(f'  5 类计数: 黄金={r2["黄金词"].sum()}, 重点={r2["重点词"].sum()}, 潜力={r2["潜力词"].sum()}, 问题={r2["问题词"].sum()}, 无效={r2["无效词"].sum()}, 合计={r2[["黄金词","重点词","潜力词","问题词","无效词"]].sum().sum()}')

print(f'\nQ3 result3: shape={r3.shape}, 列={list(r3.columns)}')
print(f'  总投入: {r3["投入金额"].sum():.2f}, 预期注册: {r3["预期注册量"].sum()}')

print(f'\nQ4 result4: shape={r4.shape}, 列={list(r4.columns)}')
print(f'  总投入: {r4["投入金额"].sum():.2f}, 预期注册: {r4["预期注册量"].sum()}')

# 读 q3 proxy accuracy
print()
print('=== Q3 代理精度详细 ===')
pa = pd.read_csv('d:/CUMCM2026Problems/results/tables/q3_proxy_accuracy.csv')
print(f'rows: {len(pa)}, columns: {list(pa.columns)}')
print('Summary:')
print(f'  Click pass率: {pa["pass_clicks"].sum()}/{len(pa)} = {pa["pass_clicks"].mean()*100:.1f}%')
print(f'  TopImp pass率: {pa["pass_topimp"].sum()}/{len(pa)} = {pa["pass_topimp"].mean()*100:.1f}%')
print(f'  Reg pass率: {pa["pass_regs"].sum()}/{len(pa)} = {pa["pass_regs"].mean()*100:.1f}%')

# 计算 share-Pearson (12 单元)
import numpy as np
def share_pearson(a, b):
    # share = a/sum(a) vs b/sum(b)
    a_share = a / a.sum() if a.sum() > 0 else a
    b_share = b / b.sum() if b.sum() > 0 else b
    if a_share.std() == 0 or b_share.std() == 0:
        return np.nan
    return np.corrcoef(a_share, b_share)[0, 1]

print(f'\n  Click share-Pearson: {share_pearson(pa["actual_clicks"], pa["pred_clicks"]):.4f}')
print(f'  TopImp share-Pearson: {share_pearson(pa["actual_top_imps"], pa["pred_topimp"]):.4f}')
print(f'  Reg share-Pearson: {share_pearson(pa["actual_regs"], pa["pred_regs"]):.4f}')

# 读 q4 uncertainty
print()
print('=== Q4 不确定性参数 ===')
with open('d:/CUMCM2026Problems/data/processed/q4/q4_uncertainty_summary.json', 'r', encoding='utf-8') as f:
    us = json.load(f)
print(json.dumps(us, ensure_ascii=False, indent=2))

# Q4 6 指标扩展
print()
print('=== Q4 6 指标扩展输出 ===')
if os.path.exists('d:/CUMCM2026Problems/results/excel/q4_6metrics_extended.csv'):
    q6 = pd.read_csv('d:/CUMCM2026Problems/results/excel/q4_6metrics_extended.csv')
    print(f'q4_6metrics_extended.csv shape: {q6.shape}, 列: {list(q6.columns)}')
    print(q6.head(3).to_string(index=False))