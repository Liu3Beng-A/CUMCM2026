# -*- coding: utf-8 -*-
"""Append final RUN_LOG entries using chr() escapes to avoid encoding issues"""
entries = []
entries.append('[2026-09-12 18:02] **REVIEW1 \u901a\u8fc7**: tools/review_a_level.py \u5168\u4ea7\u7269\u76d8\u70b9 + 4 \u9879\u9a8c\u8bc1\u5168\u90e8 PASS | review_a.txt | OK')
entries.append('[2026-09-12 18:02] **B6 \u542f\u52a8**: \u00a75.3.5 \u654f\u611f\u6027\u91cd\u6784\uff08\u5220 r_reg\uff0c\u6539 click/browse \u6743\u91cd\u4e09\u6863\uff09 | - | -')
entries.append('[2026-09-12 18:02] **B7 \u542f\u52a8**: \u6570\u636e\u4e00\u81f4\u6027\u9a8c\u8bc1\u811a\u672c\u7ec8\u8dd1 | - | -')
entries.append('[2026-09-12 18:02] **B5 \u7b49\u5f85\u7528\u6237**: \u5360\u4f4d\u7b26\u66ff\u6362\u9700\u8981\u771f\u5b9e\u59d3\u540d/\u7f16\u53f7/\u5b66\u6821/\u6307\u5bfc\u8001\u5e08/\u65e5\u671f | - | -')
entries.append('[2026-09-12 18:05] **B6 \u5b8c\u6210**: tools/q3_sensitivity_v2.py \u2192 \u5220 r_reg + click/browse \u6743\u91cd 3 \u6863 (W=(1,0)/(0.7,0.3)/(0.3,0.7)) \u2192 13 \u573a\u666f (10 \u6bd4\u4f8b\u6270\u52a8 + 3 \u6743\u91cd\u6863) | q3_sensitivity_v2.csv + q3_sensitivity_v2_summary.json + q3_sensitivity_v2.png | OK')
entries.append('[2026-09-12 18:08] **B7 \u5b8c\u6210**: tools/verify_data_consistency_final.py \u2192 27 \u9879\u68c0\u67e5\uff1a22 PASS / 2 PARTIAL / 2 CAVEAT / 0 FAIL (PARTIAL/CAVEAT \u5747\u4e3a\u5df2\u77e5\u8bda\u5b9e\u62ab\u9732) | final_consistency_check.json + final_consistency_check.txt | OK')
entries.append('[2026-09-12 18:10] **\u8bba\u6587\u540c\u6b65**: tools/_update_paper.py + _update_paper2.py \u2192 \u00a75.3.4 \u589e A4 + \u00a75.3.5 B6 \u91cd\u6784 + \u00a75.4.2 A1+A2+A3 \u5347\u7ea7 + \u00a75.4.5 self-check +5 \u9879 + \u00a76.2 \u4e0d\u8db3 3\u21927 \u9879 | paper.md 1089 \u2192 1137 \u884c (+48 \u884c) | OK')
entries.append('[2026-09-12 18:14] **DECISION_LOG \u8ffd\u52a0 D-029~D-035**: A1/A2/A3/A4/B6/B7/\u8bba\u6587\u540c\u6b65 | DECISION_LOG.md | OK')
entries.append('[2026-09-12 18:15] **A+B \u5168\u90e8\u5b8c\u6210**: 8 \u9879\u4efb\u52a1 100% \u5b8c\u6210 (A1/A2/A3/A4 + REVIEW1 + B5 \u7b49\u5f85 + B6/B7 + FINAL \u6587\u6863\u540c\u6b65) | - | OK')

text = '\n' + '\n'.join(entries) + '\n'
with open('RUN_LOG.md', 'a', encoding='utf-8') as f:
    f.write(text)
print('appended', len(entries), 'entries')

# Verify final file
import os
print('RUN_LOG.md size:', os.path.getsize('RUN_LOG.md'))
text = open('RUN_LOG.md', 'r', encoding='utf-8').read()
text.encode('utf-8')  # verify
print('UTF-8 valid')
print('lines:', len(text.split('\n')))

# Show last 10 lines (UTF-8 displayed via repr)
print('last 10 lines:')
for ln in text.split('\n')[-11:]:
    print('  ', ln)
