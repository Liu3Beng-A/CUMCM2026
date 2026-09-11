"""分析三种方法：等权、熵权、TOPSIS的排名差异。"""
import numpy as np

M = np.array([
    [43.22, 69.73, 49.46, 99.57],   # 500635396
    [72.49, 60.21, 28.97, 97.88],   # 495403620
    [35.41, 55.40, 48.43, 35.07],   # 525368335
    [47.25, 57.23, 69.63, 61.51],   # 495817671
    [39.60, 54.90, 63.11, 92.86],   # 63563817
])
plan_ids = ['500635396', '495403620', '525368335', '495817671', '63563817']

# === 1) 等权 ===
s_eq = M.mean(axis=1)
# === 2) 熵权 ===
x_norm = M / 100.0
col_sum = x_norm.sum(axis=0)
p = x_norm / col_sum
k = 1.0 / np.log(len(M))
E = -k * np.sum(p * np.log(p), axis=0)
d = 1.0 - E
w_entropy = d / d.sum()
s_ent = (x_norm * w_entropy).sum(axis=1) * 100.0
# === 3) 等权TOPSIS ===
norm = np.sqrt((M**2).sum(axis=0))
r = M / norm
w_t = np.full(M.shape[1], 1.0/M.shape[1])
v = r * w_t
a_pos = v.max(axis=0)
a_neg = v.min(axis=0)
d_pos = np.sqrt(((v - a_pos)**2).sum(axis=1))
d_neg = np.sqrt(((v - a_neg)**2).sum(axis=1))
c = d_neg / (d_pos + d_neg)
s_tops = c * 100.0

print('方案      等权       熵权       TOPSIS')
for i, pid in enumerate(plan_ids):
    print(f'{pid}  {s_eq[i]:7.2f}   {s_ent[i]:7.2f}   {s_tops[i]:7.2f}')

print('\n排名（1=最优）')
import pandas as pd
df = pd.DataFrame({
    '方案': plan_ids,
    '等权综合分': s_eq,
    '熵权综合分': s_ent,
    'TOPSIS综合分': s_tops,
})
df['等权排名'] = df['等权综合分'].rank(ascending=False, method='min').astype(int)
df['熵权排名'] = df['熵权综合分'].rank(ascending=False, method='min').astype(int)
df['TOPSIS排名'] = df['TOPSIS综合分'].rank(ascending=False, method='min').astype(int)
print(df.to_string(index=False))

print('\n解释：为什么熵权 ≈ 等权？')
print(f'熵权权重: {np.round(w_entropy, 4).tolist()}')
print(f'差异(熵权 - 0.25): {np.round(w_entropy - 0.25, 4).tolist()}')
print('关键观察：5 个方案在 4 个维度上的差异主要在 D4(时间) 和 D3(出价)')
print('而 D2(关键词) 熵权只有 0.0296 ≈ 几乎无贡献（5个方案在关键词上分差小）')
print('这是数据集本身的特点，非算法 bug')
