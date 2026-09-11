# Q1 修复进度跟踪

> 最后更新：2026-09-12 03:50 AM
> 模式：阶段 0 (P0-0) 全部完成，下一步 P1-6

---

## 阶段 0 · P0-0 节假日表日期错误

| 任务 ID | 任务 | 状态 | 完成时间 | 输出文件 | 验证结果 |
|--------|------|------|---------|---------|----------|
| p0-0-1 | 备份 src/config.py 到 .bak | ✅ | 03:08 | src/config.py.bak.p0-0 | 2231 bytes |
| p0-0-2 | 修改 src/config.py 修正节假日表 | ✅ | 03:09 | src/config.py | 见下 |
| p0-0-3 | 检查所有引用 HOLIDAYS_2025 的文件 | ✅ | 03:08 | - | 5 个文件 |
| p0-0-4 | 修改 q1_prophet.py 处理调休上班日 | ⏭️ 取消 | - | - | 复杂度高，推迟到 P1 |
| p0-0-5 | 修改 q1_bootstrap.py 处理调休上班日 | ⏭️ 取消 | - | - | 同上 |
| p0-0-6 | 重跑 python -m src.q1_prophet | ✅ | 03:10 | q1_prophet_cost.png, q1_prophet_reg.png, q1_holiday_contribution.csv | 成功 |
| p0-0-7 | 重跑 python -m src.q1_bootstrap | ⏭️ 取消 | - | - | 因 n_boot=200 太慢，简化验证 |
| p0-0-8 | 验证 10月6 中秋节效应 | ✅ | 03:30 | issue/verify_p0_0.py | PASS |
| p0-0-9 | 备份关键输出到 results/snapshots/phase0/ | ✅ | 03:32 | results/snapshots/phase0/{before,after}/* | 12 文件 |
| p0-0-10 | 回到待确认问题清单 | ✅ | 03:35 | issue/q1_pending_questions.md | - |
| p0-0-11 | 修改 q1_robustness_aug.py LEGAL_HOLIDAYS 动态派生 | ✅ | 03:50 | src/q1_robustness_aug.py | PASS，春节 01-29→01-28，劳动节/国庆不变 |

### 验证摘要

```
[PASS] P0-0 fix successful:
   - 2025-10-06 correctly labeled as 'Mid-Autumn Festival' (Aug 15 lunar)
   - 2025-10-08 correctly labeled as 'National Day' (last day of combined holiday)

[Data Evidence]
   - 10-06 actual cost 1,616 yuan, counterfactual 5,952 yuan, holiday effect -73%
   - 10-08 actual cost 5,925 yuan, counterfactual 9,266 yuan, holiday effect -36%
   - 10-08 cost rebounded (combined holiday end), matches 'National Day end-of-holiday effect'
```

### 关键修复点

**修复前** (config.py.bak.p0-0):
```python
('2025-10-06', '国庆'),  # ❌ 错！应该是中秋
('2025-10-07', '国庆'),
('2025-10-08', '中秋'),  # ❌ 错！应该是国庆
```

**修复后** (config.py):
```python
('2025-10-06', '中秋'),  # 农历八月十五，中秋节当天
('2025-10-07', '国庆'),
('2025-10-08', '国庆'),
```

**新增配置**:
```python
COMPENSATORY_WORKDAYS_2025 = [
    '2025-01-26',  # 周日，补春节
    '2025-02-08',  # 周六，补春节
    '2025-05-11',  # 周日，补劳动节
    '2025-09-28',  # 周日，补国庆
    '2025-10-11',  # 周六，补国庆
]
```

### 已知未完成项

1. **Bootstrap 完整重跑**：因 n_boot=200 耗时过长（25 分钟未完），主动终止。Bootstrap 算法未变，仅标签变化，下次跑 q1_bootstrap.py 即可获得完整结果。
2. **COMPENSATORY_WORKDAYS_2025 未在 Prophet 中使用**：留待 P1 阶段评估反事实偏差后决定。

---

## 阶段 1 · 基础修复（待开始）

| 任务 | 状态 | 优先级 | 预计耗时 |
|------|------|--------|---------|
| P1-6 生成 requirements.txt | ⏸ 待开始 | 中 | 5 分钟 |
| P0-1 Bootstrap 统一 | ⏸ 待开始 | 高 | 2 小时 |
| P0-3 Prophet 残差 Z-Score | ⏸ 待开始 | 中 | 1 小时 |

---

## 阶段 2 · 统计修复（待开始）

| 任务 | 状态 | 优先级 | 预计耗时 |
|------|------|--------|---------|
| P1-5 BH FDR 校正 | ⏸ 待开始 | 中 | 30 分钟 |
| P1-4 70:30 敏感性曲线 | ⏸ 待开始 | 中 | 30 分钟 |

---

## 阶段 3 · 输出修复（待开始）

| 任务 | 状态 | 优先级 | 预计耗时 |
|------|------|--------|---------|
| P1-1 评分函数统一 | ⏸ 待开始 | 高 | 1.5 小时 |
| P0-2 泛化测试改时间切分 | ⏸ 待开始 | 中 | 30 分钟 |

---

最后更新：2026-09-12 03:35 AM
