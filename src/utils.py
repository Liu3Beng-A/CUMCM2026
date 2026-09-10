"""通用工具：路径、字体、绘图风格"""
import os
import sys
import io

# UTF-8 stdout (Windows GBK 兼容)
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 项目根目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 路径常量
DATA_DIR = os.path.join(ROOT, 'data')
RAW_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')
RESULTS_DIR = os.path.join(ROOT, 'results')
FIGURES_DIR = os.path.join(RESULTS_DIR, 'figures')
TABLES_DIR = os.path.join(RESULTS_DIR, 'tables')
EXCEL_DIR = os.path.join(RESULTS_DIR, 'excel')
PAPER_FIG_DIR = os.path.join(ROOT, 'paper', 'figures')

# 中文字体设置（matplotlib）
def setup_matplotlib():
    """配置中文字体"""
    import matplotlib
    matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False  # 解决负号显示
    return matplotlib

def ensure_dir(path):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)
    return path

def find_attachment_dir():
    """定位附件根目录（兼容中文文件名）"""
    import glob
    candidates = glob.glob(os.path.join(ROOT, '*附件*'))
    for c in candidates:
        if os.path.isdir(c):
            return c
    raise FileNotFoundError('找不到附件目录')


if __name__ == '__main__':
    print(f'ROOT: {ROOT}')
    print(f'RAW_DIR: {RAW_DIR}')
    print(f'EXCEL_DIR: {EXCEL_DIR}')
