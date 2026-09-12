"""
Q3 · 关键词关联分析（cosine 相似度 + FP-Growth 辅助 · BIAS_v2 数据源代理）
==========================================================================

**锁定决策（D-Q3Q4-008 / D-021 / §2.2 Layer 2 修订）**：
- ⚠️ Sheet1 没有"关键词"列；Sheet3 仅 (unit, keyword) 静态关系
- ⚠️ 数据结构决定：同单元 kw trivially 100% 共现；跨单元 kw 0% 共现
- ⚠️ FP-Growth 在这种结构下只能找到同单元 trivial 规则
- ✅ 主方法：cosine 相似度（画像相似 = 投放策略可类比 = 关联）
- ✅ 辅助：FP-Growth（同单元，必出，但 lift=常数，仅作 proof-of-concept）

**算法**：
1. 关键词画像：(kw_cost, kw_clicks, kw_browses, bounce, avg_time) × 标准化
2. cosine 相似度矩阵 909 × 909 → top-50 pairs (sim ≥ 0.5)
3. 关联网络（节点=词，边=sim>0.7）
4. FP-Growth（同单元，必出 top-50 by lift 仅作 proof-of-concept）

**主要输入**：
- `data/processed/q3/q3_target_window.pkl`
- `data/processed/q3/q3_keyword_pool.pkl`

**主要输出**：
- `results/tables/q3_keyword_assoc_rules.csv`：50 条 top 关联（cosine）
- `results/figures/q3_keyword_cooccurrence.png`：共现热力图
- `results/figures/q3_assoc_network.png`：关联网络图
- `data/processed/q3/q3_keyword_profiles.pkl`：909 词画像
- `data/processed/q3/q3_keyword_sim_matrix.pkl`：909×909 相似度矩阵
"""
import os
import sys
import pandas as pd
import numpy as np
import pickle
from sklearn.preprocessing import StandardScaler
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import PROCESSED_DIR, RESULTS_DIR, TABLES_DIR, FIGURES_DIR, ensure_dir  # noqa: E402
from src.plot_style import apply_style  # noqa: E402


# 锁定参数
TOP_N_RULES = 50
SIM_THRESHOLD = 0.50  # cosine 相似度阈值


def build_keyword_profiles(pool):
    """构建 909 词的画像（5 维特征）"""
    # 处理潜在的 column 名差异 + avg_time 用数值版
    col_map = {}
    for col in pool.columns:
        if col in ('跳出率', '跳出率_均值', 'bounce'):
            col_map[col] = 'bounce'
    pool = pool.rename(columns=col_map)
    # 用 '平均访问时长_秒'（numeric）作为 avg_time
    avg_time_col = '平均访问时长_秒' if '平均访问时长_秒' in pool.columns else 'avg_time'
    profiles = pool[['关键词', 'unit_id', 'plan_id', 'kw_cost', 'kw_clicks',
                     'kw_browses', 'bounce', avg_time_col]].copy()
    profiles = profiles.rename(columns={avg_time_col: 'avg_time'})
    profiles['关键词'] = profiles['关键词'].astype(str)
    # avg_time 转数值
    profiles['avg_time'] = pd.to_numeric(profiles['avg_time'], errors='coerce')
    # 处理 NaN
    for col in ['kw_cost', 'kw_clicks', 'kw_browses', 'bounce', 'avg_time']:
        profiles[col] = pd.to_numeric(profiles[col], errors='coerce').fillna(
            pd.to_numeric(profiles[col], errors='coerce').median()
        )
    # 派生指标（per-yuan 比率）
    profiles['ctr'] = profiles['kw_clicks'] / profiles['kw_cost'].clip(lower=0.01)
    profiles['browses_per_click'] = profiles['kw_browses'] / profiles['kw_clicks'].clip(lower=0.01)
    return profiles


def compute_similarity(profiles, top_n=TOP_N_RULES, sim_threshold=SIM_THRESHOLD):
    """cosine 相似度矩阵 + top-N pairs（聚焦高价值关键词对）"""
    feature_cols = ['kw_cost', 'kw_clicks', 'kw_browses', 'bounce', 'avg_time',
                    'ctr', 'browses_per_click']
    feats = profiles[feature_cols].values
    scaler = StandardScaler()
    feats_std = scaler.fit_transform(feats)

    # cosine 相似度
    norms = np.linalg.norm(feats_std, axis=1, keepdims=True)
    feats_norm = feats_std / norms.clip(min=1e-9)
    sim = feats_norm @ feats_norm.T  # 909 × 909

    # ---- 过滤 1：剔除低价值关键词对（双方 kw_cost 都 < 中位数）----
    cost = profiles['kw_cost'].values
    cost_median = np.median(cost)
    high_value = cost >= cost_median

    # ---- 过滤 2：剔除自相关 ----
    n = sim.shape[0]
    mask = (high_value[:, None] & high_value[None, :]) & (np.arange(n)[:, None] != np.arange(n)[None, :])
    rows, cols = np.where(mask)

    pairs = []
    for i, j in zip(rows, cols):
        pairs.append((int(i), int(j), float(sim[i, j])))

    pairs_sorted = sorted(pairs, key=lambda x: -x[2])

    # ---- 过滤 3：去重（i<j）----
    unique_pairs = []
    seen = set()
    for i, j, s in pairs_sorted:
        key = (min(i, j), max(i, j))
        if key not in seen:
            seen.add(key)
            unique_pairs.append((i, j, s))

    # ---- 过滤 4：相似度阈值 + top-N ----
    above = [p for p in unique_pairs if p[2] >= sim_threshold]
    top_pairs = above[:top_n] if len(above) >= top_n else unique_pairs[:top_n]

    # 格式化
    rules_rows = []
    for i, j, s in top_pairs:
        rules_rows.append({
            'antecedents': profiles.iloc[i]['关键词'],
            'consequents': profiles.iloc[j]['关键词'],
            'ant_unit': profiles.iloc[i]['unit_id'],
            'con_unit': profiles.iloc[j]['unit_id'],
            'support': s,
            'confidence': s,
            'lift': s,
            'metric': 'cosine',
        })
    rules = pd.DataFrame(rules_rows)
    return sim, profiles, rules


def fpgrowth_unit_only(mat, pool, min_support=0.10, min_confidence=0.60):
    """FP-Growth 辅助：仅作 proof-of-concept（同单元 trivial 关联）"""
    from mlxtend.frequent_patterns import fpgrowth, association_rules

    mat_b = mat.astype(bool)
    freq_itemsets = fpgrowth(mat_b, min_support=min_support, use_colnames=True, max_len=2)
    rules = association_rules(freq_itemsets, metric='confidence', min_threshold=min_confidence)
    rules = rules.sort_values('lift', ascending=False).head(TOP_N_RULES)
    rules['antecedents'] = rules['antecedents'].apply(lambda x: ','.join(sorted(str(k) for k in x)))
    rules['consequents'] = rules['consequents'].apply(lambda x: ','.join(sorted(str(k) for k in x)))
    rules['metric'] = 'fp_growth'
    print(f"  [FP-Growth 辅助] {len(rules)} 条（同单元 trivial，仅作 PoC）")
    return freq_itemsets, rules


def plot_similarity_heatmap(sim, profiles, top_n=30):
    """Top-30 高相似度词 共现热力图"""
    apply_style()
    # 取相似度均值最高的 top-30 词
    mean_sim = sim.mean(axis=1)
    top_idx = mean_sim.argsort()[-top_n:][::-1]
    top_kws = [profiles.iloc[i]['关键词'] for i in top_idx]
    sub = sim[np.ix_(top_idx, top_idx)]

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(sub, cmap='YlOrRd', aspect='auto', vmin=0, vmax=1)
    ax.set_xticks(range(top_n))
    ax.set_yticks(range(top_n))
    ax.set_xticklabels(top_kws, rotation=90, fontsize=7)
    ax.set_yticklabels(top_kws, fontsize=7)
    ax.set_title(f'Q3 Top-{top_n} 关键词 cosine 相似度矩阵', fontsize=11)
    plt.colorbar(im, ax=ax, label='cosine similarity')
    plt.tight_layout()
    out_path = os.path.join(FIGURES_DIR, 'q3_keyword_cooccurrence.png')
    plt.savefig(out_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  -> {out_path}")


def plot_network(rules, top_edges=50):
    """关联规则网络图"""
    import networkx as nx
    apply_style()
    G = nx.Graph()
    top = rules.head(top_edges)
    for _, r in top.iterrows():
        a = str(r['antecedents'])
        b = str(r['consequents'])
        G.add_edge(a, b, weight=r['lift'])
    fig, ax = plt.subplots(figsize=(14, 10))
    pos = nx.spring_layout(G, k=0.5, seed=42)
    nx.draw_networkx_nodes(G, pos, node_size=200, node_color='lightblue', ax=ax)
    nx.draw_networkx_edges(
        G, pos, edge_color='gray',
        width=[d['weight'] * 2 for _, _, d in G.edges(data=True)],
        alpha=0.6, ax=ax,
    )
    nx.draw_networkx_labels(G, pos, font_size=8, ax=ax)
    ax.set_title(f'Q3 关键词关联网络图（top-{top_edges} by cosine/fp_growth）', fontsize=11)
    ax.axis('off')
    plt.tight_layout()
    out_path = os.path.join(FIGURES_DIR, 'q3_assoc_network.png')
    plt.savefig(out_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  -> {out_path}")


def main():
    print("=" * 70)
    print("Q3 · 关键词关联分析（cosine 主 + FP-Growth 辅 · BIAS_v2 修订）")
    print("=" * 70)

    out_dir = ensure_dir(os.path.join(PROCESSED_DIR, 'q3'))
    target = pd.read_pickle(os.path.join(out_dir, 'q3_target_window.pkl'))
    pool = pd.read_pickle(os.path.join(out_dir, 'q3_keyword_pool.pkl'))

    print(f"\n[输入] 16 天单元日 {target.shape[0]} 行 | 入选项池 {pool.shape[0]} 词")

    # ---- Step 1: 关键词画像 ----
    print("\n[Step 1] 构建 909 词 7 维画像")
    profiles = build_keyword_profiles(pool)
    profiles.to_pickle(os.path.join(out_dir, 'q3_keyword_profiles.pkl'))
    print(f"  画像 shape = {profiles.shape}")
    print(f"  -> q3_keyword_profiles.pkl 写入 OK")

    # ---- Step 2: cosine 相似度 ----
    print("\n[Step 2] cosine 相似度矩阵 + top-50 pairs")
    sim, profiles, rules_cos = compute_similarity(profiles)
    np.save(os.path.join(out_dir, 'q3_keyword_sim_matrix.npy'), sim)
    print(f"  相似度矩阵 shape = {sim.shape} | 非负 {(sim >= 0).sum() / sim.size * 100:.1f}%")
    print(f"  平均相似度 = {sim[sim < 1].mean():.3f} | 中位数 = {np.median(sim[sim < 1]):.3f}")
    cost_med = profiles['kw_cost'].median()
    n_pairs = ((profiles['kw_cost'].values[:, None] >= cost_med) &
               (profiles['kw_cost'].values[None, :] >= cost_med)).sum() // 2 - 909 // 2
    print(f"  高价值（kw_cost≥{cost_med:.0f}）词对 = {n_pairs} 条")

    # ---- Step 3: FP-Growth 辅助 ----
    print("\n[Step 3] FP-Growth 辅助（同单元 trivial，仅 PoC）")
    mat = pd.read_pickle(os.path.join(out_dir, 'q3_unit_keyword_matrix.pkl'))
    freq_itemsets, rules_fpg = fpgrowth_unit_only(mat, pool)
    freq_itemsets.to_pickle(os.path.join(out_dir, 'q3_freq_itemsets.pkl'))

    # ---- Step 4: 合并主输出（cosine 为主，fp_growth 为辅）----
    print("\n[Step 4] 合并关联规则 + 写入主表")
    rules = pd.concat([rules_cos, rules_fpg], ignore_index=True)
    rules_path = os.path.join(TABLES_DIR, 'q3_keyword_assoc_rules.csv')
    rules.to_csv(rules_path, index=False, encoding='utf-8-sig')
    print(f"  -> {rules_path} | {len(rules)} 条规则（cosine {len(rules_cos)} + fp_growth {len(rules_fpg)}）")

    # ---- Step 5: 关联统计 ----
    print("\n[Step 5] 关联统计")
    print(f"  cosine top-{TOP_N_RULES}:")
    print(f"    平均相似度 = {rules_cos['lift'].mean():.4f}")
    print(f"    相似度范围 = [{rules_cos['lift'].min():.3f}, {rules_cos['lift'].max():.3f}]")
    print(f"    跨单元对数 = {(rules_cos['ant_unit'] != rules_cos['con_unit']).sum()}")
    print(f"  fp_growth top-{TOP_N_RULES}:")
    print(f"    平均提升度 = {rules_fpg['lift'].mean():.4f}")

    # ---- Step 6: 图表 ----
    print("\n[Step 6] 生成图表")
    plot_similarity_heatmap(sim, profiles, top_n=30)
    plot_network(rules_cos, top_edges=50)

    # ---- Step 7: 高置信必共现规则（cosine ≥ 0.7）----
    must_cooccur = rules_cos[rules_cos['lift'] >= 0.7].copy()
    must_path = os.path.join(TABLES_DIR, 'q3_must_cooccur_rules.csv')
    must_cooccur.to_csv(must_path, index=False, encoding='utf-8-sig')
    print(f"  -> {must_path} | {len(must_cooccur)} 条高相似度（≥ 0.7）")

    print("\n" + "=" * 70)
    print(f"✅ Q3 关联分析完成 · {len(rules_cos)} cosine + {len(rules_fpg)} fp_growth")
    print("=" * 70)


if __name__ == '__main__':
    main()
