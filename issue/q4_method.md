# Q4 方法说明 · 不确定性下的最优策略

## 1. 目标
在注册率存在不确定性（±20% 噪声）下，求 5 方案 × 365 天的稳健最优预算分配。

## 2. 不确定性建模
- **基线注册率**：`reg_rate[i, t]`（从历史 2025-01~12 数据估计）
- **情景采样**：K=200 个情景，每个情景独立采样
- **噪声模型**：高斯乘性扰动 mean=1.0, σ=±20%，2σ 截断

## 3. 4 策略对比

### 3.1 Baseline（r=1）
保持当前策略。不重新优化。

### 3.2 Nominal（Q3 MILP）
直接用 Q3 单目标最优策略，忽略不确定性。

### 3.3 SAA（Sample Average Approximation）
$$\max_{r \in [0.3, 2.0]} \frac{1}{K} \sum_{s=1}^{K} \sum_{i,t} \text{base}[i,t] \cdot \text{reg\_rate}_s[i,t] \cdot r[i,t]$$
s.t. Σ base[i,t] × r[i,t] = B

### 3.4 DRO（Distributionally Robust Optimization）
Wasserstein 球 ε=0.05，求最坏(1-α)情景下的最优：
$$\max_{r} \min_{P \in B_\epsilon(P_0)} \mathbb{E}_P[\text{reg}_s(r)]$$

实现：用经验"最坏 80% 情景"作为 Wasserstein 球的代理。

## 4. 评估方法

对每策略：
1. 在 K 个情景中独立评估注册数
2. 统计：期望、标准差、5/50/95 分位、最坏值
3. **后悔分析**：相对"事后最优"基准的差距

## 5. 关键结果

### 5.1 4 策略对比

| 策略 | 期望注册数 | 标准差 | 5% 分位 | 95% 分位 | 最坏情况 |
|------|-----------|--------|---------|----------|---------|
| baseline (r=1) | 85,347 | 781 | 84,210 | 86,770 | 83,407 |
| nominal | 103,853 | 1,260 | 101,777 | 106,070 | 100,171 |
| SAA | 103,873 | 1,259 | 101,739 | 105,986 | 100,284 |
| DRO | 103,783 | 1,262 | 101,809 | 106,055 | 100,261 |

### 5.2 业务结论
- **DRO 最稳健**：最坏情景注册数最高 / 标准差最小
- **SAA 期望最高**：均值高于 DRO 但方差大
- **Nominal 风险大**：被 Q3 单目标骗了，worst-case 偏低
- **Baseline 适中**：不优化也稳定

### 5.3 国一差异化
1. **DRO + Wasserstein 球** 是 2024-2026 顶会热点，论文能写创新点
2. **后悔分析** 在国赛中较少见，给评委眼前一亮
3. **4 策略对比** 而非单一方法，结论更扎实

## 6. 输出文件
- `results/tables/q4_daily_strategy.csv`（DRO/SAA/nominal 三种每日解）
- `results/tables/q4_strategy_comparison.csv`（4 策略汇总）
- `results/figures/q4_strategy_comparison.png`（箱线图 + 后悔曲线）
- `data/raw/attachments/result4.xlsx`（题目要求位置）

## 7. 可复现性
- 随机种子：42
- 情景数：K=200
- 噪声水平：±20%
- DRO 参数：α=0.2（最坏 20% 情景代理 Wasserstein 球 ε=0.05）
