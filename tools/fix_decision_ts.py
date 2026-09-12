"""
DECISION_LOG.md 二次修复：D-017~D-022 时间戳 14:18 → 15:30
（保持时间顺序：15:25 D-014 → 15:30 D-017~D-022）
"""
import os

DECISION_LOG = 'D:/CUMCM2026Problems/DECISION_LOG.md'

with open(DECISION_LOG, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 14:18 → 15:30（只针对 D-017~D-022）
old_markers = [
    '[2026-09-12 14:18] D-017 |',
    '[2026-09-12 14:18] D-018 |',
    '[2026-09-12 14:18] D-019 |',
    '[2026-09-12 14:18] D-020 |',
    '[2026-09-12 14:18] D-021 |',
    '[2026-09-12 14:18] D-022 |',
]
new_markers = [
    '[2026-09-12 15:30] D-017 |',
    '[2026-09-12 15:30] D-018 |',
    '[2026-09-12 15:30] D-019 |',
    '[2026-09-12 15:30] D-020 |',
    '[2026-09-12 15:30] D-021 |',
    '[2026-09-12 15:30] D-022 |',
]

for old, new in zip(old_markers, new_markers):
    content = content.replace(old, new)

with open(DECISION_LOG, 'w', encoding='utf-8') as f:
    f.write(content)

print('修复完成')
print(f'当前 D-017 时间戳：', end='')
for line in content.split('\n'):
    if 'D-017 |' in line:
        print(line[:30])
        break
