"""把项目根目录加到 sys.path，确保 src.* 可导入"""
import sys, os

# 两次 dirname：src/__init__.py -> src -> 项目根
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(_THIS_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# UTF-8 stdout
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass
