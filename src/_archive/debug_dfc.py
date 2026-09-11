"""调试 data_loader"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'd:\CUMCM2026Problems')

from src.data_loader import load_processed
dfc, dfr, dfk = load_processed()
print('campaign columns:', list(dfc.columns))
print('shape:', dfc.shape)
print(dfc.head(2))
