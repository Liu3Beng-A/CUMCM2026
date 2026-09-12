"""
Q4 · 数据预处理 + 不确定性估计（PoC 修订 · 合并版）
======================================================

**锁定决策（D-Q3Q4-024 / PoC_REPORT §2.1）**：
- ⚠️ 同期口径：2025-09-11~17 = 7 天同期预算 = 23,488.02 元（已验证）
- ⚠️ 不确定性从 **推广单元级历史 30 天** 估计 CV（不是全年 365 天）
- ⚠️ 6 因子 CV：cpc / impressions / top_imp_pos / clicks / browses / regs
- ⚠️ 6 因子间允许弱相关，但模型化为独立扰动（PoC 简化）

**主要输入**：
- `data/processed/q1/unit_daily.pkl`：2025 全年单元日
- `data/processed/q2/keyword_classified.pkl`：909 词
- `data/processed/q3/q3_optimal_plan.pkl`：Q3 计划（用于 Q4 同期对照）

**主要输出**（写到 `data/processed/q4/`）：
- `q4_same_period_2025.pkl`：2025-09-11~17 单元日数据
- `q4_unit_cv.pkl`：12 单元 × 6 因子 CV（不确定性矩阵）
- `q4_budget_ceiling.pkl`：同期预算 = 23,488.02 元
- `q4_uncertainty_summary.json`：CV 汇总
"""
import os
import sys
import pandas as pd
import numpy as np
import pickle
import json
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import PROCESSED_DIR, ensure_dir  # noqa: E402


# Q4 锁定参数
Q4_DATES_2025 = [f"2025-09-{d:02d}" for d in range(11, 18)]  # 同期 7 天
Q4_DATES_2026 = [f"2026-09-{d:02d}" for d in range(11, 18)]  # 预测 7 天
HISTORY_DAYS = 30  # CV 估计窗口：最近 30 天
UNCERTAINTY_FACTORS = ['cpc', 'impressions', 'top_imp_pos', 'clicks', 'browses', 'regs']


def main():
    print("=" * 70)
    print("Q4 · 数据预处理 + 不确定性估计（PoC 修订）")
    print("=" * 70)

    out_dir = ensure_dir(os.path.join(PROCESSED_DIR, 'q4'))

    # ---- 加载 ----
    unit_daily = pd.read_pickle(os.path.join(PROCESSED_DIR, 'q1', 'unit_daily.pkl'))
    unit_daily = unit_daily.rename(columns={
        '日期': 'date', '方案ID': 'plan_id', '推广单元ID': 'unit_id',
        '展现量': 'impressions', '点击量': 'clicks', '消费额': 'cost',
        '上方位展现量': 'top_imp', 'CTR': 'ctr', 'CPC': 'cpc',
    })
    unit_daily['date'] = pd.to_datetime(unit_daily['date']).dt.strftime('%Y-%m-%d')
    reg_daily = pd.read_excel('data/raw/attachments/附件1.xlsx', sheet_name=1)
    reg_daily = reg_daily.rename(columns={'日期': 'date', '新注册数 ': 'regs'})
    reg_daily['date'] = pd.to_datetime(reg_daily['date']).dt.strftime('%Y-%m-%d')

    print(f"\n[输入] unit_daily {unit_daily.shape} | reg_daily {reg_daily.shape}")

    # ---- Step 1: 2025-09-11~17 同期 7 天 ----
    same_period = unit_daily[unit_daily['date'].isin(Q4_DATES_2025)].copy()
    print(f"\n[Step 1] 同期 7 天 = {same_period.shape[0]} 行 | "
          f"去重单元 {same_period['unit_id'].nunique()}")
    same_period.to_pickle(os.path.join(out_dir, 'q4_same_period_2025.pkl'))

    # 浏览量代理 = 点击 × 历史 浏览/点击 比
    kw_pool = pd.read_pickle(os.path.join(PROCESSED_DIR, 'q2', 'keyword_classified.pkl'))
    browse_per_click = kw_pool['浏览'].sum() / max(kw_pool['点击'].sum(), 1e-6)
    print(f"  浏览/点击 比 = {browse_per_click:.3f}")

    same_period['browses'] = (same_period['clicks'] * browse_per_click).round().astype(int)
    same_period = same_period.merge(reg_daily, on='date', how='left')
    same_period['regs'] = same_period['regs'].fillna(0)
    # reg 分配：按当日 click 占比
    daily_click_sum = same_period.groupby('date')['clicks'].transform('sum')
    same_period['regs'] = (
        same_period['regs'] * same_period['clicks'] / daily_click_sum.clip(lower=1)
    ).fillna(0).round().astype(int)
    # 含 browses/regs 重新保存
    same_period.to_pickle(os.path.join(out_dir, 'q4_same_period_2025.pkl'))

    # 同期预算
    same_period_budget = same_period['cost'].sum()
    print(f"  同期预算 = {same_period_budget:.2f} 元")

    # ---- Step 2: 不确定性 CV（历史 30 天推广单元级）----
    # 窗口：2025-08-18 ~ 2025-09-16 (30 天覆盖同期前 26 天 + 同期 7 天)
    history_start = '2025-08-18'
    history_end = '2025-09-16'  # 比同期截止 09-17 早 1 天
    history = unit_daily[
        (unit_daily['date'] >= history_start) & (unit_daily['date'] <= history_end)
    ].copy()
    print(f"\n[Step 2] 历史 {HISTORY_DAYS} 天 ({history_start} ~ {history_end}) = "
          f"{history.shape[0]} 行")

    history = history.merge(reg_daily, on='date', how='left')
    history['regs'] = history['regs'].fillna(0)
    # reg 分配：按当日 click 占比
    daily_click_sum = history.groupby('date')['clicks'].transform('sum')
    history['regs'] = (
        history['regs'] * history['clicks'] / daily_click_sum.clip(lower=1)
    ).fillna(0).round().astype(int)
    history['browses'] = (history['clicks'] * browse_per_click).round().astype(int)
    history['top_imp_pos'] = history['top_imp']
    history['cpc'] = history['CPC'] if 'CPC' in history.columns else history['cpc']

    # CV = std / mean
    cv_records = []
    for u in sorted(history['unit_id'].unique()):
        sub = history[history['unit_id'] == u]
        if len(sub) < 5:
            continue
        rec = {'unit_id': u}
        for fac in UNCERTAINTY_FACTORS:
            if fac in sub.columns:
                vals = sub[fac].dropna()
                if len(vals) > 0 and vals.mean() > 0:
                    rec[f'cv_{fac}'] = float(vals.std() / vals.mean())
                else:
                    rec[f'cv_{fac}'] = 0.5  # fallback
            else:
                rec[f'cv_{fac}'] = 0.5
        cv_records.append(rec)
    cv_df = pd.DataFrame(cv_records)
    print(f"  单元 CV 矩阵 = {cv_df.shape}")
    print(cv_df.describe().to_string())
    cv_df.to_pickle(os.path.join(out_dir, 'q4_unit_cv.pkl'))

    # ---- Step 3: 同期预算上限 ----
    budget_data = {
        'period': '2025-09-11~17',
        'budget': float(same_period_budget),
        'days': 7,
        'daily_avg': float(same_period_budget / 7),
    }
    budget_path = os.path.join(out_dir, 'q4_budget_ceiling.pkl')
    pd.DataFrame([budget_data]).to_pickle(budget_path)
    print(f"\n[Step 3] 同期预算 = {same_period_budget:.2f} 元 / 7 天 = "
          f"{same_period_budget/7:.2f} 元/天")

    # ---- Step 4: 不确定性汇总 ----
    summary = {
        'same_period': '2025-09-11~17',
        'same_period_budget': float(same_period_budget),
        'history_window': f'{history_start} ~ {history_end}',
        'history_days': HISTORY_DAYS,
        'n_units_cv': int(cv_df.shape[0]),
        'mean_cv': {f'cv_{fac}': float(cv_df[f'cv_{fac}'].mean()) for fac in UNCERTAINTY_FACTORS},
        'median_cv': {f'cv_{fac}': float(cv_df[f'cv_{fac}'].median()) for fac in UNCERTAINTY_FACTORS},
        'max_cv': {f'cv_{fac}': float(cv_df[f'cv_{fac}'].max()) for fac in UNCERTAINTY_FACTORS},
        'factors': UNCERTAINTY_FACTORS,
        'correlation_model': 'independent (PoC simplification)',
    }
    summary_path = os.path.join(out_dir, 'q4_uncertainty_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n  -> q4_uncertainty_summary.json 写入 OK")

    # ---- Step 5: 同期预算明细（按单元）----
    unit_budget_q4 = same_period.groupby('unit_id')['cost'].sum().reset_index()
    unit_budget_q4.columns = ['unit_id', 'unit_budget_7d']
    unit_budget_q4.to_pickle(os.path.join(out_dir, 'q4_unit_budget_ceiling.pkl'))
    print(f"\n[Step 5] 同期 7 天 单元预算上限（前 5）:")
    print(unit_budget_q4.head().to_string())

    print("\n" + "=" * 70)
    print(f"✅ Q4 数据预处理完成 · 同期预算 {same_period_budget:.2f} 元")
    print("=" * 70)


if __name__ == '__main__':
    main()
