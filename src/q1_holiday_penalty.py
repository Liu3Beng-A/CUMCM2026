"""Q1 节日扣分注入评分（改-5）

目的：
- 把 Bootstrap 显著性结果注入到"投放策略与时间"维度的综合评分
- 按显著性等级对负贡献节日进行分级扣分

分级标准：
- p < 0.05 且显著负贡献：扣 15 分（错位严重）
- p < 0.10 且显著负贡献：扣 8 分
- p < 0.20 且显著负贡献：扣 3 分
- p >= 0.20：不扣分（视为噪声）

输出：
- q1_holiday_penalty.json：扣分明细
- 修改 q1_score.json 中的 time_strategy 综合分
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import numpy as np
import pandas as pd

from src.utils import TABLES_DIR, ensure_dir


# 分级扣分配置
PENALTY_RULES = [
    {'p_threshold': 0.05, 'penalty': 15, 'label': '严重错位 (p<0.05)'},
    {'p_threshold': 0.10, 'penalty': 8,  'label': '中度错位 (0.05≤p<0.10)'},
    {'p_threshold': 0.20, 'penalty': 3,  'label': '轻度错位 (0.10≤p<0.20)'},
]


def compute_penalty(bootstrap_csv_path=None):
    """根据 Bootstrap 结果计算扣分

    Returns
    -------
    dict : {
        'total_penalty': 总扣分（最大 30）,
        'details': [每个节日的扣分明细],
        'summary': '分级汇总'
    }
    """
    if bootstrap_csv_path is None:
        bootstrap_csv_path = os.path.join(TABLES_DIR, 'q1_bootstrap_ci.csv')

    # 如果 Bootstrap 结果不存在 → 不扣分
    if not os.path.exists(bootstrap_csv_path):
        return {
            'total_penalty': 0,
            'details': [],
            'summary': 'Bootstrap 结果未生成，跳过节日扣分',
        }

    df = pd.read_csv(bootstrap_csv_path, encoding='utf-8-sig')

    # 只看消费额维度（注册量更复杂，避免重复扣分）
    df_cost = df[df['指标'] == '总消费额'].copy()

    # 每个节日取一次（按日期合并：消费额和注册量取更显著的）
    aggregated = df_cost.groupby(['日期', '节日']).agg(
        p_min=('p值(双侧)', 'min'),
        mean_diff=('均值差', 'mean'),
    ).reset_index()

    details = []
    total_penalty = 0
    for _, row in aggregated.iterrows():
        p = row['p_min']
        diff = row['mean_diff']
        # 只对负贡献做扣分
        if diff >= 0:
            continue
        # 选择最大扣分（最严格的）
        for rule in PENALTY_RULES:
            if p < rule['p_threshold']:
                penalty = rule['penalty']
                label = rule['label']
                break
        else:
            penalty = 0
            label = '不显著'
        if penalty > 0:
            details.append({
                '日期': row['日期'],
                '节日': row['节日'],
                'p值': round(p, 4),
                '均值差': round(diff, 2),
                '扣分': penalty,
                '等级': label,
            })
            total_penalty += penalty

    # 总扣分封顶 30（防止极端）
    total_penalty = min(total_penalty, 30)

    # 汇总
    by_label = {}
    for d in details:
        by_label.setdefault(d['等级'], []).append(d['扣分'])
    summary = {label: sum(p) for label, p in by_label.items()}

    return {
        'total_penalty': total_penalty,
        'details': details,
        'summary': summary,
    }


def apply_penalty_to_score(score_json_path=None):
    """把扣分应用到 q1_score.json 的"投放策略与时间"维度

    Returns
    -------
    新综合评分
    """
    if score_json_path is None:
        score_json_path = os.path.join(TABLES_DIR, 'q1_score.json')

    penalty_result = compute_penalty()

    with open(score_json_path, 'r', encoding='utf-8') as f:
        result = json.load(f)

    old_time_score = result['dimensions']['投放策略与时间']['score']
    new_time_score = max(0, old_time_score - penalty_result['total_penalty'])
    result['dimensions']['投放策略与时间']['score'] = round(new_time_score, 1)
    result['dimensions']['投放策略与时间']['original_score'] = old_time_score
    result['dimensions']['投放策略与时间']['holiday_penalty'] = penalty_result
    result['holiday_penalty_method'] = 'Bootstrap-based 分级扣分 (改-5)'

    # 改-6：同步更新每个方案的"投放策略与时间"维度
    # 原因：Bootstrap 扣分基于全公司日历，每个方案都受影响
    for pid, sc in result.get('plan_scores', {}).items():
        old_p_time = sc['投放策略与时间']
        new_p_time = max(0, old_p_time - penalty_result['total_penalty'])
        sc['投放策略与时间'] = round(new_p_time, 1)
        sc['_投放策略与时间_原值'] = old_p_time

    # 重算综合分
    new_overall = sum(
        info['weight_mixed'] * info['score']
        for info in result['dimensions'].values()
    )
    result['overall_score'] = round(new_overall, 1)
    # 重算评级
    if new_overall >= 85:   result['grade'] = 'A (优秀)'
    elif new_overall >= 70: result['grade'] = 'B (良好)'
    elif new_overall >= 55: result['grade'] = 'C (一般)'
    else:                   result['grade'] = 'D (需改进)'

    # 改-6：同步更新每个方案的综合分（CRITIC 混合权重）
    w = result['dimensions']
    for pid, sc in result.get('plan_scores', {}).items():
        # 使用本方案的时间维度原值（_投放策略与时间_原值）来重算原综合分
        old_p_time = sc.get('_投放策略与时间_原值', sc['投放策略与时间'] + penalty_result['total_penalty'])
        sc['_综合分_原值'] = round(
            w['设计质量与创意']['weight_mixed']   * sc['设计质量与创意'] +
            w['关键词管理与运用']['weight_mixed'] * sc['关键词管理与运用'] +
            w['出价策略与预算']['weight_mixed']   * sc['出价策略与预算'] +
            w['投放策略与时间']['weight_mixed']   * old_p_time, 2)
        sc['综合分'] = round(
            w['设计质量与创意']['weight_mixed']   * sc['设计质量与创意'] +
            w['关键词管理与运用']['weight_mixed'] * sc['关键词管理与运用'] +
            w['出价策略与预算']['weight_mixed']   * sc['出价策略与预算'] +
            w['投放策略与时间']['weight_mixed']   * sc['投放策略与时间'], 2)

    with open(score_json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'[save] {score_json_path}', flush=True)
    print(f'\n=== 节日扣分注入 ===', flush=True)
    print(f'原"投放策略与时间"分: {old_time_score}', flush=True)
    print(f'总扣分: -{penalty_result["total_penalty"]}', flush=True)
    print(f'新"投放策略与时间"分: {new_time_score}', flush=True)
    print(f'新综合分: {result["overall_score"]} ({result["grade"]})', flush=True)
    print(f'\n扣分明细:', flush=True)
    for d in penalty_result['details']:
        print(f'  - {d["日期"]} {d["节日"]}: -{d["扣分"]} ({d["等级"]}, p={d["p值"]})', flush=True)

    # 也保存 penalty 结果到独立文件
    penalty_path = os.path.join(TABLES_DIR, 'q1_holiday_penalty.json')
    with open(penalty_path, 'w', encoding='utf-8') as f:
        json.dump(penalty_result, f, ensure_ascii=False, indent=2)
    print(f'\n[save] {penalty_path}', flush=True)

    return result


if __name__ == '__main__':
    apply_penalty_to_score()
