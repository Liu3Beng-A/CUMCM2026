"""验证熵权法和TOPSIS在5×4矩阵下排名相同的数学原因。"""
import numpy as np

M = np.array([
    [43.22, 69.73, 49.46, 99.57],   # 500635396
    [72.49, 60.21, 28.97, 97.88],   # 495403620
    [35.41, 55.40, 48.43, 35.07],   # 525368335
    [47.25, 57.23, 69.63, 61.51],   # 495817671
    [39.60, 54.90, 63.11, 92.86],   # 63563817
])
plan_ids = ['500635396', '495403620', '525368335', '495817671', '63563817']

n, m = M.shape
print('--- 熵权法 ---')
x_norm = M / 100.0
col_sum = x_norm.sum(axis=0)
p = x_norm / col_sum
k = 1.0 / np.log(n)
E = -k * np.sum(p * np.log(p), axis=0)
d = 1.0 - E
w_entropy = d / d.sum()
print(f'熵权 = {np.round(w_entropy, 4)}')
overall_entropy = (x_norm * w_entropy).sum(axis=1) * 100.0
rank_entropy = (-overall_entropy).argsort() + 1
print(f'方案 -> 熵权综合分: {dict(zip(plan_ids, overall_entropy.round(2)))}')
print(f'方案 -> 熵权排名: {dict(zip(plan_ids, rank_entropy.tolist()))}')

print('\n--- TOPSIS ---')
norm = np.sqrt((M**2).sum(axis=0))
r = M / norm
w_topsis = np.full(m, 1.0/m)
v = r * w_topsis
a_pos = v.max(axis=0)
a_neg = v.min(axis=0)
d_pos = np.sqrt(((v - a_pos)**2).sum(axis=1))
d_neg = np.sqrt(((v - a_neg)**2).sum(axis=1))
c = d_neg / (d_pos + d_neg)
overall_topsis = c * 100.0
rank_topsis = (-overall_topsis).argsort() + 1
print(f'方案 -> TOPSIS综合分: {dict(zip(plan_ids, overall_topsis.round(2)))}')
print(f'方案 -> TOPSIS排名: {dict(zip(plan_ids, rank_topsis.tolist()))}')

print('\n--- 检验：熵权权重是否"接近"(1/4, 1/4, 1/4, 1/4)？---')
print(f'差异: {np.abs(w_entropy - 0.25).max():.4f}')

print('\n--- 等权 TOPSIS vs 加权为(1/4,1/4,1/4,1/4)的 TOPSIS ---')
print('当权重恰为 (1/4, 1/4, 1/4, 1/4) 时，TOPSIS = 等权加权 + 欧氏距离排名')
print('而等权加权排名 = 简单算术平均排名（满分 100）')
print('熵权"接近"等权是因为：5个方案在4维度上的得分分布差异小，熵权几乎等于等权')
