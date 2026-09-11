"""问题3：基于关键词分类的最优投放策略

任务：
1. 在每个推广单元中合理选择关键词
2. 在方案/单元/关键词三个层面分配预算
3. 输出2025年2月1-8日和8月1-8日的每日最优策略
4. 约束：低成本、高效益、预算不超额
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def build_optimization_model(dfc, dfr, dfk_classified):
    """构造优化模型"""
    pass


def solve_two_periods(model):
    """求解2月和8月两个周期"""
    pass


def save_result3(solution):
    """保存到 result3.xlsx"""
    pass


def main():
    print('[Q3] 待实现')


if __name__ == '__main__':
    main()
