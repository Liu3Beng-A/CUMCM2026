"""Q3Q4 数据探测 PoC
按 mdc 强制流程"先读数据再写代码"，确认 Sheet1/2/3 的时间粒度/可用列/缺失情况。
"""
import pandas as pd
import numpy as np
import json

ROOT = 'D:/CUMCM2026Problems'
ATT = f'{ROOT}/data/raw/attachments/附件1.xlsx'

SHEET_NAMES = pd.ExcelFile(ATT).sheet_names
print('Sheets:', SHEET_NAMES)

print('=' * 70)
print('PoC · 读取附件 1 三表 · 原始列名 + 时间粒度探测')
print('=' * 70)

# ============ Sheet1 ============
print('\n' + '=' * 70)
print('【Sheet1】方案日表')
print('=' * 70)
s1 = pd.read_excel(ATT, sheet_name=SHEET_NAMES[0])
print(f'shape = {s1.shape}')
print(f'列名 = {list(s1.columns)}')
print(f'日期范围 = {s1["日期"].min()} ~ {s1["日期"].max()}')
print(f'唯一日期数 = {s1["日期"].nunique()} (期望 365)')
print(f'唯一方案ID = {s1["方案ID"].nunique()}')
print(f'唯一推广单元 = {s1["推广单元ID"].nunique()}')
print(f'每天 (日期×方案×推广单元) 行数 = {len(s1) / s1["日期"].nunique():.1f}')

# 上方位相关列
print('\n上方位相关列（用于"预期展位"映射）：')
for col in ['上方位展现量', '上方位首位展现量', '上方位点击量', '上方位消费额']:
    if col in s1.columns:
        s = s1[col]
        print(f'  {col:30s} sum={s.sum():>15,.0f}  mean={s.mean():>10,.2f}  null={s.isnull().sum()}')

dates_16 = s1[s1['日期'].between('2025-02-01', '2025-02-08') | s1['日期'].between('2025-08-01', '2025-08-08')]
print(f'\n2025-02-01~08 + 08-01~08 (16天) Sheet1 行数 = {len(dates_16)}')
print(f'  唯一 (日期×推广单元) 组合 = {dates_16.groupby(["日期","推广单元ID"]).ngroups}')
print(f'  推广单元总消费 = {dates_16["消费额"].sum():,.2f}')

# ============ Sheet2 ============
print('\n' + '=' * 70)
print('【Sheet2】新注册表')
print('=' * 70)
s2 = pd.read_excel(ATT, sheet_name=SHEET_NAMES[1])
s2.columns = [c.strip() for c in s2.columns]
print(f'shape = {s2.shape}')
print(f'列名 (strip 后) = {list(s2.columns)}')
print(f'日期范围 = {s2["日期"].min()} ~ {s2["日期"].max()}')
print(f'新注册数 sum = {s2["新注册数"].sum():,}')
print(f'日均注册 = {s2["新注册数"].mean():.2f}')

reg_16 = s2[s2['日期'].between('2025-02-01', '2025-02-08') | s2['日期'].between('2025-08-01', '2025-08-08')]
print(f'\n16 天总注册 = {reg_16["新注册数"].sum():,}')
print(f'  日均注册 = {reg_16["新注册数"].mean():.2f}')

# ============ Sheet3 ============
print('\n' + '=' * 70)
print('【Sheet3】关键词表 · 关键问题：浏览量是日级还是累计？')
print('=' * 70)
s3 = pd.read_excel(ATT, sheet_name=SHEET_NAMES[2])
print(f'shape = {s3.shape}')
print(f'列名 = {list(s3.columns)}')
print(f'唯一方案ID = {s3["方案ID"].nunique()}')
print(f'唯一推广单元 = {s3["推广单元ID"].nunique()}')

# 关键判定：浏览量 vs Sheet1 总览量/消费额
total_cost_s3 = s3['消费额'].sum()
total_click_s3 = s3['点击量'].sum()
total_browse_s3 = s3['浏览量'].sum()

total_cost_s1 = s1['消费额'].sum()
total_click_s1 = s1['点击量'].sum()
total_imp_s1 = s1['展现量'].sum()

print(f'\n【关键判定】Sheet3 累计 vs Sheet1 365 天合计：')
print(f'  消费额  Sheet3={total_cost_s3:>15,.2f}   Sheet1={total_cost_s1:>15,.2f}   比={total_cost_s3/total_cost_s1:.4f}')
print(f'  点击量  Sheet3={total_click_s3:>15,.0f}   Sheet1={total_click_s1:>15,.0f}   比={total_click_s3/total_click_s1:.4f}')
print(f'  浏览量  Sheet3={total_browse_s3:>15,.0f}   Sheet1无此列')
print(f'  展现量  Sheet3无此列                 Sheet1={total_imp_s1:>15,.0f}')

if abs(total_cost_s3 - total_cost_s1) / total_cost_s1 < 0.001:
    print(f'\n  → 结论：Sheet3 消费额 ≈ Sheet1 全年合计（差<0.1%），Sheet3 是"关键词级全年累计"口径')

# 跳出率/访问时长 null
print(f'\n【Sheet3 跳出率/访问时长】空值与特殊值统计：')
for col in ['跳出率', '平均访问时长']:
    if col in s3.columns:
        n_null = s3[col].isnull().sum()
        n_slash = (s3[col].astype(str) == '/').sum()
        n_total = len(s3)
        print(f'  {col:15s} null={n_null:4d}/{n_total} ({n_null/n_total:.2%})  "/"={n_slash:4d} ({n_slash/n_total:.2%})')

print(f'\n【Sheet3 单关键词年均统计】')
print(f'  平均消费额 = {s3["消费额"].mean():.2f}')
print(f'  平均点击量 = {s3["点击量"].mean():.2f}')
print(f'  平均浏览量 = {s3["浏览量"].mean():.2f}')
print(f'  CPC(消费/点击) 全体均值 = {(s3["消费额"] / s3["点击量"].replace(0, np.nan)).mean():.4f}')
print(f'  CPC(消费/点击) 全体中位数 = {(s3["消费额"] / s3["点击量"].replace(0, np.nan)).median():.4f}')
print(f'  0 点击词数 = {(s3["点击量"] == 0).sum()}')
print(f'  0 消费词数 = {(s3["消费额"] == 0).sum()}')

# ============ 关键词级 CPC CV ============
print('\n' + '=' * 70)
print('【Q4 因子】关键词级 CPC CV 可估性（Sheet3 全年累计，CV 退化）')
print('=' * 70)
s3_valid = s3[(s3['点击量'] > 0) & (s3['消费额'] > 0)].copy()
s3_valid['cpc'] = s3_valid['消费额'] / s3_valid['点击量']
print(f'有效词数（有消费有点击） = {len(s3_valid)} / {len(s3)} = {len(s3_valid)/len(s3):.2%}')
print(f'  CPC mean = {s3_valid["cpc"].mean():.4f}')
print(f'  CPC std  = {s3_valid["cpc"].std():.4f}')
print(f'  CPC CV   = {s3_valid["cpc"].std() / s3_valid["cpc"].mean():.4f} （Sheet3 是全年累计 → CV 是"跨词"变异，不是"跨日"变异）')
print(f'\n→ 关键结论：Sheet3 是"全年累计"，CPC CV 反映的是"不同关键词之间的变异"，')
print(f'  无法直接用作"同一关键词每天的不确定性"（Q4 6 因子需要的是后者）')
print(f'  → Q4 必须改用 Sheet1 推广单元日级 30 天滚动 CV，或在文档中说明"用推广单元级变异代理"')

# ============ Sheet1 30 天滚动 CV（推广单元日级）============
print('\n' + '=' * 70)
print('【Q4 因子】Sheet1 推广单元日级 30 天滚动 CV（真实"跨日变异"）')
print('=' * 70)
s1_sorted = s1.sort_values(['推广单元ID', '日期']).copy()
cv_results = []
for unit_id, grp in s1_sorted.groupby('推广单元ID'):
    grp = grp.sort_values('日期')
    if len(grp) < 30:
        continue
    rolling_cv = grp['消费额'].rolling(30).std() / grp['消费额'].rolling(30).mean()
    cv_results.append({
        'unit': unit_id,
        'cost_cv_median': float(rolling_cv.median()),
        'cost_cv_mean': float(rolling_cv.mean()),
        'click_cv_median': float((grp['点击量'].rolling(30).std() / grp['点击量'].rolling(30).mean()).median()),
        'imp_cv_median': float((grp['展现量'].rolling(30).std() / grp['展现量'].rolling(30).mean()).median()),
    })
print('推广单元 30 天滚动 CV 中位数（"跨日变异"）：')
for r in cv_results:
    print(f'  unit={r["unit"]:>10}  消费CV={r["cost_cv_median"]:.3f}  点击CV={r["click_cv_median"]:.3f}  展现CV={r["imp_cv_median"]:.3f}')

# ============ 注册分配 ============
print('\n' + '=' * 70)
print('【注册分配】Sheet2 日级 → 关键词级（需用 Sheet1 消费额占比分配）')
print('=' * 70)
s1_16 = s1[s1['日期'].between('2025-02-01', '2025-02-08') | s1['日期'].between('2025-08-01', '2025-08-08')].copy()

daily_unit_cost = s1_16.groupby(['日期', '推广单元ID'])['消费额'].sum().reset_index()
print(f'16 天 推广单元-日 记录数 = {len(daily_unit_cost)}')
print(f'  其中消费=0 的记录 = {(daily_unit_cost["消费额"] == 0).sum()}')

unit_total = s3.groupby('推广单元ID')['消费额'].sum().reset_index()
unit_total.columns = ['推广单元ID', 'unit_total_cost_2025']
print(f'\nSheet3 中有消费的推广单元数 = {(unit_total["unit_total_cost_2025"] > 0).sum()} / {len(unit_total)}')
print(f'  Sheet3 消费合计 = {unit_total["unit_total_cost_2025"].sum():,.2f}')
print(f'  Sheet1 消费合计 = {s1["消费额"].sum():,.2f}')

# ============ 16 天预算 ============
print('\n' + '=' * 70)
print('【MILP 约束】16 天预算上限')
print('=' * 70)
budget_16 = s1_16['消费额'].sum()
print(f'2025-02-01~02-08 + 2025-08-01~08-08 16 天消费 = {budget_16:,.2f} 元')
print(f'  日均 = {budget_16/16:,.2f} 元')
print(f'  推广单元-日均 = {budget_16/16/12:,.2f} 元')
unit_budget = s1_16.groupby('推广单元ID')['消费额'].mean()
print(f'  各推广单元日均消费 max = {unit_budget.max():.2f}, min = {unit_budget.min():.2f}')

# 入选项预估
n_gold = 431
n_focus = 238
n_potential = 240
n_total_select = n_gold + n_focus + n_potential
print(f'\n  入选项 = 黄金 + 重点 + 潜力 = {n_total_select} 词 / 2227 = {n_total_select/2227:.2%}')
print(f'  16 天 × 12 推广单元 × 入选项 = {16*12*n_total_select:,} 行 (上界)')
print(f'  假设平均每天每单元选 30 词 → 实际行数 ≈ {16*12*30:,} 行 (5K-20K 范围 ✓)')

# ============ 汇总 ============
poC_result = {
    'sheet1_rows': int(len(s1)),
    'sheet1_dates': int(s1['日期'].nunique()),
    'sheet1_plans': int(s1['方案ID'].nunique()),
    'sheet1_units': int(s1['推广单元ID'].nunique()),
    'sheet2_rows': int(len(s2)),
    'sheet2_total_reg': int(s2['新注册数'].sum()),
    'sheet2_reg_16': int(reg_16['新注册数'].sum()),
    'sheet3_rows': int(len(s3)),
    'sheet3_units': int(s3['推广单元ID'].nunique()),
    'sheet3_total_cost': float(total_cost_s3),
    'sheet1_total_cost': float(total_cost_s1),
    'sheet3_total_browse': int(total_browse_s3),
    'budget_16_total': float(budget_16),
    'budget_16_per_unit_per_day': float(budget_16 / 16 / 12),
    'valid_kw_with_clicks': int(len(s3_valid)),
    'cpc_cv_across_kw': float(s3_valid['cpc'].std() / s3_valid['cpc'].mean()),
}
with open(f'{ROOT}/tools/poc_summary.json', 'w', encoding='utf-8') as f:
    json.dump(poC_result, f, ensure_ascii=False, indent=2)
print(f'\n汇总已存：tools/poc_summary.json')
