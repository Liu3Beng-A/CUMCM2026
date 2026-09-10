"""数据加载与预处理"""
import os
import pandas as pd
import numpy as np

from src.utils import RAW_DIR, PROCESSED_DIR, find_attachment_dir, ensure_dir


def load_raw_data():
    """
    加载原始附件1的三张表
    Returns:
        df_campaign: Sheet1 - 投放方案与消费记录 (日期 x 方案 x 单元)
        df_registration: Sheet2 - 每天新注册用户数
        df_keyword: Sheet3 - 关键词统计数据
    """
    att_dir = find_attachment_dir()
    att1_path = os.path.join(att_dir, '附件1.xlsx')

    df_campaign = pd.read_excel(att1_path, sheet_name='Sheet1')
    df_registration = pd.read_excel(att1_path, sheet_name='Sheet2')
    df_keyword = pd.read_excel(att1_path, sheet_name='Sheet3')

    # 字段名清洗
    df_registration.columns = [c.strip() for c in df_registration.columns]
    if '新注册数' in df_registration.columns:
        df_registration.rename(columns={'新注册数': '新注册数'}, inplace=True)

    # 时间字段
    df_campaign['日期'] = pd.to_datetime(df_campaign['日期'])
    df_registration['日期'] = pd.to_datetime(df_registration['日期'])

    # 关键词预处理
    df_keyword = _clean_keyword(df_keyword)

    return df_campaign, df_registration, df_keyword


def _clean_keyword(df):
    """清洗关键词数据：跳出率/平均访问时长的'/'处理"""
    df = df.copy()
    # 跳出率：'/' -> NaN
    df['跳出率'] = pd.to_numeric(df['跳出率'], errors='coerce')
    df['平均访问时长_秒'] = df['平均访问时长'].apply(_parse_duration)
    return df


def _parse_duration(s):
    """解析 HH:MM:SS 格式的时长为秒"""
    if pd.isna(s) or s == '/' or not isinstance(s, str):
        return np.nan
    try:
        parts = s.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return np.nan
    return np.nan


def save_processed(df_campaign, df_registration, df_keyword, tag='main'):
    """将清洗后的数据保存为 pickle（parquet对中文混合类型支持不好）"""
    ensure_dir(PROCESSED_DIR)
    df_campaign.to_pickle(os.path.join(PROCESSED_DIR, f'campaign_{tag}.pkl'))
    df_registration.to_pickle(os.path.join(PROCESSED_DIR, f'registration_{tag}.pkl'))
    # keyword 里有 HH:MM:SS 字符串列，转成数值列再存
    dfk_save = df_keyword.copy()
    if '平均访问时长' in dfk_save.columns:
        dfk_save = dfk_save.drop(columns=['平均访问时长'])
    dfk_save.to_pickle(os.path.join(PROCESSED_DIR, f'keyword_{tag}.pkl'))
    print(f'[saved] campaign / registration / keyword ({tag}) -> pickle')


def load_processed(tag='main'):
    """读取清洗后的数据"""
    import pickle
    base = PROCESSED_DIR
    with open(os.path.join(base, f'campaign_{tag}.pkl'), 'rb') as f:
        df_campaign = pickle.load(f)
    with open(os.path.join(base, f'registration_{tag}.pkl'), 'rb') as f:
        df_registration = pickle.load(f)
    with open(os.path.join(base, f'keyword_{tag}.pkl'), 'rb') as f:
        df_keyword = pickle.load(f)
    return df_campaign, df_registration, df_keyword


def campaign_basic_metrics(df_campaign):
    """添加基本派生指标：CTR、CPC、上方位占比"""
    df = df_campaign.copy()
    df['CTR'] = df['点击量'] / df['展现量'].replace(0, np.nan)
    df['CPC'] = df['消费额'] / df['点击量'].replace(0, np.nan)
    df['上方位占比'] = df['上方位展现量'] / df['展现量'].replace(0, np.nan)
    df['上方首位占比'] = df['上方首位展现量'] / df['展现量'].replace(0, np.nan)
    df['上方位CTR'] = df['上方位点击量'] / df['上方位展现量'].replace(0, np.nan)
    df['上方位CPC'] = df['上方位消费额'] / df['上方位点击量'].replace(0, np.nan)
    return df


def keyword_basic_metrics(df_keyword):
    """关键词层面：CTR、CPC、是否活跃"""
    df = df_keyword.copy()
    df['有消费'] = df['消费额'] > 0
    df['CTR'] = df['点击量'] / df['浏览量'].replace(0, np.nan)
    df['CPC'] = df['消费额'] / df['点击量'].replace(0, np.nan)
    return df


if __name__ == '__main__':
    print('=== 加载原始数据 ===')
    c, r, k = load_raw_data()
    print(f'campaign: {c.shape}')
    print(f'registration: {r.shape}')
    print(f'keyword: {k.shape}')

    c2 = campaign_basic_metrics(c)
    k2 = keyword_basic_metrics(k)
    print('\ncampaign 派生指标:')
    print(c2[['CTR', 'CPC', '上方位占比']].describe())
