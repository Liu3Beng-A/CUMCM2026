"""
Q2 · 6 项数学模型与数据补充模块（2026-09-12 14:03 用户确认）

**不修改主分类器**（D-Q2-002 锁定 T_cost=8.06 / T_benefit=0.904 不变）
**输出**（在主流程结果之上追加 6 项分析）：
- S2 ①  q2_thresholds_compare.json   - 阈值 3 对比（均匀 vs 加权 vs 行业）
- S3 ②  q2_field_robustness.csv       - 字段 4 组合 + Cohen's κ
- S4 ③  q2_extreme_audit_v2.csv        - 极值审计 v2（保留型/削减型 + 业务阈值）
- S5 ⑤  keyword_classified.pkl         - 加 ghost_browsing / potential_revival 列
- S6 ⑥  q2_zero_keyword_breakdown.csv  - 888 三零词细分（潜在激活清单）
- 通用  q2_robustness_report.json      - 汇总报告

**业务阈值（业务驱动，可解释）**
- ghost_browsing: 消费=0 但 (点击>0 或 浏览>0)
- potential_revival: 消费=0 且 点击=0 且 浏览=0 但 (跳出率 != 0.5 或 平均访问时长 > 0)
- 风险评级: 消费 > 10000 = 高 / 5000~10000 = 中 / < 5000 = 低
- 极值类型: 重点词 = 保留型极值 / 问题词 = 削减型极值
"""
import os
import sys
import json
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.utils import (
    RAW_DIR, PROCESSED_DIR, TABLES_DIR, FIGURES_DIR, ensure_dir
)

# =====================================================
# 路径常量
# =====================================================
Q2_PROCESSED_DIR = os.path.join(PROCESSED_DIR, 'q2')
Q2_KEYWORD_PKL = os.path.join(Q2_PROCESSED_DIR, 'keyword_classified.pkl')

CMP_JSON = os.path.join(TABLES_DIR, 'q2_thresholds_compare.json')
ROBUST_CSV = os.path.join(TABLES_DIR, 'q2_field_robustness.csv')
AUDIT_V2_CSV = os.path.join(TABLES_DIR, 'q2_extreme_audit_v2.csv')
ZERO_BREAK_CSV = os.path.join(TABLES_DIR, 'q2_zero_keyword_breakdown.csv')
REPORT_JSON = os.path.join(TABLES_DIR, 'q2_robustness_report.json')

CLASS_NAMES = ['黄金词', '重点词', '潜力词', '问题词', '无效词']

# 行业基准（百度 SEM 行业经验值，中等竞争行业）
INDUSTRY_BENCHMARK_CPC = 1.5  # 元/点击


# =====================================================
# ① 阈值 3 对比（S2）
# =====================================================
def compare_thresholds(df_valid: pd.DataFrame) -> dict:
    """三套阈值对比：均匀中位数 / 消费加权 CPC 中位数 / 行业基准 CPC=1.5 元

    输入：有效词 df（消费>0）
    输出：3 套阈值 × 各自 5 类计数
    """
    cost = df_valid['成本'].astype(float).values
    clicks = df_valid['点击'].astype(float).values
    cpc = cost / np.maximum(clicks, 1)
    cpc_inv = clicks / np.maximum(cost, 0.01)

    # 三套阈值
    T_cost_uniform = float(np.median(cost))   # 均匀加权
    T_cost_weighted = float(np.average(cost, weights=np.maximum(cost, 1)))  # 消费加权平均

    # 方案 A: 均匀加权
    T_benefit_A = float(np.median(cpc_inv))

    # 方案 B: 消费加权 CPC 倒数中位数（用分位数形式：累计消费过半对应的 CPC）
    sorted_idx = np.argsort(cpc_inv)
    cumcost = np.cumsum(cost[sorted_idx]) / cost.sum()
    T_benefit_B = float(cpc_inv[sorted_idx[np.searchsorted(cumcost, 0.5)]])

    # 方案 C: 行业基准 CPC = 1.5 元（即 CPC 倒数 = 1/1.5 = 0.6667）
    T_benefit_C = 1.0 / INDUSTRY_BENCHMARK_CPC

    # 三套 5 类计数
    def classify(T_c, T_b):
        cls = []
        for c, ci in zip(cost, cpc_inv):
            if c <= T_c and ci >= T_b:
                cls.append('黄金词')
            elif c > T_c and ci >= T_b:
                cls.append('重点词')
            elif c <= T_c and ci < T_b:
                cls.append('潜力词')
            elif c > T_c and ci < T_b:
                cls.append('问题词')
            else:
                cls.append('潜力词')
        return pd.Series(cls).value_counts().reindex(CLASS_NAMES, fill_value=0).to_dict()

    return {
        'A_uniform_median': {
            'T_cost': T_cost_uniform,
            'T_benefit': T_benefit_A,
            'method': '成本中位数 + CPC 倒数中位数（当前主选择）',
            'counts': classify(T_cost_uniform, T_benefit_A),
        },
        'B_weighted_median': {
            'T_cost': T_cost_weighted,
            'T_benefit': T_benefit_B,
            'method': '消费加权 CPC 倒数中位数（按累计消费过半）',
            'counts': classify(T_cost_weighted, T_benefit_B),
        },
        'C_industry_benchmark': {
            'T_cost': T_cost_uniform,  # 成本侧保留原中位数
            'T_benefit': T_benefit_C,
            'method': f'行业基准 CPC={INDUSTRY_BENCHMARK_CPC} 元（即 T_benefit={T_benefit_C:.4f}）',
            'counts': classify(T_cost_uniform, T_benefit_C),
        },
        'main_choice': 'A_uniform_median',
    }


# =====================================================
# ② 字段稳健性 4 组合（S3）
# =====================================================
def field_robustness(df_valid: pd.DataFrame) -> pd.DataFrame:
    """4 种 (成本轴, 效益轴) 组合 → 5 类计数 + Cohen's κ（与主选择 A 的关键词级一致率）

    组合：
    1. (消费额, CPC倒数)  ← 主选择
    2. (消费额, 点击数)
    3. (CPC, 点击数/消费额倒数 = CPC本身)
       注：第3种 (CPC, 点击率) 因为没有曝光数据，无法算点击率，改用 CPC vs 跳出率
    4. (CPC, 跳出率倒数 = 1-跳出率) ← 业务可解释：高 CPC 但低跳出 = 流量精准
    """
    cost = df_valid['成本'].astype(float).values
    clicks = df_valid['点击'].astype(float).values
    browse = df_valid['浏览'].astype(float).values
    bounce = df_valid['跳出率_数值'].astype(float).values
    cpc = cost / np.maximum(clicks, 1)
    cpc_inv = clicks / np.maximum(cost, 0.01)
    retain_rate = 1 - bounce  # 留存率 = 1 - 跳出率

    combos = {
        # name: (cost_arr, benefit_arr, desc)
        '1.消费额×CPC倒数(主选)': (cost, cpc_inv, '成本=消费额, 效益=CPC倒数'),
        '2.消费额×点击量':      (cost, clicks, '成本=消费额, 效益=点击量(绝对)'),
        '3.CPC×留存率':         (cpc, retain_rate, '成本=CPC, 效益=1-跳出率'),
        '4.CPC倒数×点击量':     (cpc_inv, clicks, '成本=CPC倒数(便宜), 效益=点击量'),
    }

    # 主分类（组合 1）的关键词级 label
    def classify(arr_cost, arr_ben):
        Tc = np.median(arr_cost)
        Tb = np.median(arr_ben)
        cls = np.empty(len(arr_cost), dtype=object)
        for i, (c, b) in enumerate(zip(arr_cost, arr_ben)):
            if c <= Tc and b >= Tb:
                cls[i] = '黄金词'
            elif c > Tc and b >= Tb:
                cls[i] = '重点词'
            elif c <= Tc and b < Tb:
                cls[i] = '潜力词'
            else:
                cls[i] = '问题词'
        return cls, Tc, Tb

    main_cls, _, _ = classify(cost, cpc_inv)

    rows = []
    for name, (ax_cost, ax_ben, desc) in combos.items():
        cls, Tc, Tb = classify(ax_cost, ax_ben)
        cnt = pd.Series(cls).value_counts().reindex(['黄金词', '重点词', '潜力词', '问题词'], fill_value=0).to_dict()

        # Cohen's κ（与主分类的关键词级一致率）
        # 简化版：直接计算一致率（accuracy），Cohen's κ 需要混淆矩阵
        agreement = (cls == main_cls).mean()
        # Cohen's κ 公式：κ = (p_o - p_e) / (1 - p_e)
        n = len(cls)
        labels = ['黄金词', '重点词', '潜力词', '问题词']
        po = agreement
        pe = sum((cls == l).mean() * (main_cls == l).mean() for l in labels)
        kappa = (po - pe) / (1 - pe) if pe < 1 else 0.0

        row = {'组合': name, '说明': desc,
               'T_cost': round(float(Tc), 4), 'T_benefit': round(float(Tb), 4),
               '黄金词': cnt['黄金词'], '重点词': cnt['重点词'],
               '潜力词': cnt['潜力词'], '问题词': cnt['问题词'],
               '一致率': round(agreement, 4), 'Cohen κ': round(kappa, 4)}
        rows.append(row)

    return pd.DataFrame(rows)


# =====================================================
# ③ 极值审计升级（S4）
# =====================================================
def extreme_audit_v2(df_audit_full: pd.DataFrame) -> pd.DataFrame:
    """在原有极值审计基础上加 2 列：
    - 极值类型: 重点词 → 保留型极值 / 问题词 → 削减型极值 / 其他 → 观察型极值
    - 风险评级(业务): 消费 > 10000 = 高 / 5000-10000 = 中 / < 5000 = 低

    输入：df_audit_full（已 mark_extreme 的全集）
    输出：仅触发审计的极值词
    """
    df = df_audit_full[df_audit_full['触发审计']].copy()

    # 极值类型（业务语义）
    df['极值类型'] = df['分类'].map({
        '重点词': '保留型极值',   # 高消费高效益 → 加码
        '问题词': '削减型极值',   # 高消费低效益 → 削减
    }).fillna('观察型极值')

    # 风险评级（业务阈值）
    def biz_risk(c):
        if c > 10000:
            return '高'
        elif c >= 5000:
            return '中'
        else:
            return '低'
    df['风险评级_业务'] = df['成本'].apply(biz_risk)

    # 触发规则（沿用）
    df['触发规则'] = df.apply(
        lambda r: (
            'q95' if r['审计规则1_q95'] and not r['审计规则2_高CPC高消费']
            else '高CPC高消费' if r['审计规则2_高CPC高消费'] and not r['审计规则1_q95']
            else '双触发'
        ), axis=1
    )

    df['推广单元'] = df['推广单元ID']
    df['CPC'] = df['成本'] / np.maximum(df['点击'], 1)

    out = df[[
        '序号', '关键词', '方案ID', '推广单元', '分类', '极值类型',
        '成本', '点击', '浏览', 'CPC', '风险评级', '风险评级_业务',
        '触发规则',
    ]].rename(columns={'成本': '消费', '点击': '点击量', '浏览': '浏览量'})
    out = out.sort_values('消费', ascending=False).reset_index(drop=True)
    return out


# =====================================================
# ⑤ 异常词标记（S6）
# =====================================================
def flag_ghost_browsing(df_all: pd.DataFrame) -> tuple:
    """标记 ghost_browsing：消费=0 但 (点击>0 或 浏览>0)

    返回：(df_with_flag, n_ghost)
    """
    df = df_all.copy()
    ghost_mask = (df['成本'] <= 0) & ((df['点击'] > 0) | (df['浏览'] > 0))
    df['异常标记'] = np.where(ghost_mask, 'ghost_browsing', '')
    return df, int(ghost_mask.sum())


# =====================================================
# ⑥ 888 三零词细分（S7）
# =====================================================
def zero_keyword_breakdown(df_all: pd.DataFrame) -> tuple:
    """888 三零词（消费=点击=浏览=0）细分

    - ghost_browsing 已被 flag（不在此列）
    - potential_revival: 跳出率 != 0.5 或 平均访问时长 > 0 → 有人访问但漏斗未配置
    - truly_dead: 跳出率 = 0.5 (中性填充) 且 平均访问时长 = 0 → 完全无数据
    """
    df = df_all.copy()
    df['平均访问时长_秒'] = df.get('平均访问时长_秒', 0)  # 防御

    # 三零词
    triple_zero = (df['成本'] == 0) & (df['点击'] == 0) & (df['浏览'] == 0)
    # 非 ghost_browsing（已经在 ⑤ 单独处理）
    not_ghost = df['异常标记'] != 'ghost_browsing'
    mask = triple_zero & not_ghost

    # potential_revival: 跳出率有值（非 0.5 默认）或 平均访问时长 > 0
    potential = mask & ((df['跳出率_数值'] != 0.5) | (df['平均访问时长_秒'] > 0))
    truly_dead = mask & ~potential

    df.loc[potential, '异常标记'] = 'potential_revival'
    # truly_dead 标记为空（默认）

    return df, int(potential.sum()), int(truly_dead.sum())


# =====================================================
# 主流程：跑全部 6 项
# =====================================================
def run_all(verbose: bool = True) -> dict:
    """6 项补充分析一站式执行"""
    print('=' * 60)
    print('Q2 6 项数学/数据补充分析')
    print('=' * 60)
    ensure_dir(TABLES_DIR)

    # 加载主分类结果
    df_all = pd.read_pickle(Q2_KEYWORD_PKL)
    df_valid = df_all[df_all['分类'] != '无效词'].copy()
    print(f'\n加载 pkl: {len(df_all)} 总词 / {len(df_valid)} 有效词')

    report = {}

    # S2 ① 阈值 3 对比
    print('\n[S2 ①] 阈值 3 对比 ...')
    cmp_data = compare_thresholds(df_valid)
    with open(CMP_JSON, 'w', encoding='utf-8') as f:
        json.dump(cmp_data, f, ensure_ascii=False, indent=2)
    print(f'  → {CMP_JSON}')
    if verbose:
        for k in ['A_uniform_median', 'B_weighted_median', 'C_industry_benchmark']:
            d = cmp_data[k]
            print(f'  {k}: T_cost={d["T_cost"]:.2f}  T_benefit={d["T_benefit"]:.4f}  '
                  f'黄金={d["counts"]["黄金词"]} 重点={d["counts"]["重点词"]} '
                  f'潜力={d["counts"]["潜力词"]} 问题={d["counts"]["问题词"]}')
    report['S2_threshold_compare'] = {k: cmp_data[k]['counts'] for k in
                                       ['A_uniform_median', 'B_weighted_median', 'C_industry_benchmark']}

    # S3 ② 字段稳健性
    print('\n[S3 ②] 字段稳健性 4 组合 + Cohen κ ...')
    df_robust = field_robustness(df_valid)
    df_robust.to_csv(ROBUST_CSV, index=False, encoding='utf-8-sig')
    print(f'  → {ROBUST_CSV}')
    if verbose:
        print(df_robust.to_string(index=False))
    report['S3_field_robustness'] = df_robust.to_dict('records')

    # S5 ⑤ + S7 ⑥ 先做（要修改 df_all 的异常标记，再传给 S4 ③ 用）
    print('\n[S5 ⑤] ghost_browsing 标记 ...')
    df_all, n_ghost = flag_ghost_browsing(df_all)
    print(f'  ghost_browsing 词数：{n_ghost}')
    report['S5_ghost_browsing'] = n_ghost

    print('\n[S7 ⑥] 888 三零词细分 ...')
    df_all, n_revival, n_dead = zero_keyword_breakdown(df_all)
    print(f'  potential_revival：{n_revival} / truly_dead：{n_dead}')
    report['S7_zero_breakdown'] = {'potential_revival': n_revival, 'truly_dead': n_dead}

    # S4 ③ 极值审计 v2（用已带 异常标记 的 df_all，但 audit 流程独立）
    print('\n[S4 ③] 极值审计 v2（保留型 vs 削减型）...')
    # 需要先重做 mark_extreme（因为 pkl 里没有 审计规则1_q95 列）
    from src.q2_classify import mark_extreme
    df_audit_full = mark_extreme(df_all)
    audit_v2 = extreme_audit_v2(df_audit_full)
    audit_v2.to_csv(AUDIT_V2_CSV, index=False, encoding='utf-8-sig')
    print(f'  → {AUDIT_V2_CSV}（{len(audit_v2)} 词）')
    n_keep = (audit_v2['极值类型'] == '保留型极值').sum()
    n_cut = (audit_v2['极值类型'] == '削减型极值').sum()
    n_obs = (audit_v2['极值类型'] == '观察型极值').sum()
    print(f'  保留型={n_keep}（重点词）削减型={n_cut}（问题词）观察型={n_obs}')

    # 风险评级业务阈值分布
    risk_dist = audit_v2['风险评级_业务'].value_counts().to_dict()
    print(f'  业务风险评级分布：{risk_dist}')
    report['S4_audit_v2'] = {
        'n_total': len(audit_v2),
        'n_keep': int(n_keep), 'n_cut': int(n_cut), 'n_obs': int(n_obs),
        'risk_dist': risk_dist,
    }

    # S6 风险评级（业务阈值已嵌入 S4，无需额外输出）

    # 持久化 pkl（带异常标记）
    df_all.to_pickle(Q2_KEYWORD_PKL)
    print(f'\n更新 pkl → {Q2_KEYWORD_PKL}（新增 异常标记 列）')

    # 汇总报告
    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'汇总报告 → {REPORT_JSON}')

    return report


# =====================================================
# CLI
# =====================================================
if __name__ == '__main__':
    run_all(verbose=True)
