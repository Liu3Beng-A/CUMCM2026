import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
from src.q1_data_prep import build_q1_data

data = build_q1_data()
dfc = data['campaign_daily']

print('=== 方案月度预算 CV 诊断 ===')
rows = []
for pid in dfc['方案ID'].unique():
    df_p = dfc[dfc['方案ID'] == pid]
    daily_p = df_p.groupby('日期', as_index=False)['消费额'].sum()
    monthly = daily_p.set_index('日期').resample('ME')['消费额'].sum()
    cv_month = monthly.std() / monthly.mean() if monthly.mean() > 0 else 999
    n_days = len(daily_p)
    s_time = max(0, min(100, 100 - abs(cv_month - 0.3) * 150))
    top_month = monthly.idxmax() if len(monthly) > 0 else None
    top_share = monthly.max() / monthly.sum() if len(monthly) > 0 else 0
    print(f'  方案 {pid}: n_days={n_days}, 月份数={len(monthly)}, '
          f'CV={cv_month:.3f}, s_time={s_time:.2f}')
    if top_month is not None:
        print(f'    最高消费月份: {top_month.strftime("%Y-%m")}, 占比 {top_share:.1%}')
    rows.append({
        '方案ID': pid,
        '有效天数': n_days,
        '有消费月数': len(monthly),
        '月度预算CV': round(cv_month, 3),
        's_time': round(s_time, 2),
        '最高消费月份': top_month.strftime('%Y-%m') if top_month is not None else 'N/A',
        '最高月份占比': round(top_share, 4),
    })

df_out = pd.DataFrame(rows)
print('\n汇总表:')
print(df_out.to_string(index=False))
df_out.to_csv('results/tables/q1_zero_score_diagnosis.csv',
              index=False, encoding='utf-8-sig')
print('\n[save] results/tables/q1_zero_score_diagnosis.csv')
