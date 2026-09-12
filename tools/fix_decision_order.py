"""
DECISION_LOG.md 时间顺序修复：
14:18 的 D-011~D-016 重命名为 15:30 的 D-017~D-022（保持时间顺序 + 不重复 ID）
"""
import os
import re

DECISION_LOG = 'D:/CUMCM2026Problems/DECISION_LOG.md'

with open(DECISION_LOG, 'r', encoding='utf-8') as f:
    content = f.read()

# 14:18 的 D-011~D-016 改名为 D-017~D-022（按 D-016 后续）
remap = {
    'D-011': 'D-017',
    'D-012': 'D-018',
    'D-013': 'D-019',
    'D-014': 'D-020',
    'D-015': 'D-021',
    'D-016': 'D-022',
}

# 注意：只替换"14:18 D-XXX"，不替换 15:25 的 D-011~D-014
# 通过定位 "\n\n[2026-09-12 14:18] D-011 |" 之后到文件末尾的区域
idx_start = content.find('\n\n[2026-09-12 14:18] D-011 |')
if idx_start < 0:
    print('未找到 14:18 段落，跳过')
    exit()

section = content[idx_start:]
# 只在这个 section 里替换
new_section = section
for old_id, new_id in remap.items():
    new_section = new_section.replace(old_id, new_id)

# 把 section 插入到 15:25 D-014 之后
# 找 15:25 D-014 行尾
marker_end_15_25 = "[2026-09-12 15:25] D-014 | Q3/Q4 方法架构"
idx_end = content.find(marker_end_15_25)
if idx_end < 0:
    print('未找到 15:25 D-014 marker，跳过')
    exit()

# 找到 D-014 这一行结尾
line_end = content.find('\n', idx_end)
new_content = content[:line_end+1] + '\n' + new_section.lstrip() + '\n'

with open(DECISION_LOG, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f'修复完成。新长度：{len(new_content)} chars')
print(f'原 section 长度：{len(section)}, 新 section 长度：{len(new_section)}')
