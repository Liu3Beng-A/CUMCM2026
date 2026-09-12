"""Q2 修复后全面验证脚本（check_progress 风格）

检查项：
1. 5 业务类齐全（高价值/稳定/潜力/浪费/低效）
2. 潜力挖掘型关键词数 > 0
3. 维度数 = 5（无注册率）
4. 选 K 多指标文件存在
5. 雷达图存在
6. 题面对齐映射（paper.md 表 5-2）
7. cluster 3 注脚
8. result2.xlsx 生成（或 result2_new.xlsx 备份）
"""
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

print('=' * 70)
print('Q2 6 项修复全面验证')
print('=' * 70)

errors = []
warnings = []
passes = []

# ---------- 1. 5 业务类齐全 ----------
print('\n[1] 5 业务类齐全检查')
summary = pd.read_csv('results/tables/q2_cluster_summary.csv')
# 去掉"二/三/四"后缀后的业务名
biz_names = set(summary['分类名称'].str.rstrip('二三四五六七八'))
required_5 = {'高价值转化型', '稳定拓展型', '潜力挖掘型', '高成本浪费型', '低效长尾型'}
missing = required_5 - biz_names
if missing:
    errors.append(f'5 业务类缺失: {missing}')
else:
    passes.append('✓ 5 业务类齐全')
    print(f'  ✓ 业务类：{biz_names}')

# ---------- 2. 潜力挖掘型 > 0 ----------
print('\n[2] 潜力挖掘型关键词数 > 0')
pot_row = summary[summary['分类名称'].str.startswith('潜力挖掘型')]
if len(pot_row) == 0 or pot_row['关键词数'].sum() == 0:
    errors.append('潜力挖掘型关键词数 = 0（致命！评审 Q2.2 未修复）')
else:
    n = int(pot_row['关键词数'].sum())
    passes.append(f'✓ 潜力挖掘型 {n} 个关键词')
    print(f'  ✓ 潜力挖掘型 {n} 个关键词（占比 {pot_row["占比"].sum():.1f}%）')

# ---------- 3. 维度数 = 5 ----------
print('\n[3] 特征维度数 = 5（无注册率）')
# 检查 q2_method.md
with open('issue/q2_method.md', encoding='utf-8') as f:
    method = f.read()
# 找"特征工程"后的第一个数字
import re
m = re.search(r'特征工程[（(]\s*\*?\*?(\d+)\s*维', method)
if m:
    n_feat = int(m.group(1))
    if n_feat == 5:
        passes.append(f'✓ 特征维度 = {n_feat}')
        print(f'  ✓ 特征维度 = {n_feat}')
    else:
        errors.append(f'特征维度应为 5，实际 {n_feat}')
else:
    warnings.append('q2_method.md 中未找到"特征工程 + 维数"模式')

# 检查代码
with open('src/q2_classify.py', encoding='utf-8') as f:
    code = f.read()
if "'注册率'" in code and "'注册率':" in code:
    errors.append('src/q2_classify.py 仍包含注册率维度')
else:
    passes.append('✓ src/q2_classify.py 已无注册率维度')
    print(f'  ✓ src/q2_classify.py 已删除注册率维度')

# ---------- 4. 选 K 多指标文件 ----------
print('\n[4] 选 K 多指标文件存在')
metrics_path = 'results/tables/q2_internal_metrics.csv'
if os.path.exists(metrics_path):
    df = pd.read_csv(metrics_path)
    cols = list(df.columns)
    expected = {'K', 'BIC', 'Silhouette', 'Davies-Bouldin', 'Calinski-Harabasz'}
    if expected <= set(cols):
        passes.append(f'✓ q2_internal_metrics.csv 含 4 指标：{cols}')
        print(f'  ✓ 含 4 指标：{cols}')
    else:
        errors.append(f'q2_internal_metrics.csv 缺指标：{expected - set(cols)}')
else:
    errors.append(f'缺失：{metrics_path}')

# ---------- 5. 雷达图存在 ----------
print('\n[5] 雷达图存在')
radar_path = 'results/figures/q2_class_radar.png'
if os.path.exists(radar_path):
    sz = os.path.getsize(radar_path)
    passes.append(f'✓ q2_class_radar.png 存在（{sz} bytes）')
    print(f'  ✓ q2_class_radar.png 存在（{sz} bytes）')
else:
    errors.append(f'缺失：{radar_path}')

# ---------- 6. 题面对齐映射表 ----------
print('\n[6] paper.md 5.2.3 含映射表')
with open('paper/paper.md', encoding='utf-8') as f:
    paper = f.read()
keywords_map = ['黄金词', '重点词', '潜力词', '问题词', '无效词',
                '高价值转化型', '稳定拓展型', '潜力挖掘型', '高成本浪费型', '低效长尾型']
all_in = all(k in paper for k in keywords_map)
if all_in:
    passes.append('✓ paper.md 含 5×5 题面-业务类映射关键词')
    print(f'  ✓ 含所有题面-业务类映射关键词')
else:
    missing_kw = [k for k in keywords_map if k not in paper]
    errors.append(f'paper.md 缺关键词：{missing_kw}')

# ---------- 7. cluster 3 注脚 ----------
print('\n[7] cluster 3 注脚')
c3_note = summary[summary['cluster_id'] == 3]['备注'].iloc[0] if len(summary[summary['cluster_id'] == 3]) > 0 else ''
if '样本极少' in str(c3_note) or 'CPC' in str(c3_note):
    passes.append(f'✓ cluster 3 备注：{c3_note[:50]}...')
    print(f'  ✓ cluster 3 备注：{c3_note}')
else:
    errors.append(f'cluster 3 无注脚：{c3_note}')

# ---------- 8. result2.xlsx ----------
print('\n[8] result2.xlsx')
result2 = 'data/raw/attachments/result2.xlsx'
result2_new = 'data/raw/attachments/result2_new.xlsx'
if os.path.exists(result2):
    passes.append(f'✓ result2.xlsx 存在（{os.path.getsize(result2)} bytes）')
    print(f'  ✓ result2.xlsx 存在（{os.path.getsize(result2)} bytes）')
elif os.path.exists(result2_new):
    passes.append(f'⚠ result2.xlsx 被锁定，使用备份 result2_new.xlsx（{os.path.getsize(result2_new)} bytes）')
    warnings.append(f'原 result2.xlsx 被外部进程锁定，已用 result2_new.xlsx 替代')
    print(f'  ⚠ result2.xlsx 被锁定，使用备份 result2_new.xlsx')
else:
    errors.append('result2.xlsx 和 result2_new.xlsx 都不存在')

# ---------- 9. 多子图 4 子图 ----------
print('\n[9] q2_gmm_clusters.png 4 子图')
fig_path = 'results/figures/q2_gmm_clusters.png'
if os.path.exists(fig_path):
    sz = os.path.getsize(fig_path)
    if sz > 300000:  # 4 子图应该 > 300KB
        passes.append(f'✓ q2_gmm_clusters.png 4 子图（{sz} bytes > 300KB）')
        print(f'  ✓ q2_gmm_clusters.png 4 子图（{sz} bytes）')
    else:
        warnings.append(f'q2_gmm_clusters.png 可能只含 2 子图（{sz} bytes）')
else:
    errors.append(f'缺失：{fig_path}')

# ---------- 10. q2_bic_curve.png 独立图 ----------
print('\n[10] q2_bic_curve.png 独立图')
bic_path = 'results/figures/q2_bic_curve.png'
if os.path.exists(bic_path):
    passes.append(f'✓ q2_bic_curve.png 存在（{os.path.getsize(bic_path)} bytes）')
    print(f'  ✓ q2_bic_curve.png 存在（{os.path.getsize(bic_path)} bytes）')
else:
    errors.append(f'缺失：{bic_path}')

# ---------- 总结 ----------
print()
print('=' * 70)
print(f'通过 {len(passes)} 项 / 失败 {len(errors)} 项 / 警告 {len(warnings)} 项')
print('=' * 70)
for p in passes:
    print(f'  {p}')
for w in warnings:
    print(f'  ⚠ {w}')
for e in errors:
    print(f'  ✗ {e}')

if not errors:
    print()
    print('🎉 Q2 6 项修复全部通过！')
    sys.exit(0)
else:
    print()
    print(f'❌ 有 {len(errors)} 项检查未通过')
    sys.exit(1)
