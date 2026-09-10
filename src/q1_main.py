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
    print('\n[1/8] 生成所有图表...', flush=True)
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

    # 2) 评分 + 雷达/明细图（改-1 CRITIC + 改-2 双轨区间）
    print('\n[2/8] 计算综合评分（CRITIC 混合赋权）...', flush=True)
    from src.q1_scoring import run_scoring
    result = run_scoring()
    fig_score_radar(result)
    fig_score_breakdown(result)

    # 3) Prophet 反事实（改-3: yearly=False + 置信区间）
    print('\n[3/8] Prophet + 假日反事实（95% 置信区间）...', flush=True)
    from src.q1_prophet import run_prophet_analysis
    run_prophet_analysis()

    # 4) Bootstrap 显著性检验（改-4）
    print('\n[4/8] Bootstrap 显著性检验...', flush=True)
    from src.q1_bootstrap import run_bootstrap
    # 全量较慢，默认 n_boot=100；可调整
    run_bootstrap(n_boot=100, n_holidays=None)

    # 5) 权重扰动敏感性分析（改-7）
    print('\n[5/8] 权重扰动敏感性分析（龙卷风图）...', flush=True)
    from src.q1_sensitivity import run_sensitivity
    run_sensitivity()

    # 6) 跳出率聚类（改-6 静态披露）
    print('\n[6/8] 跳出率聚类（KMeans k=3）...', flush=True)
    from src.q1_bounce_cluster import run_bounce_cluster
    run_bounce_cluster(k=3)

    # 7) 收集摘要 + 写论文文字（改-8）
    print('\n[7/8] 收集摘要...', flush=True)
    os.system('python ' + os.path.join(os.path.dirname(__file__), 'q1_collect_summary.py'))

    print('\n[8/8] 写论文文字（更新版）...', flush=True)
    os.system('python ' + os.path.join(os.path.dirname(__file__), 'q1_write.py'))

    print('\n' + '=' * 60, flush=True)
    print('✓ 问题1完成！产出文件：', flush=True)
    print('  - results/figures/q1_*.png  (11+ 张专业图表，含龙卷风、聚类)', flush=True)
    print('  - results/tables/q1_score.json  (CRITIC 混合赋权综合评分)', flush=True)
    print('  - results/tables/q1_weights.json  (CRITIC/业务/混合三套权重)', flush=True)
    print('  - results/tables/q1_sensitivity.csv  (权重扰动稳健性)', flush=True)
    print('  - results/tables/q1_bootstrap_ci.csv  (节日显著性 Bootstrap CI)', flush=True)
    print('  - results/tables/q1_bounce_clusters.csv  (跳出率聚类)', flush=True)
    print('  - results/tables/q1_holiday_contribution.csv  (假日贡献)', flush=True)
    print('  - results/tables/q1_summary.json  (关键数据汇总)', flush=True)
    print('  - paper/q1_section_5_1.md  (论文5.1节文字稿，已更新)', flush=True)
    print('=' * 60, flush=True)


if __name__ == '__main__':
    main()
