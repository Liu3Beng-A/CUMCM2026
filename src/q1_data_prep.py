"""Q1 数据预处理模块

输入：data/processed/{campaign, registration, keyword}_main.pkl
输出：data/processed/q1/ 下面的多种聚合数据
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

from src.data_loader import load_processed
from src.utils import PROCESSED_DIR, ensure_dir

Q1_DIR = os.path.join(PROCESSED_DIR, 'q1')


def daily_agg(dfc, dfr):
    """日级聚合：消费、点击、展现、注册 + 上方位聚合"""
    df = dfc.copy()
    # 业务指标
    df['CTR'] = df['点击量'] / df['展现量'].replace(0, np.nan)
    df['CPC'] = df['消费额'] / df['点击量'].replace(0, np.nan)
    df['上方位占比'] = df['上方位展现量'] / df['展现量'].replace(0, np.nan)
    df['上方首位占比'] = df['上方首位展现量'] / df['展现量'].replace(0, np.nan)
    df['上方位CTR'] = df['上方位点击量'] / df['上方位展现量'].replace(0, np.nan)
    df['上方位CPC'] = df['上方位消费额'] / df['上方位点击量'].replace(0, np.nan)
    return df


def plan_daily_agg(dfc_daily):
    """方案×日聚合"""
    return dfc_daily.groupby(['日期', '方案ID'], as_index=False).agg(
        展现量=('展现量', 'sum'),
        点击量=('点击量', 'sum'),
        消费额=('消费额', 'sum'),
        上方位展现量=('上方位展现量', 'sum'),
        上方位首位展现量=('上方首位展现量', 'sum'),
        上方位点击量=('上方位点击量', 'sum'),
        上方位消费额=('上方位消费额', 'sum'),
        推广单元数=('推广单元ID', 'nunique'),
    )


def unit_daily_agg(dfc_daily):
    """单元×日聚合（一行=一单元一天，dfc本身就是此粒度）"""
    return dfc_daily.copy()


def plan_overall(dfc, dfk=None):
    """方案全年汇总（dfc不含关键词列，从dfk并入关键词数）"""
    df = dfc.groupby('方案ID', as_index=False).agg(
        展现量=('展现量', 'sum'),
        点击量=('点击量', 'sum'),
        消费额=('消费额', 'sum'),
        上方位展现量=('上方位展现量', 'sum'),
        上方位首位展现量=('上方首位展现量', 'sum'),
        上方位点击量=('上方位点击量', 'sum'),
        上方位消费额=('上方位消费额', 'sum'),
        单元数=('推广单元ID', 'nunique'),
        投放天数=('日期', 'nunique'),
    )
    if dfk is not None and '关键词' in dfk.columns:
        kw_cnt = dfk.groupby('方案ID')['关键词'].nunique().reset_index()
        kw_cnt.columns = ['方案ID', '关键词数']
        df = df.merge(kw_cnt, on='方案ID', how='left')
    return df.sort_values('消费额', ascending=False)


def unit_overall(dfc, dfk=None):
    """单元全年汇总"""
    df = dfc.groupby(['方案ID', '推广单元ID'], as_index=False).agg(
        展现量=('展现量', 'sum'),
        点击量=('点击量', 'sum'),
        消费额=('消费额', 'sum'),
        上方位展现量=('上方位展现量', 'sum'),
        上方位首位展现量=('上方首位展现量', 'sum'),
        上方位点击量=('上方位点击量', 'sum'),
        上方位消费额=('上方位消费额', 'sum'),
        投放天数=('日期', 'nunique'),
    )
    if dfk is not None and '关键词' in dfk.columns:
        kw_cnt = dfk.groupby(['方案ID', '推广单元ID'])['关键词'].nunique().reset_index()
        kw_cnt.columns = ['方案ID', '推广单元ID', '关键词数']
        df = df.merge(kw_cnt, on=['方案ID', '推广单元ID'], how='left')
    return df


def keyword_overall(dfk):
    """关键词全年汇总"""
    df = dfk.copy()
    df['有消费'] = df['消费额'] > 0
    df['有浏览'] = df['浏览量'] > 0
    df['有转化'] = df['点击量'] > 0
    df['平均浏览'] = df['浏览量'] / df['点击量'].replace(0, np.nan)
    df['CTR'] = df['点击量'] / df['浏览量'].replace(0, np.nan)  # 这里浏览量=展现量
    df['CPC'] = df['消费额'] / df['点击量'].replace(0, np.nan)
    return df


def build_q1_data():
    """构建所有Q1需要的聚合数据"""
    ensure_dir(Q1_DIR)
    print('[q1] loading raw data...', flush=True)
    dfc, dfr, dfk = load_processed()

    print('[q1] daily aggregate...', flush=True)
    dfc_daily = daily_agg(dfc, dfr)

    print('[q1] plan × day aggregate...', flush=True)
    plan_daily = plan_daily_agg(dfc_daily)
    plan_daily['CTR'] = plan_daily['点击量'] / plan_daily['展现量'].replace(0, np.nan)
    plan_daily['CPC'] = plan_daily['消费额'] / plan_daily['点击量'].replace(0, np.nan)
    plan_daily['上方位占比'] = plan_daily['上方位展现量'] / plan_daily['展现量'].replace(0, np.nan)
    plan_daily['上方位CTR'] = plan_daily['上方位点击量'] / plan_daily['上方位展现量'].replace(0, np.nan)

    print('[q1] unit × day aggregate...', flush=True)
    unit_daily = unit_daily_agg(dfc_daily)
    unit_daily['CTR'] = unit_daily['点击量'] / unit_daily['展现量'].replace(0, np.nan)
    unit_daily['CPC'] = unit_daily['消费额'] / unit_daily['点击量'].replace(0, np.nan)
    unit_daily['上方位占比'] = unit_daily['上方位展现量'] / unit_daily['展现量'].replace(0, np.nan)

    print('[q1] overall aggregates...', flush=True)
    plan_total = plan_overall(dfc, dfk)
    unit_total = unit_overall(dfc, dfk)
    keyword_total = keyword_overall(dfk)

    # 注册数据是全公司层面，按 总消费额+总点击量 计算
    # 1) 计算每日全公司总和
    daily_company = dfc.groupby('日期', as_index=False).agg(
        总展现量=('展现量', 'sum'),
        总点击量=('点击量', 'sum'),
        总消费额=('消费额', 'sum'),
        总上方位展现=('上方位展现量', 'sum'),
        总上方位点击=('上方位点击量', 'sum'),
        总上方位消费=('上方位消费额', 'sum'),
    )
    daily_company['CTR'] = daily_company['总点击量'] / daily_company['总展现量'].replace(0, np.nan)
    daily_company['CPC'] = daily_company['总消费额'] / daily_company['总点击量'].replace(0, np.nan)
    daily_company['上方位CTR'] = daily_company['总上方位点击'] / daily_company['总上方位展现'].replace(0, np.nan)
    daily_company['上方位CPC'] = daily_company['总上方位消费'] / daily_company['总上方位点击'].replace(0, np.nan)

    # 2) 合并注册数据
    daily_full = daily_company.merge(dfr, on='日期', how='left')
    daily_full['注册转化率'] = daily_full['新注册数'] / daily_full['总点击量'].replace(0, np.nan)
    daily_full['每元注册'] = daily_full['新注册数'] / daily_full['总消费额'].replace(0, np.nan)

    # 3) plan_daily 不再存注册量（注册量是公司层面的）
    plan_daily_no_reg = plan_daily.copy()
    if '新注册数' in plan_daily_no_reg.columns:
        plan_daily_no_reg = plan_daily_no_reg.drop(columns=['新注册数'])

    # 保存
    print('[q1] saving to', Q1_DIR, flush=True)
    dfc_daily.to_pickle(os.path.join(Q1_DIR, 'campaign_daily.pkl'))
    plan_daily.to_pickle(os.path.join(Q1_DIR, 'plan_daily.pkl'))
    unit_daily.to_pickle(os.path.join(Q1_DIR, 'unit_daily.pkl'))
    plan_total.to_pickle(os.path.join(Q1_DIR, 'plan_total.pkl'))
    unit_total.to_pickle(os.path.join(Q1_DIR, 'unit_total.pkl'))
    keyword_total.to_pickle(os.path.join(Q1_DIR, 'keyword_total.pkl'))
    daily_full.to_pickle(os.path.join(Q1_DIR, 'daily_full.pkl'))
    plan_daily_no_reg.to_pickle(os.path.join(Q1_DIR, 'plan_daily_no_reg.pkl'))

    # 输出概览
    print('\n=== 方案汇总 ===', flush=True)
    cols = ['方案ID', '展现量', '点击量', '消费额', '单元数', '关键词数']
    print(plan_total[cols].to_string(index=False), flush=True)
    print(f'\n总消费额: {plan_total["消费额"].sum():.2f} 元', flush=True)
    print(f'总展现量: {plan_total["展现量"].sum():,}', flush=True)
    print(f'总点击量: {plan_total["点击量"].sum():,}', flush=True)
    print(f'总新注册: {dfr["新注册数"].sum():,}', flush=True)

    return {
        'campaign_daily': dfc_daily,
        'plan_daily': plan_daily,
        'unit_daily': unit_daily,
        'plan_total': plan_total,
        'unit_total': unit_total,
        'keyword_total': keyword_total,
        'daily_full': daily_full,
        'registration': dfr,
    }


if __name__ == '__main__':
    data = build_q1_data()
    print('\n[done] Q1 data prepared.', flush=True)
