"""Q2 补充审计：跨方案对比 + 异常词 + 极值分析"""
import pandas as pd
import numpy as np

df = pd.read_pickle('data/processed/q2/keyword_classified.pkl')

print('=' * 60)
print('Q2 数据体检（4 项）')
print('=' * 60)

# 1. 5 类 vs 方案 交叉表
print('\n=== 1. 5 类 x 方案 交叉表（占比%）===')
ct = pd.crosstab(df['方案ID'], df['分类'], normalize='index') * 100
print(ct.round(1).to_string())

# 2. 异常词
print('\n=== 2. 异常词（消费=0 但点击>0）===')
abnormal = df[(df['成本'] == 0) & ((df['点击'] > 0) | (df['浏览'] > 0))]
print(f'数量：{len(abnormal)}')
if len(abnormal) > 0:
    print(abnormal[['序号','关键词','方案ID','推广单元ID','成本','点击','浏览','跳出率_数值']].to_string())

# 3. 12 推广单元 5 类分布
print('\n=== 3. 12 推广单元 5 类分布 ===')
df_unit = pd.read_csv('results/tables/q2_unit_cluster_summary.csv')
df_unit['有效词率%'] = ((df_unit['黄金词'] + df_unit['重点词'] + df_unit['潜力词'] + df_unit['问题词']) /
                       df_unit['关键词总数'] * 100).round(1)
df_unit['问题词率%'] = (df_unit['问题词'] / df_unit['关键词总数'] * 100).round(1)
df_unit['平均CPC'] = df_unit['平均CPC'].round(2)
print(df_unit[['方案ID','推广单元','关键词总数','黄金词','重点词','潜力词','问题词','无效词',
               '总消费','平均CPC','有效词率%','问题词率%']].to_string())

# 4. 极值审计
print('\n=== 4. 极值审计分析 ===')
audit = pd.read_csv('results/tables/q2_extreme_audit.csv')
print('\nTop 5 极值词：')
print(audit.head(5)[['序号','关键词','方案ID','分类','消费','点击量','CPC','风险评级','触发规则']].to_string())

print(f'\n极值审计 105 词统计：')
print(f'  总消费 = {audit["消费"].sum():,.0f} 元')
print(f'  总点击 = {audit["点击量"].sum():,.0f}')
print(f'  CPC 均值 = {(audit["消费"] / np.maximum(audit["点击量"], 1)).mean():.2f} 元')
print(f'  占全年消费比例 = {audit["消费"].sum() / 1425900 * 100:.1f}%')
print(f'\n风险评级分布：')
print(audit['风险评级'].value_counts().to_string())
print(f'\n触发规则分布：')
print(audit['触发规则'].value_counts().to_string())
print(f'\n5 类在极值审计中的分布：')
print(audit['分类'].value_counts().to_string())
