"""
DECISION_LOG.md 二次修复：D-017~D-022 → D-015~D-020（连续编号）
"""
DECISION_LOG = 'D:/CUMCM2026Problems/DECISION_LOG.md'
with open(DECISION_LOG, 'r', encoding='utf-8') as f:
    content = f.read()

# 只针对 15:30 这 6 条改 ID
remap = [
    ('[2026-09-12 15:30] D-017 |', '[2026-09-12 15:30] D-015 |'),
    ('[2026-09-12 15:30] D-018 |', '[2026-09-12 15:30] D-016 |'),
    ('[2026-09-12 15:30] D-019 |', '[2026-09-12 15:30] D-017 |'),
    ('[2026-09-12 15:30] D-020 |', '[2026-09-12 15:30] D-018 |'),
    ('[2026-09-12 15:30] D-021 |', '[2026-09-12 15:30] D-019 |'),
    ('[2026-09-12 15:30] D-022 |', '[2026-09-12 15:30] D-020 |'),
]

for old, new in remap:
    content = content.replace(old, new)

with open(DECISION_LOG, 'w', encoding='utf-8') as f:
    f.write(content)

print('编号连续化完成：D-015~D-020')
