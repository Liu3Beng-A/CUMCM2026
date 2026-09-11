import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import numpy as np
from src.q1_data_prep import build_q1_data

data = build_q1_data()
daily = data['daily_full']
from src.q1_robustness_aug import find_aug_anomaly, build_clean_dataset, run_bootstrap_comparison
abnormal_date, abnormal_row, z = find_aug_anomaly(daily)
print('异常日:', abnormal_date, 'z=', round(z, 2))
clean = build_clean_dataset(daily, abnormal_date)
print('clean shape:', clean.shape, 'daily shape:', daily.shape)

try:
    res, full = run_bootstrap_comparison(daily, clean, n_boot=80)
    print('--- bootstrap ok ---')
    print(full.head(20).to_string())
    print('rows:', len(full))
except Exception as e:
    import traceback
    traceback.print_exc()
