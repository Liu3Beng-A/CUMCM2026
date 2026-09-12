# -*- coding: utf-8 -*-
"""Probe attachment templates & data sheets (verification only)."""
import pandas as pd
import os

ATT2 = r"data\raw\attachments\附件2"
ATT1 = r"data\raw\attachments\附件1.xlsx"

print("=" * 70)
print("【1】 附件 2 模板（Q2/Q3/Q4 输出格式 · 唯一权威）")
print("=" * 70)
for name in ["result2.xlsx", "result3.xlsx", "result4.xlsx"]:
    path = os.path.join(ATT2, name)
    df = pd.read_excel(path)
    print(f"\n  {name}  shape={df.shape}")
    print(f"  Columns: {list(df.columns)}")
    print(f"  Rows: 0 (空模板，仅表头)")
    print(f"  Cols count: {len(df.columns)}")

print("\n" + "=" * 70)
print("【2】 附件 1 数据源（Q1/Q2/Q3/Q4 输入）")
print("=" * 70)
for s in ["Sheet1", "Sheet2", "Sheet3"]:
    df = pd.read_excel(ATT1, sheet_name=s)
    print(f"\n  {s}  shape={df.shape}")
    print(f"  Columns (raw): {list(df.columns)}")
    print(f"  Columns (stripped): {list(df.columns.str.strip())}")

print("\n" + "=" * 70)
print("【3】 关键交叉验证")
print("=" * 70)
s1 = pd.read_excel(ATT1, sheet_name="Sheet1")
s3 = pd.read_excel(ATT1, sheet_name="Sheet3")
print(f"  Sheet1 消费额 全年合计 = {s1['消费额'].sum():.2f}")
print(f"  Sheet3 消费额 全年合计 = {s3['消费额'].sum():.2f}")
print(f"  差异 = {abs(s1['消费额'].sum() - s3['消费额'].sum()) / s1['消费额'].sum() * 100:.4f}%")

# 验证 Q3 时间窗预算
s1["日期"] = pd.to_datetime(s1["日期"])
mask_q3 = (s1["日期"] >= "2025-02-01") & (s1["日期"] <= "2025-02-08") | \
          (s1["日期"] >= "2025-08-01") & (s1["日期"] <= "2025-08-08")
q3_total = s1.loc[mask_q3, "消费额"].sum()
feb = s1.loc[(s1["日期"] >= "2025-02-01") & (s1["日期"] <= "2025-02-08"), "消费额"].sum()
aug = s1.loc[(s1["日期"] >= "2025-08-01") & (s1["日期"] <= "2025-08-08"), "消费额"].sum()
print(f"\n  Q3 02-01~08 消费 = {feb:.2f}")
print(f"  Q3 08-01~08 消费 = {aug:.2f}")
print(f"  Q3 16 天合计 = {q3_total:.2f}")

# Q4 同期预算
mask_q4 = (s1["日期"] >= "2025-09-11") & (s1["日期"] <= "2025-09-17")
q4_total = s1.loc[mask_q4, "消费额"].sum()
print(f"\n  Q4 同期 2025-09-11~17 消费 = {q4_total:.2f}")

# Sheet3 入选项
gold = (s3["消费额"] > 8.06).sum()  # 占位
print(f"\n  Sheet3 总词数 = {len(s3)}")
print(f"  Sheet3 消费=0 词数 = {(s3['消费额'] == 0).sum()}")
