"""统一绘图风格"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 立即注册中文字体
from src.font_fix import register_chinese_font
CN_FONT = register_chinese_font()

import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

from src.utils import FIGURES_DIR, ensure_dir


def apply_style():
    """应用全局绘图风格 - 中文在 sns 之后再次强制"""
    sns.set_style('whitegrid')
    sns.set_palette('Set2')
    plt.rcParams['figure.figsize'] = (10, 6)
    plt.rcParams['figure.dpi'] = 110
    plt.rcParams['savefig.dpi'] = 150
    plt.rcParams['savefig.bbox'] = 'tight'
    # 在 sns 之后再次强制设置
    matplotlib.rcParams['font.sans-serif'] = [CN_FONT, 'DejaVu Sans']
    matplotlib.rcParams['font.family'] = 'sans-serif'
    matplotlib.rcParams['axes.unicode_minus'] = False
    return plt


def force_cn(ax_or_fig=None):
    """运行中再次强制刷新（用于动态绘图）"""
    matplotlib.rcParams['font.sans-serif'] = [CN_FONT, 'DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False


def save_fig(fig, name, subdir='figures'):
    matplotlib.rcParams['font.sans-serif'] = [CN_FONT, 'DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False

    if subdir == 'paper':
        from src.utils import PAPER_FIG_DIR
        target = ensure_dir(PAPER_FIG_DIR)
    else:
        target = FIGURES_DIR
    path = os.path.join(target, f'{name}.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    print(f'[fig] saved -> {path}', flush=True)
    return path


COLORS = {
    'primary':   '#2E86AB',
    'secondary': '#A23B72',
    'accent':    '#F18F01',
    'success':   '#06A77D',
    'danger':    '#D62246',
    'neutral':   '#6C757D',
}


if __name__ == '__main__':
    plt = apply_style()
    fig, ax = plt.subplots()
    ax.bar(['甲', '乙', '丙', '丁'], [10, 23, 15, 28],
           color=[COLORS['primary'], COLORS['secondary'], COLORS['accent'], COLORS['success']])
    ax.set_title('问题1：测试中文图表')
    ax.set_xlabel('类别')
    ax.set_ylabel('数值')
    save_fig(fig, 'test_style')
