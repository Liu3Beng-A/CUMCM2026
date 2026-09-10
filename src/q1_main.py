"""Q1 主入口 - 一键完成所有Q1任务

运行后产生：
- 全部图表 (results/figures/q1_*.png)
- 综合评分 (results/tables/q1_score.json / .csv)
- 节假日贡献 (results/tables/q1_holiday_contribution.csv)
- 全文摘要 (results/tables/q1_summary.json)
- 论文5.1节文字稿 (paper/q1_section_5_1.md)
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print('=' * 60, flush=True)
    print('问题1：投放策略合理性分析  [一键运行]', flush=True)
    print('=' * 60, flush=True)

    # 1) 图表
    print('\n[1/4] 生成所有图表...', flush=True)
    from src.q1_plots import (
        fig_design_quality, fig_keyword_management,
        fig_bid_strategy, fig_time_pattern,
        fig_score_radar, fig_score_breakdown,
    )
    from src.q1_data_prep import build_q1_data
    data = build_q1_data()

    fig_design_quality(data)
    fig_keyword_management(data)
    fig_bid_strategy(data)
    fig_time_pattern(data)

    # 2) 评分 + 雷达/明细图
    print('\n[2/4] 计算综合评分...', flush=True)
    from src.q1_scoring import run_scoring
    result = run_scoring()
    fig_score_radar(result)
    fig_score_breakdown(result)

    # 3) Prophet 反事实
    print('\n[3/4] Prophet + 假日反事实...', flush=True)
    from src.q1_prophet import run_prophet_analysis
    run_prophet_analysis()

    # 4) 收集摘要 + 写论文文字
    print('\n[4/4] 写论文文字...', flush=True)
    os.system('python ' + os.path.join(os.path.dirname(__file__), 'q1_collect_summary.py'))
    os.system('python ' + os.path.join(os.path.dirname(__file__), 'q1_write.py'))

    print('\n' + '=' * 60, flush=True)
    print('✓ 问题1完成！产出文件：', flush=True)
    print('  - results/figures/q1_*.png  (11张专业图表)', flush=True)
    print('  - results/tables/q1_score.json  (综合评分)', flush=True)
    print('  - results/tables/q1_score_breakdown.csv  (评分明细)', flush=True)
    print('  - results/tables/q1_holiday_contribution.csv  (假日贡献)', flush=True)
    print('  - results/tables/q1_summary.json  (关键数据汇总)', flush=True)
    print('  - paper/q1_section_5_1.md  (论文5.1节文字稿)', flush=True)
    print('=' * 60, flush=True)


if __name__ == '__main__':
    main()
