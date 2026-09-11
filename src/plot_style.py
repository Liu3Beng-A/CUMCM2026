"""统一绘图风格 (改-7 重写版)

设计原则
========
1. 一套主调色板 (COLORS) + 一套维度色映射 (DIM_COLORS)
   - 主调：6 种语义色 (primary/secondary/accent/success/danger/neutral)
   - 维度色：4 个一级维度每个固定一个颜色，全文所有图表统一
2. 标题统一前缀 "问题 1：" (与附件题面一致)
3. 统一字体：标题 13, 轴标签 11, 刻度 10
4. 统一网格：alpha=0.3, axis='both'
5. 统一图例：upper right, framealpha=0.9
6. 统一 figsize 单图 (10, 6), 1x2 (14, 6), 2x2 (14, 10)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 立即注册中文字体
from src.font_fix import register_chinese_font
CN_FONT = register_chinese_font()

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


# =====================================================
# 主调色板 (语义色，用于主题/状态)
# =====================================================
COLORS = {
    'primary':   '#2E86AB',  # 蓝 — 主色
    'secondary': '#A23B72',  # 紫 — 次色
    'accent':    '#F18F01',  # 橙 — 强调
    'success':   '#06A77D',  # 绿 — 正向/达标
    'danger':    '#D62246',  # 红 — 负向/异常
    'neutral':   '#6C757D',  # 灰 — 中性
}

# 论文风格调色板 (Coolors palette, 全图统一)
# 与 seaborn 'Set2' 区分，统一使用色环顺序: 蓝/橙/绿/红/紫/灰
PAPER_PALETTE = [
    '#2E86AB',  # 蓝
    '#F18F01',  # 橙
    '#06A77D',  # 绿
    '#D62246',  # 红
    '#A23B72',  # 紫
    '#6C757D',  # 灰
]


# =====================================================
# 维度色映射 — 4 个一级维度固定颜色，全文统一
# =====================================================
DIM_NAMES = ['设计质量与创意', '关键词管理与运用',
             '出价策略与预算', '投放策略与时间']

DIM_COLORS = {
    '设计质量与创意':   '#2E86AB',  # 蓝
    '关键词管理与运用': '#06A77D',  # 绿
    '出价策略与预算':   '#F18F01',  # 橙
    '投放策略与时间':   '#D62246',  # 红
}

# 方案色 (5 个方案固定颜色，全文统一)
PLAN_COLORS = {
    '500635396': '#2E86AB',  # 蓝
    '495403620': '#F18F01',  # 橙
    '525368335': '#06A77D',  # 绿
    '495817671': '#D62246',  # 红
    '63563817':  '#A23B72',  # 紫
}


# =====================================================
# 全局 matplotlib 设置
# =====================================================
def apply_style():
    """应用全局绘图风格"""
    sns.set_style('whitegrid')
    sns.set_palette(PAPER_PALETTE)

    # 单一全局 figsize 默认值 (10, 6) - 调用方在 plt.subplots 里覆盖即可
    plt.rcParams['figure.figsize'] = (10, 6)
    plt.rcParams['figure.dpi'] = 110
    plt.rcParams['savefig.dpi'] = 200
    plt.rcParams['savefig.bbox'] = 'tight'

    # 字体（中英文混排）
    matplotlib.rcParams['font.sans-serif'] = [CN_FONT, 'DejaVu Sans']
    matplotlib.rcParams['font.family'] = 'sans-serif'
    matplotlib.rcParams['axes.unicode_minus'] = False

    # 统一字号
    plt.rcParams['font.size'] = 10           # 基础字号
    plt.rcParams['axes.titlesize'] = 13      # 子图标题
    plt.rcParams['axes.labelsize'] = 11      # 轴标签
    plt.rcParams['xtick.labelsize'] = 10     # x 刻度
    plt.rcParams['ytick.labelsize'] = 10     # y 刻度
    plt.rcParams['legend.fontsize'] = 10     # 图例
    plt.rcParams['figure.titlesize'] = 14    # 总标题

    # 统一网格
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['grid.linestyle'] = '--'

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
        target = PAPER_FIG_DIR
        os.makedirs(target, exist_ok=True)
    else:
        from src.utils import FIGURES_DIR
        target = FIGURES_DIR
    path = os.path.join(target, f'{name}.png')
    fig.savefig(path, dpi=200, bbox_inches='tight')
    print(f'[fig] saved -> {path}', flush=True)
    return path


def q1_title(subtitle: str) -> str:
    """生成统一格式的图表标题：'问题 1：<subtitle>'

    Parameters
    ----------
    subtitle : str
        子标题文本（不含前缀）。

    Returns
    -------
    str
        "问题 1：<subtitle>" （注意：冒号前有半角空格，与题面一致）
    """
    return f'问题 1：{subtitle}'


def apply_grid(ax, axis='both', alpha=0.3):
    """统一网格设置（关闭时 alpha=0）"""
    if axis == 'off':
        ax.grid(False)
    else:
        ax.grid(True, alpha=alpha, axis=axis, linestyle='--')


def apply_legend(ax, loc='upper right', framealpha=0.9):
    """统一图例"""
    ax.legend(loc=loc, framealpha=framealpha, edgecolor='gray',
              fancybox=False, frameon=True)


def plan_palette(n: int = 5):
    """返回方案色列表（按排序后的方案ID顺序）"""
    sorted_ids = sorted(PLAN_COLORS.keys(), key=lambda x: float(x))
    return [PLAN_COLORS[pid] for pid in sorted_ids[:n]]


# =====================================================
# 演示
# =====================================================
if __name__ == '__main__':
    plt = apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 左图：4 维度色映射
    ax = axes[0]
    vals = [69, 67, 86, 36]
    colors = [DIM_COLORS[d] for d in DIM_NAMES]
    ax.barh(DIM_NAMES, vals, color=colors, edgecolor='black', linewidth=0.6)
    ax.set_title(q1_title('维度色映射示例'))
    ax.set_xlim(0, 100)
    apply_grid(ax, axis='x')

    # 右图：方案色映射
    ax = axes[1]
    pids = sorted(PLAN_COLORS.keys())
    ax.bar(range(len(pids)), [1]*len(pids),
           color=[PLAN_COLORS[p] for p in pids],
           edgecolor='black', linewidth=0.6)
    ax.set_xticks(range(len(pids)))
    ax.set_xticklabels(pids, rotation=30)
    ax.set_title(q1_title('方案色映射示例'))
    ax.set_yticks([])
    apply_grid(ax, axis='y')

    fig.tight_layout()
    save_fig(fig, 'test_style')
