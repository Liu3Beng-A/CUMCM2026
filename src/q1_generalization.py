"""Q1 跨数据集泛化性检验

目的：验证 CRITIC 权重和节日效应估计对未见数据的泛化能力，防止方法过拟合于训练集。

三种验证策略：
- 策略 A：时间切分验证（用 1-6 月数据训练，预测 7-9 月节日效应）
- 策略 B：留一方案交叉验证（5 折留一，用 4 个方案训练权重，预测被剔除方案排名）
- 策略 C：Bootstrap 重采样（检验 CRITIC 权重和综合评分的 95% CI 稳定性）

输出：
- results/tables/q1_generalization_time_split.csv
- results/tables/q1_generalization_loo_cv.csv
- results/tables/q1_generalization_bootstrap.csv
- results/figures/q1_generalization_time_split.png
- results/figures/q1_generalization_loo_cv.png
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import json
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from prophet import Prophet

from src.q1_data_prep import build_q1_data
from src.q1_weights import compute_weights, SUBJECTIVE_WEIGHTS, critic_weights
from src.q1_scoring import _score_per_plan
from src.utils import (
    ROOT, PROCESSED_DIR, TABLES_DIR, FIGURES_DIR, ensure_dir
)
from src.plot_style import apply_style, COLORS, q1_title
from src.config import HOLIDAYS_2025, SHOPPING_FESTIVALS_2025

# 设置中文字体
plt.rcParams['font.size'] = 10
apply_style()

# 所有节假日
ALL_HOLIDAYS = list(HOLIDAYS_2025) + [(d, '购物节') for d in SHOPPING_FESTIVALS_2025]

# =============================================================================
# 策略 A：时间切分验证
# =============================================================================

def time_split_validation():
    """用 1-6 月数据训练，预测 7-9 月节日效应

    由于春节/劳动/国庆 7-9 月无数据，预测中秋（2025-09-17）和国庆 10 月的节日效应。
    输出：预测 vs 实际对比表和时序图。
    """
    print('\n=== 策略 A：时间切分验证 ===', flush=True)
    data = build_q1_data()
    daily = data['daily_full'].copy()
    daily['月份'] = daily['日期'].dt.month

    # 切分
    train = daily[daily['月份'] <= 6].copy()
    test = daily[daily['月份'] >= 7].copy()

    print(f'  训练集: {len(train)} 天 ({train["日期"].min().date()} ~ {train["日期"].max().date()})', flush=True)
    print(f'  测试集: {len(test)} 天 ({test["日期"].min().date()} ~ {test["日期"].max().date()})', flush=True)

    # ---- 1. 用训练集数据估计节日效应（简化：计算训练集各节日的日均消费额差值）----
    holiday_dates = set([pd.to_datetime(d) for d, _ in ALL_HOLIDAYS])
    train_copy = train.copy()
    train_copy['是否节日'] = train_copy['日期'].isin(holiday_dates)

    # 节日日 vs 非节日日均值
    holiday_mean = train_copy[train_copy['是否节日']]['总消费额'].mean()
    non_holiday_mean = train_copy[~train_copy['是否节日']]['总消费额'].mean()
    holiday_effect_pct = (holiday_mean - non_holiday_mean) / non_holiday_mean * 100

    print(f'  训练集节日效应: {holiday_effect_pct:+.2f}%（节日均值 {holiday_mean:.1f} vs 非节日均值 {non_holiday_mean:.1f}）', flush=True)

    # ---- 2. 用 Prophet 预测 7-12 月每日消费额 ----
    # 准备 Prophet 格式数据
    train_prophet = pd.DataFrame({
        'ds': train['日期'],
        'y': train['总消费额']
    }).sort_values('ds')

    # 拟合 Prophet
    prophet_model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
        seasonality_prior_scale=10,
    )
    prophet_model.fit(train_prophet)

    # 预测未来
    future = pd.DataFrame({'ds': pd.date_range(start='2025-07-01', end='2025-12-31', freq='D')})
    forecast = prophet_model.predict(future)

    # 提取预测值
    forecast_dict = dict(zip(forecast['ds'], forecast['yhat']))

    # ---- 3. 计算测试集实际节日效应 ----
    test_copy = test.copy()
    test_copy['是否节日'] = test_copy['日期'].isin(holiday_dates)
    test_copy['预测值'] = test_copy['日期'].map(forecast_dict)
    test_copy['预测值'] = test_copy['预测值'].fillna(forecast['yhat'].mean())

    # 计算预测误差
    test_copy['误差'] = test_copy['总消费额'] - test_copy['预测值']
    test_copy['误差百分比'] = test_copy['误差'] / test_copy['预测值'].replace(0, np.nan) * 100

    # 节日预测误差
    test_holiday = test_copy[test_copy['是否节日']]
    test_non_holiday = test_copy[~test_copy['是否节日']]

    # ---- 4. 关键节日对比 ----
    # 选取 9-10 月的关键节日
    key_dates = {
        '中秋': '2025-09-17',
        '国庆': '2025-10-01',
        '国庆': '2025-10-02',
        '国庆': '2025-10-03',
        '重阳': '2025-10-11',
        '双11': '2025-11-11',
        '双12': '2025-12-12',
    }

    results = []
    for name, d_str in key_dates.items():
        d = pd.to_datetime(d_str)
        row = test_copy[test_copy['日期'] == d]
        if len(row) > 0:
            actual = row['总消费额'].values[0]
            pred = row['预测值'].values[0]
            error_pct = (actual - pred) / pred * 100 if pred > 0 else 0
            results.append({
                '节日': name,
                '日期': d_str,
                '实际消费额': round(actual, 2),
                '预测消费额': round(pred, 2),
                '误差百分比': round(error_pct, 2),
                '实际vs预测': '偏高' if actual > pred else '偏低',
            })

    results_df = pd.DataFrame(results)

    # ---- 5. 月度汇总对比 ----
    test_copy['月份_str'] = test_copy['日期'].dt.strftime('%Y-%m')
    monthly = test_copy.groupby('月份_str').agg(
        实际总消费额=('总消费额', 'sum'),
        预测总消费额=('预测值', 'sum'),
    ).reset_index()
    monthly['预测误差'] = monthly['实际总消费额'] - monthly['预测总消费额']
    monthly['预测误差百分比'] = monthly['预测误差'] / monthly['预测总消费额'].replace(0, np.nan) * 100

    print('\n  月度预测对比：', flush=True)
    print(monthly.to_string(index=False), flush=True)

    # ---- 6. 绘图 ----
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # 图 A1: 时序对比
    ax = axes[0]
    ax.plot(test_copy['日期'], test_copy['总消费额'], label='实际消费额',
            color=COLORS['primary'], alpha=0.7, linewidth=1.5)
    ax.plot(test_copy['日期'], test_copy['预测值'], label='Holt-Winters预测',
            color=COLORS['accent'], alpha=0.7, linestyle='--', linewidth=1.5)

    # 标注节日
    for _, row in results_df.iterrows():
        ax.axvline(pd.to_datetime(row['日期']), color=COLORS['danger'], linestyle=':', alpha=0.5)
        ax.annotate(row['节日'], (pd.to_datetime(row['日期']), ax.get_ylim()[1] * 0.95),
                   fontsize=8, rotation=45)

    ax.set_title('策略 A：时间切分验证 - 7-12月消费额 实际 vs 预测', fontsize=12)
    ax.set_xlabel('日期')
    ax.set_ylabel('消费额（元）')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 图 A2: 月度误差条形图
    ax = axes[1]
    x = np.arange(len(monthly))
    width = 0.35
    bars1 = ax.bar(x - width/2, monthly['实际总消费额'], width, label='实际',
                   color=COLORS['primary'], alpha=0.7)
    bars2 = ax.bar(x + width/2, monthly['预测总消费额'], width, label='预测',
                   color=COLORS['accent'], alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(monthly['月份_str'])
    ax.set_title('策略 A：月度消费额 实际 vs 预测', fontsize=12)
    ax.set_xlabel('月份')
    ax.set_ylabel('消费额（元）')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # 添加误差百分比标签
    for i, (_, row) in enumerate(monthly.iterrows()):
        ax.annotate(f'{row["预测误差百分比"]:.1f}%',
                   (i + width/2, row['预测总消费额']),
                   fontsize=8, ha='center', va='bottom')

    fig.suptitle(q1_title('跨数据集泛化性 - 策略 A：时间切分验证'),
                 fontsize=14, fontweight='bold')
    fig.tight_layout()

    out_fig = os.path.join(FIGURES_DIR, 'q1_generalization_time_split.png')
    ensure_dir(os.path.dirname(out_fig))
    fig.savefig(out_fig, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [save] {out_fig}', flush=True)

    # 保存 CSV
    out_csv = os.path.join(TABLES_DIR, 'q1_generalization_time_split.csv')
    ensure_dir(os.path.dirname(out_csv))
    results_df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'  [save] {out_csv}', flush=True)

    # 计算平均误差
    avg_error_pct = results_df['误差百分比'].abs().mean()
    print(f'\n  策略 A 结果：关键节日预测平均误差 {avg_error_pct:.2f}%', flush=True)

    return results_df, monthly, avg_error_pct


# =============================================================================
# 策略 B：留一方案交叉验证
# =============================================================================

def loo_cross_validation():
    """5 折留一交叉验证

    每次剔除一个方案，用剩余 4 个方案的得分矩阵训练 CRITIC 权重，
    然后预测被剔除方案的排名。与实际排名对比。
    """
    print('\n=== 策略 B：留一方案交叉验证 ===', flush=True)
    data = build_q1_data()

    # 获取所有方案的 4 维度得分
    all_plan_scores = _score_per_plan(data)
    plan_ids = all_plan_scores.index.tolist()
    dim_names = list(all_plan_scores.columns)

    print(f'  方案列表: {plan_ids}', flush=True)
    print(f'  维度: {dim_names}', flush=True)

    # 计算实际排名（基于全量数据）
    # 用全量 CRITIC 权重计算综合分
    w_critic_full = critic_weights(all_plan_scores.values)
    weighted_scores_full = all_plan_scores.values @ w_critic_full
    actual_scores = dict(zip(plan_ids, weighted_scores_full))

    # 实际排名（降序，分高排名靠前）
    actual_rank = {pid: r + 1 for r, pid in enumerate(
        sorted(plan_ids, key=lambda x: actual_scores[x], reverse=True)
    )}

    print('  实际排名:', actual_rank, flush=True)

    # 留一交叉验证
    results = []
    predicted_ranks = []
    actual_ranks = []

    for fold, held_out_pid in enumerate(plan_ids, 1):
        # 训练集：剔除 held_out_pid 后的 4 个方案
        train_mask = [pid != held_out_pid for pid in plan_ids]
        train_scores = all_plan_scores.iloc[train_mask]

        # 用训练集计算 CRITIC 权重
        w_critic = critic_weights(train_scores.values)
        train_weighted = train_scores.values @ w_critic

        # 计算训练集各方案的相对得分（归一化到 0-100）
        train_min, train_max = train_weighted.min(), train_weighted.max()
        train_range = train_max - train_min if train_max != train_min else 1.0
        train_norm = (train_weighted - train_min) / train_range * 100

        # 建立训练集方案 ID 到归一化得分的映射
        train_pids = [pid for pid in plan_ids if pid != held_out_pid]
        train_pid_to_score = dict(zip(train_pids, train_norm))

        # 对被剔除方案：基于其 4 维度得分，用训练集 CRITIC 权重计算
        held_out_score_raw = all_plan_scores.loc[held_out_pid].values @ w_critic

        # 插值到训练集归一化区间
        if train_range > 0:
            held_out_score_norm = (held_out_score_raw - train_min) / train_range * 100
        else:
            held_out_score_norm = 50.0  # 训练集区分度为 0 时给中性分

        # 计算预测排名：统计有多少训练方案得分低于被剔除方案
        n_better = sum(1 for pid in train_pids if train_pid_to_score[pid] > held_out_score_norm)
        pred_rank = n_better + 1

        # 实际排名（全量数据）
        act_rank = actual_rank[held_out_pid]

        results.append({
            '折次': fold,
            '剔除方案': held_out_pid,
            '预测排名': int(pred_rank),
            '实际排名': int(act_rank),
            '预测综合分': round(held_out_score_norm, 2),
            '实际综合分': round(actual_scores[held_out_pid], 4),
        })
        predicted_ranks.append(pred_rank)
        actual_ranks.append(act_rank)

        print(f'  折{fold}: 剔除 {held_out_pid}, 预测排名={pred_rank}, 实际排名={act_rank}', flush=True)

    results_df = pd.DataFrame(results)

    # 计算 Spearman 相关系数
    rho, p_value = spearmanr(predicted_ranks, actual_ranks)
    print(f'\n  Spearman ρ = {rho:.4f} (p = {p_value:.4f})', flush=True)

    # ---- 绘图 ----
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))

    # 散点图
    colors = plt.cm.Set1(np.linspace(0, 1, len(plan_ids)))
    for i, (_, row) in enumerate(results_df.iterrows()):
        ax.scatter(row['实际排名'], row['预测排名'], s=150, c=[colors[i]],
                  label=f'方案 {row["剔除方案"]}', edgecolors='black', linewidth=1)
        ax.annotate(str(int(row['剔除方案'])),
                   (row['实际排名'], row['预测排名']),
                   fontsize=9, ha='left', va='bottom')

    # 对角线（完美预测）
    ax.plot([0.5, 5.5], [0.5, 5.5], 'k--', alpha=0.5, label='完美预测线 (y=x)')

    ax.set_xlabel('实际排名', fontsize=11)
    ax.set_ylabel('预测排名', fontsize=11)
    ax.set_title(f'策略 B：留一方案交叉验证\nSpearman ρ = {rho:.3f} (p = {p_value:.3f})', fontsize=12)
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 5.5)
    ax.set_xticks(range(1, 6))
    ax.set_yticks(range(1, 6))
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left', fontsize=9)
    ax.set_aspect('equal')

    fig.suptitle(q1_title('跨数据集泛化性 - 策略 B：留一方案交叉验证'),
                 fontsize=14, fontweight='bold')
    fig.tight_layout()

    out_fig = os.path.join(FIGURES_DIR, 'q1_generalization_loo_cv.png')
    ensure_dir(os.path.dirname(out_fig))
    fig.savefig(out_fig, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [save] {out_fig}', flush=True)

    # 保存 CSV
    out_csv = os.path.join(TABLES_DIR, 'q1_generalization_loo_cv.csv')
    ensure_dir(os.path.dirname(out_csv))
    results_df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'  [save] {out_csv}', flush=True)

    return results_df, rho, p_value


# =============================================================================
# 策略 C：Bootstrap 重采样泛化误差
# =============================================================================

def bootstrap_generalization(n_bootstrap=100):
    """Bootstrap 重采样检验权重和评分稳定性

    对全量数据做 n_bootstrap 次有放回采样，每次计算 CRITIC 权重和综合评分，
    输出：权重 95% CI 和评分 95% CI。

    修复（2026-09-11）：原版用 `0.7*CRITIC + 0.3*SUBJECTIVE_WEIGHTS` 手算混合权重，
    与 `q1_weights.py` 的归一化顺序不一致，导致基准权重过期。改为直接读取
    `results/tables/q1_score.json` 中已经算好的 `weight_mixed` / `weight_critic`。
    """
    print(f'\n=== 策略 C：Bootstrap 重采样泛化误差 (n={n_bootstrap}) ===', flush=True)
    data = build_q1_data()

    # 全量 CRITIC 权重（基准）：从最新 q1_score.json 读取，避免手算公式过期
    score_json_path = os.path.join(TABLES_DIR, 'q1_score.json')
    with open(score_json_path, 'r', encoding='utf-8') as f:
        score_data = json.load(f)
    dim_names = list(score_data['dimensions'].keys())
    w_critic_full = np.array([score_data['dimensions'][d]['weight_critic'] for d in dim_names])
    w_mixed = np.array([score_data['dimensions'][d]['weight_mixed']   for d in dim_names])
    w_mixed = w_mixed / w_mixed.sum()  # 数值归一化（防浮点漂移）

    all_plan_scores = _score_per_plan(data)
    weighted_scores_full = all_plan_scores.values @ w_critic_full
    full_mixed_scores = all_plan_scores.values @ w_mixed

    print(f'  基准混合权重: {dict(zip(dim_names, w_mixed.round(4)))}', flush=True)
    print(f'  基准综合分: {dict(zip(all_plan_scores.index, full_mixed_scores.round(2)))}', flush=True)

    # Bootstrap 重采样
    n_plans = len(all_plan_scores)
    bootstrap_weights = []
    bootstrap_scores = []

    np.random.seed(42)
    for i in range(n_bootstrap):
        # 有放回采样方案索引
        indices = np.random.choice(n_plans, size=n_plans, replace=True)
        boot_scores = all_plan_scores.values[indices]
        boot_weights = critic_weights(boot_scores)
        boot_mixed = 0.7 * boot_weights + 0.3 * np.array([
            SUBJECTIVE_WEIGHTS[name] for name in dim_names
        ])
        boot_mixed = boot_mixed / boot_mixed.sum()

        # 记录每个维度的权重
        for dim, w in zip(dim_names, boot_mixed):
            bootstrap_weights.append({'bootstrap_iter': i, '维度': dim, '混合权重': w})

        # 用 bootstrap 权重计算全量方案得分
        boot_full_scores = all_plan_scores.values @ boot_mixed
        for pid, score in zip(all_plan_scores.index, boot_full_scores):
            bootstrap_scores.append({'bootstrap_iter': i, '方案ID': pid, '综合分': score})

    weights_df = pd.DataFrame(bootstrap_weights)
    scores_df = pd.DataFrame(bootstrap_scores)

    # 计算 95% CI
    weight_ci = weights_df.groupby('维度')['混合权重'].agg(
        均值='mean', 标准差='std',
        CI下界=lambda x: x.quantile(0.025),
        CI上界=lambda x: x.quantile(0.975),
    ).reset_index()
    weight_ci['CI宽度'] = weight_ci['CI上界'] - weight_ci['CI下界']

    score_ci = scores_df.groupby('方案ID')['综合分'].agg(
        均值='mean', 标准差='std',
        CI下界=lambda x: x.quantile(0.025),
        CI上界=lambda x: x.quantile(0.975),
    ).reset_index()
    score_ci['CI宽度'] = score_ci['CI上界'] - score_ci['CI下界']

    # 全量结果对比
    weight_ci['基准权重'] = weight_ci['维度'].map(dict(zip(dim_names, w_mixed)))
    weight_ci['偏差'] = weight_ci['均值'] - weight_ci['基准权重']
    weight_ci['偏差百分比'] = weight_ci['偏差'] / weight_ci['基准权重'] * 100

    score_ci['基准分'] = score_ci['方案ID'].map(
        dict(zip(all_plan_scores.index, full_mixed_scores))
    )
    score_ci['偏差'] = score_ci['均值'] - score_ci['基准分']
    score_ci['偏差百分比'] = score_ci['偏差'] / score_ci['基准分'] * 100

    print('\n  Bootstrap 权重 95% CI:', flush=True)
    print(weight_ci.to_string(index=False), flush=True)

    print('\n  Bootstrap 综合分 95% CI:', flush=True)
    print(score_ci.to_string(index=False), flush=True)

    # ---- 绘图 ----
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 图 C1: 权重 CI
    ax = axes[0]
    y_pos = np.arange(len(weight_ci))
    ax.errorbar(weight_ci['均值'], y_pos, xerr=[
        weight_ci['均值'] - weight_ci['CI下界'],
        weight_ci['CI上界'] - weight_ci['均值']
    ], fmt='o', capsize=5, markersize=8, color=COLORS['primary'], ecolor=COLORS['primary'])
    ax.scatter(weight_ci['基准权重'], y_pos, marker='x', s=100, color=COLORS['danger'],
              label='基准权重', zorder=5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(weight_ci['维度'])
    ax.set_xlabel('混合权重', fontsize=11)
    ax.set_title('策略 C：CRITIC 权重 Bootstrap 95% CI', fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='x')

    # 图 C2: 综合分 CI
    ax = axes[1]
    y_pos = np.arange(len(score_ci))
    ax.errorbar(score_ci['均值'], y_pos, xerr=[
        score_ci['均值'] - score_ci['CI下界'],
        score_ci['CI上界'] - score_ci['均值']
    ], fmt='o', capsize=5, markersize=8, color=COLORS['accent'], ecolor=COLORS['accent'])
    ax.scatter(score_ci['基准分'], y_pos, marker='x', s=100, color=COLORS['danger'],
              label='基准分', zorder=5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([str(int(pid)) for pid in score_ci['方案ID']])
    ax.set_xlabel('综合评分', fontsize=11)
    ax.set_title('策略 C：综合评分 Bootstrap 95% CI', fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='x')

    fig.suptitle(q1_title(f'跨数据集泛化性 - 策略 C：Bootstrap 重采样 (n={n_bootstrap})'),
                 fontsize=14, fontweight='bold')
    fig.tight_layout()

    out_fig = os.path.join(FIGURES_DIR, 'q1_generalization_bootstrap.png')
    ensure_dir(os.path.dirname(out_fig))
    fig.savefig(out_fig, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [save] {out_fig}', flush=True)

    # 保存 CSV
    out_csv = os.path.join(TABLES_DIR, 'q1_generalization_bootstrap.csv')
    ensure_dir(os.path.dirname(out_csv))

    # 合并权重和评分的 CI
    combined = pd.DataFrame({
        '类型': ['权重'] * len(weight_ci) + ['评分'] * len(score_ci),
        '名称': list(weight_ci['维度']) + [str(int(pid)) for pid in score_ci['方案ID']],
        '基准值': list(weight_ci['基准权重']) + list(score_ci['基准分']),
        'Bootstrap均值': list(weight_ci['均值']) + list(score_ci['均值']),
        'Bootstrap标准差': list(weight_ci['标准差']) + list(score_ci['标准差']),
        'CI下界(2.5%)': list(weight_ci['CI下界']) + list(score_ci['CI下界']),
        'CI上界(97.5%)': list(weight_ci['CI上界']) + list(score_ci['CI上界']),
        'CI宽度': list(weight_ci['CI宽度']) + list(score_ci['CI宽度']),
        '偏差': list(weight_ci['偏差']) + list(score_ci['偏差']),
        '偏差百分比': list(weight_ci['偏差百分比']) + list(score_ci['偏差百分比']),
    })
    combined.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'  [save] {out_csv}', flush=True)

    # 计算平均 CI 宽度
    avg_weight_ci_width = weight_ci['CI宽度'].mean()
    avg_score_ci_width = score_ci['CI宽度'].mean()
    print(f'\n  策略 C 结果：权重平均 CI 宽度 {avg_weight_ci_width:.4f}，评分平均 CI 宽度 {avg_score_ci_width:.2f}', flush=True)

    return weight_ci, score_ci, avg_weight_ci_width, avg_score_ci_width


# =============================================================================
# 主入口
# =============================================================================

def run_generalization():
    """运行全部三种泛化性检验策略"""
    print('=' * 60, flush=True)
    print('问题一：跨数据集泛化性检验', flush=True)
    print('=' * 60, flush=True)

    # 策略 A：时间切分
    time_split_df, monthly_df, avg_error_pct = time_split_validation()

    # 策略 B：留一方案交叉验证
    loo_df, rho, p_value = loo_cross_validation()

    # 策略 C：Bootstrap 重采样
    weight_ci, score_ci, avg_weight_ci, avg_score_ci = bootstrap_generalization(n_bootstrap=100)

    # ---- 输出汇总 ----
    print('\n' + '=' * 60, flush=True)
    print('跨数据集泛化性检验汇总', flush=True)
    print('=' * 60, flush=True)
    print(f'策略 A（时间切分）：关键节日预测平均误差 {avg_error_pct:.2f}%', flush=True)
    print(f'策略 B（留一交叉验证）：Spearman ρ = {rho:.4f} (p = {p_value:.4f})', flush=True)
    print(f'策略 C（Bootstrap）：权重平均 CI 宽度 {avg_weight_ci:.4f}，评分平均 CI 宽度 {avg_score_ci:.2f}', flush=True)

    # 结论
    if rho >= 0.8 and avg_error_pct < 20:
        conclusion = '方法对未见数据具有较好的泛化能力，未发生过拟合。'
    elif rho >= 0.6 or avg_error_pct < 30:
        conclusion = '方法泛化能力中等，建议进一步扩大验证样本。'
    else:
        conclusion = '方法可能存在过拟合风险，建议检查模型复杂度。'

    print(f'\n结论：{conclusion}', flush=True)

    print('\n' + '=' * 60, flush=True)
    print('输出文件列表：', flush=True)
    print(f'  CSV: {TABLES_DIR}\\q1_generalization_time_split.csv', flush=True)
    print(f'  CSV: {TABLES_DIR}\\q1_generalization_loo_cv.csv', flush=True)
    print(f'  CSV: {TABLES_DIR}\\q1_generalization_bootstrap.csv', flush=True)
    print(f'  PNG: {FIGURES_DIR}\\q1_generalization_time_split.png', flush=True)
    print(f'  PNG: {FIGURES_DIR}\\q1_generalization_loo_cv.png', flush=True)
    print(f'  PNG: {FIGURES_DIR}\\q1_generalization_bootstrap.png', flush=True)
    print('=' * 60, flush=True)

    return {
        'time_split': {'df': time_split_df, 'avg_error_pct': avg_error_pct},
        'loo_cv': {'df': loo_df, 'rho': rho, 'p_value': p_value},
        'bootstrap': {'weight_ci': weight_ci, 'score_ci': score_ci,
                     'avg_weight_ci': avg_weight_ci, 'avg_score_ci': avg_score_ci},
    }


if __name__ == '__main__':
    results = run_generalization()
