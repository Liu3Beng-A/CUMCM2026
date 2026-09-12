"""Q2 关键词 5 类分类（GMM + BIC + 业务命名）

目的：
- 对 2227 个关键词（含 1337 个有效）做 5 分类
- 分类依据：高斯混合模型（GMM）+ BIC 自动选 K
- 业务命名：基于 GMM 后验概率最高类的聚类中心映射到业务含义

输出：
- results/tables/q2_keyword_classification.csv（每关键词 + 类别）
- results/figures/q2_gmm_clusters.png（PCA 2D 散点 + 类别着色）
- results/figures/q2_bic_curve.png（BIC 选 K 曲线）
- data/raw/attachments/result2.xlsx（题目要求的附件 2 位置）
- results/tables/q2_cluster_summary.csv（每类汇总）
- issue/q2_method.md（方法说明）

方法：
1. 准备 5 维特征矩阵（消费额、CPC、展现量、点击率、注册率）
2. 标准化 (z-score)
3. 对 K=2..8 跑 GMM，记录 BIC
4. 选 BIC 最小的 K
5. 后验概率分类 + 业务命名
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

from src.utils import TABLES_DIR, FIGURES_DIR, ensure_dir
from src.plot_style import apply_style, save_fig, COLORS


# 业务命名规则（按聚类中心的特征向量映射）
# 特征：[log消费额, CPC, 展现, 点击率, 注册率]
# 高价值: CPC低 + 注册率高 + 消费中
# 中价值: 中庸
# 探索: 高展现 + 低消费 + 中注册
# 浪费: 高CPC + 低注册 + 高消费
# 低效: 全低
NAMING_RULES = [
    # 名称 + 启发函数: 返回 True 表示该聚类匹配
    # 特征字典 key: 消费, CPC, 展示, 点击, 注册, 跳出 （值 0~1 归一化排名）
    ('高价值转化型',   lambda c: c['CPC']  < 0.4 and c['注册'] > 0.5 and c['消费'] > 0.3),
    ('稳定拓展型',     lambda c: c['展示'] > 0.5 and c['CPC']  < 0.6 and c['点击'] > 0.4),
    ('潜力挖掘型',     lambda c: c['展示'] > 0.5 and c['注册'] < 0.5 and c['CPC']  < 0.6),
    ('高成本浪费型',   lambda c: c['CPC']  > 0.7 and c['消费'] > 0.5 and c['注册'] < 0.5),
    ('低效长尾型',     lambda c: True),  # catch-all
]


def prepare_features(kw):
    """准备 6 维特征矩阵

    处理：
    - 注册转化率：NaN 视为 0（无效词）
    - 对数变换：消费额 / 浏览量（强偏态）
    - 注：附件关键词表中"展现量"实际存储为"浏览量"列
    """
    kw = kw.copy()
    # 注册转化率填充
    if '注册转化率' in kw.columns:
        kw['注册率_filled'] = kw['注册转化率'].fillna(0)
    else:
        kw['注册率_filled'] = 0.0

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
        '注册率':      kw['注册率_filled'],
        '跳出率':      kw['跳出率_filled'],
    })
    return feats


def select_k_by_bic(X_scaled, k_range=range(2, 9)):
    """遍历 K，用 BIC 选最佳"""
    print('\n[K 选择] 遍历 K=2..8 计算 BIC...', flush=True)
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
    print(f'\n  → 最佳 K = {best_k} (BIC={min(bics):.1f})', flush=True)
    return best_k, models[best_k], list(bics), list(k_range)


def name_clusters(cluster_centers_raw, scaler):
    """根据聚类中心在原始尺度的特征给每个聚类业务命名

    Strategy：
    - 把"消费=0、注册率=0"的死词过滤出去
    - 剩余按 消费排名 分桶：高/中/低 + 二维特征差异区分
    - 强制 5 类语义（即使 K=6/8，命名时合并命名同语义聚类）
    """
    K = len(cluster_centers_raw)
    feat_names = ['消费', 'CPC', '展示', '点击', '注册', '跳出']

    norms = {}
    for i, name in enumerate(feat_names):
        col = cluster_centers_raw[:, i]
        mn, mx = col.min(), col.max()
        norms[name] = (col - mn) / (mx - mn + 1e-9)

    ranks = {name: norms[name] for name in feat_names}

    # 识别"完全死词"（所有特征都接近 0）的聚类
    nrows = []
    for k in range(K):
        score = ranks['消费'][k] + ranks['CPC'][k] + ranks['展示'][k] + ranks['点击'][k] + ranks['注册'][k]
        nrows.append((k, score))
    nrows.sort(key=lambda x: x[1])  # 升序：最"死"的在前

    # 划分桶
    names = [None] * K
    n_dead = sum(1 for k, s in nrows if s < 0.05)
    n_remain = K - n_dead

    if n_remain <= 0:
        # 全部都死
        names = ['低效长尾型'] * K
    else:
        # 死词全部归为"低效长尾型"
        for i in range(n_dead):
            names[nrows[i][0]] = '低效长尾型'

        # 剩余按消费排名分组
        alive = nrows[n_dead:]
        n_alive = len(alive)
        for pos, (k, _) in enumerate(alive):
            cost_rank = ranks['消费'][k]
            cpc_rank = ranks['CPC'][k]
            reg_rank = ranks['注册'][k]

            if cost_rank > 0.66:
                # 顶部消费
                if cpc_rank > 0.5:
                    names[k] = '高成本浪费型' if reg_rank < 0.5 else '高价值转化型'
                else:
                    names[k] = '高价值转化型'
            elif cost_rank > 0.33:
                # 中部
                if cpc_rank > 0.6 and reg_rank < 0.5:
                    names[k] = '高成本浪费型'
                elif cpc_rank > 0.4 and reg_rank < 0.4:
                    names[k] = '潜力挖掘型'
                else:
                    names[k] = '稳定拓展型'
            else:
                # 底部
                if cpc_rank > 0.5:
                    names[k] = '潜力挖掘型'
                else:
                    names[k] = '低效长尾型'

    # 兜底 + 去重
    seen = {}
    for i in range(K):
        if names[i] is None:
            names[i] = '潜力挖掘型'
        base = names[i].rstrip('二三四五六')
        if base in seen:
            seen[base] += 1
            names[i] = base + '二三四五六七八'[seen[base]-2]
        else:
            seen[base] = 1
    return names


def main():
    print('=' * 60, flush=True)
    print('问题 2：关键词 5 类分类（GMM + BIC + 业务命名）', flush=True)
    print('=' * 60, flush=True)

    ensure_dir(TABLES_DIR)
    ensure_dir(FIGURES_DIR)

    # 1) 加载数据
    kw_path = os.path.join('data', 'processed', 'q1', 'keyword_total.pkl')
    kw = pd.read_pickle(kw_path)
    print(f'\n[加载] {len(kw)} 个关键词', flush=True)
    print(f'  列: {list(kw.columns)}', flush=True)

    # 2) 准备特征
    feats = prepare_features(kw)
    print(f'\n[特征] {feats.shape[1]} 维: {list(feats.columns)}', flush=True)
    print(f'  描述性统计：', flush=True)
    print(feats.describe().round(2).to_string(), flush=True)

    # 3) 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(feats.values)

    # 4) BIC 选 K
    best_k, best_gm, bics, ks = select_k_by_bic(X_scaled)
    labels = best_gm.predict(X_scaled)

    # 5) 反标准化聚类中心（用于业务命名）
    centers_raw = scaler.inverse_transform(best_gm.means_)
    cluster_names = name_clusters(centers_raw, scaler)
    label_to_name = {i: n for i, n in enumerate(cluster_names)}
    kw_labels = pd.Series(labels).map(label_to_name).values

    print(f'\n[聚类结果] K={best_k}', flush=True)
    for i, n in enumerate(cluster_names):
        n_count = (labels == i).sum()
        centers_str = ', '.join([f'{feat}={c:.2f}' for feat, c in zip(feats.columns, centers_raw[i])])
        print(f'  类{i} {n}: {n_count} 个 ({n_count/len(labels)*100:.1f}%) | 中心: {centers_str}', flush=True)

    # 6) 输出分类结果 CSV
    out_csv = os.path.join(TABLES_DIR, 'q2_keyword_classification.csv')
    out_df = kw.copy()
    out_df['GMM_K'] = best_k
    out_df['cluster_id'] = labels
    out_df['分类'] = kw_labels
    out_df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'\n[save] {out_csv}', flush=True)

    # 7) 输出聚类中心汇总
    summary_rows = []
    for i, n in enumerate(cluster_names):
        n_count = (labels == i).sum()
        mask = labels == i
        cluster_kw = kw[mask]
        summary_rows.append({
            'cluster_id': i,
            '分类名称': n,
            '关键词数': n_count,
            '占比': round(n_count / len(labels) * 100, 1),
            '平均消费': round(cluster_kw['消费额'].mean() if '消费额' in cluster_kw.columns else 0, 0),
            '平均CPC': round(cluster_kw['CPC'].mean() if 'CPC' in cluster_kw.columns else 0, 2),
            '平均点击率': round(cluster_kw['点击率'].mean() if '点击率' in cluster_kw.columns else 0, 4),
            '平均注册率': round(cluster_kw['注册转化率'].mean() if '注册转化率' in cluster_kw.columns else 0, 4),
            '平均跳出率': round(cluster_kw['跳出率'].mean() if '跳出率' in cluster_kw.columns else 0, 4),
            '中心原始值': '; '.join([f'{feat}={c:.2f}' for feat, c in zip(feats.columns, centers_raw[i])]),
        })
    summary_df = pd.DataFrame(summary_rows)
    summary_csv = os.path.join(TABLES_DIR, 'q2_cluster_summary.csv')
    summary_df.to_csv(summary_csv, index=False, encoding='utf-8-sig')
    print(f'[save] {summary_csv}', flush=True)
    print('\n聚类汇总:', flush=True)
    print(summary_df[['cluster_id', '分类名称', '关键词数', '占比', '平均消费', '平均CPC', '平均注册率']].to_string(index=False), flush=True)

    # 8) 写出 result2.xlsx（题目要求的"附件2位置"）
    out_xlsx = os.path.join('data', 'raw', 'attachments', 'result2.xlsx')
    os.makedirs(os.path.dirname(out_xlsx), exist_ok=True)
    with pd.ExcelWriter(out_xlsx, engine='openpyxl') as writer:
        out_df.to_excel(writer, sheet_name='关键词分类', index=False)
        summary_df.to_excel(writer, sheet_name='分类汇总', index=False)
    print(f'[save] {out_xlsx}', flush=True)

    # 9) 绘图：PCA 2D 散点
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # (a) PCA 散点
    ax = axes[0]
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    for i, n in enumerate(cluster_names):
        mask = labels == i
        ax.scatter(X_pca[mask, 0], X_pca[mask, 1], label=f'{n} ({(labels==i).sum()})',
                   alpha=0.6, s=30, edgecolors='none')

    # 画聚类中心
    centers_pca = pca.transform(best_gm.means_)
    ax.scatter(centers_pca[:, 0], centers_pca[:, 1], marker='x', s=200, c='red',
               linewidths=3, label='聚类中心', zorder=10)
    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% 方差)', fontsize=11)
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% 方差)', fontsize=11)
    ax.set_title('(a) GMM 聚类结果（PCA 2D 投影）', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3)

    # (b) BIC 曲线
    ax = axes[1]
    ax.plot(ks, bics, marker='o', linewidth=2, color=COLORS['primary'])
    best_idx = int(np.argmin(bics))
    ax.scatter([ks[best_idx]], [bics[best_idx]], s=200, c='red',
               marker='*', zorder=10, label=f'最佳 K={ks[best_idx]}')
    ax.set_xlabel('簇数 K', fontsize=11)
    ax.set_ylabel('BIC（越小越好）', fontsize=11)
    ax.set_title('(b) BIC 选 K 曲线', fontsize=12, fontweight='bold')
    ax.set_xticks(ks)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    fig.suptitle('问题 2：关键词 5 类分类（GMM + BIC 自动选 K）', fontsize=14, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, 'q2_gmm_clusters', subdir='results')
    plt.close(fig)

    # 10) 写方法说明文档
    method_md = f"""# Q2 方法说明 · 关键词 5 类分类

## 1. 目的
对附件 1 中 **{len(kw)}** 个关键词（含 **{(kw.get('有消费', pd.Series([False]*len(kw)))==1).sum() if '有消费' in kw.columns else 'N/A'}** 个有效）做 5 分类，给出差异化运营建议。

## 2. 方法

### 2.1 特征工程（6 维）
- `log消费额` = log1p(消费额)
- `CPC` = 消费额 / 点击量（直接用）
- `log展现量` = log1p(展现量)
- `点击率` = 点击量 / 展现量
- `注册转化率` = 注册数 / 点击量（NaN → 0）
- `跳出率`（NaN → 中位数填充）

### 2.2 GMM + BIC 选 K
- 算法：Gaussian Mixture Model（高斯混合）
- 协方差类型：full（最一般）
- 候选 K：2 ~ 8
- 选 K 准则：BIC 最小（Bayesian Information Criterion）
- 实际最佳 K = **{best_k}**（BIC = {min(bics):.1f}）

### 2.3 业务命名（启发式规则）
基于聚类中心在 6 维特征空间的归一化排名，按业务启发式匹配：

| 业务名 | 启发式 |
|--------|--------|
| 高价值转化型 | CPC 低 + 注册率高 |
| 稳定拓展型 | 展现高 + CPC 合理 |
| 潜力挖掘型 | 展现高 + 注册低 + CPC 低（待优化） |
| 高成本浪费型 | CPC 高 + 消费高 + 注册低（应暂停） |
| 低效长尾型 | 其他（兜底） |

## 3. 聚类结果（K={best_k}）

| 类别 | 名称 | 关键词数 | 占比 | 平均消费 | 平均 CPC | 平均注册率 |
|------|------|---------|------|---------|---------|-----------|
""" + '\n'.join([
        f"| {r['cluster_id']} | {r['分类名称']} | {r['关键词数']} | {r['占比']}% | {r['平均消费']:.0f} | {r['平均CPC']:.2f} | {r['平均注册率']:.4f} |"
        for _, r in summary_df.iterrows()
    ]) + f"""

## 4. 论文可写要点

### 4.1 业务解读
- **高价值转化型**：核心词，应加大预算
- **稳定拓展型**：补量词，可稳步扩
- **潜力挖掘型**：优化词，优化创意/落地页后可释放
- **高成本浪费型**：应暂停
- **低效长尾型**：长期观察

### 4.2 国一差异化
- 不止"4 象限 / 5 分类"硬阈值
- GMM 自适应选 K（不必拍脑袋选 5）
- 业务命名让算法贴近业务

## 5. 输出文件
- `results/tables/q2_keyword_classification.csv`（每关键词 + 类别）
- `results/tables/q2_cluster_summary.csv`（聚类中心 + 业务汇总）
- `results/figures/q2_gmm_clusters.png`（PCA 散点 + BIC 曲线）
- `data/raw/attachments/result2.xlsx`（题目要求位置）
- `issue/q2_method.md`（本文档）

## 6. 可复现性
- 随机种子：42
- n_init=3（多次随机初始化取最优）
- 数据：`data/processed/q1/keyword_total.pkl`（来自 `q1_data_prep.py`）
"""
    method_path = os.path.join('issue', 'q2_method.md')
    with open(method_path, 'w', encoding='utf-8') as f:
        f.write(method_md)
    print(f'[save] {method_path}', flush=True)

    print('\n' + '=' * 60, flush=True)
    print(f'Q2 完成：K={best_k} 类, {(kw.get("有消费", pd.Series([False]*len(kw)))==1).sum() if "有消费" in kw.columns else len(kw)} 个有效词全部已分类', flush=True)
    print('=' * 60, flush=True)

    return out_df, summary_df, best_k


if __name__ == '__main__':
    main()
