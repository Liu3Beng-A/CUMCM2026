"""Q1 备选指标体系对比：熵权法 + 模糊综合评价

本模块实现两个备选方案，作为方法论对比文档的实证支撑：

备选方案 1（熵权法）：
    - 用信息熵定权重（纯客观赋权），替代当前 CRITIC + 业务 70:30 混合
    - 输出：q1_eval_entropy_weights.csv, q1_eval_entropy_ranking.csv, q1_eval_entropy_weights_compare.png

备选方案 2（模糊综合评价法 FCE）：
    - 用梯形隶属函数计算每个方案在 8 个二级指标上的"合理性隶属度"
    - 用熵权法赋权（备选 1 输出的权重），加总得到综合隶属度
    - 输出：q1_eval_fuzzy_scores.csv, q1_eval_fuzzy_heatmap.png, q1_eval_score_compare.csv

设计原则：
    - 不修改 CRITIC / 百分位+Z-Score 已有逻辑
    - 不依赖 Prophet / Bootstrap（独立可运行）
    - 全部使用绝对路径
    - 中文 docstring
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

from src.utils import ROOT, PROCESSED_DIR, TABLES_DIR, FIGURES_DIR, ensure_dir
from src.plot_style import apply_style


# ===================== 绝对路径 =====================
PLAN_SCORES_CSV  = os.path.join(ROOT, 'results', 'tables', 'q1_plan_scores.csv')
PLAN_TOTAL_PKL   = os.path.join(PROCESSED_DIR, 'q1', 'plan_total.pkl')
PLAN_DAILY_PKL   = os.path.join(PROCESSED_DIR, 'q1', 'plan_daily.pkl')
KEYWORD_PKL      = os.path.join(PROCESSED_DIR, 'q1', 'keyword_total.pkl')
DAILY_FULL_PKL   = os.path.join(PROCESSED_DIR, 'q1', 'daily_full.pkl')

OUT_ENT_W_CSV    = os.path.join(ROOT, 'results', 'tables', 'q1_eval_entropy_weights.csv')
OUT_ENT_R_CSV    = os.path.join(ROOT, 'results', 'tables', 'q1_eval_entropy_ranking.csv')
OUT_ENT_W_PNG    = os.path.join(ROOT, 'results', 'figures', 'q1_eval_entropy_weights_compare.png')
OUT_FUZ_CSV      = os.path.join(ROOT, 'results', 'tables', 'q1_eval_fuzzy_scores.csv')
OUT_FUZ_PNG      = os.path.join(ROOT, 'results', 'figures', 'q1_eval_fuzzy_heatmap.png')
OUT_SCORE_CMP    = os.path.join(ROOT, 'results', 'tables', 'q1_eval_score_compare.csv')


# ===========================================================
# 备选方案 1：熵权法（替代 CRITIC+主观 70:30）
# ===========================================================
def entropy_weights(score_matrix: np.ndarray, dim_names: list = None) -> dict:
    """熵权法：基于信息熵的客观赋权

    步骤：
        1. 极差法归一化（将 0-100 分归一到 (0, 1] 区间）
        2. 计算各指标占比 p_ij = x_ij / Σ_i x_ij
        3. 计算各指标的信息熵 E_j = -k · Σ p_ij · ln(p_ij)，其中 k = 1/ln(n)
        4. 计算差异系数 d_j = 1 - E_j（信息熵越小，差异越大，权重越高）
        5. 计算权重 w_j = d_j / Σ d_j

    Parameters
    ----------
    score_matrix : np.ndarray
        标准化后的评分矩阵，shape = (n_plans, n_dims)
    dim_names : list of str, optional
        维度名（用于返回字典的 key），若为 None 则返回 ndarray

    Returns
    -------
    dict 或 np.ndarray
        各维度熵权（若提供 dim_names 则返回 dict）
    """
    x = np.asarray(score_matrix, dtype=float)
    n, m = x.shape
    eps = 1e-10  # 防 ln(0)

    # 1) 极差法归一化至 (0, 1]
    x_min = np.nanmin(x, axis=0)
    x_max = np.nanmax(x, axis=0)
    rng = np.where((x_max - x_min) == 0, 1.0, x_max - x_min)
    x_norm = (x - x_min) / rng
    x_norm = np.clip(x_norm, eps, 1.0)  # 防止出现 0

    # 2) 各指标占比
    col_sum = x_norm.sum(axis=0)
    p = x_norm / (col_sum + eps)
    p = np.clip(p, eps, None)  # 防 0

    # 3) 信息熵
    k = 1.0 / np.log(n)
    E = -k * np.sum(p * np.log(p), axis=0)

    # 4) 差异系数
    d = 1.0 - E

    # 5) 归一化权重
    w = d / (d.sum() + eps)

    if dim_names is not None:
        return {name: float(w[i]) for i, name in enumerate(dim_names)}
    return w


def run_entropy_scenario() -> tuple:
    """备选方案 1 入口：熵权法 vs CRITIC+主观

    输入：results/tables/q1_plan_scores.csv（5 方案 × 4 维度）
    输出：
        - results/tables/q1_eval_entropy_weights.csv：CRITIC+主观 vs 熵权法权重对比
        - results/tables/q1_eval_entropy_ranking.csv：方案排名对比（含 Spearman ρ）
        - results/figures/q1_eval_entropy_weights_compare.png：权重对比柱状图

    Returns
    -------
    (weights_df, rank_df) 两个输出表
    """
    print('\n[备选 1] 熵权法 vs CRITIC+主观 70:30 ...', flush=True)

    # 1) 读取 5 方案 × 4 维度得分矩阵
    df = pd.read_csv(PLAN_SCORES_CSV, encoding='utf-8-sig').set_index('方案ID')
    dims = list(df.columns)
    plan_ids = list(df.index)
    score_matrix = df.values
    print(f'  矩阵形状: {df.shape}，方案: {plan_ids}', flush=True)

    # 2) 计算熵权
    w_entropy = entropy_weights(score_matrix, dim_names=dims)
    print(f'  熵权: { {k: round(v, 4) for k, v in w_entropy.items()} }', flush=True)

    # 3) 当前方法（CRITIC+主观 70:30）的权重 = q1_weights.json
    # 出于模块解耦考虑，这里硬编码当前权重（与 q1_weights.json 中 mixed_weights 一致）
    w_current = {
        '设计质量与创意':   0.1994,
        '关键词管理与运用': 0.1355,
        '出价策略与预算':   0.2959,
        '投放策略与时间':   0.3692,
    }

    # 4) 权重对比表
    rows = []
    for d in dims:
        diff = w_entropy[d] - w_current[d]
        rows.append({
            '维度': d,
            'CRITIC+主观权重': round(w_current[d], 4),
            '熵权法权重':       round(w_entropy[d], 4),
            '差值(熵权-当前)':  round(diff, 4),
        })
    weights_df = pd.DataFrame(rows)
    weights_df.loc[len(weights_df)] = [
        '合计',
        round(sum(w_current.values()), 4),
        round(sum(w_entropy.values()), 4),
        round(sum(w_entropy.values()) - sum(w_current.values()), 4),
    ]
    ensure_dir(os.path.dirname(OUT_ENT_W_CSV))
    weights_df.to_csv(OUT_ENT_W_CSV, index=False, encoding='utf-8-sig')
    print(f'  [save] {OUT_ENT_W_CSV}', flush=True)

    # 5) 计算两种方法的方案综合分
    score_current = np.zeros(len(plan_ids))
    score_entropy = np.zeros(len(plan_ids))
    for i, pid in enumerate(plan_ids):
        for j, d in enumerate(dims):
            score_current[i] += w_current[d] * score_matrix[i, j]
            score_entropy[i] += w_entropy[d] * score_matrix[i, j]

    # 排名（高分为优，ascending=False）
    rank_current = pd.Series(score_current, index=plan_ids).rank(ascending=False, method='min')
    rank_entropy = pd.Series(score_entropy, index=plan_ids).rank(ascending=False, method='min')

    # 6) 排名对比表
    rank_df = pd.DataFrame({
        '方案ID':          plan_ids,
        'CRITIC+主观综合分': np.round(score_current, 2),
        '熵权法综合分':      np.round(score_entropy, 2),
        'CRITIC+主观排名':  rank_current.astype(int).values,
        '熵权法排名':        rank_entropy.astype(int).values,
    })
    rank_df['排名变化'] = rank_df['熵权法排名'] - rank_df['CRITIC+主观排名']

    # 7) Spearman ρ
    spearman_rho, spearman_p = stats.spearmanr(rank_current.values, rank_entropy.values)
    pearson_r, pearson_p = stats.pearsonr(score_current, score_entropy)

    rank_df.attrs['spearman_rho'] = round(float(spearman_rho), 4)
    rank_df.attrs['spearman_p']   = round(float(spearman_p), 4)
    rank_df.attrs['pearson_r']    = round(float(pearson_r), 4)
    rank_df.attrs['pearson_p']    = round(float(pearson_p), 4)

    rank_df.to_csv(OUT_ENT_R_CSV, index=False, encoding='utf-8-sig')
    print(f'  [save] {OUT_ENT_R_CSV}', flush=True)
    print(f'  Spearman ρ = {spearman_rho:.4f}（p={spearman_p:.4f}）', flush=True)
    print(f'  Pearson  r = {pearson_r:.4f}（p={pearson_p:.4f}）', flush=True)
    print(rank_df.to_string(index=False), flush=True)

    # 8) 权重对比柱状图
    plot_entropy_weights_compare(dims, w_current, w_entropy, OUT_ENT_W_PNG)

    return weights_df, rank_df


def plot_entropy_weights_compare(dims: list,
                                 w_current: dict,
                                 w_entropy: dict,
                                 out_path: str) -> None:
    """绘制 CRITIC+主观 vs 熵权法权重对比柱状图

    Parameters
    ----------
    dims : list
        维度名顺序。
    w_current : dict
        当前方法权重（CRITIC+主观）。
    w_entropy : dict
        熵权法权重。
    out_path : str
        图片绝对路径。
    """
    plt_mod = apply_style()
    fig, ax = plt_mod.subplots(figsize=(10, 6))

    x = np.arange(len(dims))
    width = 0.36
    cur_vals = [w_current[d] for d in dims]
    ent_vals = [w_entropy[d] for d in dims]

    bars1 = ax.bar(x - width/2, cur_vals, width, label='CRITIC+主观 70:30',
                   color='#2E86AB', edgecolor='black', linewidth=0.6)
    bars2 = ax.bar(x + width/2, ent_vals, width, label='熵权法（纯客观）',
                   color='#F18F01', edgecolor='black', linewidth=0.6)

    # 数值标签
    for b in list(bars1) + list(bars2):
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h + 0.005,
                f'{h:.3f}', ha='center', va='bottom', fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(dims, fontsize=10)
    ax.set_ylabel('权重', fontsize=11)
    ax.set_title('问题1：CRITIC+主观 70:30 vs 熵权法（备选方案1）权重对比',
                 fontsize=13, fontweight='bold')
    ax.set_ylim(0, max(max(cur_vals), max(ent_vals)) * 1.18)
    ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
    ax.grid(True, axis='y', alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    plt_mod.close(fig)
    print(f'  [fig] saved -> {out_path}', flush=True)


# ===========================================================
# 备选方案 2：模糊综合评价法（替代百分位+Z-Score）
# ===========================================================
def fuzzy_evaluate(value, lower, target_low, target_high, upper):
    """梯形隶属函数：计算某指标值对"合理"的隶属度

    隶属度 = 1 表示完全合理（值落在 [target_low, target_high] 区间内）；
    隶属度 = 0 表示完全不合理（值落在 [lower, upper] 之外）；
    隶属度 ∈ (0, 1) 表示边界过渡区。

    Parameters
    ----------
    value : float
        实际指标值。
    lower : float
        偏低阈值（通常取 P10）。
    target_low : float
        偏低/合理分界（通常取 P25）。
    target_high : float
        合理/偏高分界（通常取 P75）。
    upper : float
        偏高阈值（通常取 P90）。

    Returns
    -------
    float
        隶属度 ∈ [0, 1]。
    """
    # 区间端点顺序校验（防御性）
    if upper <= target_high or target_high <= target_low or target_low <= lower:
        # 退化情况：当作区间评分
        if lower <= value <= upper:
            return 1.0
        return 0.0

    if value < lower or value > upper:
        return 0.0
    if value < target_low:
        # 偏低过渡区 [lower, target_low]
        return (value - lower) / (target_low - lower)
    if value > target_high:
        # 偏高过渡区 [target_high, upper]
        return (upper - value) / (upper - target_high)
    # 合理区间 [target_low, target_high]
    return 1.0


def build_plan_indicator_matrix() -> pd.DataFrame:
    """构建每个方案在 8 个二级指标上的取值矩阵

    8 个指标（覆盖方案全链路）：
        1. CTR              越大约好
        2. CPC              越小越好
        3. 上方位占比       适中（约 0.3~0.6）
        4. 渗透率           适中（约 0.5~0.8）
        5. 月度预算CV       越小越好（< 0.5 健康）
        6. 关键词有效率     越大约好
        7. 平均跳出率       越小越好
        8. CPC变异系数      越小越好（稳定性）

    Returns
    -------
    pd.DataFrame
        index=方案ID，列=8 个指标名
    """
    plan_daily   = pd.read_pickle(PLAN_DAILY_PKL)
    keyword_total = pd.read_pickle(KEYWORD_PKL)
    daily_full   = pd.read_pickle(DAILY_FULL_PKL)

    # 方案×月聚合，用于月度 CV
    plan_daily = plan_daily.copy()
    plan_daily['月份'] = pd.to_datetime(plan_daily['日期']).dt.to_period('M')

    # ---- 方案级 CTR / CPC ----
    agg = plan_daily.groupby('方案ID').agg(
        total_imp=('展现量', 'sum'),
        total_clk=('点击量', 'sum'),
        total_cost=('消费额', 'sum'),
        total_top_imp=('上方位展现量', 'sum'),
        total_top_cost=('上方位消费额', 'sum'),
    )
    agg['CTR']        = agg['total_clk'] / agg['total_imp']
    agg['CPC']        = agg['total_cost'] / agg['total_clk']
    agg['上方位占比'] = agg['total_top_imp'] / agg['total_imp']
    agg['渗透率']     = agg['total_top_cost'] / agg['total_cost']

    # ---- CPC 变异系数（稳定性）----
    def cpc_cv(grp):
        cpc = grp['CPC'].dropna()
        cpc = cpc[cpc > 0]
        return cpc.std() / cpc.mean() if cpc.mean() > 0 else np.nan
    agg['CPC变异系数'] = plan_daily.groupby('方案ID').apply(cpc_cv, include_groups=False)

    # ---- 月度预算 CV ----
    monthly = plan_daily.groupby(['方案ID', '月份'])['消费额'].sum().reset_index()
    def mcv(grp):
        m = grp['消费额'].mean()
        return grp['消费额'].std() / m if m > 0 else np.nan
    agg['月度预算CV'] = monthly.groupby('方案ID').apply(mcv, include_groups=False)

    # ---- 关键词级指标 ----
    kw = keyword_total.copy()
    # 有效率（按方案聚合：当前方案"有消费"的关键词数 / 该方案总关键词数）
    kw_eff = kw.groupby('方案ID').agg(
        关键词有效率=('有消费', 'mean'),
        平均跳出率=('跳出率', 'mean'),
    )

    # ---- 合并 ----
    metric_df = agg[['CTR', 'CPC', '上方位占比', '渗透率', 'CPC变异系数', '月度预算CV']].join(kw_eff)
    metric_df = metric_df.reset_index()
    print(f'  指标矩阵形状: {metric_df.shape}', flush=True)
    print(metric_df.to_string(index=False), flush=True)
    return metric_df


def compute_thresholds(metric_df: pd.DataFrame, indicator_cols: list) -> dict:
    """为每个指标计算梯形隶属函数的 4 个阈值

    设计要点（针对 5 个方案的样本量较小的场景）：
        - target_low / target_high：用 5 个方案的"合理区间"作为核心满分区间，
          这里取 P33/P67（即 5 个方案中 1~3 名为合理区）；
        - lower / upper：用 min / max 作阈值，确保所有样本的隶属度至少进入
          过渡区（而非全部为 0 或 1），增强可比性；
        - 这种"放宽边界"的设计保留了梯形函数的语义，又缓解了样本过少
          导致隶属度退化为二值的问题。

    Parameters
    ----------
    metric_df : pd.DataFrame
        方案×指标矩阵。
    indicator_cols : list
        指标列名。

    Returns
    -------
    dict
        {指标名: (lower, target_low, target_high, upper)}
    """
    thresholds = {}
    for col in indicator_cols:
        s = metric_df[col].dropna()
        if len(s) == 0:
            thresholds[col] = (0.0, 0.0, 1.0, 1.0)
            continue
        # 5 个方案场景：用 P33/P67 作为合理区间（满分区）
        # 边界：min/max（确保所有样本至少进入过渡区）
        v_min = float(s.min())
        v_max = float(s.max())
        v_p33 = float(s.quantile(0.33))
        v_p67 = float(s.quantile(0.67))

        # 防御性退化处理
        if v_p67 <= v_p33:
            v_mid = (v_min + v_max) / 2.0
            v_p33, v_p67 = v_min, v_max if v_min == v_max else (v_mid - 0.5, v_mid + 0.5)
        # 边界微调
        eps_l = (v_p33 - v_min) * 0.05 + 1e-9
        eps_u = (v_max - v_p67) * 0.05 + 1e-9
        lower = max(v_min - eps_l, v_min)        # 用实际 min
        upper = min(v_max + eps_u, v_max)        # 用实际 max
        thresholds[col] = (lower, v_p33, v_p67, upper)
    return thresholds


# 指标方向：True → 越大越好；False → 越小越好
INDICATOR_DIRECTION = {
    'CTR':           True,    # 越大越好
    'CPC':           False,   # 越小越好
    '上方位占比':    True,    # 适中：取越大越好的形式（数据本身反映竞价竞争力）
    '渗透率':        True,    # 适中偏大
    'CPC变异系数':   False,   # 越小越稳定
    '月度预算CV':    False,   # 越小越均匀
    '关键词有效率':  True,    # 越大越好
    '平均跳出率':    False,   # 越小越好
}


def compute_membership(metric_df: pd.DataFrame,
                       indicator_cols: list,
                       thresholds: dict) -> pd.DataFrame:
    """计算每个方案在每个指标上的模糊隶属度

    Parameters
    ----------
    metric_df : pd.DataFrame
        方案×指标矩阵。
    indicator_cols : list
        指标列名。
    thresholds : dict
        {指标名: (P10, P25, P75, P90)}。

    Returns
    -------
    pd.DataFrame
        index=方案ID，列=各指标的隶属度（0-1）。
    """
    rows = []
    for _, r in metric_df.iterrows():
        row = {'方案ID': r['方案ID']}
        for col in indicator_cols:
            v = r[col]
            lo, tlo, thi, up = thresholds[col]
            mu = fuzzy_evaluate(v, lo, tlo, thi, up)
            row[col] = round(float(mu), 4)
        rows.append(row)
    return pd.DataFrame(rows).set_index('方案ID')


def run_fuzzy_scenario(entropy_weights_dict: dict = None) -> tuple:
    """备选方案 2 入口：模糊综合评价 vs 百分位+Z-Score

    输入：
        - plan_daily.pkl / keyword_total.pkl / daily_full.pkl
        - 熵权法权重（来自备选 1，函数参数；为 None 时自动重算）
    输出：
        - results/tables/q1_eval_fuzzy_scores.csv：方案×指标隶属度表 + 综合隶属度
        - results/figures/q1_eval_fuzzy_heatmap.png：隶属度热力图
        - results/tables/q1_eval_score_compare.csv：FCE vs 百分位+Z-Score 对比

    Returns
    -------
    (fuzzy_df, score_cmp_df) 两个输出表
    """
    print('\n[备选 2] 模糊综合评价法（FCE）vs 百分位+Z-Score ...', flush=True)

    indicator_cols = list(INDICATOR_DIRECTION.keys())

    # 1) 构建方案×指标矩阵
    metric_df = build_plan_indicator_matrix()

    # 2) 计算 4 阈值
    thresholds = compute_thresholds(metric_df, indicator_cols)
    print('\n  各指标阈值 (P10/P25/P75/P90):', flush=True)
    for col, thr in thresholds.items():
        print(f'    {col}: {tuple(round(x, 4) for x in thr)}', flush=True)

    # 3) 计算隶属度矩阵
    mu_df = compute_membership(metric_df, indicator_cols, thresholds)
    print('\n  隶属度矩阵:', flush=True)
    print(mu_df.round(4).to_string(), flush=True)

    # 4) 熵权法赋权 → 综合隶属度
    if entropy_weights_dict is None:
        # 从备选 1 的 5 方案×4 维度矩阵重算
        df_plan = pd.read_csv(PLAN_SCORES_CSV, encoding='utf-8-sig').set_index('方案ID')
        entropy_weights_dict = entropy_weights(df_plan.values,
                                                dim_names=list(df_plan.columns))
    # 将 4 维熵权"摊派"到 8 个指标上：按 1 级维度的业务先验分配
    # 这里采用启发式：4 个一级维度 → 8 个二级指标
    #   设计质量 → CTR, 上方位占比
    #   关键词   → 关键词有效率, 平均跳出率
    #   出价     → CPC, 渗透率, CPC变异系数
    #   投放     → 月度预算CV
    dim_to_indicators = {
        '设计质量与创意':    ['CTR', '上方位占比'],
        '关键词管理与运用':  ['关键词有效率', '平均跳出率'],
        '出价策略与预算':    ['CPC', '渗透率', 'CPC变异系数'],
        '投放策略与时间':    ['月度预算CV'],
    }
    indicator_weights = {}
    for dim, inds in dim_to_indicators.items():
        w_dim = entropy_weights_dict.get(dim, 0.25)
        indicator_weights.update({i: w_dim / len(inds) for i in inds})

    # 归一化
    total_w = sum(indicator_weights.values())
    indicator_weights = {k: v / total_w for k, v in indicator_weights.items()}
    print('\n  二级指标权重（熵权法摊派）:', flush=True)
    for k, v in indicator_weights.items():
        print(f'    {k}: {round(v, 4)}', flush=True)

    # 5) 加权综合隶属度
    mu_df = mu_df.copy()
    mu_df['综合隶属度'] = sum(mu_df[c] * w for c, w in indicator_weights.items())
    # 0-100 综合分
    mu_df['FCE综合分'] = (mu_df['综合隶属度'] * 100).round(2)

    # 6) 保存隶属度表（含权重信息）
    out_df = mu_df.reset_index()
    out_df.attrs['indicator_weights'] = indicator_weights
    out_df.attrs['thresholds'] = thresholds
    ensure_dir(os.path.dirname(OUT_FUZ_CSV))
    out_df.to_csv(OUT_FUZ_CSV, index=False, encoding='utf-8-sig')
    print(f'\n  [save] {OUT_FUZ_CSV}', flush=True)

    # 7) 隶属度热力图
    plot_fuzzy_heatmap(mu_df[indicator_cols + ['综合隶属度']], indicator_weights,
                       OUT_FUZ_PNG)

    # 8) 与当前百分位+Z-Score 评分对比
    # 当前评分矩阵 = q1_plan_scores.csv（5×4 维度综合分）
    df_plan = pd.read_csv(PLAN_SCORES_CSV, encoding='utf-8-sig').set_index('方案ID')
    # 百分位+Z-Score 综合分 = 各方案 4 维度的均值（与 q1_baseline 等权对比口径一致）
    current_score = df_plan.mean(axis=1)

    # 按方案 ID 对齐 FCE 综合分（避免顺序不一致）
    fce_score = mu_df['FCE综合分'].reindex(current_score.index)

    score_cmp_df = pd.DataFrame({
        '方案ID':     current_score.index,
        '百分位+Z-Score综合分': current_score.round(2).values,
        'FCE综合分':           fce_score.round(2).values,
    })
    score_cmp_df['绝对差异'] = (score_cmp_df['FCE综合分'] - score_cmp_df['百分位+Z-Score综合分']).round(2)
    score_cmp_df['相对差异(%)'] = (
        score_cmp_df['绝对差异'] / score_cmp_df['百分位+Z-Score综合分'].replace(0, np.nan) * 100
    ).round(2)
    score_cmp_df['百分位+Z排名'] = score_cmp_df['百分位+Z-Score综合分'].rank(ascending=False, method='min').astype(int)
    score_cmp_df['FCE排名']      = score_cmp_df['FCE综合分'].rank(ascending=False, method='min').astype(int)
    score_cmp_df['排名变化']     = score_cmp_df['FCE排名'] - score_cmp_df['百分位+Z排名']

    # Spearman ρ
    sp_rho, sp_p = stats.spearmanr(
        score_cmp_df['百分位+Z排名'].values,
        score_cmp_df['FCE排名'].values,
    )
    score_cmp_df.attrs['spearman_rho'] = round(float(sp_rho), 4)
    score_cmp_df.attrs['spearman_p']   = round(float(sp_p), 4)

    score_cmp_df.to_csv(OUT_SCORE_CMP, index=False, encoding='utf-8-sig')
    print(f'\n  [save] {OUT_SCORE_CMP}', flush=True)
    print(f'  Spearman ρ (排名) = {sp_rho:.4f}（p={sp_p:.4f}）', flush=True)
    print(score_cmp_df.to_string(index=False), flush=True)

    return out_df, score_cmp_df


def plot_fuzzy_heatmap(mu_df: pd.DataFrame, weights: dict, out_path: str) -> None:
    """绘制模糊综合评价隶属度热力图

    Parameters
    ----------
    mu_df : pd.DataFrame
        方案×指标隶属度矩阵（含"综合隶属度"列）。
    weights : dict
        各二级指标的权重（用于顶部权重条）。
    out_path : str
        图片绝对路径。
    """
    plt_mod = apply_style()
    fig, (ax1, ax2) = plt_mod.subplots(
        2, 1, figsize=(11, 8),
        gridspec_kw={'height_ratios': [1, 5]},
    )

    # ---- 上：指标权重条 ----
    indicator_cols = [c for c in mu_df.columns if c != '综合隶属度']
    w_vals = [weights.get(c, 0) for c in indicator_cols]
    x = np.arange(len(indicator_cols))
    bars = ax1.bar(x, w_vals, color='#06A77D', edgecolor='black', linewidth=0.6)
    for b, w in zip(bars, w_vals):
        ax1.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.005,
                 f'{w:.3f}', ha='center', va='bottom', fontsize=8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(indicator_cols, rotation=20, ha='right', fontsize=9)
    ax1.set_ylabel('权重（熵权法摊派）', fontsize=10)
    ax1.set_title('问题1：模糊综合评价（FCE）—— 隶属度热力图',
                   fontsize=13, fontweight='bold')
    ax1.set_ylim(0, max(w_vals) * 1.25 if max(w_vals) > 0 else 1)
    ax1.grid(True, axis='y', alpha=0.3)

    # ---- 下：热力图 ----
    heat_data = mu_df[indicator_cols].values
    im = ax2.imshow(heat_data, aspect='auto', cmap='RdYlGn', vmin=0, vmax=1)
    ax2.set_xticks(np.arange(len(indicator_cols)))
    ax2.set_xticklabels(indicator_cols, rotation=20, ha='right', fontsize=9)
    ax2.set_yticks(np.arange(len(mu_df.index)))
    ax2.set_yticklabels([str(int(i)) for i in mu_df.index], fontsize=10)

    # 单元格内数字
    for i in range(heat_data.shape[0]):
        for j in range(heat_data.shape[1]):
            v = heat_data[i, j]
            txt_color = 'white' if v < 0.5 else 'black'
            ax2.text(j, i, f'{v:.2f}', ha='center', va='center',
                     color=txt_color, fontsize=9, fontweight='bold')

    # 右侧 colorbar
    cbar = fig.colorbar(im, ax=ax2, fraction=0.025, pad=0.02)
    cbar.set_label('隶属度', fontsize=10)

    # 右侧加一列综合隶属度
    overall = mu_df['综合隶属度'].values
    ax2.scatter([len(indicator_cols) - 0.5] * len(overall),
                np.arange(len(overall)),
                s=overall * 250 + 30,
                c=overall, cmap='RdYlGn', vmin=0, vmax=1,
                edgecolors='black', linewidths=0.8, marker='o')
    for i, v in enumerate(overall):
        ax2.text(len(indicator_cols) - 0.5, i, f'{v:.2f}',
                 ha='center', va='center', fontsize=8, color='black')

    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    plt_mod.close(fig)
    print(f'  [fig] saved -> {out_path}', flush=True)


# ===========================================================
# 主入口
# ===========================================================
def main():
    """主流程：跑两个备选方案，输出全部 6 个文件"""
    print('=' * 60, flush=True)
    print('  问题1：备选指标体系对比', flush=True)
    print('  备选方案 1：熵权法（替代 CRITIC+主观 70:30）', flush=True)
    print('  备选方案 2：模糊综合评价（替代百分位+Z-Score）', flush=True)
    print('=' * 60, flush=True)

    # ---- 备选 1：熵权法 ----
    weights_df, rank_df = run_entropy_scenario()
    sp_rho_1 = rank_df.attrs['spearman_rho']
    pr_r_1   = rank_df.attrs['pearson_r']

    # ---- 备选 2：模糊综合评价 ----
    fuzzy_df, score_cmp_df = run_fuzzy_scenario()
    sp_rho_2 = score_cmp_df.attrs['spearman_rho']

    # ---- 验证清单 ----
    print('\n' + '=' * 60, flush=True)
    print('  验证清单', flush=True)
    print('=' * 60, flush=True)

    # 1) 熵权法权重总和
    entropy_sum = sum([w for k, w in {
        '设计质量与创意':   weights_df.loc[weights_df['维度'] == '设计质量与创意', '熵权法权重'].iloc[0],
        '关键词管理与运用': weights_df.loc[weights_df['维度'] == '关键词管理与运用', '熵权法权重'].iloc[0],
        '出价策略与预算':   weights_df.loc[weights_df['维度'] == '出价策略与预算', '熵权法权重'].iloc[0],
        '投放策略与时间':   weights_df.loc[weights_df['维度'] == '投放策略与时间', '熵权法权重'].iloc[0],
    }.items()])
    sum_check = abs(entropy_sum - 1.0) < 0.001
    print(f'  [1] 熵权法权重总和 = {entropy_sum:.4f}  {"✓" if sum_check else "✗"}（容差 0.001）', flush=True)

    # 2) 模糊隶属度 [0, 1]
    mu_only = fuzzy_df.drop(columns=['方案ID'], errors='ignore')
    membership_in_range = (
        (mu_only.drop(columns=['FCE综合分'], errors='ignore').min().min() >= 0) &
        (mu_only.drop(columns=['FCE综合分'], errors='ignore').max().max() <= 1)
    )
    print(f'  [2] 模糊隶属度 ∈ [0, 1]  {"✓" if membership_in_range else "✗"}', flush=True)

    # 3) 所有 6 个输出文件存在
    files = [
        OUT_ENT_W_CSV, OUT_ENT_R_CSV, OUT_ENT_W_PNG,
        OUT_FUZ_CSV,   OUT_FUZ_PNG,   OUT_SCORE_CMP,
    ]
    print(f'  [3] 输出文件检查：', flush=True)
    for f in files:
        exists = os.path.exists(f)
        print(f'      {"✓" if exists else "✗"} {f}', flush=True)

    # 4) 排名对比 Spearman ρ
    print(f'  [4] Spearman ρ（备选1 当前 vs 熵权）= {sp_rho_1:.4f}', flush=True)
    print(f'      Spearman ρ（备选2 百分位+Z vs FCE）= {sp_rho_2:.4f}', flush=True)

    # ---- 输出文件路径汇总 ----
    print('\n' + '=' * 60, flush=True)
    print('  输出文件清单（绝对路径）', flush=True)
    print('=' * 60, flush=True)
    print(f'  1. {OUT_ENT_W_CSV}', flush=True)
    print(f'  2. {OUT_ENT_R_CSV}', flush=True)
    print(f'  3. {OUT_ENT_W_PNG}', flush=True)
    print(f'  4. {OUT_FUZ_CSV}', flush=True)
    print(f'  5. {OUT_FUZ_PNG}', flush=True)
    print(f'  6. {OUT_SCORE_CMP}', flush=True)
    print('=' * 60, flush=True)
    print('  [done] 备选指标体系对比完成', flush=True)


if __name__ == '__main__':
    main()
