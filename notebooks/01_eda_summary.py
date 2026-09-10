import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
import pandas as pd
import numpy as np

root = r'D:\CUMCM2026Problems'
att_dir = os.path.join(root, '附件')
att1 = os.path.join(att_dir, '附件1.xlsx')

# 读取各sheet
df1 = pd.read_excel(att1, sheet_name='Sheet1')
df2 = pd.read_excel(att1, sheet_name='Sheet2')
df3 = pd.read_excel(att1, sheet_name='Sheet3')

print('=== Sheet1: 投放方案与消费记录 ===')
print(f'总记录数: {len(df1)}')
print(f'日期范围: {df1["日期"].min()} 到 {df1["日期"].max()}')
print(f'方案ID数量: {df1["方案ID"].nunique()}')
print(f'推广单元ID数量: {df1["推广单元ID"].nunique()}')
print(f'总展现量: {df1["展现量"].sum():,}')
print(f'总点击量: {df1["点击量"].sum():,}')
print(f'总消费额: {df1["消费额"].sum():,.2f} 元')
print(f'上方位消费额: {df1["上方位消费额"].sum():,.2f} 元')

print('\n=== Sheet2: 新注册用户数 ===')
print(f'总天数: {len(df2)}')
print(f'总新注册数: {df2["新注册数 "].sum():,} 人')
print(f'日均注册: {df2["新注册数 "].mean():.1f}')

print('\n=== Sheet3: 关键词统计数据 ===')
print(f'总关键词数: {len(df3)}')
print(f'有消费关键词数: {(df3["消费额"] > 0).sum()}')
print(f'无消费关键词数: {(df3["消费额"] == 0).sum()}')
print(f'总消费: {df3["消费额"].sum():,.2f}')
print(f'总点击量: {df3["点击量"].sum():,}')
print(f'总浏览量: {df3["浏览量"].sum():,}')
print(f'方案数: {df3["方案ID"].nunique()}')
print(f'推广单元数: {df3["推广单元ID"].nunique()}')

# 关键词效益分析
df3_active = df3[df3['消费额'] > 0].copy()
df3_active['点击率'] = df3_active['点击量'] / df3_active['浏览量'].replace(0, 1)
df3_active['单次点击成本'] = df3_active['消费额'] / df3_active['点击量'].replace(0, 1)

print(f'\n有消费的关键词: {len(df3_active)} 个')
print(f'平均单次点击成本: {df3_active["单次点击成本"].mean():.2f} 元')
print(f'平均跳出率: {df3_active["跳出率"].mean():.4f}')

# 方案维度
print('\n=== 各方案汇总 ===')
plan_summary = df1.groupby('方案ID').agg(
    展现量=('展现量', 'sum'),
    点击量=('点击量', 'sum'),
    消费额=('消费额', 'sum'),
    上方位消费额=('上方位消费额', 'sum'),
).reset_index()
print(plan_summary.to_string())

# 月度趋势
df1['月份'] = pd.to_datetime(df1['日期']).dt.to_period('M')
monthly = df1.groupby('月份').agg(
    消费额=('消费额', 'sum'),
    点击量=('点击量', 'sum'),
    展现量=('展现量', 'sum'),
).reset_index()
print('\n=== 月度趋势 ===')
print(monthly.to_string())
