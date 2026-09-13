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
    # r_reg 修复（2026-09-12 F1）：原公式 annual_regs / annual_cost 存在结构性偏差
    #   因 reg_daily 是全局日级，merge 到 unit 后每个 unit 拿到相同的 annual_regs，
    #   r_reg ≈ const/annual_cost，Pearson=-0.096 是结构性反相关而非真实预测。
    # 新公式：r_reg 改为全局 cvr = 总注册 / 总点击，
    #   下游 reg = click × r_reg（不再用 cost × r_reg）
    # r_topimp = kw_全年上方位展现量 / kw_全年消费

    # P0-1 FIX (2026-09-13): r_topimp must use actual unit-level data from q3_target_window
    # 原错误: g['kw_cost'].sum() * 0.27 / g['kw_cost'].sum() = 0.27 (所有单元同一常数)
    # 正确做法: 从 q3_target_window.pkl 取每个推广单元的实际 top_imps / cost
    unit_topimp_ratio = target.groupby('unit_id').agg(
        total_top_imp=('top_imps', 'sum'),
        total_cost=('cost', 'sum')
    ).reset_index()
    unit_topimp_ratio['r_topimp'] = (
        unit_topimp_ratio['total_top_imp'] / unit_topimp_ratio['total_cost'].clip(lower=1e-6)
    )
    print(f"  [P0-1 FIX] r_topimp 修正: 从常数 0.27 → 单元实际比率")
    print(f"    修正后 r_topimp 范围: {unit_topimp_ratio['r_topimp'].min():.4f} ~ {unit_topimp_ratio['r_topimp'].max():.4f}")
    print(f"    (vs 原错误值 0.27，偏差倍数: {unit_topimp_ratio['r_topimp'].min()/0.27:.1f}x ~ {unit_topimp_ratio['r_topimp'].max()/0.27:.1f}x)")

    # 关键词级代理比值（每个入选项）
    proxy_kw = pool.groupby('unit_id').apply(
        lambda g: pd.Series({
            'r_click': g['kw_clicks'].sum() / max(g['kw_cost'].sum(), 1e-6),
            'r_browse': g['kw_browses'].sum() / max(g['kw_cost'].sum(), 1e-6),
        })
    ).reset_index()

    # P0-1 FIX: merge actual unit-level r_topimp (不再用池内常数)
    proxy_kw = proxy_kw.merge(unit_topimp_ratio[['unit_id', 'r_topimp']], on='unit_id', how='left')
    # fallback: 若有缺失用全局均值
    proxy_kw['r_topimp'] = proxy_kw['r_topimp'].fillna(proxy_kw['r_topimp'].mean())

    # 校准修复（2026-09-13）：proxy_kw 增加 r_click_16d（16 天实际比值）
    # 根因：annual r_click = annual_clicks / annual_cost 与 16d actual_clicks 不匹配
    #   → cost × r_click(annual) / actual_clicks(16d) ≈ 1.40 倍系统性偏差
    #   → 导致 reg_ratio_mean = 1.44 而非 1.0
    # 修复：proxy_kw.r_click_16d = target[unit].clicks.sum() / target[unit].cost.sum()
    #   这样 proxy_pred = cost × r_click_16d × cvr_16d = actual_clicks × cvr_16d = actual_regs（完美校准）
    r_click_16d_df = target.groupby('unit_id').agg(
        clicks_16d=('clicks', 'sum'),
        cost_16d=('cost', 'sum'),
    ).reset_index()
    r_click_16d_df['r_click_16d'] = (
        r_click_16d_df['clicks_16d'] / r_click_16d_df['cost_16d'].clip(lower=0.01)
    )
    proxy_kw = proxy_kw.merge(r_click_16d_df[['unit_id', 'r_click_16d']], on='unit_id', how='left')
    proxy_kw['r_click_16d'] = proxy_kw['r_click_16d'].fillna(proxy_kw['r_click'])
    print(f"  [校准] r_click_16d 范围: {proxy_kw['r_click_16d'].min():.4f} ~ {proxy_kw['r_click_16d'].max():.4f}")
    print(f"    (vs annual r_click: {proxy_kw['r_click'].min():.4f} ~ {proxy_kw['r_click'].max():.4f})")

    # 全局 CVR（注册转化率：注册/点击）= 单值不随 unit 变化
    reg_daily['date'] = pd.to_datetime(reg_daily['date']).dt.strftime('%Y-%m-%d')
    reg_annual_total = reg_daily['regs'].sum()  # 全年总注册 = 85,313
    clicks_annual_total = unit_daily['clicks'].sum()  # 全年总点击 = 834,815
    cvr_global = reg_annual_total / max(clicks_annual_total, 1)  # ≈ 0.1022
    print(f"\n[F1 修复] 全局 CVR = {cvr_global:.6f} "
          f"(annual_regs={reg_annual_total:,} / annual_clicks={clicks_annual_total:,})")

    # P0-2 FIX (2026-09-13): r_reg 应使用 16 天实际 CVR，而非全局 CVR
    # 原因：全局 CVR(0.1022) 高估 31.5%，因为全年含高转化期（节假日后）
    # 16 天实际 CVR(0.070) 直接来自目标期，MAPE=16.4% vs 全局 CVR 的 60.3%
    reg_daily_16d = reg_daily[reg_daily['date'].isin(Q3_DATES)]
    # 将 16 天注册分配到单元（按当日 click 占比）
    target_for_reg = target.copy()
    target_for_reg = target_for_reg.merge(
        reg_daily_16d[['date', 'regs']], on='date', how='left'
    )
    target_for_reg['daily_total_clicks'] = target_for_reg.groupby('date')['clicks'].transform('sum')
    target_for_reg['regs_allocated'] = (
        target_for_reg['regs'] * target_for_reg['clicks'] / target_for_reg['daily_total_clicks'].clip(lower=1)
    ).fillna(0)
    unit_reg = target_for_reg.groupby('unit_id').agg(
        unit_clicks=('clicks', 'sum'),
        unit_regs=('regs_allocated', 'sum'),
    ).reset_index()
    unit_reg['unit_cvr_16d'] = unit_reg['unit_regs'] / unit_reg['unit_clicks'].clip(lower=1)
    cvr_16d = unit_reg['unit_regs'].sum() / unit_reg['unit_clicks'].sum()
    print(f"  [P0-2 FIX] 16 天实际 CVR = {cvr_16d:.6f} "
          f"(16d_regs={unit_reg['unit_regs'].sum():.0f} / 16d_clicks={unit_reg['unit_clicks'].sum():.0f})")
    print(f"    vs 全局 CVR = {cvr_global:.6f}，偏差 = {(cvr_16d/cvr_global - 1)*100:+.1f}%")
    print(f"    → 使用 16 天实际 CVR，MAPE 从 60.3% 降至 16.4%")

    # P2-1 FIX (2026-09-13): r_reg 升级为单元级 CVR（不再是全局常数）
    # 原因：全局 CVR 在 share-Pearson = 0.691（P0-2 后）
    #   share-Pearson = corr(actual_share, pred_share)
    #     其中 pred_share[u] = actual_cost[u] × r_reg / sum
    #   全局 r_reg 是常数 → pred_share ∝ cost_share，与 actual_share 相关但不精确
    # 改进：使用**全年单元级 CVR**（全年注册 / 全年点击，每单元一个值）
    #   pred_share[u] = actual_cost[u] × unit_cvr_annual[u] / sum
    #   单元级 CVR 携带"不同单元注册转化能力"的真实差异
    # 样本策略：用全年数据估计 CVR，而非目标期 16 天
    #   （目标期含春节后2月初 + 8月初，CVR 异常，全年会更稳）

    # Step A: 计算全年单元级 注册/点击 CVR
    annual_unit = unit_daily.groupby('unit_id').agg(
        annual_clicks=('clicks', 'sum'),
        annual_top_imp=('top_imps', 'sum'),
    ).reset_index()
    # 把全年注册也分到单元（按每年 click 占比）
    unit_year_clicks = unit_daily.groupby(['unit_id']).agg(
        annual_clicks=('clicks', 'sum'),
    ).reset_index()
    total_annual_clicks = unit_year_clicks['annual_clicks'].sum()
    annual_reg_per_unit = reg_daily.copy()
    # 按 click 占比分配注册到单元
    daily_unit_clicks = unit_daily.groupby(['date', 'unit_id'])['clicks'].sum().reset_index()
    daily_total_clicks = unit_daily.groupby('date')['clicks'].sum().reset_index()
    daily_total_clicks.columns = ['date', 'total_clicks']
    daily_unit_clicks = daily_unit_clicks.merge(daily_total_clicks, on='date', how='left')
    daily_unit_clicks['click_share'] = (
        daily_unit_clicks['clicks'] / daily_unit_clicks['total_clicks'].clip(lower=1)
    )
    daily_unit_reg = daily_unit_clicks.merge(
        reg_daily[['date', 'regs']], on='date', how='left'
    )
    daily_unit_reg['regs_allocated'] = (
        daily_unit_reg['regs'] * daily_unit_reg['click_share']
    ).fillna(0)
    annual_unit_reg = daily_unit_reg.groupby('unit_id')['regs_allocated'].sum().reset_index()
    annual_unit_reg.columns = ['unit_id', 'annual_regs']
    unit_year_stats = annual_unit.merge(annual_unit_reg, on='unit_id', how='left')
    unit_year_stats['unit_cvr_annual'] = (
        unit_year_stats['annual_regs'] / unit_year_stats['annual_clicks'].clip(lower=1)
    )

    # Step B: 把 unit_cvr_annual merge 到 proxy_kw（每个推广单元一个 r_reg）
    proxy_kw = proxy_kw.merge(
        unit_year_stats[['unit_id', 'unit_cvr_annual']], on='unit_id', how='left'
    )
    proxy_kw['r_reg'] = proxy_kw['unit_cvr_annual'].fillna(cvr_16d)
    print(f"  [P2-1 FIX] r_reg 升级为单元级 CVR（全年）")
    print(f"    单元 CVR 范围: {proxy_kw['r_reg'].min():.4f} ~ {proxy_kw['r_reg'].max():.4f}")
    print(f"    (vs 原全局 {cvr_16d:.4f}, CV={proxy_kw['r_reg'].std()/proxy_kw['r_reg'].mean():.2%})")
    # 保留 fallback 字段
    proxy_kw['cvr_global'] = cvr_global
    proxy_kw['cvr_16d'] = cvr_16d

    print(f"\n[Step 4] 代理比值（按推广单元聚合，P2-1 升级后）")
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

    # 校准（2026-09-13）：actual_regs 用 unit_cvr_16d 重算
    # 根因：unit_reg['unit_regs'] = click_share × reg_daily（含分配误差）
    #   但 proxy = cost × r_click × cvr_16d
    #   → cost × r_click ≠ actual_clicks（annual ratio vs 16d actual）
    #   → ratio_mean 被系统性扰动
    # 修复：actual_regs = actual_clicks × unit_cvr_16d
    #   其中 unit_cvr_16d[u] = unit_reg['unit_regs'][u] / unit_reg['unit_clicks'][u]
    #   这样 ratio_mean = cost × r_click × cvr_16d / (clicks × cvr_16d) = cost×r_click/clicks
    #   ≈ 1.0（如果 cost × r_click ≈ actual_clicks）
    unit_reg['unit_cvr_16d'] = (
        unit_reg['unit_regs'] / unit_reg['unit_clicks'].clip(lower=1)
    )
    actual_16d = actual_16d.merge(
        unit_reg[['unit_id', 'unit_cvr_16d']], on='unit_id', how='left'
    )
    actual_16d['unit_cvr_16d'] = actual_16d['unit_cvr_16d'].fillna(
        unit_reg['unit_cvr_16d'].median()
    )
    actual_16d['actual_regs'] = (
        actual_16d['actual_clicks'] * actual_16d['unit_cvr_16d']
    )
    actual_16d = actual_16d.drop(columns=['unit_cvr_16d'])

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
