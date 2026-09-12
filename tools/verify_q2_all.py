"""
S3: Verify all Q2 artifacts comprehensively
"""
import pandas as pd
import numpy as np
import json

ROOT = 'D:/CUMCM2026Problems'

# ========== 1. result2 output verification ==========
print('=== 1. result2.xlsx 验证 ===')
out = pd.read_excel(f'{ROOT}/results/excel/result2.xlsx')
tpl = pd.read_excel(f'{ROOT}/data/raw/attachments/附件2/result2.xlsx', header=None)

print(f'输出 shape: {out.shape}, 模板 shape: {tpl.shape}')
print(f'输出列: {list(out.columns)}')
print(f'模板列: {list(tpl.iloc[0])}')
print(f'列名对齐: {list(out.columns) == list(tpl.iloc[0])}')
print(f'5类计数: 黄金={out["黄金词"].sum()} 重点={out["重点词"].sum()} 潜力={out["潜力词"].sum()} 问题={out["问题词"].sum()} 无效={out["无效词"].sum()}')
print(f'总行数: {len(out)} (期望 2227)')
print(f'每行5类和=1: {(out[["黄金词","重点词","潜力词","问题词","无效词"]].sum(axis=1)==1).all()}')

# ========== 2. Thresholds verification ==========
print('\n=== 2. 阈值验证 ===')
with open(f'{ROOT}/results/tables/q2_thresholds.json', 'r', encoding='utf-8') as f:
    th = json.load(f)
print(f'T_cost={th["T_cost"]:.4f}元, T_benefit={th["T_benefit"]:.4f} (CPC倒数)')
print(f'5类计数: {th["counts"]}')

# 验证：用实际数据重新计算阈值
df_all = pd.read_pickle(f'{ROOT}/data/processed/q2/keyword_classified.pkl')
df_valid = df_all[df_all['分类'] != '无效词'].copy()
cost_vals = df_valid['成本'].astype(float).values
clicks_vals = df_valid['点击'].astype(float).values
cpc_inv_vals = clicks_vals / np.maximum(cost_vals, 0.01)
recomputed_Tc = float(np.median(cost_vals))
recomputed_Tb = float(np.median(cpc_inv_vals))
print(f'重算 T_cost={recomputed_Tc:.4f} (存储值={th["T_cost"]:.4f}, 一致: {abs(recomputed_Tc-th["T_cost"])<0.01})')
print(f'重算 T_benefit={recomputed_Tb:.4f} (存储值={th["T_benefit"]:.4f}, 一致: {abs(recomputed_Tb-th["T_benefit"])<0.01})')

# 验证 4 象限分类
cls_counts = {'黄金词':0,'重点词':0,'潜力词':0,'问题词':0}
for c, b in zip(cost_vals, cpc_inv_vals):
    if c <= recomputed_Tc and b >= recomputed_Tb:
        cls_counts['黄金词'] += 1
    elif c > recomputed_Tc and b >= recomputed_Tb:
        cls_counts['重点词'] += 1
    elif c <= recomputed_Tc and b < recomputed_Tb:
        cls_counts['潜力词'] += 1
    else:
        cls_counts['问题词'] += 1
print(f'重算有效词分类: {cls_counts}')
print(f'重算有效词总数: {sum(cls_counts.values())} (实际有效词: {len(df_valid)})')

# ========== 3. 异常标记验证 ==========
print('\n=== 3. 异常标记验证 ===')
if '异常标记' in df_all.columns:
    print(f'异常标记列存在: True')
    print(f'异常标记分布:')
    print(df_all['异常标记'].value_counts())
else:
    print('异常标记列不存在!')

# ========== 4. 极值审计 v2 验证 ==========
print('\n=== 4. 极值审计 v2 验证 ===')
audit_v2 = pd.read_csv(f'{ROOT}/results/tables/q2_extreme_audit_v2.csv')
print(f'极值审计 v2 行数: {len(audit_v2)}')
print(f'极值类型分布:')
print(audit_v2['极值类型'].value_counts())
print(f'业务风险评级分布:')
print(audit_v2['风险评级_业务'].value_counts())
print(f'保留型（重点词）: {(audit_v2["极值类型"]=="保留型极值").sum()} (应为 14)')
print(f'削减型（问题词）: {(audit_v2["极值类型"]=="削减型极值").sum()} (应为 91)')
print(f'触发规则分布:')
print(audit_v2['触发规则'].value_counts())

# ========== 5. 推广单元聚合验证 ==========
print('\n=== 5. 推广单元聚合验证 ===')
unit = pd.read_csv(f'{ROOT}/results/tables/q2_unit_cluster_summary.csv')
print(f'聚合表行数: {len(unit)} (期望 12)')
print(f'聚合表列: {list(unit.columns)}')
print(f'各单元关键词总数: {unit["关键词总数"].sum()} (期望 2227)')
cls_unit_sum = {c: int(unit[c].sum()) for c in ['黄金词','重点词','潜力词','问题词','无效词']}
cls_out_sum = {c: int(out[c].sum()) for c in ['黄金词','重点词','潜力词','问题词','无效词']}
print(f'聚合 sum: {cls_unit_sum}')
print(f'明细 sum: {cls_out_sum}')
print(f'明细=聚合: {cls_unit_sum==cls_out_sum}')

# ========== 6. field robustness 验证 ==========
print('\n=== 6. 字段稳健性验证 ===')
robust = pd.read_csv(f'{ROOT}/results/tables/q2_field_robustness.csv')
print(robust.to_string())

# ========== 7. thresholds compare 验证 ==========
print('\n=== 7. 阈值 3 对比验证 ===')
with open(f'{ROOT}/results/tables/q2_thresholds_compare.json', 'r', encoding='utf-8') as f:
    cmp = json.load(f)
for k, v in cmp.items():
    if isinstance(v, dict) and 'counts' in v:
        print(f'{k}: T_cost={v["T_cost"]:.2f} T_benefit={v["T_benefit"]:.4f} counts={v["counts"]}')

# ========== 8. Zero keyword breakdown ==========
print('\n=== 8. 三零词细分 ===')
# 检查 q2_zero_keyword_breakdown.csv 是否存在
import os
fn = f'{ROOT}/results/tables/q2_zero_keyword_breakdown.csv'
if os.path.exists(fn):
    zdf = pd.read_csv(fn)
    print(f'q2_zero_keyword_breakdown.csv 存在: {len(zdf)}行')
    print(zdf.head())
else:
    print(f'q2_zero_keyword_breakdown.csv 不存在！')

# 从 pkl 里手动验证
triple_zero = (df_all['成本']==0) & (df_all['点击']==0) & (df_all['浏览']==0)
print(f'三零词总数（三零=消费=0 且点击=0 且浏览=0）: {triple_zero.sum()}')
print(f'非三零词总数: {(~triple_zero).sum()}')
print(f'总词数: {len(df_all)}')

# ========== 9. 模板列名与输出对齐验证 ==========
print('\n=== 9. 模板列名与输出对齐 ===')
tpl_cols = list(tpl.iloc[0])
out_cols = list(out.columns)
print(f'模板: {tpl_cols}')
print(f'输出: {out_cols}')
print(f'完全对齐: {tpl_cols == out_cols}')
