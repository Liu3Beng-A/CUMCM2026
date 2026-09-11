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


# 法定节假日窗口（用于聚合扣分；与 paper.md 5.1.5 节、q1_holiday_penalty.json 完全一致）
AGG_HOLIDAY_WINDOWS = {
    '春节':   ('2025-01-28', '2025-02-04'),
    '清明':   ('2025-04-04', '2025-04-06'),
    '劳动节': ('2025-05-01', '2025-05-05'),
    '端午':   ('2025-05-31', '2025-06-02'),
    '国庆':   ('2025-10-01', '2025-10-07'),
    '中秋':   ('2025-10-06', '2025-10-08'),  # 与国庆部分重叠
    '元旦':   ('2025-01-01', '2025-01-01'),
}


def compute_penalty_aggregated(bootstrap_csv_path=None):
    """按"节日聚合"计算扣分（与 paper.md 5.1.5 节、q1_holiday_penalty.json 完全一致）

    规则（与 docs 严格对齐）：
    - 对每个法定节假日窗口，按"窗口天数 × 2 指标"做显著性检验
    - 100% 显著（p<0.05）：扣分 = round(1.5 × 窗口天数)
    - 80-99% 显著：扣分 = round(0.8 × 窗口天数)
    - < 80% 显著：不扣分
    - 总扣分封顶 -30

    Returns
    -------
    dict : 聚合扣分结果（含 summary / details / stat）
    """
    if bootstrap_csv_path is None:
        bootstrap_csv_path = os.path.join(TABLES_DIR, 'q1_bootstrap_ci.csv')

    if not os.path.exists(bootstrap_csv_path):
        return {
            'total_penalty': 0,
            'method': '按节日聚合（Bootstrap 结果未生成，跳过）',
            'summary': {},
            'details': [],
        }

    df = pd.read_csv(bootstrap_csv_path, encoding='utf-8-sig')

    details = []
    summary = {}
    total_penalty = 0
    total_tests = 0
    total_sig = 0
    n_boot_min = 100  # 默认 n_boot
    n_boot_max = 100

    # 推断 n_boot 范围
    if 'n_boot' in df.columns:
        n_boot_min = int(df['n_boot'].min())
        n_boot_max = int(df['n_boot'].max())

    for holiday, (start, end) in AGG_HOLIDAY_WINDOWS.items():
        # 选窗口内 + 节日名匹配的行
        window_mask = (df['日期'] >= start) & (df['日期'] <= end) & (df['节日'] == holiday)
        sub = df[window_mask]
        if len(sub) == 0:
            continue

        # 严格聚合规则（与 docs 完全一致）：以"天"为单位，每天的"消费 + 注册"两个指标都 p<0.05 + 负贡献才算"显著天"
        days = sorted(sub['日期'].unique())
        sig_days = 0
        for d in days:
            day_df = sub[sub['日期'] == d]
            cost_row = day_df[day_df['指标'] == '总消费额']
            reg_row = day_df[day_df['指标'] == '新注册数']
            if len(cost_row) == 0 or len(reg_row) == 0:
                continue
            cost_sig = (cost_row.iloc[0]['p值(双侧)'] < 0.05) and (cost_row.iloc[0]['均值差'] < 0)
            reg_sig  = (reg_row.iloc[0]['p值(双侧)']  < 0.05) and (reg_row.iloc[0]['均值差']  < 0)
            if cost_sig and reg_sig:
                sig_days += 1

        n_total_days = len(days)
        sig_ratio = sig_days / n_total_days if n_total_days > 0 else 0
        window_days = n_total_days

        # 计算扣分（与 docs 完全对齐）
        if sig_ratio >= 1.0:
            penalty = round(1.5 * window_days)
        elif sig_ratio >= 0.8 and window_days >= 5:
            # 80% 显著 + 窗口 >= 5 天 才扣；否则不扣（避免短期节日误伤）
            penalty = round(0.8 * window_days)
        else:
            penalty = 0

        # 平均差与平均 p
        cost_sub = sub[sub['指标'] == '总消费额']
        reg_sub = sub[sub['指标'] == '新注册数']
        cost_diff = round(float(cost_sub['均值差'].mean()), 2) if len(cost_sub) > 0 else None
        reg_diff = round(float(reg_sub['均值差'].mean()), 2) if len(reg_sub) > 0 else None
        avg_p = round(float(sub['p值(双侧)'].mean()), 3)

        total_tests += len(sub)
        total_sig += (sub['p值(双侧)'] < 0.05).sum()

        if penalty > 0:
            total_penalty += penalty
            summary[holiday] = penalty
            details.append({
                '节日': holiday,
                '窗口': f'{start} ~ {end}（{window_days} 天）',
                '总检验数': len(sub),
                '显著数': int((sub['p值(双侧)'] < 0.05).sum()),
                '显著性比例': f'{int(sig_ratio*100)}%',
                '消费平均差': cost_diff,
                '注册平均差': reg_diff,
                '平均p值': avg_p,
                '扣分': penalty,
                '等级': ('严重错位（{} 天 × 2 指标全部 p<0.05）'.format(window_days)
                        if sig_ratio >= 1.0 else
                        '显著错位（{} 天中 {} 天 × 2 指标显著）'.format(window_days, sig_days)),
            })

    total_penalty = min(total_penalty, 30)

    return {
        'total_penalty': total_penalty,
        'method': '按节日聚合的 Bootstrap 显著性分级扣分（全量 37 节日 × 100 次）',
        'summary': summary,
        'details': details,
        'stat': {
            '总检验数': total_tests,
            '显著数': total_sig,
            '显著率': f'{int(total_sig/total_tests*100) if total_tests else 0}%',
            'n_boot_target': 100,
            'n_boot_valid_min': n_boot_min,
            'n_boot_valid_max': n_boot_max,
        },
    }


def apply_penalty_to_score(score_json_path=None):
    """把扣分应用到 q1_score.json 的"投放策略与时间"维度

    Returns
    -------
    新综合评分
    """
    if score_json_path is None:
        score_json_path = os.path.join(TABLES_DIR, 'q1_score.json')

    # 改：用按"节日聚合"逻辑（与 paper.md 5.1.5 节、q1_holiday_penalty.json 一致）
    penalty_result = compute_penalty_aggregated()

    # 同步保存到 q1_holiday_penalty.json
    out_penalty_json = os.path.join(TABLES_DIR, 'q1_holiday_penalty.json')

    # 把 numpy 类型转 python 原生类型（防止 JSON 序列化失败）
    def _to_native(obj):
        if isinstance(obj, dict):
            return {k: _to_native(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_to_native(v) for v in obj]
        if hasattr(obj, 'item'):  # numpy scalar
            return obj.item()
        return obj

    penalty_result_native = _to_native(penalty_result)
    with open(out_penalty_json, 'w', encoding='utf-8') as f:
        json.dump(penalty_result_native, f, ensure_ascii=False, indent=2)
    print(f'[save] {out_penalty_json}', flush=True)

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

    # 同步更新 overall_score_breakdown 中"投放策略与时间"的 dimension_score
    if 'overall_score_breakdown' in result and '投放策略与时间' in result['overall_score_breakdown']:
        wd = result['overall_score_breakdown']['投放策略与时间']
        wd['dimension_score'] = round(new_time_score, 1)
        wd['weighted'] = round(wd['weight_mixed'] * new_time_score, 2)
        wd['original_dimension_score'] = round(old_time_score, 1)
        wd['original_weighted'] = round(wd['weight_mixed'] * old_time_score, 2)

    # 同步更新 plan_overall_scores 和 plan_avg_for_reference
    if 'plan_overall_scores' in result:
        new_plan_overall = {}
        for pid_key, sc in result['plan_scores'].items():
            new_plan_overall[int(pid_key) if not isinstance(pid_key, str) or pid_key.lstrip('-').isdigit() else pid_key] = round(sum(
                sc[dim] * result['dimensions'][dim]['weight_mixed']
                for dim in result['dimensions']
            ), 2)
        result['plan_overall_scores'] = new_plan_overall
        result['plan_avg_for_reference'] = round(float(np.mean(list(new_plan_overall.values()))), 2)

    # 更新 plan_scores[pid].综合分
    if 'plan_overall_scores' in result:
        for pid_key, sc in result['plan_scores'].items():
            pid_int = int(pid_key) if (isinstance(pid_key, str) and pid_key.lstrip('-').isdigit()) else (pid_key if isinstance(pid_key, int) else None)
            if pid_int is not None and pid_int in result['plan_overall_scores']:
                sc['综合分'] = result['plan_overall_scores'][pid_int]
    # 重算评级（统一阈值：A≥85 / B70-84 / C60-69 / D50-59 / E<50；与 paper.md 附录 D 一致）
    if new_overall >= 85:   result['grade'] = 'A (优秀)'
    elif new_overall >= 70: result['grade'] = 'B (良好)'
    elif new_overall >= 60: result['grade'] = 'C (一般)'
    elif new_overall >= 50: result['grade'] = 'D (偏差)'
    else:                   result['grade'] = 'E (差)'

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
        json.dump(_to_native(result), f, ensure_ascii=False, indent=2)
    print(f'[save] {score_json_path}', flush=True)
    print(f'\n=== 节日扣分注入 ===', flush=True)
    print(f'原"投放策略与时间"分: {old_time_score}', flush=True)
    print(f'总扣分: -{penalty_result["total_penalty"]}', flush=True)
    print(f'新"投放策略与时间"分: {new_time_score}', flush=True)
    print(f'新综合分: {result["overall_score"]} ({result["grade"]})', flush=True)
    print(f'\n扣分明细:', flush=True)
    for d in penalty_result['details']:
        if '日期' in d:
            # 旧"逐日"格式
            print(f'  - {d["日期"]} {d["节日"]}: -{d["扣分"]} ({d["等级"]}, p={d["p值"]})', flush=True)
        else:
            # 新"聚合"格式（按节日）
            print(f'  - {d["节日"]} {d["窗口"]}: -{d["扣分"]} ({d["等级"]}, 平均p={d["平均p值"]})', flush=True)

    # 也保存 penalty 结果到独立文件
    penalty_path = os.path.join(TABLES_DIR, 'q1_holiday_penalty.json')
    with open(penalty_path, 'w', encoding='utf-8') as f:
        json.dump(_to_native(penalty_result), f, ensure_ascii=False, indent=2)
    print(f'\n[save] {penalty_path}', flush=True)

    return result


if __name__ == '__main__':
    # 默认跑聚合版（与 paper.md 5.1.5 / q1_holiday_penalty.json 对齐）
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'aggregated'
    if mode == 'legacy':
        # 旧"逐日"逻辑保留为参考
        from src.utils import TABLES_DIR
        legacy_result = compute_penalty()
        out_legacy = os.path.join(TABLES_DIR, 'q1_holiday_penalty.json')
        with open(out_legacy, 'w', encoding='utf-8') as f:
            json.dump(legacy_result, f, ensure_ascii=False, indent=2)
        print(f'[legacy save] {out_legacy}', flush=True)
    else:
        apply_penalty_to_score()
