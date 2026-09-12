"""Update Q3Q4_Method_Architecture.md paths"""
with open('D:/CUMCM2026Problems/Q3Q4_Method_Architecture.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Update all references to data/raw/attachments/result*.xlsx to results/excel/result*.xlsx
import re
matches = re.findall(r'data/raw/attachments/result[234]\.xlsx', content)
print(f'Found {len(matches)} references to update')

content = content.replace('data/raw/attachments/result2.xlsx', 'results/excel/result2.xlsx')
content = content.replace('data/raw/attachments/result3.xlsx', 'results/excel/result3.xlsx')
content = content.replace('data/raw/attachments/result4.xlsx', 'results/excel/result4.xlsx')

with open('D:/CUMCM2026Problems/Q3Q4_Method_Architecture.md', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
remaining = re.findall(r'data/raw/attachments/result[234]\.xlsx', content)
print(f'Remaining: {len(remaining)} references')
