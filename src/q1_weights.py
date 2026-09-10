"""Q1 CRITIC + 业务混合赋权（改-1）

目的：
- 替换原版"拍脑袋"的一级维度权重（20/30/25/25）
- CRITIC 法基于"5 方案 × 4 维度"得分矩阵
- 混合权重：70% CRITIC（数据驱动） + 30% 业务经验权重

CRITIC 原理：
- 对比强度：标准差 σ_j（越大越好）
- 冲突性：  Σ(1 - r_jk)（与其他指标相关性越小越好）
- 权重：    w_j = σ_j × conflict_j / Σ

优点：
- 数学严谨，考虑变异性+冲突性
- 5 个方案的样本下仍可计算（仅作为参考权重）
- 70:30 混合保留业务可解释性

输出：
- q1_weights.json：CRITIC、业务、混合三套权重 + 对比表
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import numpy as np
import pandas as pd

from src.utils import TABLES_DIR, ensure_dir


# ============= 业务经验权重（拍脑袋的先验） =============
SUBJECTIVE_WEIGHTS = {
    '设计质量与创意':   0.20,
    '关键词管理与运用': 0.30,
    '出价策略与预算':   0.25,
    '投放策略与时间':   0.25,
}

# ============= 混合比例 =============
MIX_RATIO_CRITIC = 0.70     # CRITIC 客观权重占比
MIX_RATIO_SUBJ   = 0.30     # 业务经验权重占比


def critic_weights(score_matrix: np.ndarray) -> np.ndarray:
    """CRITIC 权重计算

    Parameters
    ----------
    score_matrix : np.ndarray of shape (n_samples, n_indicators)
        例如 5 方案 × 4 维度得分矩阵

    Returns
    -------
    np.ndarray of shape (n_indicators,)
        CRITIC 权重（归一化）
    """
    X = np.asarray(score_matrix, dtype=float)
    # 1) 标准差（对比强度）
    sigma = X.std(axis=0, ddof=0)
    # 2) 相关系数矩阵
    if X.shape[1] < 2:
        # 只有一个指标时给满权重
        return np.ones(X.shape[1])
    corr = np.corrcoef(X.T)
    # 处理 NaN（如某指标完全相同 → std=0）
    corr = np.nan_to_num(corr, nan=0.0)
    # 3) 冲突性 = Σ(1 - r_jk)
    conflict = (1 - corr).sum(axis=0)
    # 4) CRITIC 权重
    raw = sigma * conflict
    if raw.sum() == 0:
        return np.ones(X.shape[1]) / X.shape[1]
    w = raw / raw.sum()
    return w


def mix_weights(critic_w: np.ndarray, subj_w: np.ndarray,
                ratio_critic: float = MIX_RATIO_CRITIC,
                ratio_subj: float = MIX_RATIO_SUBJ) -> np.ndarray:
    """主客观权重线性混合

    w_final = ratio_critic * w_critic + ratio_subj * w_subjective
    """
    assert abs(ratio_critic + ratio_subj - 1.0) < 1e-6, "比例必须和为 1"
    w = ratio_critic * critic_w + ratio_subj * subj_w
    # 归一化（确保 sum=1）
    return w / w.sum()


def compute_weights(score_matrix: np.ndarray, dimension_names: list,
                    subjective: dict = SUBJECTIVE_WEIGHTS):
    """主入口：算混合权重

    Parameters
    ----------
    score_matrix : np.ndarray, shape=(n_schemes, n_dims)
        例如 5 个方案 × 4 个维度的得分矩阵
    dimension_names : list of str
        维度名顺序 ['设计质量', '关键词管理', ...]
    subjective : dict
        业务权重

    Returns
    -------
    dict 包含 critic / subjective / mixed 三套权重 + 元数据
    """
    # CRITIC
    w_critic = critic_weights(score_matrix)
    # 业务
    w_subj = np.array([subjective[name] for name in dimension_names])
    # 混合
    w_mixed = mix_weights(w_critic, w_subj)

    result = {
        'dimension_names': dimension_names,
        'mix_ratio': {'critic': MIX_RATIO_CRITIC, 'subjective': MIX_RATIO_SUBJ},
        'critic_weights':     {n: round(float(w), 4) for n, w in zip(dimension_names, w_critic)},
        'subjective_weights': {n: round(float(w), 4) for n, w in zip(dimension_names, w_subj)},
        'mixed_weights':      {n: round(float(w), 4) for n, w in zip(dimension_names, w_mixed)},
        'score_matrix':       score_matrix.tolist(),
    }
    return result


def save_weights(result: dict, path: str = None):
    """保存权重结果到 JSON"""
    ensure_dir(TABLES_DIR)
    if path is None:
        path = os.path.join(TABLES_DIR, 'q1_weights.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'[save] {path}', flush=True)

    # 同时输出 CSV 对比表
    df = pd.DataFrame({
        '一级维度':   result['dimension_names'],
        '业务权重':   [result['subjective_weights'][n] for n in result['dimension_names']],
        'CRITIC权重': [result['critic_weights'][n]     for n in result['dimension_names']],
        '混合权重':   [result['mixed_weights'][n]      for n in result['dimension_names']],
    })
    csv_path = path.replace('.json', '.csv')
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f'[save] {csv_path}', flush=True)
    print(df.to_string(index=False), flush=True)
    return df


def get_mixed_weights_dict(result: dict) -> dict:
    """从结果中提取混合权重 dict（供评分函数使用）"""
    return result['mixed_weights']


if __name__ == '__main__':
    # 单元测试：模拟一个 5×4 矩阵
    np.random.seed(42)
    # 让"关键词管理"维度区分度最大
    score_matrix = np.array([
        [60, 95, 70, 65],   # 方案1：关键词最优
        [70, 50, 75, 60],   # 方案2
        [80, 80, 65, 70],   # 方案3
        [55, 90, 60, 55],   # 方案4
        [75, 60, 80, 75],   # 方案5
    ])
    dims = ['设计质量与创意', '关键词管理与运用', '出价策略与预算', '投放策略与时间']
    result = compute_weights(score_matrix, dims)
    save_weights(result)
