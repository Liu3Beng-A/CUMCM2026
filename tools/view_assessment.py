import json
with open(r'd:\CUMCM2026Problems\results\tables\comprehensive_assessment_20260912.json','r',encoding='utf-8') as f:
    d = json.load(f)
lines = []
lines.append('=== A. 综合评分 ===')
for k,v in d['scores'].items():
    lines.append('  ' + str(k) + ': ' + str(v))
lines.append('')
lines.append('=== B. 改进清单 (' + str(len(d['improvements'])) + ' 项) ===')
for it in d['improvements']:
    lines.append('[' + it['id'] + '] ' + it['priority'])
    lines.append('  问题: ' + it['issue'])
    lines.append('  当前: ' + it['current_state'])
    lines.append('  工作量: ' + it['effort'])
    lines.append('')
lines.append('=== C. 待跑数据 (' + str(len(d['pending_data_runs'])) + ' 项) ===')
for it in d['pending_data_runs']:
    lines.append('[' + it['id'] + '] ' + it['task'])
    lines.append('  目的: ' + it['purpose'])
    lines.append('  紧急度: ' + it['urgency'] + ' | 时间: ' + it['estimated_time'])
    lines.append('  产物:')
    for dv in it['deliverables']:
        lines.append('    - ' + dv)
    lines.append('')
out = r'd:\CUMCM2026Problems\results\tables\comprehensive_assessment_view.txt'
with open(out,'w',encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('written', len(lines), 'lines')
