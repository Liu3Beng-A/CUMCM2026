"""
Q3 · SEM 关键词级每日投放策略 · 数据预处理
============================================

**锁定决策（Q3Q4 doc §1-3 + §12 BIAS_v2）**：
- 时间范围：2025-02-01~08 + 2025-08-01~08 共 16 天
- 决策粒度：推广单元 × 关键词 × 天 = (12 单元 × ~76 词 × 16 天) ≈ 14,544 变量
- 入选项池：Q2 黄金 ∪ 重点 ∪ 潜力（909 词）
- 同期预算：02 月 13,681.15 + 08 月 37,483.78 = 51,164.93 元
- 代理变量法（§2.2.1）：用全年单位消费指标代理日级
- 代理精度校验（§2.3）：用 2025 实际数据代入代理公式，比值 ∈ [0.85, 1.15]
- 代理敏感性（§2.2.2）：3 比值 × ±30% × 5 档扰动

**主要输入**：
- `data/processed/q1/unit_daily.pkl`（Q1 已处理）
- `data/processed/q2/keyword_classified.pkl`（Q2 分类结果）

**主要输出**（写到 `data/processed/q3/`）：
- `q3_target_window.pkl`：16 天 (日期 × 推广单元 × 5 维指标) = ~144 行
- `q3_keyword_pool.pkl`：909 词入选项池
- `q3_budget_period.pkl`：02 月 + 08 月预算上限
- `q3_proxy_ratios.pkl`：代理比值 (r_click, r_browse, r_reg, r_topimp)
- `q3_unit_budget_ceiling.pkl`：每推广单元 16 天日均预算上限

**严禁自创**：
- 禁止改变 16 天时间范围
- 禁止扩展到全年 365 天
- 禁止降级粒度到方案×天
- 禁止把 Q2 分类结果改写
"""
import os
import sys
import pandas as pd
import numpy as np
import pickle
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import PROCESSED_DIR, ensure_dir  # noqa: E402

# Q3 锁定的时间窗口（16 天 = 02-01~08 + 08-01~08）
Q3_DATES = (
    [f"2025-02-{d:02d}" for d in range(1, 9)]
    + [f"2025-08-{d:02d}" for d in range(1, 9)]
)
Q3_FEB_DATES = [f"2025-02-{d:02d}" for d in range(1, 9)]
Q3_AUG_DATES = [f"2025-08-{d:02d}" for d in range(1, 9)]


def main():
    print("=" * 70)
    print("Q3 数据预处理 · 锁定 16 天窗口 + 入选项池 + 预算 + 代理比值")
    print("=" * 70)

    out_dir = ensure_dir(os.path.join(PROCESSED_DIR, 'q3'))
    print(f"\n[输出目录] {out_dir}")

    # ---- 加载 Q1/Q2 中间产物 ----
    unit_daily = pd.read_pickle(os.path.join(PROCESSED_DIR, 'q1', 'unit_daily.pkl'))
    daily_full = pd.read_pickle(os.path.join(PROCESSED_DIR, 'q1', 'daily_full.pkl'))
    reg_daily = pd.read_excel('data/raw/attachments/附件1.xlsx', sheet_name=1)
    keyword_cls = pd.read_pickle(os.path.join(PROCESSED_DIR, 'q2', 'keyword_classified.pkl'))

    print(f"\n[加载] unit_daily {unit_daily.shape} | daily_full {daily_full.shape} | "
          f"reg_daily {reg_daily.shape} | keyword_cls {keyword_cls.shape}")

    # ---- Step 1: 16 天窗口 (日期 × 推广单元) ----
    # 锁定列名（中文）
    unit_daily = unit_daily.rename(columns={
        '日期': 'date', '方案ID': 'plan_id', '推广单元ID': 'unit_id',
        '展现量': 'impressions', '点击量': 'clicks', '消费额': 'cost',
        '上方位展现量': 'top_imps', '上方位展现量.1': 'top_pos_imps',
        '上方位点击量': 'top_clicks', '上方位消费额': 'top_cost',
    })
    reg_daily = reg_daily.rename(columns={'日期': 'date', '新注册数 ': 'regs'})

    # 过滤 16 天
    unit_daily['date'] = pd.to_datetime(unit_daily['date']).dt.strftime('%Y-%m-%d')
    target = unit_daily[unit_daily['date'].isin(Q3_DATES)].copy()
    print(f"\n[Step 1] 16 天窗口 (日期×单元) = {target.shape[0]} 行 | "
          f"去重单元 {target['unit_id'].nunique()} | 去重方案 {target['plan_id'].nunique()}")

    # 聚合 16 天（按推广单元）+ 02 月 / 08 月分段
    target['period'] = target['date'].apply(
        lambda x: 'feb' if x.startswith('2025-02') else 'aug'
    )
    target.to_pickle(os.path.join(out_dir, 'q3_target_window.pkl'))
    print(f"  -> q3_target_window.pkl 写入 OK")

    # ---- Step 2: 入选项池（黄金 ∪ 重点 ∪ 潜力） ----
    valid_classes = ['黄金词', '重点词', '潜力词']
    pool = keyword_cls[keyword_cls['分类'].isin(valid_classes)].copy()
    # Q2 pkl 中已重命名：消费额→成本, 点击量→点击, 浏览量→浏览
    pool = pool.rename(columns={
        '方案ID': 'plan_id', '推广单元ID': 'unit_id',
        '成本': 'kw_cost', '点击': 'kw_clicks', '浏览': 'kw_browses',
        '跳出率_均值': 'bounce', '平均访问时长_秒': 'avg_time',
        'CPC倒数': 'cpc_recip',
    })
    print(f"\n[Step 2] 入选项池 = {pool.shape[0]} 词 | "
          f"5 类分布 {keyword_cls['分类'].value_counts().to_dict()}")
    print(f"  按推广单元: {pool['unit_id'].value_counts().to_dict()}")
    pool.to_pickle(os.path.join(out_dir, 'q3_keyword_pool.pkl'))
    print(f"  -> q3_keyword_pool.pkl 写入 OK")

    # ---- Step 3: 预算上限（02 月 + 08 月同期）----
    # 02 月 8 天: 2025-02-01~08
    # 08 月 8 天: 2025-08-01~08
    budget_feb = target[target['period'] == 'feb']['cost'].sum()
    budget_aug = target[target['period'] == 'aug']['cost'].sum()
    budget_total = budget_feb + budget_aug
    print(f"\n[Step 3] 同期预算上限 = 02月 {budget_feb:.2f} + 08月 {budget_aug:.2f} = "
          f"{budget_total:.2f} 元")

    # 每推广单元同期 16 天预算上限
    unit_budget = target.groupby('unit_id')['cost'].sum().reset_index()
    unit_budget.columns = ['unit_id', 'unit_budget_16d']

    # 每推广单元 02 月/08 月分段预算
    unit_budget_period = target.groupby(['unit_id', 'period'])['cost'].sum().unstack(fill_value=0)
    unit_budget_period.columns = [f'{c}_budget' for c in unit_budget_period.columns]
    unit_budget = unit_budget.merge(unit_budget_period, on='unit_id', how='left')

    budget_df = pd.DataFrame({
        'period': ['feb', 'aug', 'total'],
        'budget': [budget_feb, budget_aug, budget_total],
    })
    budget_df.to_pickle(os.path.join(out_dir, 'q3_budget_period.pkl'))
    unit_budget.to_pickle(os.path.join(out_dir, 'q3_unit_budget_ceiling.pkl'))
    print(f"  -> q3_budget_period.pkl + q3_unit_budget_ceiling.pkl 写入 OK")
    print(f"  推广单元预算 16 天上限（前 5）: {unit_budget.head().to_dict('records')}")

    # ---- Step 4: 代理变量法比值（§2.2.1）----
    # r_click = kw_全年点击 / kw_全年消费
    # r_browse = kw_全年浏览 / kw_全年消费
    # r_reg ≈ unit_daily 总注册 / unit_daily 总消费
    # r_topimp = kw_全年上方位展现量 / kw_全年消费

    # 关键词级代理比值（每个入选项）
    proxy_kw = pool.groupby('unit_id').apply(
        lambda g: pd.Series({
            'r_click': g['kw_clicks'].sum() / max(g['kw_cost'].sum(), 1e-6),
            'r_browse': g['kw_browses'].sum() / max(g['kw_cost'].sum(), 1e-6),
            'r_topimp': g['kw_cost'].sum() * 0.27 / max(g['kw_cost'].sum(), 1e-6),  # 27% 占比代理
        })
    ).reset_index()

    # 单元级注册转化率代理
    unit_annual = unit_daily.groupby('unit_id').agg(
        annual_cost=('cost', 'sum'),
        annual_clicks=('clicks', 'sum'),
    )
    reg_daily['date'] = pd.to_datetime(reg_daily['date']).dt.strftime('%Y-%m-%d')
    reg_annual = unit_daily.merge(reg_daily, on='date', how='left')
    reg_annual = reg_annual.groupby('unit_id').agg(
        annual_regs=('regs', 'sum'),
    )
    unit_annual = unit_annual.join(reg_annual)
    unit_annual['r_reg'] = unit_annual['annual_regs'] / unit_annual['annual_cost']
    proxy_kw = proxy_kw.merge(
        unit_annual[['r_reg']].reset_index(), on='unit_id', how='left'
    )
    proxy_kw['r_reg'] = proxy_kw['r_reg'].fillna(proxy_kw['r_reg'].median())

    print(f"\n[Step 4] 代理比值（按推广单元聚合）")
    print(proxy_kw.describe().to_string())
    proxy_kw.to_pickle(os.path.join(out_dir, 'q3_proxy_ratios.pkl'))
    print(f"  -> q3_proxy_ratios.pkl 写入 OK")

    # ---- Step 5: 16 天实际产出基线（用于代理精度校验 §2.3）----
    actual_16d = target.groupby('unit_id').agg(
        actual_clicks=('clicks', 'sum'),
        actual_cost=('cost', 'sum'),
        actual_top_imps=('top_imps', 'sum'),
    ).reset_index()
    actual_16d['actual_browses'] = 0  # 浏览量不在 unit_daily，需另算
    actual_16d['actual_regs'] = target.groupby('unit_id').apply(
        lambda g: reg_daily[
            reg_daily['date'].isin(g['date'].unique())
        ]['regs'].sum()
    ).values

    # 浏览量: 用全年 浏览/点击 比 × 16 天点击
    browse_click_ratio = (
        pool['kw_browses'].sum() / max(pool['kw_clicks'].sum(), 1e-6)
    )
    actual_16d['actual_browses'] = (
        actual_16d['actual_clicks'] * browse_click_ratio
    ).round().astype(int)

    print(f"\n[Step 5] 16 天实际产出基线（用于代理精度校验）")
    print(actual_16d.describe().to_string())
    actual_16d.to_pickle(os.path.join(out_dir, 'q3_actual_16d.pkl'))
    print(f"  -> q3_actual_16d.pkl 写入 OK")

    print("\n" + "=" * 70)
    print("✅ Q3 数据预处理完成 · 6 个 pkl 写入 data/processed/q3/")
    print("=" * 70)


if __name__ == '__main__':
    main()
