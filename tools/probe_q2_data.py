# -*- coding: utf-8 -*-
"""Q2 数据画像探查脚本（一次性）"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np

df = pd.read_excel('data/raw/attachments/附件1.xlsx', sheet_name='Sheet3')
print('Shape:', df.shape)
print('Columns:', list(df.columns))
print()

cost = pd.to_numeric(df['消费额'], errors='coerce')
clk = pd.to_numeric(df['点击量'], errors='coerce')
view = pd.to_numeric(df['浏览量'], errors='coerce')
br = df['跳出率']
avgtime = df['平均访问时长']

# 数值列分布
for c, s in [('消费额', cost), ('点击量', clk), ('浏览量', view)]:
    print(f'{c}: min={s.min():.2f} q10={s.quantile(0.10):.2f} q25={s.quantile(0.25):.2f} med={s.median():.2f} q75={s.quantile(0.75):.2f} q90={s.quantile(0.90):.2f} max={s.max():.2f} mean={s.mean():.2f} skew={s.skew():.2f}')

print()
print('--- 跳出率 ---')
br_slash = (br.astype(str).str.strip() == '/').sum()
br_num = pd.to_numeric(br, errors='coerce')
print(f'  "/": {br_slash} ({br_slash/len(br)*100:.2f}%)')
print(f'  数值化: {br_num.notna().sum()} ({br_num.notna().sum()/len(br)*100:.2f}%)')
print(f'  数值部分: med={br_num.median():.4f} mean={br_num.mean():.4f} min={br_num.min():.4f} max={br_num.max():.4f}')

print()
print('--- 平均访问时长 ---')
at_slash = (avgtime.astype(str).str.strip() == '/').sum()
print(f'  "/": {at_slash} ({at_slash/len(avgtime)*100:.2f}%)')

print()
print('--- 关键四象限 ---')
print(f'消费=0 AND 点击=0 AND 浏览=0: {((cost==0)&(clk==0)&(view==0)).sum()} ({(cost==0).sum()/len(df)*100:.2f}% 全集)')
print(f'消费>0 AND 点击=0 AND 浏览=0: {((cost>0)&(clk==0)&(view==0)).sum()}')
print(f'消费=0 BUT (点击>0 OR 浏览>0): {((cost==0)&((clk>0)|(view>0))).sum()}')
print(f'消费>0 AND 点击>0 AND 浏览>0: {((cost>0)&(clk>0)&(view>0)).sum()}')

print()
print('--- CPC 分布（消费>0 AND 点击>0）---')
cpc = cost / clk.replace(0, np.nan)
v = cpc.dropna()
print(f'count={len(v)} med={v.median():.3f} mean={v.mean():.3f} q25={v.quantile(0.25):.3f} q75={v.quantile(0.75):.3f} max={v.max():.2f}')

print()
print('--- Top10 高消费 ---')
idx = cost.nlargest(10).index
print(df.loc[idx, ['序号', '关键词', '方案ID', '推广单元ID', '消费额', '点击量', '浏览量', '跳出率']].to_string())

print()
print('--- Top10 高点击 ---')
idx = clk.nlargest(10).index
print(df.loc[idx, ['序号', '关键词', '方案ID', '推广单元ID', '消费额', '点击量', '浏览量', '跳出率']].to_string())

print()
print('--- Top10 高 CPC（消费>0 AND 点击>0）---')
v_df = df[(cost > 0) & (clk > 0)].copy()
v_df['_cpc'] = v_df['消费额'] / v_df['点击量']
top10cpc = v_df.nlargest(10, '_cpc')
print(top10cpc[['序号', '关键词', '方案ID', '推广单元ID', '消费额', '点击量', '浏览量', '跳出率', '_cpc']].to_string())

print()
print('--- 按方案聚合（关键词数 / 总消费 / 总点击）---')
agg = df.groupby('方案ID').agg(
    n_keyword=('序号', 'count'),
    sum_cost=('消费额', 'sum'),
    sum_clk=('点击量', 'sum'),
    sum_view=('浏览量', 'sum')
).round(2)
agg['占比成本'] = (agg['sum_cost'] / agg['sum_cost'].sum() * 100).round(2)
agg['占比点击'] = (agg['sum_clk'] / agg['sum_clk'].sum() * 100).round(2)
print(agg)

print()
print('--- 按推广单元聚合（仅 Top15 关键词数）---')
uagg = df.groupby(['方案ID', '推广单元ID']).size().sort_values(ascending=False).head(15)
print(uagg)
