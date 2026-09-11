"""Q1 Bootstrap 显著性检验（改-4）

目的：
- 对 Prophet 反事实差值（节日贡献）做显著性检验
- 用 Bootstrap 重采样估计差值的 95% 置信区间
- 判断"节日贡献是否显著 ≠ 0"

方法：
1. 对原始日级数据做 N=1000 次有放回重采样
2. 每次拟合 Prophet（含 holidays vs 不含 holidays）
3. 计算每次的"假日窗口实际值 - 无假日预测"差值
4. 取 2.5%/97.5% 分位数作为 95% CI

输出：
- q1_bootstrap_ci.csv：每个节日的 CI 估计 + p 值
- q1_bootstrap_distribution.png：分布图

性能优化：
- Prophet 拟合较慢，只对每个节日的"窗口数据"做 Bootstrap
- 单次预测（带 holidays vs 不带）做快速比较
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from prophet import Prophet

from src.q1_data_prep import build_q1_data
from src.utils import FIGURES_DIR, TABLES_DIR, ensure_dir
from src.config import HOLIDAYS_2025, SHOPPING_FESTIVALS_2025
from src.plot_style import apply_style, save_fig, COLORS


ALL_HOLIDAYS = list(HOLIDAYS_2025) + [(d, '购物节') for d in SHOPPING_FESTIVALS_2025]


def make_holidays_df(holidays):
    return pd.DataFrame({
        'holiday': [h[1] for h in holidays],
        'ds':      pd.to_datetime([h[0] for h in holidays]),
        'lower_window': 0,
        'upper_window': 1,
    })


def _bootstrap_one_holiday(daily_series, value_col, holiday_date_str,
                           holiday_name, n_boot=200, window_days=1, seed=42):
    """单个节日的 Bootstrap CI

    Returns
    -------
    dict : {holiday, mean_diff, ci_low, ci_high, p_value}
    """
    np.random.seed(seed)
    d_holiday = pd.to_datetime(holiday_date_str)

    # 准备数据
    df = daily_series[['日期', value_col]].copy()
    df.columns = ['ds', 'y']
    df = df.sort_values('ds').reset_index(drop=True)

    diffs = []
    fail_a = 0  # 模型 A（含 holidays）失败计数
    fail_b = 0  # 模型 B（无 holidays）失败计数
    fail_window = 0  # 窗口期匹配失败计数
    max_attempts = n_boot * 5  # 最多尝试 5 倍次数，避免无限循环
    attempts = 0
    n = len(df)

    while len(diffs) < n_boot and attempts < max_attempts:
        attempts += 1
        # 有放回重采样
        idx = np.random.choice(n, size=n, replace=True)
        boot = df.iloc[idx].reset_index(drop=True)

        # 两次预测
        future = boot[['ds']]
        # 模型 A：含 holidays
        try:
            m_a = Prophet(yearly_seasonality=False, weekly_seasonality=True,
                          daily_seasonality=False, holidays=make_holidays_df(ALL_HOLIDAYS),
                          holidays_prior_scale=20, changepoint_prior_scale=0.05,
                          seasonality_prior_scale=10, interval_width=0.95)
            m_a.fit(boot)
            fc_a = m_a.predict(future)
            yhat_a = fc_a.set_index('ds')['yhat']
            yhat_a = yhat_a[~yhat_a.index.duplicated(keep='first')]
        except Exception:
            fail_a += 1
            continue

        # 模型 B：无 holidays
        try:
            m_b = Prophet(yearly_seasonality=False, weekly_seasonality=True,
                          daily_seasonality=False,
                          changepoint_prior_scale=0.05, seasonality_prior_scale=10, interval_width=0.95)
            m_b.fit(boot)
            fc_b = m_b.predict(future)
            yhat_b = fc_b.set_index('ds')['yhat']
            yhat_b = yhat_b[~yhat_b.index.duplicated(keep='first')]
        except Exception:
            fail_b += 1
            continue

        # 窗口期内的差值
        win_start = d_holiday - pd.Timedelta(days=0)
        win_end   = d_holiday + pd.Timedelta(days=window_days)
        mask = (yhat_a.index >= win_start) & (yhat_a.index <= win_end)
        if mask.sum() == 0:
            fail_window += 1
            continue
        # 实际值：因 boot 有重复日期，先聚合到每天
        boot_daily = boot.groupby('ds')['y'].sum()
        act = boot_daily.reindex(yhat_a.index[mask], fill_value=0).sum()
        pred_with    = yhat_a[mask].sum()
        pred_without = yhat_b[mask].sum()
        diffs.append(pred_with - pred_without)

    diffs = np.array(diffs)
    if len(diffs) == 0:
        return None
    if len(diffs) < n_boot:
        print(f'    [warn] {holiday_name} {holiday_date_str}: 仅 {len(diffs)}/{n_boot} 次成功'
              f'（失败 A={fail_a}, B={fail_b}, 窗口={fail_window}）', flush=True)
    return {
        '节日':       holiday_name,
        '日期':       holiday_date_str,
        '指标':       value_col,
        '均值差':     float(diffs.mean()),
        '中位数差':   float(np.median(diffs)),
        'CI下限(2.5%)':  float(np.percentile(diffs, 2.5)),
        'CI上限(97.5%)': float(np.percentile(diffs, 97.5)),
        'p值(双侧)':  float(2 * min((diffs <= 0).mean(), (diffs >= 0).mean())),
        'n_boot_target': n_boot,
        'n_boot_valid':  len(diffs),
        'n_boot_fail_a': fail_a,
        'n_boot_fail_b': fail_b,
    }


def run_bootstrap(n_boot=200, n_holidays=None, value_cols=('总消费额', '新注册数')):
    """主入口：跑所有节日的 Bootstrap

    Parameters
    ----------
    n_holidays : int or None
        - None: 跑全部 37 个节日
        - int: 跑前 N 个代表性节日（按业务重要性）
        - list: 指定的 [(date_str, name), ...] 节日列表
    """
    print('[bootstrap] 加载数据...', flush=True)
    data = build_q1_data()
    daily = data['daily_full']

    # 决定要跑的节日
    if n_holidays is None:
        holidays_to_test = ALL_HOLIDAYS
    elif isinstance(n_holidays, list):
        holidays_to_test = n_holidays
    else:
        # 默认选 6 个代表性节日（覆盖各类）
        rep_dates = {'2025-01-29', '2025-02-14', '2025-05-01', '2025-06-18',
                     '2025-10-01', '2025-11-11'}
        holidays_to_test = [(d, n) for d, n in ALL_HOLIDAYS if d in rep_dates]
        if len(holidays_to_test) == 0:
            holidays_to_test = ALL_HOLIDAYS[:n_holidays]

    rows = []
    for vc in value_cols:
        print(f'\n[bootstrap] 指标={vc}, 节日数={len(holidays_to_test)}, n_boot={n_boot}', flush=True)
        for i, (d_str, name) in enumerate(holidays_to_test):
            print(f'  [{i+1}/{len(holidays_to_test)}] {name} {d_str} ...', flush=True)
            r = _bootstrap_one_holiday(daily, vc, d_str, name, n_boot=n_boot, seed=42+i)
            if r:
                rows.append(r)

    df = pd.DataFrame(rows)
    out_csv = os.path.join(TABLES_DIR, 'q1_bootstrap_ci.csv')
    df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'\n[save] {out_csv}', flush=True)

    # 画图：每个节日的均值差 + 置信区间
    plt = apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=False)

    for ax, vc in zip(axes, value_cols):
        sub = df[df['指标'] == vc].sort_values('均值差')
        x = np.arange(len(sub))
        ax.errorbar(sub['均值差'], x,
                    xerr=[sub['均值差'] - sub['CI下限(2.5%)'], sub['CI上限(97.5%)'] - sub['均值差']],
                    fmt='o', color=COLORS['primary'], ecolor=COLORS['secondary'], capsize=3)
        ax.axvline(0, color='red', linestyle='--', alpha=0.5, label='零线')
        ax.set_yticks(x)
        ax.set_yticklabels([f'{r["节日"]} {r["日期"]}' for _, r in sub.iterrows()], fontsize=7)
        ax.set_title(f'{vc}：节日贡献 Bootstrap 95% CI (n={n_boot})', fontsize=11)
        ax.set_xlabel('节日效应差值（带-无）')
        ax.grid(True, alpha=0.3)
        ax.legend()

    fig.suptitle('问题 1：节日效应 Bootstrap 显著性检验', fontsize=13, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, 'q1_bootstrap_ci', subdir='results')
    plt.close(fig)

    # 汇总
    print('\n=== Bootstrap 汇总 ===', flush=True)
    sig = df[df['p值(双侧)'] < 0.05]
    print(f'总检验数: {len(df)}, 显著 (p<0.05): {len(sig)}', flush=True)
    print(sig[['日期', '节日', '指标', '均值差', 'p值(双侧)']].to_string(index=False), flush=True)

    return df


if __name__ == '__main__':
    import sys as _sys
    n_boot = int(_sys.argv[1]) if len(_sys.argv) > 1 else 200
    run_bootstrap(n_boot=n_boot, n_holidays=None)
