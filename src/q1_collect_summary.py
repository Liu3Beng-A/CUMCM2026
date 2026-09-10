"""收集Q1论文需要的数据摘要，保存为 json 以便撰写"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'd:\CUMCM2026Problems')

import json
import pickle
import pandas as pd
import numpy as np
from src.q1_data_prep import build_q1_data


def main():
    data = build_q1_data()
    plan_total = data['plan_total']
    unit_total = data['unit_total']
    keyword_total = data['keyword_total']
    dfc = data['campaign_daily']
    daily = data['daily_full']
    dfr = data['registration']

    summary = {}

    # 总体
    summary['总览'] = {
        '总消费额(元)': float(plan_total['消费额'].sum()),
        '总展现量': int(plan_total['展现量'].sum()),
        '总点击量': int(plan_total['点击量'].sum()),
        '总新注册': int(dfr['新注册数'].sum()),
        'CPC均值(元)': float(daily['CPC'].mean()),
        'CTR均值': float(daily['CTR'].mean()),
        '平均每日消费(元)': float(daily['总消费额'].mean()),
        '平均每日注册': float(daily['新注册数'].mean()),
        '整体注册转化率': float(daily['注册转化率'].mean()),
        '每元注册': float(daily['每元注册'].mean()),
    }

    # 方案维度
    plan_total['上方位占比'] = plan_total['上方位展现量'] / plan_total['展现量'].replace(0, np.nan)
    plan_total['CTR'] = plan_total['点击量'] / plan_total['展现量'].replace(0, np.nan)
    plan_total['CPC'] = plan_total['消费额'] / plan_total['点击量'].replace(0, np.nan)
    plan_total['注册转化估算'] = dfr['新注册数'].sum() * (plan_total['消费额'] / plan_total['消费额'].sum())
    summary['方案明细'] = plan_total[['方案ID', '展现量', '点击量', '消费额', '上方位占比', 'CTR', 'CPC', '单元数', '关键词数']].to_dict('records')

    # 单元维度
    unit_total['上方位占比'] = unit_total['上方位展现量'] / unit_total['展现量'].replace(0, np.nan)
    unit_total['CTR'] = unit_total['点击量'] / unit_total['展现量'].replace(0, np.nan)
    unit_total['CPC'] = unit_total['消费额'] / unit_total['点击量'].replace(0, np.nan)
    summary['单元上方位占比'] = unit_total[['推广单元ID', '方案ID', '上方位占比', '消费额', 'CTR', 'CPC']].to_dict('records')

    # 关键词维度
    eff = keyword_total[keyword_total['有消费']]
    summary['关键词摘要'] = {
        '关键词总数': int(len(keyword_total)),
        '有消费关键词数': int(keyword_total['有消费'].sum()),
        '无效词比例': float((~keyword_total['有消费']).mean()),
        '有效率': float(keyword_total['有消费'].mean()),
        '有效词的CPC中位数': float(eff['CPC'].median()),
        '有效词的CPC P90': float(eff['CPC'].quantile(0.9)),
        '有效词的跳出率均值': float(eff['跳出率'].mean()),
        '前20%词占消费比': float(
            np.cumsum(eff['消费额'].sort_values(ascending=False).values)[int(len(eff)*0.2)] / eff['消费额'].sum()
        ),
    }

    # 时间维度
    daily_copy = daily.copy()
    daily_copy['月份'] = daily_copy['日期'].dt.to_period('M').astype(str)
    monthly = daily_copy.groupby('月份')[['总消费额', '新注册数']].sum().reset_index()
    monthly['每元注册'] = monthly['新注册数'] / monthly['总消费额']
    summary['月度明细'] = monthly.to_dict('records')

    daily_copy['星期几'] = daily_copy['日期'].dt.dayofweek
    weekly = daily_copy.groupby('星期几')[['总消费额', '新注册数']].sum().reset_index()
    summary['周内分布'] = weekly.to_dict('records')

    # 节日贡献（读 CSV）
    contrib = pd.read_csv(r'd:\CUMCM2026Problems\results\tables\q1_holiday_contribution.csv', encoding='utf-8')
    summary['假日效应'] = {
        '法定节假日消费额总贡献(元)': float(contrib[contrib['节日'] != '购物节'][contrib['指标'] == '消费额']['节日贡献绝对值'].sum()),
        '法定节假日注册量总贡献': float(contrib[contrib['节日'] != '购物节'][contrib['指标'] == '注册量']['节日贡献绝对值'].sum()),
        '购物节消费额总贡献(元)': float(contrib[contrib['节日'] == '购物节'][contrib['指标'] == '消费额']['节日贡献绝对值'].sum()),
        '购物节注册量总贡献': float(contrib[contrib['节日'] == '购物节'][contrib['指标'] == '注册量']['节日贡献绝对值'].sum()),
        '关键正向节日(消费)': contrib[contrib['节日贡献百分比'] > 0].sort_values('节日贡献百分比', ascending=False).head(5)[
            ['日期', '节日', '节日贡献百分比', '指标']
        ].to_dict('records'),
        '关键负向节日(消费)': contrib[contrib['节日贡献百分比'] < 0].sort_values('节日贡献百分比').head(5)[
            ['日期', '节日', '节日贡献百分比', '指标']
        ].to_dict('records'),
    }

    # 评分
    with open(r'd:\CUMCM2026Problems\results\tables\q1_score.json', 'r', encoding='utf-8') as f:
        summary['综合评分'] = json.load(f)

    out = r'd:\CUMCM2026Problems\results\tables\q1_summary.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    print(f'[save] {out}', flush=True)

    # 打印摘要
    print('\n=== 总览 ===', flush=True)
    for k, v in summary['总览'].items():
        print(f'  {k}: {v}', flush=True)
    print('\n=== 关键词摘要 ===', flush=True)
    for k, v in summary['关键词摘要'].items():
        print(f'  {k}: {v}', flush=True)
    print('\n=== 综合评分 ===', flush=True)
    print(f'总分: {summary["综合评分"]["overall_score"]} {summary["综合评分"]["grade"]}', flush=True)


if __name__ == '__main__':
    main()
