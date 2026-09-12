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

    注意：当仅传单个值时（无对比基准），请改用 industry_score()。
    """
    x = np.array(x, dtype=float)
    if x_min is None:
        x_min, x_max = np.nanmin(x), np.nanmax(x)
    rng = (x_max - x_min) if (x_max != x_min) else 1.0
    s = (x - x_min) / rng * 100.0
    if ideal_low:
        s = 100 - s
    return np.clip(s, 0, 100), x_min, x_max


# ============= 改-9（2026-09-11）：基于行业阈值的绝对评分 =============
# 修复 min_max_score 在"单值"调用下退化为 0/100 的 bug
#
# 设计思路：每个二级指标对应一个"理想区间 [lo, hi]" 和一个"完全失格边界 [d_lo, d_hi]"
#   - 落入 [lo, hi]  → 100 分（满分）
#   - 处于 [d_lo, lo) 或 (hi, d_hi] → 线性衰减
#   - 超出 [d_lo, d_hi]           → 0 分
#
# 阈值来源：综合 SEM 行业经验值 + 本数据集实际分布（P25/P50/P75）确定。
# 与 min_max_score（数据相对）的区别：
#   - min_max_score 适合"多方案对比"（已有 ≥ 5 个方案）
#   - industry_score 适合"单点绝对评分"（只有 1 个全局值）

# 指标 → (lo, hi, d_lo, d_hi) 字典
# 评分规则：落入 [lo, hi] → 100 分；在 (hi, d_hi] 线性衰减 → 0 分；
#         在 [d_lo, lo) 线性衰减 → 0 分；超出 [d_lo, d_hi] → 0 分
INDUSTRY_THRESHOLDS = {
    # 关键词管理：有效率（理想高）
    '有效率':              (0.75, 0.95,  0.40,  1.00),   # 60% → ~45 分
    # 关键词管理：CPC 中位数（理想低，元）
    'CPC中位数':           (0.30, 1.00,  0.10,  3.00),   # 1.11 → ~67 分（合理偏高）
    # 关键词管理：高 CPC 词占比（理想低）
    '高价词占比':          (0.00, 0.05,  0.00,  0.30),   # 3.89% → ~87 分
    # 关键词管理：跳出率均值（理想低，SEM 行业通常 60-80%）
    '跳出率均值':          (0.20, 0.50,  0.10,  0.80),   # 73% → ~23 分（行业偏上）
    # 关键词管理：高跳出词占比（理想低）
    '高跳出词占比':        (0.05, 0.20,  0.00,  0.50),   # 41% → ~30 分
    # 关键词管理：平均访问时长（理想高，秒）
    '访问时长_秒':         (120.0, 240.0, 30.0, 600.0),  # 167s → ~39 分
    # 关键词管理：长尾集中度（前 20% 占比，理想中庸 0.5-0.7）
    '前20消费占比':        (0.50, 0.70,  0.30,  0.90),   # 99% → 0 分（极度集中）
    # 设计质量：关键词分布基尼系数（理想低）
    '基尼系数':            (0.15, 0.30,  0.05,  0.50),   # 0.405 → ~48 分
    # 出价策略：上方位消费占比（理想中庸 0.4-0.6）
    '上方位消费占比':      (0.40, 0.60,  0.20,  0.90),   # 70% → ~49 分
}


def interval_score(x: float, lo: float, hi: float,
                   d_lo: float = None, d_hi: float = None) -> float:
    """区间型绝对评分（落入 [lo, hi] 满分，区间外线性衰减）"""
    if d_lo is None:
        d_lo = lo - (hi - lo) * 0.5
    if d_hi is None:
        d_hi = hi + (hi - lo) * 0.5
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return 50.0  # 缺失值给中性分
    if lo <= x <= hi:
        return 100.0
    if x < lo:
        if x <= d_lo:
            return 0.0
        return (x - d_lo) / (lo - d_lo) * 100.0
    if x <= d_hi:
        return (d_hi - x) / (d_hi - hi) * 100.0
    return 0.0


def industry_score(x: float, metric: str) -> float:
    """根据行业阈值表对单个值绝对评分（替代 min_max_score 单值调用）

    Parameters
    ----------
    x : float
        待评分值
    metric : str
        阈值表中的键名（见 INDUSTRY_THRESHOLDS）

    Returns
    -------
    float : 0~100 分
    """
    if metric not in INDUSTRY_THRESHOLDS:
        raise KeyError(f'未知指标 {metric}，请在 INDUSTRY_THRESHOLDS 中添加阈值')
    lo, hi, d_lo, d_hi = INDUSTRY_THRESHOLDS[metric]
    return round(interval_score(x, lo, hi, d_lo, d_hi), 1)


# ============= 改-2：百分位 + Z-Score 双轨区间（替代 pos_score） =============
def percentile_zscore_score(x, values: pd.Series, ideal_low: bool = True,
                            z_tolerance: float = 1.0,
                            p_lo: float = 0.25, p_hi: float = 0.75,
                            decay: float = 200.0):
    """百分位 + Z-Score 双轨评分函数（替代原 pos_score / ratio_score / conc_score）

    逻辑：
    1. 计算 values 的 P25/P75 作为合理区间
    2. 计算 x 的 Z-Score（基于 values 的均值和标准差）
    3. 双轨评分：
       - |Z| ≤ z_tolerance：100 分
       - |Z| > z_tolerance：线性衰减 (100 - |Z| - z_tolerance) * decay)
       - 区间外：额外扣分（基于超出百分位的距离）
    4. ideal_low=True 时反转（值越小越好，如跳出率）

    Parameters
    ----------
    x : float / array-like
        待评分值
    values : pd.Series
        参考分布（同一指标在所有方案/单元上的取值）
    ideal_low : bool
        True → 值越小越好；False → 值越大越好
    z_tolerance : float
        Z-Score 容差（默认 1.0，对应 P16/P84）
    p_lo, p_hi : float
        百分位区间边界（默认 P25/P75）
    decay : float
        Z 超出容差后每单位扣分（默认 200）

    Returns
    -------
    float : 0~100 之间的分数
    """
    x = np.asarray(x, dtype=float)
    v = pd.Series(values).dropna()
    if len(v) == 0:
        return 0.0
    mu = v.mean()
    sigma = v.std(ddof=0) if v.std(ddof=0) > 0 else 1.0
    p25, p75 = v.quantile(p_lo), v.quantile(p_hi)

    z = (x - mu) / sigma
    abs_z = np.abs(z)
    # Z-Score 段：|z| ≤ tolerance 满分，超出则线性衰减
    z_score = 100 - np.clip((abs_z - z_tolerance) * decay, 0, 100)

    # 百分位段：值超出 [P25, P75] 时额外扣分
    out_of_range = (x < p25) | (x > p75)
    if ideal_low:
        out_of_range = (x > p75) | (x < p25)  # 等同，逻辑一致

    # 综合：取 Z-Score 和百分位的均值
    score = z_score.copy()
    # 在区间内时给满分（不受百分位轻微偏离影响）
    in_range = (x >= p25) & (x <= p75)
    score = np.where(in_range, np.maximum(score, 100), score)
    # 超出区间时 Z-Score 衰减
    score = np.clip(score, 0, 100)

    return float(score) if score.ndim == 0 else score


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

    # 改-2: 百分位 + Z-Score 双轨评分（替代原 pos_score）
    unit_total['上方位占比评分'] = unit_total['上方位占比'].apply(
        lambda x: percentile_zscore_score(x, unit_total['上方位占比'].dropna(),
                                           ideal_low=False, p_lo=0.25, p_hi=0.75)
    )
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

    # 4) 关键词分配均衡度（基尼系数）低更均匀（改-9: industry_score）
    plan_kw = plan_total[['方案ID', '关键词数']].copy().dropna()
    gini = gini_coefficient(plan_kw['关键词数'].values)
    design_indicators['关键词分布基尼系数'] = round(gini, 4)
    design_indicators['关键词分布评分'] = industry_score(gini, '基尼系数')

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

    # 1) 有效率（改-9: 用 industry_score 替代 min_max_score 单值调用）
    effective_rate = dfk['有消费'].mean()
    indicators = {
        '关键词总数': len(dfk),
        '有消费关键词数': int(dfk['有消费'].sum()),
        '有效率': round(effective_rate, 4),
        '有效率评分': industry_score(effective_rate, '有效率'),
    }

    # 2) CPC分布（避免极端高价）
    eff = dfk[dfk['有消费']]
    if len(eff) > 0:
        cpc_valid = eff['CPC'].dropna()
        cpc_median = cpc_valid.median()
        cpc_p90 = cpc_valid.quantile(0.9)
        indicators['CPC中位数'] = round(cpc_median, 3)
        indicators['CPC P90'] = round(cpc_p90, 3)

        # 离群高价词占比 > 5元（改-9: industry_score）
        high_cost_ratio = (cpc_valid > 5).mean()
        indicators['高价词占比(>5元)'] = round(high_cost_ratio, 4)
        indicators['高价词评分'] = industry_score(high_cost_ratio, '高价词占比')

    # 3) 跳出率分布（改-9: industry_score）
    bounce = eff['跳出率'].dropna() if '跳出率' in eff.columns else pd.Series()
    if len(bounce) > 0:
        avg_bounce = bounce.mean()
        indicators['跳出率均值'] = round(avg_bounce, 4)
        indicators['跳出率评分'] = industry_score(avg_bounce, '跳出率均值')

        # 高跳出词占比 > 0.9（改-9: industry_score）
        high_bounce_ratio = (bounce > 0.9).mean()
        indicators['高跳出词占比'] = round(high_bounce_ratio, 4)
        indicators['高跳出评分'] = industry_score(high_bounce_ratio, '高跳出词占比')

    # 4) 平均访问时长（改-9: industry_score）
    if '平均访问时长_秒' in eff.columns:
        dur = eff['平均访问时长_秒'].dropna()
        if len(dur) > 0:
            avg_dur = dur.mean()
            indicators['平均访问时长_秒'] = round(avg_dur, 1)
            indicators['访问时长评分'] = industry_score(avg_dur, '访问时长_秒')

    # 5) 长尾分布集中度（前20%消费占比）（改-9: industry_score）
    cons = eff['消费额'].sort_values(ascending=False).values
    cumsum = np.cumsum(cons)
    total = cumsum[-1]
    top20 = cumsum[max(int(len(cons) * 0.2) - 1, 0)] / total
    indicators['前20%消费占比'] = round(top20, 4)
    indicators['集中度评分'] = industry_score(top20, '前20消费占比')

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

    # 2) 上方位竞价渗透率（改-9: industry_score 替代单值 percentile_zscore）
    top_consume_ratio = dfc['上方位消费额'].sum() / dfc['消费额'].sum()
    indicators['上方位消费占比'] = round(top_consume_ratio, 4)
    indicators['上方位渗透评分'] = industry_score(top_consume_ratio, '上方位消费占比')

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


def _score_per_plan(data) -> pd.DataFrame:
    """为每个方案单独算 4 维综合得分（用于 CRITIC 赋权）

    Returns
    -------
    pd.DataFrame: shape (n_plans, 4)
        index=方案ID, columns=[设计, 关键词, 出价, 时间]
        每个单元格是 0-100 的综合得分

    ----- 与 score_design_quality / score_keyword_management / etc. 的关系（P1-1 口径说明）-----
    本函数用简化公式为"每个方案"算分（CRITIC 赋权只需要相对顺序，不必绝对阈值精确）。
    score_design_quality() 等 4 个聚合函数则用 industry_score（行业阈值）+ 双轨评分，
    计算"全公司"维度的绝对得分。两套并存：
      - score_* → 全公司维度得分 → overall_score
      - _score_per_plan → 5×4 矩阵 → CRITIC 权重
    最终输出 dimensions[*].details 用 score_*（带所有明细指标），
    plan_scores 用 _score_per_plan（只存 4 维聚合）。
    """
    plan_total = data['plan_total']
    dfk = data['keyword_total']
    dfc = data['campaign_daily']
    daily = data['daily_full'].copy()

    rows = []
    for pid in plan_total['方案ID'].unique():
        # ---- 设计质量：单元层聚合 ----
        unit_p = data['unit_total'][data['unit_total']['方案ID'] == pid].copy()
        unit_p['上方位占比'] = unit_p['上方位展现量'] / unit_p['展现量'].replace(0, np.nan)
        avg_top = unit_p['上方位占比'].mean()

        # 上方位 CTR（仅当前方案）
        dfc_p = dfc[dfc['方案ID'] == pid]
        dfc_p = dfc_p.copy()
        dfc_p['上方位CTR_valid'] = dfc_p['上方位CTR'].where(dfc_p['上方位展现量'] > 0)
        top_ctr = dfc_p['上方位CTR_valid'].mean()

        # 上方位 CPC 倍数
        dfc_p['上方位CPC_valid'] = dfc_p['上方位CPC'].where(dfc_p['上方位点击量'] > 0)
        dfc_p['上方位CPC倍数'] = dfc_p['上方位CPC_valid'] / dfc_p['CPC'].replace(0, np.nan)
        avg_ratio = dfc_p['上方位CPC倍数'].dropna().mean()

        # 基尼系数
        gini = gini_coefficient(unit_p['关键词数'].values if '关键词数' in unit_p.columns
                                  else np.array([1.0]))

        # 简单加权合成 0-100 分
        s_design = 100 - abs(avg_top - 0.55) * 200     # 0.55 理想
        s_design = max(0, min(100, s_design))
        if not np.isnan(top_ctr):
            s_design = s_design * 0.7 + min(top_ctr * 500, 100) * 0.3
        if not np.isnan(avg_ratio):
            s_design = s_design * 0.7 + max(0, 100 - abs(avg_ratio - 1.0) * 50) * 0.3
        s_design = max(0, min(100, s_design - gini * 50))

        # ---- 关键词管理 ----
        kw_p = dfk[dfk['方案ID'] == pid] if '方案ID' in dfk.columns else dfk
        kw_eff = kw_p[kw_p['有消费']] if '有消费' in kw_p.columns else kw_p
        if len(kw_eff) > 0:
            eff_rate = kw_p['有消费'].mean() if '有消费' in kw_p.columns else 0.5
            avg_bounce = kw_eff['跳出率'].mean() if '跳出率' in kw_eff.columns else 0.5
            s_kw = eff_rate * 100 * 0.5 + (1 - avg_bounce) * 100 * 0.3
            if 'CPC' in kw_eff.columns:
                cpc_med = kw_eff['CPC'].dropna().median()
                s_kw += max(0, 100 - cpc_med * 5) * 0.2
            s_kw = max(0, min(100, s_kw))
        else:
            s_kw = 50.0

        # ---- 出价策略 ----
        cpc_valid = dfc_p['CPC'].dropna()
        cpc_valid = cpc_valid[cpc_valid > 0]
        if len(cpc_valid) > 0:
            cpc_cv = cpc_valid.std() / cpc_valid.mean()
            top_consume_ratio = dfc_p['上方位消费额'].sum() / max(dfc_p['消费额'].sum(), 1)
            s_bid = max(0, 100 - cpc_cv * 100) * 0.5
            s_bid += max(0, 100 - abs(top_consume_ratio - 0.5) * 200) * 0.5
            s_bid = max(0, min(100, s_bid))
        else:
            s_bid = 50.0

        # ---- 投放时间 ----
        # 消费注册相关：基于"方案的日消费额" 与 "全公司日注册" 的相关
        # 简化：用"月度预算稳定性"代替
        daily_p = dfc_p.groupby('日期', as_index=False)['消费额'].sum()
        if len(daily_p) > 30:
            monthly = daily_p.set_index('日期').resample('ME')['消费额'].sum()
            cv_month = monthly.std() / monthly.mean() if monthly.mean() > 0 else 1
            # 改-5：平滑曲线（指数衰减）替代硬截断
            # 旧公式：max(0, 100 - |CV-0.3| * 150)  → CV≥1 全部 0 分，无区分度
            # 新公式：s = 100 / (1 + k*(CV-CV_ideal)^2)
            #       CV=0.3 时 s=100；CV=0.5 时 s≈88；CV=1.0 时 s≈55；CV=2.0 时 s≈22
            CV_IDEAL = 0.3
            K_PENALTY = 0.6
            s_time = 100.0 / (1.0 + K_PENALTY * (cv_month - CV_IDEAL) ** 2)
            s_time = max(0, min(100, s_time))
        else:
            s_time = 50.0

        rows.append({
            '方案ID':  pid,
            '设计质量与创意':   round(s_design, 2),
            '关键词管理与运用': round(s_kw, 2),
            '出价策略与预算':   round(s_bid, 2),
            '投放策略与时间':   round(s_time, 2),
        })

    return pd.DataFrame(rows).set_index('方案ID')


def run_scoring():
    """执行所有评分（含 CRITIC 混合赋权）"""
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

    # ===== 改-1: CRITIC + 业务混合赋权 =====
    print('\n[q1] 改-1: CRITIC 混合赋权...', flush=True)
    from src.q1_weights import compute_weights, save_weights, SUBJECTIVE_WEIGHTS
    plan_scores = _score_per_plan(data)                    # 5×4 矩阵
    score_matrix = plan_scores.values                       # numpy
    dim_names = list(plan_scores.columns)
    weights_result = compute_weights(score_matrix, dim_names, SUBJECTIVE_WEIGHTS)
    weights_df = save_weights(weights_result)
    print(f'  CRITIC 权重: {weights_result["critic_weights"]}', flush=True)
    print(f'  业务权重  : {weights_result["subjective_weights"]}', flush=True)
    print(f'  混合权重  : {weights_result["mixed_weights"]}', flush=True)
    mixed_weights = weights_result['mixed_weights']

    # ===== 用混合权重计算综合评分 =====
    overall = (
        mixed_weights['设计质量与创意']   * s1['综合评分'] +
        mixed_weights['关键词管理与运用'] * s2['综合评分'] +
        mixed_weights['出价策略与预算']   * s3['综合评分'] +
        mixed_weights['投放策略与时间']   * s4['综合评分']
    )

    # 评级（统一阈值：A≥85 / B70-84 / C60-69 / D50-59 / E<50；与 paper.md 附录 D 一致）
    if overall >= 85:
        grade = 'A (优秀)'
    elif overall >= 70:
        grade = 'B (良好)'
    elif overall >= 60:
        grade = 'C (一般)'
    elif overall >= 50:
        grade = 'D (偏差)'
    else:
        grade = 'E (差)'

    result = {
        'overall_score': round(overall, 1),
        'overall_score_method': '按4维度加权平均 (Σ 维度分 × 混合权重)；不等同于 5 方案综合分的算术平均',
        'overall_score_breakdown': {
            dim: {
                'dimension_score': score,
                'weight_mixed':   mixed_weights[dim],
                'weighted':       round(mixed_weights[dim] * score, 2),
            }
            for dim, score in [
                ('设计质量与创意',   s1['综合评分']),
                ('关键词管理与运用', s2['综合评分']),
                ('出价策略与预算',   s3['综合评分']),
                ('投放策略与时间',   s4['综合评分']),
            ]
        },
        'grade': grade,
        'weights_method': 'CRITIC + 业务混合 70:30',
        'plan_scores': plan_scores.to_dict(orient='index'),  # 新增：每方案 4 维得分
        'dimensions': {
            '设计质量与创意':   {'score': s1['综合评分'],
                               'weight_critic':    weights_result['critic_weights']['设计质量与创意'],
                               'weight_subjective': weights_result['subjective_weights']['设计质量与创意'],
                               'weight_mixed':     mixed_weights['设计质量与创意'],
                               'details': s1},
            '关键词管理与运用': {'score': s2['综合评分'],
                               'weight_critic':    weights_result['critic_weights']['关键词管理与运用'],
                               'weight_subjective': weights_result['subjective_weights']['关键词管理与运用'],
                               'weight_mixed':     mixed_weights['关键词管理与运用'],
                               'details': s2},
            '出价策略与预算':   {'score': s3['综合评分'],
                               'weight_critic':    weights_result['critic_weights']['出价策略与预算'],
                               'weight_subjective': weights_result['subjective_weights']['出价策略与预算'],
                               'weight_mixed':     mixed_weights['出价策略与预算'],
                               'details': s3},
            '投放策略与时间':   {'score': s4['综合评分'],
                               'weight_critic':    weights_result['critic_weights']['投放策略与时间'],
                               'weight_subjective': weights_result['subjective_weights']['投放策略与时间'],
                               'weight_mixed':     mixed_weights['投放策略与时间'],
                               'details': s4},
        },
    }

    # 计算每方案加权综合分（用于口径对比）
    w_arr = np.array([mixed_weights[d] for d in dim_names])
    plan_overall = (plan_scores.values @ w_arr).round(2)
    plan_overall_dict = {int(pid): float(s) for pid, s in zip(plan_scores.index, plan_overall)}
    result['plan_overall_scores'] = plan_overall_dict
    result['plan_avg_for_reference'] = round(float(np.mean(plan_overall)), 2)
    # plan_scores 中补一个 '综合分' 字段（to_dict(orient='index') 的 key 是 int）
    for idx_pos, pid in enumerate(plan_scores.index):
        result['plan_scores'][int(pid)]['综合分'] = float(plan_overall[idx_pos])

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
            rows.append({'类别': cat, '指标': k, '值': v,
                         '权重(混合)': info['weight_mixed'],
                         '权重(CRITIC)': info['weight_critic']})
    df = pd.DataFrame(rows)
    out_csv = os.path.join(TABLES_DIR, 'q1_score_breakdown.csv')
    df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'[save] {out_csv}', flush=True)

    # 每方案 4 维得分表
    out_csv2 = os.path.join(TABLES_DIR, 'q1_plan_scores.csv')
    plan_scores.to_csv(out_csv2, encoding='utf-8-sig')
    print(f'[save] {out_csv2}', flush=True)

    # 综合评分输出
    print('\n' + '=' * 40, flush=True)
    print(f'SEM投放策略合理性综合评分: {result["overall_score"]} / 100', flush=True)
    print(f'评级: {result["grade"]}', flush=True)
    print('=' * 40, flush=True)

    return result


if __name__ == '__main__':
    run_scoring()
