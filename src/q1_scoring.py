"""Q1 合理性指标评分系统

采用4个一级指标 × 多个二级指标的评分体系
权重分配：设计质量20% + 关键词管理30% + 出价策略25% + 投放时间25%
每个二级指标换算为0-100分

最终输出：
- q1_indicators.csv：所有指标明细
- q1_score.json：综合评分结果
- q1_score_breakdown.csv：评分明细
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import numpy as np
import pandas as pd

from src.q1_data_prep import build_q1_data
from src.utils import TABLES_DIR, ensure_dir


# ============= 工具：min-max 标准化到 0~100 =============
def min_max_score(x, ideal_low=True, x_min=None, x_max=None):
    """x 数值序列转 0~100 分
    ideal_low=True：值越小越好（如跳出率、问题词占比）
    """
    x = np.array(x, dtype=float)
    if x_min is None:
        x_min, x_max = np.nanmin(x), np.nanmax(x)
    rng = (x_max - x_min) if (x_max != x_min) else 1.0
    s = (x - x_min) / rng * 100.0
    if ideal_low:
        s = 100 - s
    return np.clip(s, 0, 100), x_min, x_max


# ============= 一级指标评分函数 =============

def score_design_quality(data):
    """5.1.1 设计质量与创意

    二级指标：
    - 单元上方位占比：合理值0.4-0.7
    - 上方位CTR：越高越好
    - 上方位CPC vs 整体CPC的倍数：1.0左右理想（不盲追首位）
    - 方案结构：基尼系数衡量关键词分配的均衡度
    """
    plan_total = data['plan_total']
    unit_total = data['unit_total']

    # 1) 单元平均上方位占比
    unit_total = unit_total.copy()
    unit_total['上方位占比'] = unit_total['上方位展现量'] / unit_total['展现量'].replace(0, np.nan)
    avg_top = unit_total['上方位占比'].mean()

    # 理想区间 0.4 - 0.7
    def pos_score(x, ideal_lo=0.4, ideal_hi=0.7):
        if pd.isna(x):
            return 0
        if ideal_lo <= x <= ideal_hi:
            return 100
        d = min(abs(x - ideal_lo), abs(x - ideal_hi))
        return max(0, 100 - d * 200)  # 超出区间每0.5扣100分

    unit_total['上方位占比评分'] = unit_total['上方位占比'].apply(pos_score)
    design_indicators = {
        '单元上方位占比均值': round(avg_top, 4),
        '上方位占比评分': round(unit_total['上方位占比评分'].mean(), 1),
        '上方位占比区间': f"[{unit_total['上方位占比'].min():.3f}, {unit_total['上方位占比'].max():.3f}]",
    }

    # 2) 上方位CTR
    dfc = data['campaign_daily']
    dfc['上方位CTR_valid'] = dfc['上方位CTR'].where(dfc['上方位展现量'] > 0)
    top_ctr = dfc['上方位CTR_valid'].mean()
    ctr_score, ctr_min, ctr_max = min_max_score(
        dfc['上方位CTR_valid'].fillna(0).values,
        ideal_low=False
    )
    design_indicators['上方位CTR均值'] = round(top_ctr, 4)
    design_indicators['上方位CTR评分'] = round(ctr_score.mean(), 1)

    # 3) 上方位CPC倍数（过高说明盲追首位）
    dfc['上方位CPC_valid'] = dfc['上方位CPC'].where(dfc['上方位点击量'] > 0)
    dfc['上方位CPC倍数'] = dfc['上方位CPC_valid'] / dfc['CPC'].replace(0, np.nan)
    avg_ratio = dfc['上方位CPC倍数'].dropna().mean()
    design_indicators['上方位CPC倍数均值'] = round(avg_ratio, 3)
    ratio_score, _, _ = min_max_score(
        dfc['上方位CPC倍数'].dropna().fillna(avg_ratio).values,
        ideal_low=True  # 倍数越小越好
    )
    design_indicators['上方位CPC倍数评分'] = round(ratio_score.mean(), 1)

    # 4) 关键词分配均衡度（基尼系数）低更均匀
    plan_kw = plan_total[['方案ID', '关键词数']].copy().dropna()
    gini = gini_coefficient(plan_kw['关键词数'].values)
    design_indicators['关键词分布基尼系数'] = round(gini, 4)
    gini_score, _, _ = min_max_score([gini] * 5, ideal_low=True)
    design_indicators['关键词分布评分'] = round(gini_score[0], 1)

    # 综合得分（等权）
    design_indicators['综合评分'] = round(np.mean([
        design_indicators['上方位占比评分'],
        design_indicators['上方位CTR评分'],
        design_indicators['上方位CPC倍数评分'],
        design_indicators['关键词分布评分'],
    ]), 1)

    return design_indicators


def gini_coefficient(x):
    """基尼系数"""
    x = np.array(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return 0
    if x.min() < 0:
        x = x - x.min()
    total = x.sum()
    if total == 0:
        return 0
    x_sorted = np.sort(x)
    n = len(x)
    cum = np.cumsum(x_sorted) / total
    return (2 * np.sum((np.arange(1, n + 1) * x_sorted))) / (n * total) - (n + 1) / n


def score_keyword_management(data):
    """5.1.2 关键词管理与运用

    二级指标：
    - 有效率（有消费关键词 / 总关键词）：越高越好
    - 注册转化率分布：均值高+方差小
    - 高跳出率词占比：低好
    - 平均访问时长：长好
    - 长尾分布：Pareto（前20%消费占比）：合理集中度
    """
    dfk = data['keyword_total']

    # 1) 有效率
    effective_rate = dfk['有消费'].mean()
    eff_score, _, _ = min_max_score([effective_rate], ideal_low=False)
    indicators = {
        '关键词总数': len(dfk),
        '有消费关键词数': int(dfk['有消费'].sum()),
        '有效率': round(effective_rate, 4),
        '有效率评分': round(eff_score[0], 1),
    }

    # 2) CPC分布（避免极端高价）
    eff = dfk[dfk['有消费']]
    if len(eff) > 0:
        cpc_valid = eff['CPC'].dropna()
        cpc_median = cpc_valid.median()
        cpc_p90 = cpc_valid.quantile(0.9)
        indicators['CPC中位数'] = round(cpc_median, 3)
        indicators['CPC P90'] = round(cpc_p90, 3)

        # 离群高价词占比 > 5元
        high_cost_ratio = (cpc_valid > 5).mean()
        hc_score, _, _ = min_max_score([high_cost_ratio], ideal_low=True)
        indicators['高价词占比(>5元)'] = round(high_cost_ratio, 4)
        indicators['高价词评分'] = round(hc_score[0], 1)

    # 3) 跳出率分布
    bounce = eff['跳出率'].dropna() if '跳出率' in eff.columns else pd.Series()
    if len(bounce) > 0:
        avg_bounce = bounce.mean()
        bounce_score, _, _ = min_max_score([avg_bounce], ideal_low=True)
        indicators['跳出率均值'] = round(avg_bounce, 4)
        indicators['跳出率评分'] = round(bounce_score[0], 1)

        # 高跳出词占比 > 0.9
        high_bounce_ratio = (bounce > 0.9).mean()
        hb_score, _, _ = min_max_score([high_bounce_ratio], ideal_low=True)
        indicators['高跳出词占比'] = round(high_bounce_ratio, 4)
        indicators['高跳出评分'] = round(hb_score[0], 1)

    # 4) 平均访问时长
    if '平均访问时长_秒' in eff.columns:
        dur = eff['平均访问时长_秒'].dropna()
        if len(dur) > 0:
            avg_dur = dur.mean()
            dur_score, _, _ = min_max_score([avg_dur], ideal_low=False)
            indicators['平均访问时长_秒'] = round(avg_dur, 1)
            indicators['访问时长评分'] = round(dur_score[0], 1)

    # 5) 长尾分布集中度（前20%消费占比）
    cons = eff['消费额'].sort_values(ascending=False).values
    cumsum = np.cumsum(cons)
    total = cumsum[-1]
    top20 = cumsum[max(int(len(cons) * 0.2) - 1, 0)] / total
    # 0.5~0.7 算合理（既集中又不过度集中）
    def conc_score(x, ideal_lo=0.5, ideal_hi=0.7):
        if ideal_lo <= x <= ideal_hi:
            return 100
        d = min(abs(x - ideal_lo), abs(x - ideal_hi))
        return max(0, 100 - d * 200)
    indicators['前20%消费占比'] = round(top20, 4)
    indicators['集中度评分'] = round(conc_score(top20), 1)

    # 综合得分
    score_list = [
        indicators.get('有效率评分', 50),
        indicators.get('高价词评分', 50),
        indicators.get('跳出率评分', 50),
        indicators.get('高跳出评分', 50),
        indicators.get('访问时长评分', 50),
        indicators.get('集中度评分', 50),
    ]
    indicators['综合评分'] = round(np.mean(score_list), 1)

    return indicators


def score_bid_strategy(data):
    """5.1.3 出价策略与预算

    二级指标：
    - CPC分布集中度（IQR/median）
    - 上方位竞价渗透率：上方位消费/总消费
    - 预算使用节奏（CV）
    """
    dfc = data['campaign_daily']
    daily = data['daily_full']

    indicators = {}

    # 1) CPC 分布
    cpc_valid = dfc['CPC'].dropna()
    cpc_valid = cpc_valid[cpc_valid > 0]
    indicators['CPC均值'] = round(cpc_valid.mean(), 3)
    indicators['CPC标准差'] = round(cpc_valid.std(), 3)
    cv = cpc_valid.std() / cpc_valid.mean() if cpc_valid.mean() > 0 else 999
    # CV 越接近1的某区间越好：太大说明波动，过小可能不灵活
    cv_score = 100 - min(abs(cv - 0.5) * 100, 100)
    indicators['CPC变异系数'] = round(cv, 3)
    indicators['CPC稳定性评分'] = round(cv_score, 1)

    # 2) 上方位竞价渗透率
    top_consume_ratio = dfc['上方位消费额'].sum() / dfc['消费额'].sum()
    indicators['上方位消费占比'] = round(top_consume_ratio, 4)
    # 0.4~0.65 合理
    def ratio_score(x, lo=0.4, hi=0.65):
        if lo <= x <= hi:
            return 100
        return max(0, 100 - min(abs(x - lo), abs(x - hi)) * 200)
    indicators['上方位渗透评分'] = round(ratio_score(top_consume_ratio), 1)

    # 3) 预算使用节奏（月度CV）
    daily['月份'] = daily['日期'].dt.to_period('M')
    monthly_cost = daily.groupby('月份')['总消费额'].sum()
    cv_month = monthly_cost.std() / monthly_cost.mean()
    indicators['月度预算变异系数'] = round(cv_month, 3)
    # 越接近0.5（有一定节奏但不剧烈）越好
    mr_score = 100 - min(abs(cv_month - 0.5) * 100, 100)
    indicators['月度均匀度评分'] = round(mr_score, 1)

    # 4) 方案 CPC 一致性（方案间差异）
    plan_cpc = dfc.groupby('方案ID')['消费额'].sum() / dfc.groupby('方案ID')['点击量'].sum()
    plan_cpc_std = plan_cpc.std() / plan_cpc.mean()
    indicators['方案CPC差异'] = round(plan_cpc_std, 3)
    plan_score = 100 - min(plan_cpc_std * 100, 100)
    indicators['方案一致性评分'] = round(plan_score, 1)

    indicators['综合评分'] = round(np.mean([
        indicators['CPC稳定性评分'],
        indicators['上方位渗透评分'],
        indicators['月度均匀度评分'],
        indicators['方案一致性评分'],
    ]), 1)

    return indicators


def score_time_strategy(data):
    """5.1.4 投放策略与时间规律

    二级指标：
    - 月度消费/注册量的相关系数：越高投放→注册越准
    - 周内分布均匀度
    - 注册转化率稳定度
    - 季度内趋势的合理性
    """
    daily = data['daily_full'].copy()
    indicators = {}

    # 1) 消费-注册相关系数
    corr = daily[['总消费额', '新注册数']].corr().iloc[0, 1]
    indicators['消费注册相关系数'] = round(corr, 4)
    indicators['消费注册评分'] = round((corr + 1) / 2 * 100, 1)

    # 2) 周内分布均匀度（按星期几）
    daily['星期几'] = daily['日期'].dt.dayofweek
    weekly_cost = daily.groupby('星期几')['总消费额'].sum()
    cv_week = weekly_cost.std() / weekly_cost.mean()
    indicators['周内预算变异'] = round(cv_week, 3)
    wk_score = 100 - min(cv_week * 100, 100)
    indicators['周内均匀度评分'] = round(wk_score, 1)

    # 3) 注册转化率稳定度
    cv_cr = daily['注册转化率'].std() / daily['注册转化率'].mean()
    indicators['转化率变异系数'] = round(cv_cr, 3)
    cr_score = 100 - min(cv_cr * 50, 100)
    indicators['转化率稳定度评分'] = round(cr_score, 1)

    # 4) 注册量月度趋势合理性
    daily['月份'] = daily['日期'].dt.to_period('M')
    monthly_reg = daily.groupby('月份')['新注册数'].sum()
    # 若月度增长平稳（无暴跌），评高分
    monthly_diff = monthly_reg.diff().dropna()
    neg_ratio = (monthly_diff < 0).mean()
    indicators['月度注册下降月份占比'] = round(neg_ratio, 4)
    trend_score = 100 - min(neg_ratio * 150, 100)
    indicators['趋势评分'] = round(trend_score, 1)

    indicators['综合评分'] = round(np.mean([
        indicators['消费注册评分'],
        indicators['周内均匀度评分'],
        indicators['转化率稳定度评分'],
        indicators['趋势评分'],
    ]), 1)

    return indicators


def run_scoring():
    """执行所有评分"""
    print('[q1] 加载数据...', flush=True)
    data = build_q1_data()

    print('[q1] 1) 设计质量评分...', flush=True)
    s1 = score_design_quality(data)
    print('  评分 =', s1['综合评分'], flush=True)

    print('[q1] 2) 关键词管理评分...', flush=True)
    s2 = score_keyword_management(data)
    print('  评分 =', s2['综合评分'], flush=True)

    print('[q1] 3) 出价策略评分...', flush=True)
    s3 = score_bid_strategy(data)
    print('  评分 =', s3['综合评分'], flush=True)

    print('[q1] 4) 投放时间评分...', flush=True)
    s4 = score_time_strategy(data)
    print('  评分 =', s4['综合评分'], flush=True)

    # 权重分配
    weights = {
        '设计质量与创意':   0.20,
        '关键词管理与运用': 0.30,
        '出价策略与预算':   0.25,
        '投放策略与时间':   0.25,
    }
    overall = (
        weights['设计质量与创意']   * s1['综合评分'] +
        weights['关键词管理与运用'] * s2['综合评分'] +
        weights['出价策略与预算']   * s3['综合评分'] +
        weights['投放策略与时间']   * s4['综合评分']
    )

    # 评级
    if overall >= 85:
        grade = 'A (优秀)'
    elif overall >= 70:
        grade = 'B (良好)'
    elif overall >= 55:
        grade = 'C (一般)'
    else:
        grade = 'D (需改进)'

    result = {
        'overall_score': round(overall, 1),
        'grade': grade,
        'dimensions': {
            '设计质量与创意':   {'score': s1['综合评分'], 'weight': weights['设计质量与创意'],   'details': s1},
            '关键词管理与运用': {'score': s2['综合评分'], 'weight': weights['关键词管理与运用'], 'details': s2},
            '出价策略与预算':   {'score': s3['综合评分'], 'weight': weights['出价策略与预算'],   'details': s3},
            '投放策略与时间':   {'score': s4['综合评分'], 'weight': weights['投放策略与时间'],   'details': s4},
        },
    }

    # 保存
    ensure_dir(TABLES_DIR)
    out_json = os.path.join(TABLES_DIR, 'q1_score.json')
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'\n[save] {out_json}', flush=True)

    # 明细表
    rows = []
    for cat, info in result['dimensions'].items():
        d = info['details']
        for k, v in d.items():
            rows.append({'类别': cat, '指标': k, '值': v, '权重': info['weight']})
    df = pd.DataFrame(rows)
    out_csv = os.path.join(TABLES_DIR, 'q1_score_breakdown.csv')
    df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'[save] {out_csv}', flush=True)

    # 综合评分输出
    print('\n' + '=' * 40, flush=True)
    print(f'SEM投放策略合理性综合评分: {result["overall_score"]} / 100', flush=True)
    print(f'评级: {result["grade"]}', flush=True)
    print('=' * 40, flush=True)

    return result


if __name__ == '__main__':
    run_scoring()
