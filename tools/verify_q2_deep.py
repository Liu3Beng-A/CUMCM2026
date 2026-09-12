"""
S3补充: 深入验证模板结构 + 关键数学问题
"""
import pandas as pd
import numpy as np

ROOT = 'D:/CUMCM2026Problems'

# 读取模板（不跳过header）
print('=== A. 模板完整内容 ===')
tpl_raw = pd.read_excel(f'{ROOT}/data/raw/attachments/附件2/result2.xlsx', sheet_name=0, header=None)
print(f'模板总行数（含数据行）: {len(tpl_raw)}')
print(f'模板列数: {len(tpl_raw.columns)}')
print('完整内容:')
print(tpl_raw.to_string())

print('\n=== B. 推广单元列唯一值（验证：是单元ID还是关键词序号？）===')
out = pd.read_excel(f'{ROOT}/results/excel/result2.xlsx')
print(f'推广单元列唯一值数: {out["推广单元"].nunique()}')
print(f'推广单元唯一值: {sorted(out["推广单元"].unique())}')
print(f'序号列范围: {out["序号"].min()} ~ {out["序号"].max()}')
print(f'序号列唯一值数: {out["序号"].nunique()} (应接近 2227)')

print('\n=== C. 关键问题：result2.xlsx 是按关键词逐行 还是 按推广单元聚合 ===')
# 如果是按单元聚合，应该只有 12 行
print(f'result2.xlsx 当前行数: {len(out)}')
print(f'如果是按单元聚合，应该是 ~12 行')
print(f'如果是按关键词逐行，应该是 2227 行')
print(f'当前 2227 行 = 按关键词逐行（one-hot 编码）')

print('\n=== D. 极值审计数据一致性 ===')
# 极值词应该是重点词或问题词
audit = pd.read_csv(f'{ROOT}/results/tables/q2_extreme_audit_v2.csv')
print(f'极值词分类分布: {audit["分类"].value_counts().to_dict()}')
# q2_extreme_audit.csv (v1) 应该有同样数据
audit_v1 = pd.read_csv(f'{ROOT}/results/tables/q2_extreme_audit.csv')
print(f'v1极值词分类分布: {audit_v1["分类"].value_counts().to_dict()}')
print(f'v1 行数: {len(audit_v1)}, v2 行数: {len(audit)}')

print('\n=== E. 极值词保留型/削减型 分布检查 ===')
# 理论上：极值词 = 问题词 + 重点词（但不是所有问题词/重点词都是极值）
df = pd.read_pickle(f'{ROOT}/data/processed/q2/keyword_classified.pkl')
print(f'有效词中问题词总数: {(df["分类"]=="问题词").sum()}')
print(f'有效词中重点词总数: {(df["分类"]=="重点词").sum()}')
print(f'极值词中问题词（削减型）: {len(audit[audit["极值类型"]=="削减型极值"])}')
print(f'极值词中重点词（保留型）: {len(audit[audit["极值类型"]=="保留型极值"])}')
print(f'非极值问题词: {(df["分类"]=="问题词").sum() - len(audit[audit["极值类型"]=="削减型极值"])}')
print(f'非极值重点词: {(df["分类"]=="重点词").sum() - len(audit[audit["极值类型"]=="保留型极值"])}')

print('\n=== F. 极值词占比合理性 ===')
total_extreme = len(audit)
total_problem = (df["分类"]=="问题词").sum()
total_key = (df["分类"]=="重点词").sum()
print(f'问题词极值率: {len(audit[audit["极值类型"]=="削减型极值"])}/{total_problem} = {len(audit[audit["极值类型"]=="削减型极值"])/total_problem:.1%}')
print(f'重点词极值率: {len(audit[audit["极值类型"]=="保留型极值"])}/{total_key} = {len(audit[audit["极值类型"]=="保留型极值"])/total_key:.1%}')
