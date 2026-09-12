"""Update issue/q2_implementation_plan.md paths"""
with open('D:/CUMCM2026Problems/issue/q2_implementation_plan.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Update main output paths
content = content.replace(
    "| Q2 主交付物 | `data/raw/attachments/result2.xlsx` | 题面要求 | **2227 行**（= 2227 关键词 one-hot） |",
    "| Q2 主交付物 | `results/excel/result2.xlsx` | 题面要求 + 统一汇总目录 | **2227 行**（= 2227 关键词 one-hot） |"
)
content = content.replace(
    "- `export_result2(df_one_hot) → path`：写 `data/raw/attachments/result2.xlsx`",
    "- `export_result2(df_one_hot) → path`：写 `results/excel/result2.xlsx`"
)

with open('D:/CUMCM2026Problems/issue/q2_implementation_plan.md', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
import re
remaining = re.findall(r'data/raw/attachments/result[234]\.xlsx', content)
print(f'仍引用 data/raw/attachments/result*.xlsx 的位置数: {len(remaining)}')
for i, m in enumerate(re.finditer(r'data/raw/attachments/result[234]\.xlsx', content)):
    pos = m.start()
    line_no = content[:pos].count('\n') + 1
    line_text = content.split('\n')[line_no-1].strip()
    print(f'  L{line_no}: {line_text[:100]}')
