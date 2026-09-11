"""问题2：关键词五分类
- 黄金词：低成本、高效益
- 重点词：高成本、高效益
- 潜力词：低成本、低效益
- 问题词：高成本、低效益
- 无效词：无成本、无效益

成本：CPC（点击单价）或 总消费额
效益：可参考注册转化、浏览量、或综合评分
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np


def classify_keywords(dfk):
    """分类核心逻辑"""
    pass


def save_result2(df_classified):
    """保存到 result2.xlsx"""
    pass


def main():
    print('[Q2] 待实现')
    # dfc, dfr, dfk = load_raw_data()
    # df_classified = classify_keywords(dfk)
    # save_result2(df_classified)


if __name__ == '__main__':
    main()
