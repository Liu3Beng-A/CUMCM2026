"""验证 mdc v3 自动日志规则写入"""
with open('.cursor/rules/project-context.mdc', encoding='utf-8') as fp:
    mdc = fp.read()

checks = [
    ('第一动作清单', '第一动作清单' in mdc),
    ('第二动作 自动日志写入', '第二动作' in mdc and '自动日志写入' in mdc),
    ('禁止忘了 log', '忘了 log' in mdc),
    ('section 13 自动日志规则', '## 13. 自动日志写入规则' in mdc),
    ('section 13.1 RUN_LOG 规则', '### 13.1 RUN_LOG' in mdc),
    ('section 13.5 常见错误', '### 13.5 常见错误' in mdc),
    ('末尾时间戳 13:50', '2026-09-12 13:50' in mdc),
    ('事故记录更新', 'mdc v3 自动日志规则' in mdc),
]
print('mdc v3 自动日志规则检查:')
for label, ok in checks:
    print('  ' + ('OK' if ok else 'FAIL') + '  ' + label)
print()
print('mdc 总行数:', len(mdc.split(chr(10))))

with open('RUN_LOG.md', encoding='utf-8') as fp:
    log = fp.read()
print('RUN_LOG 总行数:', len(log.split(chr(10))))
print('RUN_LOG 含"强制规则"块:', '强制规则' in log)
print('RUN_LOG 含 mdc v3 记录:', 'mdc v3' in log)

import os
snap = 'results/snapshots/mdc_v3_with_auto_log_20260912'
print()
print('v3 snapshot:', os.path.exists(snap))
if os.path.exists(snap):
    for f in os.listdir(snap):
        print('  -', f, os.path.getsize(os.path.join(snap, f)), 'bytes')
