"""Q1 Baseline 方法对比（改-8）

目的
----
对同一 5 方案 × 4 维度的得分矩阵，使用三套独立客观赋权/排序方法
（等权平均、熵权法、等权 TOPSIS）计算综合得分与方案排名，
与当前 CRITIC 70:30 混合赋权的结果进行对比，验证评分体系的稳健性。

输入
----
results/tables/q1_plan_scores.csv ：5 方案 × 4 维度的得分矩阵
results/tables/q1_score.json      ：当前 CRITIC 综合得分（overall_score）

输出
----
results/tables/q1_baseline_comparison.csv
    每行 = 一个方案，列：方案ID, 当前CRITIC综合分, 等权综合分,
        熵权综合分, TOPSIS综合分, 4 种方法的排名
results/tables/q1_baseline_corr.csv
    当前方法与 3 个 baseline 的 Pearson/Spearman 相关系数
results/figures/q1_baseline_rank_scatter.png
    4 种方法排名一致性散点图

方法
----
1) 等权平均：四维度简单算术平均
2) 熵权法：先 0-1 归一化 → 计算各维度的信息熵 → 差异系数 → 归一化得权重 → 加权求和
3) 等权 TOPSIS：向量归一化 → 等权加权 → 欧氏距离 → 接近度 × 100
"""
import sys, os, io
import json

# UTF-8 stdout（兼容 Windows GBK）
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

from src.utils import TABLES_DIR, FIGURES_DIR, ensure_dir
from src.plot_style import apply_style, save_fig


# ===== 绝对路径 =====
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_SCORES_CSV = os.path.join(ROOT, 'results', 'tables', 'q1_plan_scores.csv')
SCORE_JSON      = os.path.join(ROOT, 'results', 'tables', 'q1_score.json')
OUT_CMP_CSV     = os.path.join(ROOT, 'results', 'tables', 'q1_baseline_comparison.csv')
OUT_CORR_CSV    = os.path.join(ROOT, 'results', 'tables', 'q1_baseline_corr.csv')
OUT_FIG         = os.path.join(ROOT, 'results', 'figures', 'q1_baseline_rank_scatter.png')


# =====================
# 三套 Baseline 方法
# =====================
def baseline_equal_weight(df: pd.DataFrame) -> pd.Series:
    """Baseline 1：等权平均。

    直接对每个方案的 4 维度得分取算术平均，得到综合分（0-100）。
    反映"完全无偏好"的基准排序。

    Parameters
    ----------
    df : pd.DataFrame
        方案 × 维度得分矩阵。

    Returns
    -------
    pd.Series
        每个方案的综合分（索引与 df 一致）。
    """
    return df.mean(axis=1)


def baseline_entropy_weight(df: pd.DataFrame) -> tuple[pd.Series, dict]:
    """Baseline 2：熵权法（Entropy Weight Method）。

    步骤：
        1. Min-Max 归一化（这里得分已在 0-100，直接 / 100）；
        2. 计算占比 p_ij = x_ij / Σ_i x_ij；
        3. 信息熵 E_j = -k · Σ p_ij · ln(p_ij)，其中 k = 1/ln(n)；
        4. 差异系数 d_j = 1 - E_j；
        5. 权重 w_j = d_j / Σ d_j；
        6. 综合分 = Σ w_j · x_ij。

    Parameters
    ----------
    df : pd.DataFrame
        方案 × 维度得分矩阵。

    Returns
    -------
    overall : pd.Series
        每个方案的加权综合分。
    weights : dict
        各维度的熵权。
    """
    x = df.values.astype(float)
    n = x.shape[0]
    eps = 1e-10  # 防止 ln(0)

    # 1) 0-1 归一化
    x_norm = x / 100.0

    # 2) 占比
    col_sum = x_norm.sum(axis=0)
    p = x_norm / (col_sum + eps)
    p = np.clip(p, eps, None)  # 防 0

    # 3) 信息熵
    k = 1.0 / np.log(n)
    E = -k * np.sum(p * np.log(p), axis=0)

    # 4) 差异系数
    d = 1.0 - E

    # 5) 归一化为权重
    w = d / d.sum()
    weights = {col: float(w[i]) for i, col in enumerate(df.columns)}

    # 6) 加权求和
    overall = (x_norm * w).sum(axis=1) * 100.0
    return pd.Series(overall, index=df.index), weights


def baseline_topsis(df: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """Baseline 3：等权 TOPSIS。

    步骤：
        1. 向量归一化 r_ij = x_ij / sqrt(Σ_i x_ij²)；
        2. 等权加权（每维 1/4）：v_ij = 0.25 · r_ij；
        3. 正/负理想解 A+ / A- = 每列最大 / 最小；
        4. 欧氏距离 D+ / D-；
        5. 接近度 C = D- / (D+ + D-)；
        6. 综合分 = C × 100。

    Parameters
    ----------
    df : pd.DataFrame
        方案 × 维度得分矩阵。

    Returns
    -------
    overall : pd.Series
        每个方案的 TOPSIS 接近度（×100）。
    raw : pd.DataFrame
        加权后的中间矩阵，便于调试。
    """
    x = df.values.astype(float)
    m, n = x.shape
    eps = 1e-10

    # 1) 向量归一化
    norm = np.sqrt((x ** 2).sum(axis=0))
    norm = np.where(norm == 0, eps, norm)
    r = x / norm

    # 2) 等权加权
    w = np.full(n, 1.0 / n)
    v = r * w

    # 3) 正/负理想解
    a_pos = v.max(axis=0)
    a_neg = v.min(axis=0)

    # 4) 距离
    d_pos = np.sqrt(((v - a_pos) ** 2).sum(axis=1))
    d_neg = np.sqrt(((v - a_neg) ** 2).sum(axis=1))

    # 5) 接近度
    c = d_neg / (d_pos + d_neg + eps)
    overall = pd.Series(c * 100.0, index=df.index)

    raw = pd.DataFrame(v, index=df.index, columns=df.columns)
    return overall, raw


# =====================
# 相关系数与排名
# =====================
def compute_correlations(critic_scores: np.ndarray,
                         base_scores: dict) -> pd.DataFrame:
    """计算当前 CRITIC 综合分与各 baseline 的 Pearson / Spearman 系数。

    Parameters
    ----------
    critic_scores : np.ndarray
        当前方法的综合分向量。
    base_scores : dict
        {baseline 名: 综合分向量}。

    Returns
    -------
    pd.DataFrame
        每行一个 baseline，含 Pearson、Spearman 两列。
    """
    rows = []
    for name, s in base_scores.items():
        pearson, _ = stats.pearsonr(critic_scores, s)
        spearman, _ = stats.spearmanr(critic_scores, s)
        rows.append({
            'Baseline': name,
            'Pearson': round(float(pearson), 4),
            'Spearman': round(float(spearman), 4),
        })
    return pd.DataFrame(rows)


def plot_rank_scatter(rank_df: pd.DataFrame, plan_ids, out_path: str):
    """绘制 4 种方法排名一致性散点图。

    X 轴：当前 CRITIC 排名（1 = 最好）
    Y 轴：baseline 排名
    对角线 y=x 表示完全一致；偏离越大表示排名差异越大。

    Parameters
    ----------
    rank_df : pd.DataFrame
        含 4 列排名（当前/等权/熵权/TOPSIS）+ 方案ID。
    plan_ids : array-like
        方案ID顺序。
    out_path : str
        图片保存路径。
    """
    plt = apply_style()
    fig, ax = plt.subplots(figsize=(9, 7))

    baselines = {
        # key in plot → (column name in rank_df, color, marker)
        '等权平均': ('等权排名',   '#2E86AB', 'o'),
        '熵权法':   ('熵权排名',   '#A23B72', 's'),
        'TOPSIS':  ('TOPSIS排名', '#F18F01', '^'),
    }
    critic_rank = rank_df['当前CRITIC排名'].values

    for name, (col, color, marker) in baselines.items():
        y = rank_df[col].values
        ax.scatter(critic_rank, y, c=color, marker=marker,
                   s=130, edgecolors='black', linewidths=0.8,
                   alpha=0.85, label=name, zorder=3)
        # 在每个点旁标方案 ID
        for i, pid in enumerate(plan_ids):
            ax.annotate(str(pid),
                        (critic_rank[i], y[i]),
                        textcoords='offset points',
                        xytext=(8, 6), fontsize=8, color='#333333')

    # 对角线
    lim_min, lim_max = 0.5, 5.5
    ax.plot([lim_min, lim_max], [lim_min, lim_max],
            color='red', linestyle='--', alpha=0.5, linewidth=1.2,
            label='y = x（完全一致）')

    ax.set_xlim(lim_min, lim_max)
    ax.set_ylim(lim_max, lim_min)  # 反转：排名 1 在顶部
    ax.set_xticks(range(1, 6))
    ax.set_yticks(range(1, 6))
    ax.set_xlabel('当前 CRITIC 排名（1 = 最优）', fontsize=11)
    ax.set_ylabel('Baseline 排名（1 = 最优）', fontsize=11)
    ax.set_title('问题1：4 种评分方法的方案排名一致性', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=10, framealpha=0.9)

    fig.tight_layout()
    # 直接保存到绝对路径（绕过 save_fig 的默认目录）
    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'[fig] saved -> {out_path}', flush=True)


# =====================
# 主入口
# =====================
def run_baseline_comparison():
    """主流程：加载数据 → 三套 baseline → 汇总 → 画图 → 输出。"""
    print('[baseline] 加载得分矩阵...', flush=True)
    df = pd.read_csv(PLAN_SCORES_CSV, encoding='utf-8-sig')
    df = df.set_index('方案ID')
    plan_ids = df.index.tolist()
    print(f'  矩阵形状: {df.shape}, 方案: {plan_ids}', flush=True)

    print('[baseline] 读取当前 CRITIC 综合分...', flush=True)
    with open(SCORE_JSON, 'r', encoding='utf-8') as f:
        score_data = json.load(f)
    # 从 plan_scores 重建综合分（用混合权重再算一次，确保口径一致）
    # 这里直接读取每个方案的混合加权结果 = overall_score 的分解
    # 为简洁，从混合权重与维度分重算
    dims = ['设计质量与创意', '关键词管理与运用', '出价策略与预算', '投放策略与时间']
    mixed_w = {
        '设计质量与创意':   0.1994,
        '关键词管理与运用': 0.1355,
        '出价策略与预算':   0.2959,
        '投放策略与时间':   0.3692,
    }
    critic_scores = pd.Series(index=df.index, dtype=float)
    for pid in plan_ids:
        s = 0.0
        for d in dims:
            s += mixed_w[d] * df.loc[pid, d]
        critic_scores.loc[pid] = s
    print(f'  当前 CRITIC 综合分（重算）: {critic_scores.round(2).tolist()}', flush=True)

    # --- Baseline 1：等权 ---
    print('[baseline] 1/3 等权平均...', flush=True)
    s_equal = baseline_equal_weight(df)
    print(f'  等权综合分: {s_equal.round(2).tolist()}', flush=True)

    # --- Baseline 2：熵权 ---
    print('[baseline] 2/3 熵权法...', flush=True)
    s_entropy, w_entropy = baseline_entropy_weight(df)
    print(f'  熵权综合分: {s_entropy.round(2).tolist()}', flush=True)
    print(f'  熵权权重: { {k: round(v, 4) for k, v in w_entropy.items()} }', flush=True)

    # --- Baseline 3：TOPSIS ---
    print('[baseline] 3/3 等权 TOPSIS...', flush=True)
    s_topsis, _ = baseline_topsis(df)
    print(f'  TOPSIS 综合分: {s_topsis.round(2).tolist()}', flush=True)

    # ===== 汇总表 =====
    cmp_df = pd.DataFrame({
        '方案ID': plan_ids,
        '当前CRITIC综合分': critic_scores.round(2).values,
        '等权综合分':       s_equal.round(2).values,
        '熵权综合分':       s_entropy.round(2).values,
        'TOPSIS综合分':     s_topsis.round(2).values,
    })
    # 排名（分数越高，排名越靠前，ascending=False）
    cmp_df['当前CRITIC排名'] = cmp_df['当前CRITIC综合分'].rank(ascending=False, method='min').astype(int)
    cmp_df['等权排名']       = cmp_df['等权综合分'].rank(ascending=False, method='min').astype(int)
    cmp_df['熵权排名']       = cmp_df['熵权综合分'].rank(ascending=False, method='min').astype(int)
    cmp_df['TOPSIS排名']     = cmp_df['TOPSIS综合分'].rank(ascending=False, method='min').astype(int)

    ensure_dir(os.path.dirname(OUT_CMP_CSV))
    cmp_df.to_csv(OUT_CMP_CSV, index=False, encoding='utf-8-sig')
    print(f'\n[save] {OUT_CMP_CSV}', flush=True)
    print(cmp_df.to_string(index=False), flush=True)

    # ===== 相关系数 =====
    base_score_dict = {
        '等权平均': s_equal.values,
        '熵权法':   s_entropy.values,
        'TOPSIS':  s_topsis.values,
    }
    corr_df = compute_correlations(critic_scores.values, base_score_dict)
    corr_df.to_csv(OUT_CORR_CSV, index=False, encoding='utf-8-sig')
    print(f'\n[save] {OUT_CORR_CSV}', flush=True)
    print(corr_df.to_string(index=False), flush=True)

    # ===== 排名散点图 =====
    rank_df = cmp_df[['方案ID', '当前CRITIC排名', '等权排名', '熵权排名', 'TOPSIS排名']]
    ensure_dir(os.path.dirname(OUT_FIG))
    plot_rank_scatter(rank_df, plan_ids, OUT_FIG)

    # ===== 检查硬指标 =====
    min_spearman = corr_df['Spearman'].min()
    min_pearson = corr_df['Pearson'].min()
    flag = '✓' if (min_spearman >= 0.7 and min_pearson >= 0.7) else '✗'
    print(f'\n[check] {flag} Pearson 最小={min_pearson:.4f}, '
          f'Spearman 最小={min_spearman:.4f} (阈值 0.7)', flush=True)

    # ===== 输出最终行 =====
    pearson_equal = corr_df.loc[corr_df['Baseline'] == '等权平均', 'Pearson'].iloc[0]
    pearson_entropy = corr_df.loc[corr_df['Baseline'] == '熵权法', 'Pearson'].iloc[0]
    pearson_topsis = corr_df.loc[corr_df['Baseline'] == 'TOPSIS', 'Pearson'].iloc[0]
    print(
        f'[done] baseline_comparison 完成：当前方法与等权 Pearson={pearson_equal:.2f}，'
        f'与熵权 {pearson_entropy:.2f}，与 TOPSIS {pearson_topsis:.2f}',
        flush=True,
    )

    return cmp_df, corr_df


if __name__ == '__main__':
    run_baseline_comparison()
