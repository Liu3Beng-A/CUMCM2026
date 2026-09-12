"""S1 备份所有错位产物到 snapshot 目录"""
import os, shutil

snap = 'results/snapshots/hallucination_v1_20260912'
os.makedirs(snap, exist_ok=True)

files_to_backup = [
    'src/q2_classify.py',
    'src/q3_optimizer.py',
    'src/q4_uncertainty.py',
    'results/tables/q2_keyword_classification.csv',
    'results/tables/q2_cluster_summary.csv',
    'results/tables/q2_internal_metrics.csv',
    'results/tables/q3_daily_strategy.csv',
    'results/tables/q3_plan_summary.csv',
    'results/tables/q3_pareto_front.csv',
    'results/tables/q4_daily_strategy.csv',
    'results/tables/q4_strategy_comparison.csv',
    'results/figures/q2_gmm_clusters.png',
    'results/figures/q2_bic_curve.png',
    'results/figures/q2_class_radar.png',
    'results/figures/q3_strategy.png',
    'results/figures/q3_pareto.png',
    'results/figures/q4_strategy_comparison.png',
    'data/raw/attachments/result2.xlsx',
    'data/raw/attachments/result2_new.xlsx',
    'data/raw/attachments/result3.xlsx',
    'data/raw/attachments/result4.xlsx',
    'issue/q2_method.md',
    'issue/q3_method.md',
    'issue/q4_method.md',
    'paper/paper.md',
    'WORK_STATE.md',
    'RUN_LOG.md',
    'DECISION_LOG.md',
    'tools/check_q2.py',
]

print('=' * 70)
print(f'S1 备份错位产物 -> {snap}/')
print('=' * 70)

ok, missing = 0, []
for f in files_to_backup:
    if not os.path.exists(f):
        missing.append(f)
        continue
    dst = os.path.join(snap, f)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(f, dst)
    sz = os.path.getsize(dst)
    print(f'  OK {f:55s}  {sz:>10,} bytes')
    ok += 1

print()
print(f'备份成功 {ok} / 失败 {len(missing)}')
if missing:
    print('缺失（不需要备份）:', missing)

# 快照说明
readme_path = os.path.join(snap, 'README.md')
with open(readme_path, 'w', encoding='utf-8') as f:
    f.write('# 事故快照：hallucination_v1_20260912\n\n')
    f.write('## 时间\n2026-09-12 13:20\n\n')
    f.write('## 事故\n之前 agent 在 Q2/Q3/Q4 实现中严重错位题面理解：\n')
    f.write('- 自创 GMM+BIC+多指标+雷达图，忽略附件 2 result 模板的硬性格式要求\n')
    f.write('- 决策变量粒度错（方案x天，应为关键词x天 或 推广单元x关键词x天）\n')
    f.write('- 时间范围错（365 天全年，应为 16 天 或 7 天）\n')
    f.write('- 预测指标漏（只算注册，应为 4-6 个）\n\n')
    f.write(f'## 此目录用途\n- 保留 {ok} 个错位产物作为事故证据（不可删除）\n')
    f.write('- Q2/Q3/Q4 重做时禁止参考这里的代码（避免再次陷入幻觉）\n')
    f.write('- 仅用于对比"幻觉版"vs"真实题面版"\n\n')
    f.write('## 注意\n- 附件 2 模板 (`data/raw/attachments/附件2/result2/3/4.xlsx`) 未在此目录中——它们是题面提供的模板，必须保留\n')
print(f'\n[save] {readme_path}')
