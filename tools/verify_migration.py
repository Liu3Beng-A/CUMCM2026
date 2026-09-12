"""Final verification: result2.xlsx in new location + all active references updated"""
import os
import pandas as pd

ROOT = 'D:/CUMCM2026Problems'

print('='*70)
print('结果验证：result2.xlsx 迁移')
print('='*70)

# 1. 新位置存在
new_path = f'{ROOT}/results/excel/result2.xlsx'
print(f'\n[1] 新位置文件存在: {os.path.exists(new_path)}')
print(f'    路径: {new_path}')

# 2. 旧位置不存在
old_path = f'{ROOT}/data/raw/attachments/result2.xlsx'
print(f'\n[2] 旧位置文件已移除: {not os.path.exists(old_path)}')
print(f'    路径: {old_path}')

# 3. 文件可读 + 内容正确
out = pd.read_excel(new_path)
print(f'\n[3] 文件可读 + 内容正确:')
print(f'    shape = {out.shape}')
print(f'    列名 = {list(out.columns)}')
print(f'    5 类 sum = 黄金{out["黄金词"].sum()} 重点{out["重点词"].sum()} 潜力{out["潜力词"].sum()} 问题{out["问题词"].sum()} 无效{out["无效词"].sum()}')
print(f'    总和 = {out[["黄金词","重点词","潜力词","问题词","无效词"]].sum().sum()} (期望 2227)')

# 4. EXCEL_DIR 已被使用
print(f'\n[4] src/q2_classify.py 输出路径已更新')
with open(f'{ROOT}/src/q2_classify.py', 'r', encoding='utf-8') as f:
    code = f.read()
old_marker1 = "RAW_DIR + \"/attachments/result2.xlsx\""
old_marker2 = "RAW_DIR, 'attachments', 'result2.xlsx'"
has_old = old_marker1 in code or old_marker2 in code
print(f'    含 EXCEL_DIR 引用: {"EXCEL_DIR" in code}')
print(f'    含旧路径 RAW_DIR/attachments/result2.xlsx: {has_old}')

# 5. 所有活跃文件路径已更新（除快照和历史归档）
import re
print(f'\n[5] 活跃文件中 data/raw/attachments/result 残留扫描:')
active_files = [
    'src/q2_classify.py',
    'src/q2_robustness.py',
    'src/q2_plots.py',
    'paper/paper.md',
    '.cursor/rules/project-context.mdc',
    'WORK_STATE.md',
    'Q3Q4_Method_Architecture.md',
    'paper/paper_appendix_q234.md',
    'issue/q2_implementation_plan.md',
    'tools/check_q2.py',
    'tools/verify_q2_all.py',
    'tools/verify_q2_deep.py',
    'tools/verify_result2.py',
]
total_old_refs = 0
for fp in active_files:
    full_path = f'{ROOT}/{fp}'
    if not os.path.exists(full_path):
        continue
    with open(full_path, 'r', encoding='utf-8') as f:
        text = f.read()
    refs = re.findall(r'data/raw/attachments/result[234]\.xlsx', text)
    if refs:
        print(f'    {fp}: {len(refs)} 残留')
        total_old_refs += len(refs)
print(f'    总残留: {total_old_refs}')

# 6. 新路径已正确写入
print(f'\n[6] 活跃文件中 results/excel/result 引用:')
new_refs = 0
for fp in active_files:
    full_path = f'{ROOT}/{fp}'
    if not os.path.exists(full_path):
        continue
    with open(full_path, 'r', encoding='utf-8') as f:
        text = f.read()
    refs = re.findall(r'results/excel/result[234]\.xlsx', text)
    if refs:
        new_refs += refs
        print(f'    {fp}: {refs}')
print(f'    总新引用: {sum(new_refs) if isinstance(new_refs, list) else new_refs}')
