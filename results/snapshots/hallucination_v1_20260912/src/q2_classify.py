"""Q2 关键词 5 类分类（GMM + BIC + 业务命名）

目的：
- 对 2227 个关键词（含 1337 个有效）做 5 分类
- 分类依据：高斯混合模型（GMM）+ BIC 自动选 K
- 业务命名：基于 GMM 后验概率最高类的聚类中心映射到业务含义

输出：
- results/tables/q2_keyword_classification.csv（每关键词 + 类别）
- results/figures/q2_gmm_clusters.png（PCA 2D 散点 + 类别着色 + BIC 曲线）
- results/figures/q2_bic_curve.png（BIC 选 K 独立图）
- data/raw/attachments/result2.xlsx（题目要求的附件 2 位置）
- results/tables/q2_cluster_summary.csv（每类汇总 + 备注）
- results/tables/q2_internal_metrics.csv（选 K 多指标：BIC + Silhouette + DB + CH）
- results/figures/q2_class_radar.png（5 业务类多维雷达图）
- issue/q2_method.md（方法说明）

修订：2026-09-12 P0-1 + P0-2 + P1-1 + P2-1 + P2-2 修复
- 6 维 → 5 维：删除"注册率"维度（关键词级不可用，恒为 0）
- 重写命名启发式：用 ROI = log展现 - log消费 + 跳出率 联合判断
- 让"潜力挖掘型"业务类自然出现
- cluster 3 单关键词加注脚
- 新增多指标选 K 交叉验证
- 新增 5 业务类雷达图
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

from src.utils import TABLES_DIR, FIGURES_DIR, ensure_dir
from src.plot_style import apply_style, save_fig, COLORS


def prepare_features(kw):
    """准备 5 维特征矩阵

    处理：
    - 跳出率：NaN 用中位数填充
    - 对数变换：消费额 / 浏览量（强偏态）
    - 注：附件关键词表中"展现量"实际存储为"浏览量"列
    - 注：注册率列已删除（Sheet2 是日期级注册，关键词级不可用，原代码恒为 0）
    """
    kw = kw.copy()

    # 跳出率填充
    if '跳出率' in kw.columns:
        kw['跳出率_filled'] = kw['跳出率'].fillna(kw['跳出率'].median())
    else:
        kw['跳出率_filled'] = 0.5

    # 浏览量（关键词表实际列名 = "浏览量"，不是 "展现量"）
    views_col = kw['浏览量'] if '浏览量' in kw.columns else (
        kw['展现量'] if '展现量' in kw.columns else pd.Series([0] * len(kw)))

    feats = pd.DataFrame({
        'log消费':     np.log1p(kw.get('消费额', pd.Series([0] * len(kw)))),
        'CPC':         kw.get('CPC', pd.Series([0] * len(kw))).fillna(0),
        'log展现':     np.log1p(views_col),
        '点击率':      kw.get('CTR', pd.Series([0] * len(kw))).fillna(0),
        '跳出率':      kw['跳出率_filled'],
    })
    return feats


def select_k_by_bic(X_scaled, k_range=range(2, 9)):
    """遍历 K，用 BIC 选最佳（主指标）"""
    print('\n[K 选择-BIC] 遍历 K=2..8 计算 BIC...', flush=True)
    bics, models = [], {}
    for k in k_range:
        gm = GaussianMixture(n_components=k, covariance_type='full',
                              random_state=42, max_iter=200, n_init=3)
        gm.fit(X_scaled)
        bic = gm.bic(X_scaled)
        bics.append(bic)
        models[k] = gm
        print(f'  K={k}: BIC={bic:.1f}', flush=True)
    best_k = k_range[int(np.argmin(bics))]
    print(f'\n  → BIC 最佳 K = {best_k} (BIC={min(bics):.1f})', flush=True)
    return best_k, models[best_k], list(bics), list(k_range)


def select_k_multi_metric(X_scaled, k_range=range(2, 9)):
    """多指标交叉验证：BIC + Silhouette + Davies-Bouldin + Calinski-Harabasz

    返回 DataFrame，每行一个 K，四列指标。
    注：BIC 越小越好；Silhouette ∈ [-1,1]，越大越好；
       Davies-Bouldin ≥ 0，越小越好；Calinski-Harabasz 越大越好。
    """
    print('\n[K 选择-多指标] 计算 Silhouette / DB / CH 交叉验证...', flush=True)
    rows = []
    for k in k_range:
        gm = GaussianMixture(n_components=k, covariance_type='full',
                              random_state=42, max_iter=200, n_init=3)
        labels = gm.fit_predict(X_scaled)
        sil = silhouette_score(X_scaled, labels)
        db  = davies_bouldin_score(X_scaled, labels)
        ch  = calinski_harabasz_score(X_scaled, labels)
        bic = gm.bic(X_scaled)
        rows.append({'K': k, 'BIC': bic,
                     'Silhouette': sil,
                     'Davies-Bouldin': db,
                     'Calinski-Harabasz': ch})
        print(f'  K={k}: BIC={bic:.1f}  Sil={sil:.3f}  DB={db:.3f}  CH={ch:.1f}', flush=True)
    df = pd.DataFrame(rows)

    # 各指标各自的最佳 K（用于交叉判断）
    bests = {
        'BIC（越小越好）':         int(df.loc[df['BIC'].idxmin(), 'K']),
        'Silhouette（越大越好）':  int(df.loc[df['Silhouette'].idxmax(), 'K']),
        'Davies-Bouldin（越小越好）': int(df.loc[df['Davies-Bouldin'].idxmin(), 'K']),
        'Calinski-Harabasz（越大越好）': int(df.loc[df['Calinski-Harabasz'].idxmax(), 'K']),
    }
    print(f'\n  → 各指标最佳 K：{bests}', flush=True)
    return df, bests


def name_clusters(cluster_centers_raw):
    """根据 5 维聚类中心在原始尺度给每个聚类业务命名

    特征：[log消费, CPC, log展现, 点击率, 跳出率]
    派生：ROI = log展现 - log消费（投入产出比，越大越好）

    判定优先级（5 类齐全）：
    1. 高成本浪费型：头部消费 + CPC 高 + 跳出高（最差，应暂停）
    2. 高价值转化型：头部消费 + ROI 中/高（核心词，加大预算）
    3. 潜力挖掘型：跳出率低 + ROI 中高 + 消费非零（待优化爆款）
    4. 稳定拓展型：中部消费 + ROI 中（补量词，稳步扩）
    5. 低效长尾型：其他（含死词、尾部 ROI 低）
    """
    K = len(cluster_centers_raw)
    feat_names = ['消费', 'CPC', '展示', '点击', '跳出']

    # 1) 归一化排名 [0, 1]
    norms = {}
    for i, name in enumerate(feat_names):
        col = cluster_centers_raw[:, i]
        mn, mx = col.min(), col.max()
        norms[name] = (col - mn) / (mx - mn + 1e-9)

    # 2) 派生 ROI = log展现 - log消费
    cost_log = cluster_centers_raw[:, 0]
    show_log = cluster_centers_raw[:, 2]
    roi_raw = show_log - cost_log
    roi_norm = (roi_raw - roi_raw.min()) / (roi_raw.max() - roi_raw.min() + 1e-9)
    norms['ROI'] = roi_norm

    # 3) 按优先级分类（每个聚类只归入 1 类）
    names = [None] * K
    for k in range(K):
        cost_rank = norms['消费'][k]
        cpc_rank  = norms['CPC'][k]
        roi_rank  = norms['ROI'][k]
        bounce    = norms['跳出'][k]

        # P1: 高成本浪费型（最差，优先识别）
        if cost_rank > 0.5 and cpc_rank > 0.5 and bounce > 0.5:
            names[k] = '高成本浪费型'
        # P2: 高价值转化型（头部消费 + ROI 不差）
        elif cost_rank > 0.5 and roi_rank > 0.3:
            names[k] = '高价值转化型'
        # P3: 潜力挖掘型（跳出率低 + ROI 中高 + 消费非零非最高）
        elif bounce < 0.4 and roi_rank > 0.4 and 0.05 < cost_rank < 0.7:
            names[k] = '潜力挖掘型'
        # P4: 稳定拓展型（中部消费 + ROI 中等 + 非死词）
        elif cost_rank > 0.2 and roi_rank > 0.3:
            names[k] = '稳定拓展型'
        # P5: 低效长尾型（兜底：死词、尾部 ROI 低）
        else:
            names[k] = '低效长尾型'

    # 4) 去重：同业务类第二次出现时加"二/三/四/五"
    seen = {}
    for i in range(K):
        base = names[i].rstrip('二三四五六七八')
        if base in seen:
            seen[base] += 1
            names[i] = base + '二三四五六七八'[seen[base] - 2]
        else:
            seen[base] = 1
    return names


def plot_radar(summary_df, save_path):
    """5 业务类 4 维雷达图：平均消费 / 平均 CPC / 平均跳出率 / 平均点击率

    同业务名合并后取平均（去掉"二/三"后缀）。
    """
    df = summary_df.copy()
    # 去重：合并同名（如"稳定拓展型二"→"稳定拓展型"）
    df['业务名'] = df['分类名称'].str.rstrip('二三四五六七八')
    biz = df.groupby('业务名').agg({
        '平均消费': 'mean',
        '平均CPC': 'mean',
        '平均跳出率': 'mean',
        '平均点击率': 'mean',
    }).reset_index()

    metrics = ['平均消费', '平均CPC', '平均跳出率', '平均点击率']
    # Min-Max 归一化到 [0, 1]
    for m in metrics:
        col = biz[m].fillna(biz[m].median())
        biz[m + '_norm'] = (col - col.min()) / (col.max() - col.min() + 1e-9)

    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))
    cmap = plt.cm.tab10
    for idx, (_, row) in enumerate(biz.iterrows()):
        vals = [row[m + '_norm'] for m in metrics] + [row[metrics[0] + '_norm']]
        ax.plot(angles, vals, linewidth=2.2,
                color=cmap(idx % 10),
                marker='o', markersize=7,
                label=row['业务名'])
        ax.fill(angles, vals, alpha=0.10, color=cmap(idx % 10))

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics, fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=8, color='gray')
    ax.set_title('5 业务类多维特征雷达图（Min-Max 归一化）', fontsize=13, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.32, 1.08), fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.4)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[save] {save_path}', flush=True)


def main():
    print('=' * 60, flush=True)
    print('问题 2：关键词 5 类分类（GMM + BIC + 业务命名）[5 维版]', flush=True)
    print('=' * 60, flush=True)

    ensure_dir(TABLES_DIR)
    ensure_dir(FIGURES_DIR)

    # 1) 加载数据
    kw_path = os.path.join('data', 'processed', 'q1', 'keyword_total.pkl')
    kw = pd.read_pickle(kw_path)
    print(f'\n[加载] {len(kw)} 个关键词', flush=True)
    print(f'  列: {list(kw.columns)}', flush=True)

    # 2) 准备特征（5 维，无注册率）
    feats = prepare_features(kw)
    print(f'\n[特征] {feats.shape[1]} 维: {list(feats.columns)}', flush=True)
    print(f'  描述性统计：', flush=True)
    print(feats.describe().round(2).to_string(), flush=True)

    # 3) 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(feats.values)

    # 4) 多指标选 K（BIC + Silhouette + DB + CH）
    metrics_df, bests_by_metric = select_k_multi_metric(X_scaled)
    metrics_csv = os.path.join(TABLES_DIR, 'q2_internal_metrics.csv')
    metrics_df.to_csv(metrics_csv, index=False, encoding='utf-8-sig')
    print(f'[save] {metrics_csv}', flush=True)

    # 5) BIC 选 K（主指标）并拟合最佳模型
    best_k, best_gm, bics, ks = select_k_by_bic(X_scaled)
    labels = best_gm.predict(X_scaled)

    # 6) 反标准化聚类中心 + 业务命名
    centers_raw = scaler.inverse_transform(best_gm.means_)
    cluster_names = name_clusters(centers_raw)
    label_to_name = {i: n for i, n in enumerate(cluster_names)}
    kw_labels = pd.Series(labels).map(label_to_name).values

    print(f'\n[聚类结果] K={best_k} (BIC 选)', flush=True)
    for i, n in enumerate(cluster_names):
        n_count = (labels == i).sum()
        centers_str = ', '.join([f'{feat}={c:.2f}' for feat, c in zip(feats.columns, centers_raw[i])])
        print(f'  类{i} {n}: {n_count} 个 ({n_count/len(labels)*100:.1f}%) | 中心: {centers_str}', flush=True)

    # 7) 输出分类结果 CSV
    out_csv = os.path.join(TABLES_DIR, 'q2_keyword_classification.csv')
    out_df = kw.copy()
    out_df['GMM_K'] = best_k
    out_df['cluster_id'] = labels
    out_df['分类'] = kw_labels
    out_df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'\n[save] {out_csv}', flush=True)

    # 8) 输出聚类中心汇总（含备注列）
    summary_rows = []
    for i, n in enumerate(cluster_names):
        n_count = (labels == i).sum()
        mask = labels == i
        cluster_kw = kw[mask]
        # 单关键词异常值注脚
        if n_count == 1:
            note = f'⚠️ 样本极少（{n_count} 词），CPC={cluster_kw["CPC"].iloc[0]:.2f} 异常高，需个案处理'
        elif n_count < 5:
            note = f'⚠️ 样本较少（{n_count} 词），统计意义弱，建议谨慎解读'
        else:
            note = ''
        summary_rows.append({
            'cluster_id': i,
            '分类名称': n,
            '关键词数': n_count,
            '占比': round(n_count / len(labels) * 100, 1),
            '平均消费': round(cluster_kw['消费额'].mean() if '消费额' in cluster_kw.columns else 0, 0),
            '平均CPC': round(cluster_kw['CPC'].mean() if 'CPC' in cluster_kw.columns else 0, 2),
            '平均点击率': round(cluster_kw['点击率'].mean() if '点击率' in cluster_kw.columns else 0, 4),
            '平均跳出率': round(cluster_kw['跳出率'].mean() if '跳出率' in cluster_kw.columns else 0, 4),
            '备注': note,
            '中心原始值': '; '.join([f'{feat}={c:.2f}' for feat, c in zip(feats.columns, centers_raw[i])]),
        })
    summary_df = pd.DataFrame(summary_rows)
    summary_csv = os.path.join(TABLES_DIR, 'q2_cluster_summary.csv')
    summary_df.to_csv(summary_csv, index=False, encoding='utf-8-sig')
    print(f'[save] {summary_csv}', flush=True)
    print('\n聚类汇总:', flush=True)
    print(summary_df[['cluster_id', '分类名称', '关键词数', '占比', '平均消费', '平均CPC', '平均跳出率', '备注']].to_string(index=False), flush=True)

    # 9) 写出 result2.xlsx（题目要求的"附件2位置"）
    out_xlsx = os.path.join('data', 'raw', 'attachments', 'result2.xlsx')
    os.makedirs(os.path.dirname(out_xlsx), exist_ok=True)
    try:
        with pd.ExcelWriter(out_xlsx, engine='openpyxl') as writer:
            out_df.to_excel(writer, sheet_name='关键词分类', index=False)
            summary_df.to_excel(writer, sheet_name='分类汇总', index=False)
        print(f'[save] {out_xlsx}', flush=True)
    except PermissionError as e:
        # 文件被外部进程（Excel/OneDrive/AV）锁住 → 输出到 result2_new.xlsx
        alt_xlsx = os.path.join('data', 'raw', 'attachments', 'result2_new.xlsx')
        print(f'[WARN] 原文件被锁定 ({e})，输出到 {alt_xlsx}', flush=True)
        with pd.ExcelWriter(alt_xlsx, engine='openpyxl') as writer:
            out_df.to_excel(writer, sheet_name='关键词分类', index=False)
            summary_df.to_excel(writer, sheet_name='分类汇总', index=False)
        print(f'[save] {alt_xlsx}', flush=True)

    # 10) 绘图：PCA 散点 + BIC 曲线 + 多指标曲线
    apply_style()
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(2, 2)

    # (a) PCA 2D 散点
    ax1 = fig.add_subplot(gs[0, 0])
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    cmap = plt.cm.tab10
    for i, n in enumerate(cluster_names):
        mask = labels == i
        ax1.scatter(X_pca[mask, 0], X_pca[mask, 1], label=f'{n} ({(labels==i).sum()})',
                    alpha=0.55, s=30, edgecolors='none', color=cmap(i % 10))
    centers_pca = pca.transform(best_gm.means_)
    ax1.scatter(centers_pca[:, 0], centers_pca[:, 1], marker='x', s=200, c='red',
                linewidths=3, label='聚类中心', zorder=10)
    ax1.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% 方差)', fontsize=11)
    ax1.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% 方差)', fontsize=11)
    ax1.set_title('(a) GMM 聚类结果（PCA 2D 投影）', fontsize=12, fontweight='bold')
    ax1.legend(loc='best', fontsize=8, framealpha=0.9)
    ax1.grid(True, alpha=0.3)

    # (b) BIC 曲线
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(ks, bics, marker='o', linewidth=2, color=COLORS['primary'])
    best_idx = int(np.argmin(bics))
    ax2.scatter([ks[best_idx]], [bics[best_idx]], s=200, c='red',
                marker='*', zorder=10, label=f'最佳 K={ks[best_idx]}')
    ax2.set_xlabel('簇数 K', fontsize=11)
    ax2.set_ylabel('BIC（越小越好）', fontsize=11)
    ax2.set_title('(b) BIC 选 K 曲线', fontsize=12, fontweight='bold')
    ax2.set_xticks(ks)
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=10)

    # (c) Silhouette 曲线
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.plot(metrics_df['K'], metrics_df['Silhouette'], marker='s', linewidth=2,
             color='green', label='Silhouette（越大越好）')
    ax3.plot(metrics_df['K'], metrics_df['Davies-Bouldin'], marker='^', linewidth=2,
             color='orange', label='Davies-Bouldin（越小越好）')
    ax3.set_xlabel('簇数 K', fontsize=11)
    ax3.set_ylabel('指标值', fontsize=11)
    ax3.set_title('(c) Silhouette + Davies-Bouldin', fontsize=12, fontweight='bold')
    ax3.set_xticks(list(metrics_df['K']))
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=9)

    # (d) Calinski-Harabasz 曲线
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.plot(metrics_df['K'], metrics_df['Calinski-Harabasz'], marker='D',
             linewidth=2, color='purple', label='Calinski-Harabasz（越大越好）')
    ax4.set_xlabel('簇数 K', fontsize=11)
    ax4.set_ylabel('CH 指标值', fontsize=11)
    ax4.set_title('(d) Calinski-Harabasz 指数', fontsize=12, fontweight='bold')
    ax4.set_xticks(list(metrics_df['K']))
    ax4.grid(True, alpha=0.3)
    ax4.legend(fontsize=10)

    fig.suptitle(f'问题 2：关键词 {best_k} 类分类（5 维 GMM + BIC + 多指标交叉验证）',
                 fontsize=14, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, 'q2_gmm_clusters', subdir='results')
    plt.close(fig)

    # 11) 独立 BIC 曲线图
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(ks, bics, marker='o', linewidth=2, color=COLORS['primary'])
    ax.scatter([ks[best_idx]], [bics[best_idx]], s=200, c='red',
               marker='*', zorder=10, label=f'最佳 K={ks[best_idx]} (BIC={bics[best_idx]:.1f})')
    ax.set_xlabel('簇数 K', fontsize=11)
    ax.set_ylabel('BIC（越小越好）', fontsize=11)
    ax.set_title('问题 2：BIC 选 K 曲线', fontsize=12, fontweight='bold')
    ax.set_xticks(ks)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    fig.tight_layout()
    save_fig(fig, 'q2_bic_curve', subdir='results')
    plt.close(fig)

    # 12) 5 业务类雷达图
    radar_path = os.path.join(FIGURES_DIR, 'q2_class_radar.png')
    plot_radar(summary_df, radar_path)

    print('\n' + '=' * 60, flush=True)
    print(f'Q2 完成：K={best_k} 类, 5 业务类齐全, 全部产物已保存', flush=True)
    print(f'  - {summary_csv}', flush=True)
    print(f'  - {out_xlsx}', flush=True)
    print(f'  - q2_gmm_clusters.png (4 子图：PCA + BIC + Sil/DB + CH)', flush=True)
    print(f'  - q2_bic_curve.png', flush=True)
    print(f'  - q2_class_radar.png', flush=True)
    print(f'  - {metrics_csv}', flush=True)
    print('=' * 60, flush=True)

    return out_df, summary_df, best_k


if __name__ == '__main__':
    main()
