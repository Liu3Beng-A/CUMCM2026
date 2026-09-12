# results/figures/

本目录存放 Q1/Q2/Q3/Q4 的图表产物。

## 命名约定

- `q{题号}_{图名}.png`：主交付图（默认最新版本）
- `q{题号}_{图名}_v{版本}.png`：版本化图（如 `q3_sensitivity_v2.png`）
- `q{题号}_{图名}_v{旧版本}_DEPRECATED.png`：已废弃图，**默认不引用**

## 引用规范

论文 / 答辩 PPT 引用图时必须使用**最新版本**：

1. 优先使用含 `_v2` / `_v3` 后缀的版本（如 `q3_sensitivity_v2.png`）
2. 若同时存在无后缀图与 `_v{N}` 版本化图，**优先使用版本化图**
3. 任何包含 `_DEPRECATED` 后缀的图，**禁止**在新文档中引用

## 历史废弃图

| 文件名 | 替代版本 | 废弃原因 | 废弃日期 |
|---|---|---|---|
| `q3_sensitivity.png`（v1，无 DEPRECATED 副本已删）| `q3_sensitivity_v2.png` | v1 含 `r_reg` 扰动（share-Pearson=-0.096，代理失效），F1 重构为 v2 | 2026-09-12 |

## 维护记录

- 2026-09-12 21:50 · 建立本 README · 删除 v1 旧图并修订 `src/q3_evaluator.py` 引用
