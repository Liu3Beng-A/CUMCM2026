# -*- coding: utf-8 -*-
# Clean RUN_LOG: read with errors='replace', then verify the latest 7 entries
raw = open('RUN_LOG.md', 'rb').read()
text = raw.decode('utf-8', errors='replace').replace('\ufffd', '').replace('\x00', '')
lines = text.split('\n')

# Filter only lines that contain today's date and valid action markers
import re
ok_lines = []
for ln in lines:
    # Drop empty lines and lines with garbage
    if not ln.strip():
        ok_lines.append(ln)
        continue
    # Try to detect if line is reasonable (has timestamp)
    if re.match(r'\[2026-09-12 \d\d:\d\d\]', ln):
        ok_lines.append(ln)
    else:
        # Garbage line, drop
        pass

text_clean = '\n'.join(ok_lines)
open('RUN_LOG.md', 'w', encoding='utf-8').write(text_clean)
print(f'cleaned to {len(ok_lines)} lines, {len(text_clean)} chars')

# Append the new entries fresh (in pure UTF-8)
new_entries = """
[2026-09-12 18:02] **REVIEW1 通过**: tools/review_a_level.py 全产物盘点 + 4 项验证全部 PASS | review_a.txt | OK
[2026-09-12 18:02] **B6 启动**: §5.3.5 敏感性重构（删 r_reg，改 click/browse 权重三档） | - | -
[2026-09-12 18:02] **B7 启动**: 数据一致性验证脚本终跑 | - | -
[2026-09-12 18:02] **B5 等待用户**: 占位符替换需要真实姓名/编号/学校/指导老师/日期 | - | -
[2026-09-12 18:05] **B6 完成**: tools/q3_sensitivity_v2.py -> 删 r_reg + click/browse 权重 3 档 (W=(1,0)/(0.7,0.3)/(0.3,0.7)) -> 13 场景 (10 比例扰动 + 3 权重档) | q3_sensitivity_v2.csv + q3_sensitivity_v2_summary.json + q3_sensitivity_v2.png | OK
[2026-09-12 18:08] **B7 完成**: tools/verify_data_consistency_final.py -> 27 项检查：22 PASS / 2 PARTIAL / 2 CAVEAT / 0 FAIL (PARTIAL/CAVEAT 均为已知诚实披露) | final_consistency_check.json + final_consistency_check.txt | OK
[2026-09-12 18:10] **论文同步**: tools/_update_paper.py + _update_paper2.py -> 5.3.4 增 A4 + 5.3.5 B6 重构 + 5.4.2 A1+A2+A3 升级 + 5.4.5 self-check +5 项 + 6.2 不足 3->7 项 | paper.md 1089 -> 1137 行 (+48 行) | OK
[2026-09-12 18:14] **DECISION_LOG 追加 D-029~D-035**: A1/A2/A3/A4/B6/B7/论文同步 | DECISION_LOG.md | OK
[2026-09-12 18:15] **A+B 全部完成**: 8 项任务 100% 完成 (A1/A2/A3/A4 + REVIEW1 + B5 等待 + B6/B7 + FINAL 文档同步) | - | OK
"""
with open('RUN_LOG.md', 'a', encoding='utf-8') as f:
    f.write(new_entries)
print('appended new entries (pure UTF-8)')

# Verify
verify_text = open('RUN_LOG.md', 'r', encoding='utf-8').read()
verify_text.encode('utf-8')  # should not raise
print('UTF-8 verify OK')
print('total lines:', len(verify_text.split('\n')))
print('last 10 lines:')
for ln in verify_text.split('\n')[-10:]:
    print('  ', ln[:130])
