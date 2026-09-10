"""强制注册中文字体"""
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager
import os
import sys

_CHINESE_FONT_NAME = None


def register_chinese_font():
    """找到系统中文字体文件，强制注册并设为默认"""
    global _CHINESE_FONT_NAME
    if _CHINESE_FONT_NAME is not None:
        return _CHINESE_FONT_NAME

    # 常见 Windows 中文字体路径
    candidates_paths = [
        'C:/Windows/Fonts/simhei.ttf',
        'C:/Windows/Fonts/SIMHEI.TTF',
        'C:/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/MSYH.TTC',
        'C:/Windows/Fonts/msyh.ttf',
        'C:/Windows/Fonts/simkai.ttf',
        'C:/Windows/Fonts/simsun.ttc',
    ]

    chosen = None
    for p in candidates_paths:
        if os.path.exists(p):
            chosen = p
            break

    if chosen is not None:
        font_manager.fontManager.addfont(chosen)
        prop = font_manager.FontProperties(fname=chosen)
        font_name = prop.get_name()
        _CHINESE_FONT_NAME = font_name
        matplotlib.rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans']
        matplotlib.rcParams['font.family'] = 'sans-serif'
        matplotlib.rcParams['axes.unicode_minus'] = False
    else:
        _CHINESE_FONT_NAME = 'DejaVu Sans'

    return _CHINESE_FONT_NAME


def setup_chinese_font():
    """公开函数，供其他模块调用"""
    return register_chinese_font()


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    name = register_chinese_font()
    print(f'[font] using: {name}', flush=True)
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 2])
    ax.set_title('中文显示测试')
    fig.savefig('d:/CUMCM2026Problems/results/figures/font_test2.png', dpi=150)
    print('saved', flush=True)
