"""
Q2 · 10 项验证脚本（自检清单，DoD）
====================================
跑完即输出 PASS/FAIL 报告，结果写入 results/tables/q2_check_report.json
"""
import os
import sys
import json
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.utils import (
    RAW_DIR, PROCESSED_DIR, RESULTS_DIR, TABLES_DIR, FIGURES_DIR, EXCEL_DIR
)

RESULT2_OUT = os.path.join(EXCEL_DIR, 'result2.xlsx')
UNIT_SUMMARY_CSV = os.path.join(TABLES_DIR, 'q2_unit_cluster_summary.csv')
EXTREME_AUDIT_CSV = os.path.join(TABLES_DIR, 'q2_extreme_audit.csv')
THRESHOLDS_JSON = os.path.join(TABLES_DIR, 'q2_thresholds.json')
KEYWORD_PKL = os.path.join(PROCESSED_DIR, 'q2', 'keyword_classified.pkl')

EXPECTED_COLS = ['方案ID', '推广单元', '序号', '黄金词', '重点词', '潜力词', '问题词', '无效词']
CLASS_COLS = ['黄金词', '重点词', '潜力词', '问题词', '无效词']

FIGURES = [
    'q2_class_distribution.png',
    'q2_threshold_sensitivity.png',
    'q2_extreme_audit.png',
    'q2_unit_class_stacked.png',
]


def check(label: str, cond: bool, expected, actual) -> dict:
    """单条校验"""
    status = 'PASS' if cond else 'FAIL'
    print(f'  [{status}] {label}: 期望={expected}, 实际={actual}')
    return {
        'check': label,
        'status': status,
        'expected': expected,
        'actual': actual,
    }


def main():
    print('=' * 60)
    print('Q2 10 项自检清单')
    print('=' * 60)

    results = []

    # 1. result2 行数 = 2227
    print('\n[1] result2.xlsx 行数 ...')
    df = pd.read_excel(RESULT2_OUT)
    results.append(check('result2 行数', len(df) == 2227, 2227, len(df)))

    # 2. result2 列名严格 8 列对齐模板
    print('\n[2] result2.xlsx 列名（严格对齐附件 2 模板）...')
    actual_cols = list(df.columns)
    results.append(check('result2 列名对齐', actual_cols == EXPECTED_COLS, EXPECTED_COLS, actual_cols))

    # 3. one-hot 完整性
    print('\n[3] one-hot 自洽（每行 5 类之和 = 1）...')
    s = df[CLASS_COLS].sum(axis=1)
    uniq = sorted(s.unique().tolist())
    results.append(check('one-hot 自洽', uniq == [1], '[1]', uniq))

    # 4. 5 类总数 = 2227
    print('\n[4] 5 类总数 ...')
    total = int(df[CLASS_COLS].sum().sum())
    results.append(check('5 类总数 = 2227', total == 2227, 2227, total))

    # 5. 无效词 ≥ 890
    print('\n[5] 无效词规则（消费=0 全部归无效）...')
    n_invalid = int(df['无效词'].sum())
    results.append(check('无效词 ≥ 890', n_invalid >= 890, '≥ 890', n_invalid))

    # 6. 推广单元聚合表行数（Sheet3 中 5 方案共享 12 推广单元，去重后 12 行）
    print('\n[6] 推广单元聚合表行数（Sheet3 实际去重 = 12）...')
    df_unit = pd.read_csv(UNIT_SUMMARY_CSV)
    n_unit = len(df_unit)
    results.append(check('推广单元聚合表行数 ∈ [10, 15]', 10 <= n_unit <= 15, '[10, 15]', n_unit))

    # 7. 双表一致性（明细 vs 聚合）
    print('\n[7] 双表一致性（明细 5 类 sum = 聚合 5 类 sum）...')
    detail_sums = {c: int(df[c].sum()) for c in CLASS_COLS}
    agg_sums = {c: int(df_unit[c].sum()) for c in CLASS_COLS}
    consistent = all(detail_sums[c] == agg_sums[c] for c in CLASS_COLS)
    results.append(check('双表 5 类一致性', consistent, detail_sums, agg_sums))

    # 8. 极值审计行数 ∈ [90, 120]
    print('\n[8] 极值审计行数（90~120）...')
    df_audit = pd.read_csv(EXTREME_AUDIT_CSV)
    n_audit = len(df_audit)
    results.append(check('极值审计词数 ∈ [90, 120]', 90 <= n_audit <= 120, '[90, 120]', n_audit))

    # 9. 4 张图齐全
    print('\n[9] 4 张图齐全 ...')
    missing = [f for f in FIGURES if not os.path.exists(os.path.join(FIGURES_DIR, f))]
    results.append(check('4 张图齐全', len(missing) == 0, FIGURES, missing))

    # 10. Q1 综合分 50.7 未变（间接：score.json 存在 + 读出 overall）
    print('\n[10] Q1 综合分未变（间接校验 score.json 存在）...')
    q1_score_path = os.path.join(TABLES_DIR, 'q1_score.json')
    q1_ok = os.path.exists(q1_score_path)
    if q1_ok:
        with open(q1_score_path, 'r', encoding='utf-8') as f:
            q1_score = json.load(f)
        overall = q1_score.get('overall_score', None)
        results.append(check('Q1 综合分保持 50.7', overall == 50.7, 50.7, overall))
    else:
        results.append(check('Q1 综合分保持 50.7', False, 50.7, 'q1_score.json missing'))

    # 汇总
    print('\n' + '=' * 60)
    n_pass = sum(1 for r in results if r['status'] == 'PASS')
    n_fail = sum(1 for r in results if r['status'] == 'FAIL')
    print(f'汇总：{n_pass}/{len(results)} PASS, {n_fail} FAIL')
    print('=' * 60)

    report = {
        'n_pass': n_pass,
        'n_fail': n_fail,
        'total': len(results),
        'results': results,
    }
    out_path = os.path.join(TABLES_DIR, 'q2_check_report.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\n报告写入：{out_path}')

    if n_fail == 0:
        print('\n🎉 Q2 10 项自检全部 PASS！')
        return 0
    else:
        print(f'\n⚠️ {n_fail} 项 FAIL，需修复后重跑')
        return 1


if __name__ == '__main__':
    sys.exit(main())
