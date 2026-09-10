"""测试中文 + seaborn设置"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plot_style import apply_style, save_fig, COLORS
import matplotlib.pyplot as plt
import numpy as np

apply_style()

fig, ax = plt.subplots()
xs = np.arange(7)
ax.bar(xs, [10, 23, 15, 30, 22, 25, 28], color=COLORS['primary'])
ax.set_xticks(xs)
ax.set_xticklabels(['周一', '周二', '周三', '周四', '周五', '周六', '周日'])
ax.set_title('问题1：周内消费分布')
ax.set_xlabel('星期')
ax.set_ylabel('消费额(元)')
ax.grid(True, alpha=0.3)
save_fig(fig, 'test_cn')
print('OK')
