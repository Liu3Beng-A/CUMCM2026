"""Q1 跳出率聚类 + 静态披露（改-6）

目的：
- 跳出率 88% 的"异常"可能不是 bug 而是数据特征
- 用 KMeans 聚类把关键词按 (消费, 跳出率) 聚成 3-5 类
- 静态披露：每类的关键词数、消费占比、跳出率分布

方法：
1. 对有消费关键词 → log(消费额) + 跳出率 做 KMeans
2. 选 K=3（低跳出高价值 / 高跳出高价 / 高跳出低价值）
3. 输出聚类结果 + 业务解读

输出：
- q1_bounce_clusters.csv：每关键词聚类标签
- q1_bounce_cluster_summary.csv：聚类汇总
- q1_bounce_clusters.png：聚类散点图
- 论文段落：聚类说明文字

为什么不"修"数据：
- 跳出率 88% 在 SEM 行业（医疗、教育）属于正常水平
- 跳出率作为"质量信号"的指标本身没问题，只是阈值定得太死
- 静态披露是最诚实、最有解释力的做法
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.q1_data_prep import build_q1_data
from src.utils import FIGURES_DIR, TABLES_DIR, ensure_dir
from src.plot_style import apply_style, save_fig, COLORS


def cluster_keywords_by_bounce(data, k=3, random_state=42):
    """对有消费关键词按 (log消费, 跳出率) 聚类"""
    dfk = data['keyword_total'].copy()
    # 仅保留有消费 + 跳出率非空的
    dfk = dfk[(dfk['有消费']) & (dfk['跳出率'].notna()) & (dfk['消费额'] > 0)]
    if len(dfk) == 0:
        print('[bounce] 无有效关键词', flush=True)
        return None

    # 准备特征
    X = np.column_stack([
        np.log1p(dfk['消费额'].values),
        dfk['跳出率'].values,
    ])
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # KMeans
    km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    labels = km.fit_predict(X_scaled)
    dfk['cluster'] = labels

    # 聚类中心反归一化
    centers = scaler.inverse_transform(km.cluster_centers_)
    dfk['cluster_log_cost'] = centers[labels, 0]
    dfk['cluster_bounce'] = centers[labels, 1]

    return dfk


def summarize_clusters(dfk):
    """聚类汇总"""
    summary = dfk.groupby('cluster').agg(
        关键词数=('关键词', 'count'),
        总消费额=('消费额', 'sum'),
        平均跳出率=('跳出率', 'mean'),
        平均消费=('消费额', 'mean'),
        平均CPC=('CPC', 'mean'),
        平均CTR=('CTR', 'mean'),
        平均访问时长秒=('平均访问时长_秒', 'mean'),
        总注册数=('新注册数', 'sum') if '新注册数' in dfk.columns else ('消费额', lambda x: 0),
    ).reset_index()
    summary['消费占比(%)'] = summary['总消费额'] / summary['总消费额'].sum() * 100
    return summary.sort_values('平均跳出率')


def interpret_clusters(summary):
    """给每类打业务标签"""
    # 按跳出率排序：第一类（最低跳出）、中间、最后
    sorted_idx = summary.sort_values('平均跳出率')['cluster'].values
    labels = {
        sorted_idx[0]: '低跳出-优质词',
        sorted_idx[1]: '中跳出-正常词' if len(sorted_idx) > 2 else '中跳出',
        sorted_idx[-1]: '高跳出-待优化词',
    }
    if len(sorted_idx) >= 4:
        labels[sorted_idx[-2]] = '中高跳出'
    summary['业务标签'] = summary['cluster'].map(labels)
    return summary


def plot_clusters(dfk, summary, k=3):
    """聚类散点图"""
    plt = apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # (a) 散点：log消费 × 跳出率，按聚类着色
    ax = axes[0]
    colors = [COLORS['success'], COLORS['accent'], COLORS['danger'],
              COLORS['secondary'], COLORS['primary']]
    for i in range(k):
        sub = dfk[dfk['cluster'] == i]
        ax.scatter(sub['消费额'], sub['跳出率'],
                   c=colors[i % len(colors)], alpha=0.4, s=15, label=f'聚类{i}')
    ax.set_xscale('log')
    ax.set_xlabel('消费额（元，对数轴）', fontsize=11)
    ax.set_ylabel('跳出率', fontsize=11)
    ax.set_title('(a) 关键词聚类散点图（按消费额+跳出率）', fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # (b) 聚类中心柱状图：跳出率 + 消费占比双轴
    ax = axes[1]
    x = np.arange(len(summary))
    width = 0.4
    ax.bar(x - width/2, summary['平均跳出率'], width,
           color=COLORS['secondary'], label='平均跳出率')
    ax.set_ylabel('平均跳出率', color=COLORS['secondary'], fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(summary['业务标签'], fontsize=10, rotation=15)
    ax.tick_params(axis='y', labelcolor=COLORS['secondary'])
    ax.set_ylim(0, 1)

    ax2 = ax.twinx()
    ax2.bar(x + width/2, summary['消费占比(%)'], width,
            color=COLORS['primary'], label='消费占比(%)')
    ax2.set_ylabel('消费占比 (%)', color=COLORS['primary'], fontsize=11)
    ax2.tick_params(axis='y', labelcolor=COLORS['primary'])

    ax.set_title('(b) 各聚类跳出率 vs 消费占比', fontsize=12)
    ax.grid(True, alpha=0.3, axis='y')

    fig.suptitle('问题 1：跳出率聚类分析（KMeans, k={}）'.format(k),
                 fontsize=13, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, 'q1_bounce_clusters', subdir='results')
    plt.close(fig)


def plot_tsne_clusters(dfk, k=3, perplexity=30, random_state=42):
    """TSNE 降维二维可视化聚类结果

    将多维特征（消费额对数 + 跳出率 + CPC + CTR）通过 TSNE 降到 2D，
    按聚类标签着色，便于直观看出"高维不可分 vs 低维可分"的差异。

    Parameters
    ----------
    dfk : pd.DataFrame
        包含 cluster 列的关键词数据
    k : int
        聚类数
    perplexity : float
        TSNE 困惑度（默认 30，适合中等规模数据）
    random_state : int
        随机种子（保证可复现）
    """
    from sklearn.manifold import TSNE

    # 准备 4 维特征
    features = np.column_stack([
        np.log1p(dfk['消费额'].fillna(0).values),
        dfk['跳出率'].fillna(0).values,
        dfk['CPC'].fillna(0).values,
        dfk['CTR'].fillna(0).values,
    ])

    # 标准化
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    print(f'[tsne] 输入特征维度: {features_scaled.shape}, perplexity={perplexity}', flush=True)

    # TSNE 降维
    tsne = TSNE(n_components=2, perplexity=perplexity,
                random_state=random_state, max_iter=1000)
    embedding = tsne.fit_transform(features_scaled)
    print(f'[tsne] 输出嵌入维度: {embedding.shape}', flush=True)

    # 画图
    plt = apply_style()
    fig, ax = plt.subplots(figsize=(11, 8))

    colors = [COLORS['success'], COLORS['accent'], COLORS['danger'],
              COLORS['secondary'], COLORS['primary']]
    labels_map = {
        0: '低跳出-优质词',
        1: '中跳出-正常词',
        2: '高跳出-待优化词',
    }

    for i in range(k):
        mask = dfk['cluster'].values == i
        if mask.sum() == 0:
            continue
        ax.scatter(embedding[mask, 0], embedding[mask, 1],
                   c=colors[i % len(colors)], alpha=0.5, s=18,
                   label=f'{labels_map.get(i, f"聚类{i}")} (n={mask.sum()})',
                   edgecolors='black', linewidths=0.2)

    ax.set_xlabel('TSNE-1', fontsize=11)
    ax.set_ylabel('TSNE-2', fontsize=11)
    ax.set_title(f'问题 1：关键词聚类 TSNE 降维可视化（k={k}, perplexity={perplexity}）',
                 fontsize=13, fontweight='bold')
    ax.legend(loc='best', fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.3)

    # 在右下角加方法说明
    method_text = (
        '方法说明：\n'
        f'· 4 维特征 = log(消费+1) + 跳出率 + CPC + CTR\n'
        f'· StandardScaler 标准化\n'
        f'· TSNE (perplexity={perplexity}, max_iter=1000)\n'
        f'· 随机种子 = {random_state}（保证可复现）'
    )
    ax.text(0.98, 0.02, method_text,
            transform=ax.transAxes, fontsize=8.5,
            verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFFFE0',
                      edgecolor='gray', alpha=0.85))

    fig.tight_layout()
    save_fig(fig, 'q1_bounce_tsne', subdir='results')
    plt.close(fig)
    print('[tsne] 已保存 q1_bounce_tsne.png', flush=True)


def generate_text_interpretation(summary):
    """生成论文段落文字"""
    total_kw = summary['关键词数'].sum()
    text = f"""
**关于"高跳出率"指标的静态披露**

通过 KMeans 聚类（k={len(summary)}），将 {total_kw} 个有消费关键词按"消费额对数 + 跳出率"聚成 3 类，业务画像如下：

"""
    for _, row in summary.iterrows():
        text += (
            f"- **{row['业务标签']}**（聚类 {int(row['cluster'])}）："
            f"{int(row['关键词数'])} 个关键词，"
            f"占总消费 {row['消费占比(%)']:.1f}%，"
            f"平均跳出率 {row['平均跳出率']:.1%}，"
            f"平均 CPC {row['平均CPC']:.2f} 元，"
            f"平均访问时长 {row['平均访问时长秒']:.1f} 秒。\n"
        )

    high_bounce = summary[summary['平均跳出率'] > 0.85]
    if len(high_bounce) > 0:
        text += f"\n其中 **{high_bounce.iloc[0]['业务标签']}** 占关键词数 "
        text += f"{high_bounce.iloc[0]['关键词数']/total_kw*100:.1f}%，"
        text += f"占总消费 {high_bounce.iloc[0]['消费占比(%)']:.1f}%。"
        text += "\n\n**业务解读**：在 SEM 行业（医疗/教育/服务）跳出率 80-90% 属于行业常态"
        text += "（用户点击后立即关闭 = 信息已获取 / 无购买意向），"
        text += "高跳出率并不直接代表关键词质量差。"
        text += "建议后续结合'访问时长'和'注册转化'综合评估。"

    return text.strip()


def run_bounce_cluster(k=3):
    """主入口"""
    print('[bounce] 加载数据...', flush=True)
    data = build_q1_data()

    print('[bounce] 聚类分析...', flush=True)
    dfk = cluster_keywords_by_bounce(data, k=k)
    if dfk is None:
        return None

    # 保存每关键词聚类
    out_csv = os.path.join(TABLES_DIR, 'q1_bounce_clusters.csv')
    dfk[['关键词', '方案ID', '消费额', '跳出率', '平均访问时长_秒', 'cluster']].to_csv(
        out_csv, index=False, encoding='utf-8-sig')
    print(f'[save] {out_csv}', flush=True)

    # 汇总
    summary = summarize_clusters(dfk)
    summary = interpret_clusters(summary)
    out_summary = os.path.join(TABLES_DIR, 'q1_bounce_cluster_summary.csv')
    summary.to_csv(out_summary, index=False, encoding='utf-8-sig')
    print(f'[save] {out_summary}', flush=True)

    # 绘图
    plot_clusters(dfk, summary, k=k)

    # 新增：TSNE 降维可视化
    plot_tsne_clusters(dfk, k=k)

    # 文字稿
    text = generate_text_interpretation(summary)
    out_text = os.path.join(TABLES_DIR, 'q1_bounce_interpretation.md')
    with open(out_text, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'[save] {out_text}', flush=True)
    print('\n=== 聚类汇总 ===', flush=True)
    print(summary.to_string(index=False), flush=True)
    print('\n=== 文字稿 ===', flush=True)
    print(text, flush=True)

    return summary, text


if __name__ == '__main__':
    run_bounce_cluster(k=3)
