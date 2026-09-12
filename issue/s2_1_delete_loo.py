"""S2-1: 删除 weight_robustness_check 函数及上方注释块"""
import sys

src = r'D:/CUMCM2026Problems/src/q1_generalization.py'
with open(src, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f'原文件总行数: {len(lines)}')

# 0-indexed: 删除 [254:411]，对应 1-indexed 行 255-411
# 包含：策略 B 注释块（255-257）+ 空行 + 整个 weight_robustness_check() 函数体
del lines[254:411]

with open(src, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f'删除后总行数: {len(lines)}')
print(f'删除行数: {411 - 254}')