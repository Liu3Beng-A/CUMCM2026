import pandas as pd
import numpy as np

# 验证 result3.xlsx
r3 = pd.read_excel('results/excel/result3.xlsx')
print('=== result3.xlsx ===')
print('Shape:', r3.shape)
print('Columns:', list(r3.columns))
print('总投入:', round(r3['投入金额'].sum(), 2))
print('预期展位总和:', r3['预期展位'].sum())
print('预期点击量总和:', r3['预期点击量'].sum())
print('预期浏览量总和:', r3['预期浏览量'].sum())
print('预期注册量总和:', r3['预期注册量'].sum())
print('日期范围:', r3['日期'].min(), '~', r3['日期'].max())
print('激活行数:', len(r3))
print()

# 验证 result4.xlsx
r4 = pd.read_excel('results/excel/result4.xlsx')
print('=== result4.xlsx ===')
print('Shape:', r4.shape)
print('Columns:', list(r4.columns))
print('总投入:', round(r4['投入金额'].sum(), 2))
print('预期展位总和:', r4['预期展位'].sum())
print('预期点击量总和:', r4['预期点击量'].sum())
print('预期浏览量总和:', r4['预期浏览量'].sum())
print('预期注册量总和:', r4['预期注册量'].sum())
print('日期范围:', r4['日期'].min(), '~', r4['日期'].max())
print('激活行数:', len(r4))
print()

# Sheet2 同期实际注册
df2 = pd.read_excel('data/raw/attachments/附件1.xlsx', sheet_name='Sheet2')
df2.columns = df2.columns.str.strip()
df2['日期'] = pd.to_datetime(df2['日期'])
q3_actual_reg = df2[(df2['日期'] >= '2025-02-01') & (df2['日期'] <= '2025-02-08')]['新注册数'].sum() + df2[(df2['日期'] >= '2025-08-01') & (df2['日期'] <= '2025-08-08')]['新注册数'].sum()
q4_actual_reg = df2[(df2['日期'] >= '2025-09-11') & (df2['日期'] <= '2025-09-17')]['新注册数'].sum()
print('=== 同期实际注册 (Sheet2) ===')
print('Q3 实际注册 (02-01~08 + 08-01~08):', q3_actual_reg)
print('Q4 实际注册 (09-11~17):', q4_actual_reg)
print()

# Sheet1 同期消费
df1 = pd.read_excel('data/raw/attachments/附件1.xlsx', sheet_name='Sheet1')
df1['日期'] = pd.to_datetime(df1['日期'])
q3_actual_cost = df1[(df1['日期'] >= '2025-02-01') & (df1['日期'] <= '2025-02-08')]['消费额'].sum() + df1[(df1['日期'] >= '2025-08-01') & (df1['日期'] <= '2025-08-08')]['消费额'].sum()
q4_actual_cost = df1[(df1['日期'] >= '2025-09-11') & (df1['日期'] <= '2025-09-17')]['消费额'].sum()
q4_actual_clicks = df1[(df1['日期'] >= '2025-09-11') & (df1['日期'] <= '2025-09-17')]['点击量'].sum()
q4_actual_topimp = df1[(df1['日期'] >= '2025-09-11') & (df1['日期'] <= '2025-09-17')]['上方位展现量'].sum()
print('=== 同期实际消费 (Sheet1) ===')
print('Q3 实际消费 (02-01~08 + 08-01~08):', q3_actual_cost)
print('Q4 实际消费 (09-11~17):', q4_actual_cost)
print('Q4 同期实际点击:', q4_actual_clicks)
print('Q4 同期实际上方位展现:', q4_actual_topimp)
print()

# Q3 同期实际点击、上方位
q3_actual_clicks = df1[(df1['日期'] >= '2025-02-01') & (df1['日期'] <= '2025-02-08')]['点击量'].sum() + df1[(df1['日期'] >= '2025-08-01') & (df1['日期'] <= '2025-08-08')]['点击量'].sum()
q3_actual_topimp = df1[(df1['日期'] >= '2025-02-01') & (df1['日期'] <= '2025-02-08')]['上方位展现量'].sum() + df1[(df1['日期'] >= '2025-08-01') & (df1['日期'] <= '2025-08-08')]['上方位展现量'].sum()
print('Q3 同期实际点击:', q3_actual_clicks)
print('Q3 同期实际上方位展现:', q3_actual_topimp)

# 计算单位预算注册转化率
print()
print('=== 单位预算注册转化率 ===')
q3_actual_eff = q3_actual_reg / q3_actual_cost
q3_pred_eff = r3['预期注册量'].sum() / r3['投入金额'].sum()
print(f'Q3 实际: {q3_actual_reg} / {q3_actual_cost:.2f} = {q3_actual_eff:.4f} 人/元')
print(f'Q3 预测: {r3["预期注册量"].sum()} / {r3["投入金额"].sum():.2f} = {q3_pred_eff:.4f} 人/元')
print(f'提升: {q3_pred_eff/q3_actual_eff:.2f}x ({(q3_pred_eff/q3_actual_eff-1)*100:.1f}%)')

q4_actual_eff = q4_actual_reg / q4_actual_cost
q4_pred_eff = r4['预期注册量'].sum() / r4['投入金额'].sum()
print(f'Q4 实际: {q4_actual_reg} / {q4_actual_cost:.2f} = {q4_actual_eff:.4f} 人/元')
print(f'Q4 预测: {r4["预期注册量"].sum()} / {r4["投入金额"].sum():.2f} = {q4_pred_eff:.4f} 人/元')
print(f'提升: {q4_pred_eff/q4_actual_eff:.2f}x ({(q4_pred_eff/q4_actual_eff-1)*100:.1f}%)')