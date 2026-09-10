"""Q1 Prophet 时间序列分解 + 假日反事实模拟

技术路线：
1. 对每日消费额和注册量两个指标分别建立 Prophet 模型
2. 加入中国法定节假日和主要购物节作为节假日因子
3. 反事实模拟：剔除 holidays 参数后重新预测 → 得到"无假日"基线
4. 实际值 - 无假日预测值 = 节日增量贡献
5. 分解各节日的贡献百分比

输出：
- q1_prophet_decomposition.png：分解图
- q1_holiday_contribution.csv：各节日贡献
- q1_counterfactual_analysis.md：反事实分析文字
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
from src.plot_style import apply_style, save_fig


# 所有自定义节日
ALL_HOLIDAYS = list(HOLIDAYS_2025) + [(d, '购物节') for d in SHOPPING_FESTIVALS_2025]


def make_holidays_df(holidays):
    """Prophet格式的holidays dataframe"""
    return pd.DataFrame({
        'holiday': [h[1] for h in holidays],
        'ds': pd.to_datetime([h[0] for h in holidays]),
        'lower_window': 0,
        'upper_window': 1,  # 节日当天 + 后1天的影响
    })


def fit_prophet(daily_df, value_col, holidays_df=None):
    """拟合Prophet模型
    daily_df: [日期, value_col]
    """
    df = daily_df[['日期', value_col]].copy()
    df.columns = ['ds', 'y']
    df = df.sort_values('ds').reset_index(drop=True)

    model = Prophet(
        yearly_seasonality=False,    # 改-3: 一年数据不足以学年度季节（避免 Prophet 警告）
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,  # 趋势变化敏感度
        seasonality_prior_scale=10,
        holidays=holidays_df,
        holidays_prior_scale=20,
        interval_width=0.95,           # 改-3: 输出 yhat_lower / yhat_upper（95% 置信区间）
    )
    model.fit(df)
    return model


def decompose_series(daily_series, value_col, title='消费额', suffix=''):
    """分解单个时间序列并画图"""
    print(f'[q1-prophet] decomposing {title}...', flush=True)
    holidays_df = make_holidays_df(ALL_HOLIDAYS)
    model = fit_prophet(daily_series, value_col, holidays_df)

    # 1) 正常预测
    future = daily_series[['日期']].copy()
    future.columns = ['ds']
    forecast = model.predict(future)

    # 2) 反事实预测：不带节假日
    model_cf = fit_prophet(daily_series, value_col, None)
    forecast_cf = model_cf.predict(future)

    # 3) 合并对比
    compare = pd.DataFrame({
        '日期': daily_series['日期'].values,
        '实际值': daily_series[value_col].values,
        '正常预测': forecast['yhat'].values,
        '正常预测下界': forecast['yhat_lower'].values,    # 改-3: 95% 置信区间下界
        '正常预测上界': forecast['yhat_upper'].values,    # 改-3: 95% 置信区间上界
        '无假日预测': forecast_cf['yhat'].values,
    })
    compare['节日贡献(实际-无假日)'] = compare['实际值'] - compare['无假日预测']
    compare['节日贡献百分比'] = compare['节日贡献(实际-无假日)'] / compare['无假日预测'].replace(0, np.nan) * 100
    # 改-3: 反事实置信区间（无假日模型）
    compare['无假日预测下界'] = forecast_cf['yhat_lower'].values
    compare['无假日预测上界'] = forecast_cf['yhat_upper'].values
    compare['节日贡献下界'] = compare['实际值'] - compare['无假日预测上界']   # 贡献的下界（保守估计）
    compare['节日贡献上界'] = compare['实际值'] - compare['无假日预测下界']   # 贡献的上界

    # 画图
    plt = apply_style()
    fig, axes = plt.subplots(4, 1, figsize=(13, 12))

    # (1) 原始 + 预测（含置信区间）
    ax = axes[0]
    ax.plot(compare['日期'], compare['实际值'], label='实际', linewidth=1.0, color='#2E86AB')
    ax.plot(compare['日期'], compare['正常预测'], label='Prophet预测', linewidth=1.0, alpha=0.7, color='#F18F01')
    ax.plot(compare['日期'], compare['无假日预测'], label='反事实(无假日)', linewidth=1.0, alpha=0.7, linestyle='--', color='#A23B72')
    # 改-3: 置信区间
    ax.fill_between(compare['日期'], forecast['yhat_lower'], forecast['yhat_upper'],
                    color='#F18F01', alpha=0.15, label='95% 置信区间')
    ax.set_title(f'(a) {title} 实际 vs 预测 vs 反事实模拟', fontsize=12)
    ax.set_ylabel(value_col)
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3)

    # (2) 趋势 + 季节性
    ax = axes[1]
    c1 = '#2E86AB'
    ax.plot(forecast['ds'], forecast['trend'], label='趋势', color=c1)
    if 'yearly' in forecast.columns:
        ax.plot(forecast['ds'], forecast['yearly'], label='年度季节性', color='#F18F01')
    ax.plot(forecast['ds'], forecast['weekly'], label='周季节性', color='#A23B72')
    if 'holidays' in forecast.columns:
        ax.plot(forecast['ds'], forecast['holidays'], label='节假日效应', color='#06A77D')
    ax.set_title('(b) 序列成分分解', fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # (3) 节日贡献
    ax = axes[2]
    ax.bar(compare['日期'], compare['节日贡献(实际-无假日)'],
           color=np.where(compare['节日贡献(实际-无假日)'] >= 0, '#06A77D', '#D62246'),
           width=1.5)
    ax.axhline(0, color='black', linewidth=0.5)
    ax.set_title('(c) 每日节日贡献 = 实际 - 无假日预测', fontsize=12)
    ax.set_ylabel('增量')
    ax.grid(True, alpha=0.3)

    # (4) 残差
    ax = axes[3]
    resid = compare['实际值'] - compare['正常预测']
    ax.plot(compare['日期'], resid, linewidth=0.8)
    ax.axhline(0, color='red', linestyle='--', alpha=0.5)
    ax.set_title('(d) 残差 = 实际 - 正常预测', fontsize=12)
    ax.set_ylabel('残差')
    ax.grid(True, alpha=0.3)

    fig.suptitle(f'问题1：{title}时间序列分解与假日反事实分析', fontsize=14, fontweight='bold')
    fig.tight_layout()

    out_png = os.path.join(FIGURES_DIR, f'q1_prophet_{suffix}.png')
    save_fig(fig, f'q1_prophet_{suffix}', subdir='results')
    plt.close(fig)

    return compare, forecast


def holiday_contribution(compare):
    """计算每个节日的贡献度"""
    print('[q1-prophet] 计算各节日贡献...', flush=True)
    rows = []
    for d_str, name in ALL_HOLIDAYS:
        d = pd.to_datetime(d_str)
        # 包含节日 ±1 天的窗口
        window = compare[(compare['日期'] >= d - pd.Timedelta(days=0)) &
                         (compare['日期'] <= d + pd.Timedelta(days=1))]
        if len(window) > 0:
            act = window['实际值'].sum()
            cf = window['无假日预测'].sum()
            contrib = act - cf
            contrib_pct = contrib / cf * 100 if cf > 0 else 0
            rows.append({
                '日期': d_str,
                '节日': name,
                '窗口实际值': round(act, 2),
                '窗口无假日预测': round(cf, 2),
                '节日贡献绝对值': round(contrib, 2),
                '节日贡献百分比': round(contrib_pct, 2),
            })
    return pd.DataFrame(rows)


def holiday_box_plot(data):
    """绘制节假日 vs 工作日 箱线图"""
    print('[q1-prophet] 节假日vs工作日对比...', flush=True)
    daily = data['daily_full'].copy()
    daily['星期几'] = daily['日期'].dt.dayofweek

    # 标节日
    holiday_dates = set([d for d, _ in ALL_HOLIDAYS])
    daily['是否节日'] = daily['日期'].isin(holiday_dates)

    # 拆分
    festival = daily[daily['是否节日']]
    normal = daily[~daily['是否节日'] & (daily['星期几'] < 5)]  # 工作日
    weekend = daily[~daily['是否节日'] & (daily['星期几'] >= 5)]

    plt = apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    for ax, col, title in zip(axes, ['总消费额', '新注册数'],
                              ['(a) 节假日 vs 工作日 消费额分布',
                               '(b) 节假日 vs 工作日 注册量分布']):
        data_to_plot = [
            festival[col].dropna(),
            normal[col].dropna(),
            weekend[col].dropna(),
        ]
        bp = ax.boxplot(data_to_plot, labels=['节假日', '工作日', '周末'],
                        patch_artist=True, showmeans=True)
        for patch, color in zip(bp['boxes'], ['#F18F01', '#2E86AB', '#A23B72']):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)
        ax.set_title(title, fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.set_ylabel(col)

    fig.suptitle('问题1：节假日效应对比分析', fontsize=14, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, 'q1_holiday_boxplot', subdir='results')
    plt.close(fig)


def run_prophet_analysis():
    print('[q1-prophet] 加载数据...', flush=True)
    data = build_q1_data()

    # 1) 消费额序列分解
    cmp_cost, fc_cost = decompose_series(
        data['daily_full'], '总消费额', '消费额（元）', 'cost'
    )

    # 2) 注册量序列分解
    cmp_reg, fc_reg = decompose_series(
        data['daily_full'], '新注册数', '日新注册数（人）', 'reg'
    )

    # 3) 节日贡献
    contrib_cost = holiday_contribution(cmp_cost)
    contrib_reg = holiday_contribution(cmp_reg)

    contrib_cost['指标'] = '消费额'
    contrib_reg['指标'] = '注册量'
    contrib_all = pd.concat([contrib_cost, contrib_reg], ignore_index=True)

    out_csv = os.path.join(TABLES_DIR, 'q1_holiday_contribution.csv')
    contrib_all.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'[save] {out_csv}', flush=True)

    # 4) 节假日箱线图
    holiday_box_plot(data)

    # 5) 汇总
    total_cost_contrib = cmp_cost['节日贡献(实际-无假日)'].sum()
    total_reg_contrib = cmp_reg['节日贡献(实际-无假日)'].sum()
    total_cost = cmp_cost['实际值'].sum()
    total_reg = cmp_reg['实际值'].sum()

    print('\n=== 假日效应汇总 ===', flush=True)
    print(f'消费额总增量: {total_cost_contrib:+.0f} 元 ({total_cost_contrib/total_cost*100:+.2f}%)', flush=True)
    print(f'注册量总增量: {total_reg_contrib:+.0f} 人 ({total_reg_contrib/total_reg*100:+.2f}%)', flush=True)

    return contrib_all, cmp_cost, cmp_reg


if __name__ == '__main__':
    run_prophet_analysis()
