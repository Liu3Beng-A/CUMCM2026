# -*- coding: utf-8 -*-
"""
Q4 · A1: 6 因子协方差矩阵估计 + Gaussian copula 采样
========================================================================

**目标**：替代原代码中 `correlation_model: independent` (PoC simplification)
**方法**：
  1) 从 Sheet1 + Sheet2 提取日级每单元每因子数据
  2) 标准化为乘子（multiplier）：multiplier[t,u,fac] = value[t,u,fac] / mean(value[u,fac])
  3) 估计 6 因子间的 Spearman 相关矩阵（log-normal 模型下 Spearman≈Pearson）
  4) 用 Gaussian copula 采样 N 个场景（保持边际分布为对数正态 + 联合结构为相关）

**输出**：
  - data/processed/q4/q4_factor_cov_matrix.csv  · 6×6 相关系数矩阵
  - data/processed/q4/q4_factor_cov_summary.json · 估算方法学说明
  - results/figures/q4_factor_correlation.png    · 热力图
"""
import os, sys, json, pickle
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import PROCESSED_DIR, RESULTS_DIR, TABLES_DIR, FIGURES_DIR, EXCEL_DIR  # noqa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.plot_style import apply_style

ATTR_DIR = r'd:\CUMCM2026Problems\data\raw\attachments'
PROC_DIR = r'd:\CUMCM2026Problems\data\processed'
TBL_DIR = r'd:\CUMCM2026Problems\results\tables'
FIG_DIR = r'd:\CUMCM2026Problems\results\figures'

# Q4 历史窗口（与 q4_unit_cv.pkl 一致）
HISTORY_START = pd.Timestamp('2025-08-18')
HISTORY_END = pd.Timestamp('2025-09-16')


def load_sheet1_daily():
    """加载 Sheet1 日级数据"""
    df = pd.read_excel(os.path.join(ATTR_DIR, '附件1.xlsx'), sheet_name=0)
    df.columns = ['date', 'plan_id', 'unit_id', 'impressions', 'clicks', 'cost',
                  'top_imp', 'top_imp_pos', 'top_click', 'top_cost']
    df['date'] = pd.to_datetime(df['date'])
    return df


def load_sheet2_daily():
    """加载 Sheet2 日级注册数据"""
    df = pd.read_excel(os.path.join(ATTR_DIR, '附件1.xlsx'), sheet_name=1)
    df.columns = ['date', 'regs']
    df['date'] = pd.to_datetime(df['date'])
    return df


def compute_unit_daily_factors():
    """计算日级每单元每因子的乘子矩阵"""
    sheet1 = load_sheet1_daily()
    sheet2 = load_sheet2_daily()

    # 限定 Q4 历史窗口
    mask = (sheet1['date'] >= HISTORY_START) & (sheet1['date'] <= HISTORY_END)
    s1 = sheet1[mask].copy()

    # 单元级日聚合（5 因子）
    daily_unit = s1.groupby(['date', 'unit_id']).agg(
        impressions=('impressions', 'sum'),
        clicks=('clicks', 'sum'),
        cost=('cost', 'sum'),
        top_imp=('top_imp', 'sum'),
        top_imp_pos=('top_imp_pos', 'mean'),  # 排名取均值
    ).reset_index()

    # 计算派生因子
    daily_unit['cpc'] = daily_unit['cost'] / daily_unit['clicks'].clip(lower=1)
    # top_imp_pos 是反向指标（数字越小越好），反转
    daily_unit['top_imp_pos_inv'] = 1.0 / daily_unit['top_imp_pos'].clip(lower=0.01)
    # 浏览量代理：点击数 × 3.712（同 q4_evaluator 默认 ratio）
    daily_unit['browses'] = daily_unit['clicks'] * 3.712

    # Sheet2 注册量是全市场级，需要按单元拆分——使用各单元点击占比分摊
    total_clicks = s1.groupby('date')['clicks'].sum().reset_index().rename(columns={'clicks': 'total_clicks'})
    daily_unit = daily_unit.merge(total_clicks, on='date', how='left')
    daily_unit = daily_unit.merge(sheet2, on='date', how='left')
    daily_unit['regs'] = daily_unit['regs'] * (daily_unit['clicks'] / daily_unit['total_clicks'].clip(lower=1))

    factors = ['cpc', 'impressions', 'top_imp_pos_inv', 'top_imp', 'clicks', 'browses', 'regs']
    return daily_unit, factors


def compute_multiplier_matrix(daily_unit, factors):
    """
    标准化为乘子：multiplier[t,u,fac] = value[t,u,fac] / mean(value[u,fac])
    返回：(dates, units, factors, multipliers) 长格式 DataFrame
    """
    means = daily_unit.groupby('unit_id')[factors].mean()
    rows = []
    for _, row in daily_unit.iterrows():
        u = row['unit_id']
        if u not in means.index:
            continue
        d = row['date']
        for fac in factors:
            mean_val = means.loc[u, fac]
            if pd.isna(mean_val) or mean_val <= 0:
                continue
            mult = row[fac] / mean_val
            rows.append({'date': d, 'unit_id': u, 'factor': fac, 'multiplier': mult})
    return pd.DataFrame(rows)


def estimate_covariance(mult_df, factors):
    """
    估计 6 因子相关矩阵（Spearman，对数正态分布下 Spearman 接近 Pearson）
    注意：注册量基于点击占比分摊，相关结构继承自 clicks
    """
    # 宽表：行=日-单元，列=因子
    wide = mult_df.pivot_table(index=['date', 'unit_id'], columns='factor', values='multiplier')
    wide = wide.dropna()

    # log 变换（对数正态 → 正态）
    log_wide = np.log(wide.clip(lower=0.01))
    corr_matrix = log_wide[factors].corr(method='spearman')  # Spearman 更稳健
    return wide, corr_matrix


def fit_log_normal_params(mult_df, factors):
    """估计每个因子在 log 空间下的均值和标准差"""
    log_stats = {}
    for fac in factors:
        sub = mult_df[mult_df['factor'] == fac]['multiplier'].clip(lower=0.01)
        log_vals = np.log(sub)
        log_stats[fac] = {'mu_log': float(log_vals.mean()), 'sigma_log': float(log_vals.std())}
    return log_stats


def gaussian_copula_sample(corr_matrix, log_stats, factors, units, n_scenarios=100, seed=42):
    """
    Gaussian copula 采样：
      1) 从 N(0, Σ) 采样 Z (n_scenarios, n_factors)
      2) Z → U = Φ(Z)
      3) U → X = exp(μ_log + σ_log · Φ⁻¹(U))
      返回 list[dict]: 每个场景 = {unit_id: {factor: multiplier}}
    """
    from scipy.stats import norm, multivariate_normal
    rng = np.random.default_rng(seed)

    n_factors = len(factors)
    # 协方差矩阵（Pearson 近似 = Spearman）
    cov = corr_matrix.values
    # 保证正定（小幅抖动）
    eigvals = np.linalg.eigvalsh(cov)
    if eigvals.min() < 1e-8:
        cov = cov + np.eye(n_factors) * (1e-6 - eigvals.min())
    L = np.linalg.cholesky(cov)

    # 采样 joint Gaussian
    Z = rng.standard_normal((n_scenarios, n_factors)) @ L.T
    U = norm.cdf(Z)
    X_log = np.zeros_like(U)
    for j, fac in enumerate(factors):
        mu = log_stats[fac]['mu_log']
        sigma = log_stats[fac]['sigma_log']
        X_log[:, j] = mu + sigma * norm.ppf(U[:, j].clip(1e-6, 1 - 1e-6))
    mult_matrix = np.exp(X_log)  # (n_scenarios, n_factors)

    # 每个单元共享同一份乘子矩阵（代理：单元特异性通过 CV 自带差异体现）
    scenarios = []
    for s in range(n_scenarios):
        scenario = {'units': units, 'mults': {}}
        for j, fac in enumerate(factors):
            # 所有单元乘以同一乘子，单元差异由 CV 决定
            scenario['mults'][fac] = np.full(len(units), mult_matrix[s, j])
        scenarios.append(scenario)
    return scenarios


def plot_correlation_heatmap(corr_matrix, factors, out_path):
    """改-P0-5：
    1) 用 vmin=-0.5, vmax=1.0 聚焦实际数据范围（避免色阶过于集中在高值区）
    2) 给完全共线对 (|ρ|>=0.95) 加 ★ 标注
    3) 数值文本根据对比度自动黑白
    """
    apply_style()
    fig, ax = plt.subplots(figsize=(8.5, 7))
    # 改-P0-5：聚焦实际数据范围（max 实际值 ~1.0, min ~0.20），不用全 -1~1
    vmin, vmax = -0.5, 1.0
    im = ax.imshow(corr_matrix.values, cmap='RdBu_r', vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(factors)))
    ax.set_yticks(range(len(factors)))
    ax.set_xticklabels(factors, rotation=35, ha='right', fontsize=10)
    ax.set_yticklabels(factors, fontsize=10)
    for i in range(len(factors)):
        for j in range(len(factors)):
            v = corr_matrix.values[i, j]
            # 改-P0-5：给完全共线对 (|ρ|≥0.95) 加 ★
            star = '★' if abs(v) >= 0.95 and i != j else ''
            # 文字颜色：|v - midpoint| > 0.3 时白色，否则黑色
            midpoint = (vmin + vmax) / 2
            color = 'white' if abs(v - midpoint) > 0.3 else 'black'
            ax.text(j, i, f'{v:.2f}{star}', ha='center', va='center', fontsize=10,
                    color=color, fontweight='bold' if abs(v) >= 0.7 else 'normal')
    cbar = plt.colorbar(im, ax=ax, label='Spearman 相关系数')
    cbar.ax.tick_params(labelsize=9)
    ax.set_title('Q4 · 6 因子相关系数矩阵（历史 30 天单元级 log-normal 估算）\n'
                 '★ 标注 |ρ|≥0.95 的完全共线对', fontsize=12, fontweight='bold')
    # 改-P0-5：加共线对说明
    ax.text(0.02, -0.18, f'注：clicks↔browses ρ=1.00（browses=clicks×3.712 派生代理，故完全共线）；'
                          f'top_imp_pos_inv↔top_imp_pos ρ=1.00（取倒数派生）',
            transform=ax.transAxes, fontsize=8, color='gray', ha='left', va='top')
    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'  -> {out_path}')


def main():
    print('=' * 70)
    print('Q4 · A1: 6 因子协方差矩阵估计 + Gaussian copula 采样')
    print('=' * 70)

    # ---- Step 1: 计算日级每单元因子 ----
    print('\n[Step 1] 计算日级每单元因子')
    daily_unit, factors = compute_unit_daily_factors()
    print(f'  daily_unit 形状: {daily_unit.shape}, 因子: {factors}')

    # ---- Step 2: 标准化为乘子 ----
    print('\n[Step 2] 标准化为乘子矩阵')
    mult_df = compute_multiplier_matrix(daily_unit, factors)
    print(f'  mult_df 形状: {mult_df.shape}')

    # ---- Step 3: 估计相关矩阵 ----
    print('\n[Step 3] 估计 Spearman 相关矩阵（log 空间）')
    wide, corr_matrix = estimate_covariance(mult_df, factors)
    print('  相关矩阵:')
    print(corr_matrix.round(3))
    print(f'  样本数（日期-单元对）: {len(wide)}')

    # ---- Step 4: 估计 log-normal 参数 ----
    print('\n[Step 4] 估计 log-normal 参数')
    log_stats = fit_log_normal_params(mult_df, factors)
    for fac, p in log_stats.items():
        print(f'  {fac:18s} mu_log={p["mu_log"]:+.4f} sigma_log={p["sigma_log"]:.4f}')

    # ---- Step 5: 保存相关矩阵 + 摘要 ----
    print('\n[Step 5] 保存产物')
    cov_path = os.path.join(PROC_DIR, 'q4', 'q4_factor_cov_matrix.csv')
    corr_matrix.to_csv(cov_path, encoding='utf-8-sig')
    print(f'  -> {cov_path}')

    summary = {
        'method': 'Spearman 相关（log-normal 空间）+ Gaussian copula',
        'history_window': '2025-08-18 ~ 2025-09-16 (30 天)',
        'sample_size_date_unit_pairs': int(len(wide)),
        'factors': factors,
        'correlation_matrix': {fac: {fac2: float(corr_matrix.loc[fac, fac2]) for fac2 in factors} for fac in factors},
        'log_normal_params': log_stats,
        'correlation_model': 'Gaussian copula (estimated from history)',
        'improvement_vs_poC': '从 independent → 估计相关，提升 Two-Stage SP 的联合分布真实性',
        'register_proxy_note': 'regs 按单元点击占比从全市场 Sheet2 分摊（仅适用于无单元级注册数据）'
    }
    summary_path = os.path.join(PROC_DIR, 'q4', 'q4_factor_cov_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f'  -> {summary_path}')

    # ---- Step 6: 相关矩阵热力图 ----
    print('\n[Step 6] 相关矩阵热力图')
    heatmap_path = os.path.join(FIG_DIR, 'q4_factor_correlation.png')
    plot_correlation_heatmap(corr_matrix, factors, heatmap_path)

    # ---- Step 7: 验证 Gaussian copula 采样 ----
    print('\n[Step 7] Gaussian copula 采样验证')
    units = sorted(daily_unit['unit_id'].unique().tolist())
    scenarios = gaussian_copula_sample(corr_matrix, log_stats, factors, units, n_scenarios=100)
    print(f'  采样 {len(scenarios)} 场景, 每场景 {len(factors)} 因子 × {len(units)} 单元')

    # 保存样本场景
    sample_scenarios_path = os.path.join(PROC_DIR, 'q4', 'q4_copula_scenarios_sample.pkl')
    with open(sample_scenarios_path, 'wb') as f:
        pickle.dump({'scenarios': scenarios[:5], 'factors': factors, 'units': units, 'log_stats': log_stats}, f)
    print(f'  -> {sample_scenarios_path} (前 5 场景示例)')

    print('\n' + '=' * 70)
    print('✅ A1 完成')
    print('=' * 70)
    return summary


if __name__ == '__main__':
    main()
