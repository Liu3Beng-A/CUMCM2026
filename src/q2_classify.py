"""
Q2 · SEM 关键词 5 类分类（投入成本 × 效益）
============================================

**实现口径（5 项决策，2026-09-12 14:30 用户拍板，Locked）**
- D-Q2-001 行粒度 = 2227 行明细（one-hot）+ 60 行推广单元聚合（双输出）
- D-Q2-002 阈值字段 = 成本=消费额 / 效益=CPC 倒数（=点击量/消费额）
- D-Q2-003 无效词判定 = 消费=0 即无效（890 词）
- D-Q2-004 双输出 = 2227 明细 → result2.xlsx；60 聚合 → q2_unit_cluster_summary.csv
- D-Q2-005 极值审计 = 消费 > q95（≈500 元）的 ~112 关键词做单独审计

**主要输入**：`data/raw/attachments/附件1.xlsx` Sheet3（2227 关键词）
**主输出**：`results/excel/result2.xlsx`（严格 8 列对齐附件 2 模板）
          `data/processed/q2/keyword_classified.pkl`（Q3 直接消费）
          `results/tables/q2_thresholds.json`（阈值参数）
          `results/tables/q2_unit_cluster_summary.csv`（60 行推广单元聚合）
          `results/tables/q2_extreme_audit.csv`（~112 极值词）
          `results/figures/q2_*.png`（3 张图：5 类分布 / 阈值敏感性 / 极值审计）

**方法栈（4 块）**
1. 数据加载 + 数值化（跳出率'/' → NaN → 0.5 中性填充；平均访问时长'/' → 0 秒）
2. 无效词判定（D-Q2-003：消费=0）
3. 有效词二维硬阈值分类（D-Q2-002：成本中位数 × 效益中位数 → 4 象限）
4. 极值审计（D-Q2-005：q95 消费 + 高 CPC 高消费）

**严禁自创**：禁止 GMM / KMeans / 谱聚类；禁止修改主分类器使用 5 维特征
**继承口径**：禁止修改 Q1 已确定的口径（评分函数 / 权重混合 / Bootstrap n=100 / BH FDR / 节日扣分封顶 -30）
"""
import os
import sys
import json
import argparse
import numpy as np
import pandas as pd

# 项目根目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.utils import (
    RAW_DIR, PROCESSED_DIR, RESULTS_DIR, TABLES_DIR, FIGURES_DIR, ensure_dir
)

# =====================================================
# 路径常量
# =====================================================
ATTACHMENT1 = os.path.join(RAW_DIR, 'attachments', '附件1.xlsx')
ATTACHMENT2 = os.path.join(RAW_DIR, 'attachments', '附件2', 'result2.xlsx')
RESULT2_OUT = os.path.join(EXCEL_DIR, 'result2.xlsx')  # 主交付（统一汇总至 results/excel/）

Q2_PROCESSED_DIR = os.path.join(PROCESSED_DIR, 'q2')
Q2_KEYWORD_PKL = os.path.join(Q2_PROCESSED_DIR, 'keyword_classified.pkl')

THRESHOLDS_JSON = os.path.join(TABLES_DIR, 'q2_thresholds.json')
UNIT_SUMMARY_CSV = os.path.join(TABLES_DIR, 'q2_unit_cluster_summary.csv')
EXTREME_AUDIT_CSV = os.path.join(TABLES_DIR, 'q2_extreme_audit.csv')

FIG_DIST = os.path.join(FIGURES_DIR, 'q2_class_distribution.png')
FIG_SENSITIVITY = os.path.join(FIGURES_DIR, 'q2_threshold_sensitivity.png')
FIG_AUDIT = os.path.join(FIGURES_DIR, 'q2_extreme_audit.png')
FIG_UNIT_STACKED = os.path.join(FIGURES_DIR, 'q2_unit_class_stacked.png')

# =====================================================
# 5 类标签（中英对照）
# =====================================================
CLASS_NAMES = ['黄金词', '重点词', '潜力词', '问题词', '无效词']
CLASS_COLS = ['黄金词', '重点词', '潜力词', '问题词', '无效词']
VALID_CLASSES = ['黄金词', '重点词', '潜力词', '问题词']  # 4 象限


# =====================================================
# Step 1 · 数据加载
# =====================================================
def load_sheet3(path: str = ATTACHMENT1) -> pd.DataFrame:
    """读 Sheet3 + 数值化

    - 跳出率：'/' → NaN → 0.5 中性填充
    - 平均访问时长：'HH:MM:SS' → 秒；'/' → 0
    - 5 维特征齐备：消费 / 点击 / 浏览 / 跳出率 / 平均访问时长(秒)
    """
    df = pd.read_excel(path, sheet_name=2)

    # 跳出率：object → 浮点（'/' 当 NaN）
    df['跳出率_数值'] = pd.to_numeric(df['跳出率'], errors='coerce').fillna(0.5)

    # 平均访问时长：'HH:MM:SS' 转秒，'/' 当 0
    def parse_dur(s):
        if not isinstance(s, str):
            return 0.0
        s = s.strip()
        if s in ('/', ''):
            return 0.0
        try:
            parts = s.split(':')
            if len(parts) == 3:
                h, m, sec = parts
                return int(h) * 3600 + int(m) * 60 + int(sec)
            elif len(parts) == 2:
                m, sec = parts
                return int(m) * 60 + int(sec)
            return float(s)
        except Exception:
            return 0.0

    df['平均访问时长_秒'] = df['平均访问时长'].apply(parse_dur)

    # 关键字段：消费额、点击量、浏览量已为数值
    df = df.rename(columns={
        '消费额': '成本',
        '点击量': '点击',
        '浏览量': '浏览',
    })
    return df


# =====================================================
# Step 2 · 无效词判定（D-Q2-003）
# =====================================================
def mark_invalid(df: pd.DataFrame) -> pd.DataFrame:
    """消费=0 标无效词（D-Q2-003）

    题面语义："无效词：无成本、无效益"
    数据观察：888 词 3 全零（消费=点击=浏览=0） + 2 词 0 消费但有少量点击（异常）
              → 一律按"无成本"判定为无效词，与业务语义一致
    """
    df = df.copy()
    df['分类'] = np.where(df['成本'] <= 0.0, '无效词', None)
    return df


# =====================================================
# Step 3 · 二维硬阈值（D-Q2-002）
# =====================================================
def compute_thresholds(df_valid: pd.DataFrame) -> dict:
    """有效词中位数 = 双阈值（D-Q2-002）

    - axis_cost = 消费额（中位数）
    - axis_benefit = CPC 倒数 = 点击量 / max(消费额, 0.01)
    """
    cost = df_valid['成本'].astype(float).values
    clicks = df_valid['点击'].astype(float).values

    # CPC 倒数（避免除零）
    cpc_inv = clicks / np.maximum(cost, 0.01)

    T_cost = float(np.median(cost))
    T_benefit = float(np.median(cpc_inv))

    return {
        'T_cost': T_cost,
        'T_benefit': T_benefit,
        'n_valid': int(len(df_valid)),
        'axis_cost': '消费额（元）',
        'axis_benefit': 'CPC 倒数 = 点击量/消费额（点击/元）',
        'method': '中位数（中位数分桶，对 heavy-tail 较稳定）',
    }


def classify_two_d(df_valid: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
    """有效词 4 象限分类

    黄金词：低成本、高效益
    重点词：高成本、高效益
    潜力词：低成本、低效益
    问题词：高成本、低效益
    """
    df = df_valid.copy()
    T_c = thresholds['T_cost']
    T_b = thresholds['T_benefit']

    cost = df['成本'].astype(float).values
    clicks = df['点击'].astype(float).values
    cpc_inv = clicks / np.maximum(cost, 0.01)

    # 4 象限分类
    classes = []
    for c, b in zip(cost, cpc_inv):
        if c <= T_c and b >= T_b:
            classes.append('黄金词')
        elif c > T_c and b >= T_b:
            classes.append('重点词')
        elif c <= T_c and b < T_b:
            classes.append('潜力词')
        else:
            classes.append('问题词')

    df['CPC倒数'] = cpc_inv
    df['分类'] = classes
    return df


# =====================================================
# Step 4 · One-hot 生成 result2.xlsx
# =====================================================
def build_one_hot(df_all: pd.DataFrame) -> pd.DataFrame:
    """生成 result2 模板格式（严格 8 列对齐附件 2）"""
    rows = []
    for _, row in df_all.iterrows():
        d = {
            '方案ID': int(row['方案ID']),
            '推广单元': int(row['推广单元ID']),  # 模板用"推广单元"，Sheet3 是"推广单元ID"
            '序号': int(row['序号']),
            '黄金词': 1 if row['分类'] == '黄金词' else 0,
            '重点词': 1 if row['分类'] == '重点词' else 0,
            '潜力词': 1 if row['分类'] == '潜力词' else 0,
            '问题词': 1 if row['分类'] == '问题词' else 0,
            '无效词': 1 if row['分类'] == '无效词' else 0,
        }
        rows.append(d)

    return pd.DataFrame(rows, columns=[
        '方案ID', '推广单元', '序号',
        '黄金词', '重点词', '潜力词', '问题词', '无效词'
    ])


# =====================================================
# Step 5 · 不变量校验
# =====================================================
def assert_invariants(df_result: pd.DataFrame) -> None:
    """5 类完整性 + one-hot 校验（D-Q2-001 + D-Q2-004）"""
    # 行数
    assert len(df_result) == 2227, f'行数应为 2227，实际 {len(df_result)}'
    # 列名
    expected = ['方案ID', '推广单元', '序号', '黄金词', '重点词', '潜力词', '问题词', '无效词']
    assert list(df_result.columns) == expected, f'列名错：{list(df_result.columns)}'
    # one-hot 完整性：每行 5 类之和 = 1
    s = df_result[CLASS_COLS].sum(axis=1)
    assert (s == 1).all(), f'one-hot 不自洽，sum 分布：{s.value_counts().to_dict()}'
    # 5 类总数 = 2227
    assert df_result[CLASS_COLS].sum().sum() == 2227, '5 类总数不等于 2227'
    print('  ✅ invariants OK: 2227 行 / 8 列 / one-hot 自洽')


# =====================================================
# Step 6 · 推广单元聚合（D-Q2-004）
# =====================================================
def aggregate_by_unit(df_all: pd.DataFrame, df_result: pd.DataFrame) -> pd.DataFrame:
    """(方案, 推广单元) 双键聚合 5 类计数 + 总消费 + 总点击 + 平均 CPC

    注：模板列名是"推广单元"（非"推广单元ID"），聚合表沿用
    """
    df = df_all.copy()
    df['黄金词'] = (df['分类'] == '黄金词').astype(int)
    df['重点词'] = (df['分类'] == '重点词').astype(int)
    df['潜力词'] = (df['分类'] == '潜力词').astype(int)
    df['问题词'] = (df['分类'] == '问题词').astype(int)
    df['无效词'] = (df['分类'] == '无效词').astype(int)

    grouped = df.groupby(['方案ID', '推广单元ID'], as_index=False).agg(
        关键词总数=('序号', 'count'),
        黄金词=('黄金词', 'sum'),
        重点词=('重点词', 'sum'),
        潜力词=('潜力词', 'sum'),
        问题词=('问题词', 'sum'),
        无效词=('无效词', 'sum'),
        总消费=('成本', 'sum'),
        总点击=('点击', 'sum'),
        总浏览=('浏览', 'sum'),
    )
    grouped['平均CPC'] = np.where(
        grouped['总点击'] > 0,
        grouped['总消费'] / grouped['总点击'],
        np.nan
    )
    # 重命名推广单元ID → 推广单元（与模板列名一致）
    grouped = grouped.rename(columns={'推广单元ID': '推广单元'})
    return grouped


# =====================================================
# Step 7 · 极值审计（D-Q2-005）
# =====================================================
def mark_extreme(df_all: pd.DataFrame) -> pd.DataFrame:
    """极值审计：消费 > q95 + 高 CPC 高消费（去重 ~112 词）

    触发规则（仅 2 条，避免过度复杂）：
    1. 消费 > q95 关键词（约 67 词）
    2. CPC > 5 元 且 消费 > q75（约 45 词，与规则 1 有重叠）
    去重后：~112 词
    """
    df = df_all.copy()
    cost = df['成本'].astype(float).values
    clicks = df['点击'].astype(float).values
    cpc = np.where(clicks > 0, cost / np.maximum(clicks, 1), np.inf)

    p95 = float(np.percentile(cost[cost > 0], 95)) if (cost > 0).any() else 0.0
    p75 = float(np.percentile(cost[cost > 0], 75)) if (cost > 0).any() else 0.0

    # 计算总消费归一化 × (1 - 效益归一化) 用于风险评级
    valid_mask = cost > 0
    if valid_mask.sum() > 0:
        cost_norm = (cost - cost.min()) / max(cost.max() - cost.min(), 1e-6)
        # 效益越高风险越低
        cpc_inv = clicks / np.maximum(cost, 0.01)
        b_norm = (cpc_inv - cpc_inv.min()) / max(cpc_inv.max() - cpc_inv.min(), 1e-6)
        risk_score = cost_norm * (1 - b_norm)
    else:
        risk_score = np.zeros_like(cost)

    # 风险评级（基于 33% / 66% 分位）
    p33 = float(np.percentile(risk_score[valid_mask], 33)) if valid_mask.sum() > 0 else 0
    p66 = float(np.percentile(risk_score[valid_mask], 66)) if valid_mask.sum() > 0 else 0

    def risk_label(s):
        if s >= p66:
            return '高'
        elif s >= p33:
            return '中'
        else:
            return '低'

    # 审计触发
    df['审计规则1_q95'] = cost > p95
    df['审计规则2_高CPC高消费'] = (cpc > 5.0) & (cost > p75)
    df['触发审计'] = df['审计规则1_q95'] | df['审计规则2_高CPC高消费']

    df['风险评分'] = risk_score
    df['风险评级'] = [risk_label(s) if (cost[i] > 0) else '低' for i, s in enumerate(risk_score)]

    return df


def export_extreme_audit(df_extreme: pd.DataFrame, path: str = EXTREME_AUDIT_CSV) -> None:
    """导出 ~112 极值词审计表

    字段：序号 | 关键词 | 方案ID | 推广单元 | 分类 | 消费 | 点击 | 浏览 | CPC | 风险评级 | 触发规则
    """
    audited = df_extreme[df_extreme['触发审计']].copy()

    audited['推广单元'] = audited['推广单元ID']  # 重命名以匹配模板
    audited['CPC'] = audited['成本'] / np.maximum(audited['点击'], 1)

    # 触发规则标签
    audited['触发规则'] = audited.apply(
        lambda r: (
            'q95' if r['审计规则1_q95'] and not r['审计规则2_高CPC高消费']
            else '高CPC高消费' if r['审计规则2_高CPC高消费'] and not r['审计规则1_q95']
            else '双触发'
        ), axis=1
    )

    out = audited[[
        '序号', '关键词', '方案ID', '推广单元', '分类',
        '成本', '点击', '浏览', 'CPC', '风险评级', '触发规则'
    ]].rename(columns={'成本': '消费', '点击': '点击量', '浏览': '浏览量'})
    out = out.sort_values('消费', ascending=False).reset_index(drop=True)
    out.to_csv(path, index=False, encoding='utf-8-sig')
    print(f'  ✅ 极值审计导出 → {path}（{len(out)} 词）')
    return out


# =====================================================
# Step 8 · 主流程
# =====================================================
def run(verbose: bool = True) -> dict:
    """Q2 主流程：5 步执行"""
    print('=' * 60)
    print('Q2 关键词 5 类分类（投入成本 × 效益）')
    print('=' * 60)

    ensure_dir(Q2_PROCESSED_DIR)
    ensure_dir(TABLES_DIR)
    ensure_dir(FIGURES_DIR)

    # Step 1: 加载
    print('\n[Step 1] 加载 Sheet3 + 数值化 ...')
    df = load_sheet3()
    if verbose:
        print(f'  shape={df.shape}')
        print(f'  数值字段：成本/点击/浏览/跳出率_数值/平均访问时长_秒')

    # Step 2: 无效词判定
    print('\n[Step 2] 无效词判定（D-Q2-003：消费=0 即无效） ...')
    df = mark_invalid(df)
    n_invalid = (df['分类'] == '无效词').sum()
    if verbose:
        print(f'  无效词数：{n_invalid}（期望 ≈ 890）')

    # Step 3: 有效词 + 阈值 + 4 象限
    df_valid = df[df['分类'].isna()].copy()
    if verbose:
        print(f'  有效词数：{len(df_valid)}')

    print('\n[Step 3] 二维硬阈值分类（D-Q2-002：成本中位数 × CPC 倒数中位数） ...')
    thresholds = compute_thresholds(df_valid)
    if verbose:
        print(f'  T_cost（消费中位数）={thresholds["T_cost"]:.4f} 元')
        print(f'  T_benefit（CPC 倒数中位数）={thresholds["T_benefit"]:.4f} 点击/元')

    df_valid = classify_two_d(df_valid, thresholds)

    # 合并 + 5 类计数
    df_all = pd.concat([df_valid, df[df['分类'] == '无效词']], ignore_index=True)
    counts = df_all['分类'].value_counts().to_dict()
    if verbose:
        print(f'  5 类计数：')
        for k in CLASS_NAMES:
            print(f'    {k}: {counts.get(k, 0)}')

    # Step 4: One-hot + result2.xlsx
    print('\n[Step 4] 生成 result2.xlsx（D-Q2-001 + D-Q2-004） ...')
    df_result = build_one_hot(df_all)
    assert_invariants(df_result)

    df_result.to_excel(RESULT2_OUT, index=False)
    print(f'  ✅ 主交付物导出 → {RESULT2_OUT}')

    # Step 5: 推广单元聚合
    print('\n[Step 5] 推广单元聚合表（D-Q2-004） ...')
    df_unit = aggregate_by_unit(df_all, df_result)
    df_unit.to_csv(UNIT_SUMMARY_CSV, index=False, encoding='utf-8-sig')
    print(f'  ✅ 推广单元聚合表导出 → {UNIT_SUMMARY_CSV}（{len(df_unit)} 行）')

    # Step 6: 阈值参数 JSON
    print('\n[Step 6] 阈值参数 JSON ...')
    thresholds_out = {
        **thresholds,
        'counts': {k: int(counts.get(k, 0)) for k in CLASS_NAMES},
        'policies': {
            'D-Q2-001': '2227 明细 one-hot + 60 聚合双输出',
            'D-Q2-002': '成本=消费额 / 效益=CPC 倒数',
            'D-Q2-003': '消费=0 即无效词',
            'D-Q2-004': '双输出（2227 明细 → result2.xlsx；60 聚合 → unit_summary.csv）',
            'D-Q2-005': '极值审计（消费 > q95 或 高CPC高消费，~112 词）',
        }
    }
    with open(THRESHOLDS_JSON, 'w', encoding='utf-8') as f:
        json.dump(thresholds_out, f, ensure_ascii=False, indent=2)
    print(f'  ✅ 阈值参数 → {THRESHOLDS_JSON}')

    # Step 7: 极值审计（D-Q2-005）
    print('\n[Step 7] 极值审计（D-Q2-005） ...')
    df_audit = mark_extreme(df_all)
    audit_out = export_extreme_audit(df_audit, EXTREME_AUDIT_CSV)

    # Step 8: 持久化 pkl（Q3 直接消费）
    df_all.to_pickle(Q2_KEYWORD_PKL)
    print(f'  ✅ 关键词分类 pkl → {Q2_KEYWORD_PKL}（Q3 可直接 join）')

    return {
        'df_result': df_result,
        'df_unit': df_unit,
        'thresholds': thresholds_out,
        'audit': audit_out,
        'df_all': df_all,
    }


# =====================================================
# CLI
# =====================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Q2 关键词 5 类分类')
    parser.add_argument('--verbose', action='store_true', default=True)
    args = parser.parse_args()
    run(verbose=args.verbose)
