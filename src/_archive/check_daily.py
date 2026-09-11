"""检查 daily_full 数据"""
import sys, os
sys.path.insert(0, r'd:\CUMCM2026Problems')
sys.stdout.reconfigure(encoding='utf-8')
import pickle

with open(r'd:\CUMCM2026Problems\data\processed\q1\daily_full.pkl', 'rb') as f:
    df = pickle.load(f)
print('columns:', list(df.columns))
print('shape:', df.shape)
print(df.head(3))
print()
print('注册转化率分布:')
print(df['注册转化率'].describe())
print()
print('总消费额describe:')
print(df['总消费额'].describe())
