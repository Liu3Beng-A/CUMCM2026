"""诊断字体问题"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 1. 注册字体
from src.font_fix import register_chinese_font
font_name = register_chinese_font()
print(f'[1] font: {font_name}', flush=True)

# 2. 检查可用字体列表
all_fonts = sorted(set(f.name for f in font_manager.fontManager.ttflist))
print(f'[2] 中文字体列表: {[f for f in all_fonts if "Hei" in f or "Sim" in f or "YaHei" in f or "Song" in f]}', flush=True)

# 3. 现在再画
print(f'[3] rcParams[font.sans-serif]: {matplotlib.rcParams["font.sans-serif"]}', flush=True)

matplotlib.rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

print(f'[4] after update: {matplotlib.rcParams["font.sans-serif"]}', flush=True)

fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(['甲', '乙', '丙', '丁'], [10, 23, 15, 28])
ax.set_title('中文显示测试')
ax.set_xlabel('类别')
fig.savefig('d:/CUMCM2026Problems/results/figures/font_test3.png', dpi=150)
print('[5] saved', flush=True)
