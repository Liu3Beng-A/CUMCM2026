# results/excel/

本目录存放问题二/三/四的 Excel 主交付物。

| 文件 | 来源 | 状态 |
|------|------|------|
| `result2.xlsx` | Q2 关键词 5 类分类（2227 行 × 8 列）| ✅ 已完成（2026-09-12） |
| `result3.xlsx` | Q3 每日投放策略 + 4 指标预测 | ⏸ 待重做 |
| `result4.xlsx` | Q4 不确定性下最优策略 + 6 期望值 | ⏸ 待重做 |

## 路径约定（2026-09-12 16:30 起）

- **统一汇总至 `results/excel/`**，不再直接写到 `data/raw/attachments/`（保持原始附件区只放输入数据）
- **模板**仍在 `data/raw/attachments/附件2/`（题面提供，不可修改）
- **路径常量**：`src/utils.py` 定义 `EXCEL_DIR = os.path.join(RESULTS_DIR, 'excel')`

## 代码引用

```python
from src.utils import EXCEL_DIR
RESULT_OUT = os.path.join(EXCEL_DIR, 'result{2,3,4}.xlsx')
```
