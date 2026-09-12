"""快速 benchmark bootstrap 单节日速度"""
import time, sys, os, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '.')
from src.q1_bootstrap import _bootstrap_one_holiday
import pandas as pd

daily = pd.read_pickle('data/processed/q1/daily_full.pkl')

# 测试不同 n_boot
for n in [20, 50, 100]:
    t0 = time.time()
    r = _bootstrap_one_holiday(daily, '总消费额', '2025-10-01', '国庆', n_boot=n)
    elapsed = time.time() - t0
    if r:
        print(f'n_boot={n}: {elapsed:.1f}s, n_eff={r["n_boot_valid"]}, mean_diff={r["均值差"]:.2f}')
    else:
        print(f'n_boot={n}: {elapsed:.1f}s, FAILED')

# 推断 37 holidays x 2 metrics x 1000 boot 的总耗时
single_n100 = elapsed  # 上面最后一次的结果
print(f'\n外推：37 holidays * 2 metrics * 100 boot = {37*2*single_n100:.0f}s = {37*2*single_n100/60:.1f}min')
print(f'外推：37 holidays * 2 metrics * 500 boot = {37*2*single_n100*5:.0f}s = {37*2*single_n100*5/60:.1f}min')
