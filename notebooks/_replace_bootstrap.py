"""替换 run_bootstrap_comparison 中的 _bootstrap_one 函数为简化版（不用 Prophet）。"""
import re

path = r'd:\CUMCM2026Problems\src\q1_robustness_aug.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 _bootstrap_one 函数定义开始到下一个 "\n    rows = []" 之前
# 使用更精确的 pattern
start_marker = "    def _bootstrap_one(df, value_col, holiday_date_str, holiday_name, n_boot=100):\n"
end_marker = "    rows = []\n"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)
if start_idx < 0 or end_idx < 0:
    print(f"[错误] 找不到标记: start={start_idx}, end={end_idx}")
    raise SystemExit(1)

print(f"[找到] 旧函数范围: {start_idx} → {end_idx}（{end_idx - start_idx} 字符）")

new_func = '''    def _bootstrap_one(df, value_col, holiday_date_str, holiday_name, n_boot=200):
        """单节日单数据集 Bootstrap（简化版 - 不用 Prophet）

        节日效应 = 当天值 - 前后 7 天均值（剔除节日当天）
        每次 bootstrap 重采样整年，对节日效应重新估计
        """
        np.random.seed(42)
        d_holiday = pd.to_datetime(holiday_date_str)

        prophet_df = df[['日期', value_col]].copy()
        prophet_df = prophet_df.sort_values('日期').reset_index(drop=True)
        n = len(prophet_df)

        # 找节日当天的位置（按日期精确匹配）
        d_str_only = pd.Timestamp(d_holiday).normalize()
        matches = prophet_df[prophet_df['日期'].dt.normalize() == d_str_only].index
        if len(matches) == 0:
            return None
        h_idx = int(matches[0])

        diffs = []
        for _ in range(n_boot):
            # 重采样整年
            idx_boot = np.random.choice(n, size=n, replace=True)
            boot_y = prophet_df.loc[idx_boot, value_col].values
            boot_dates = prophet_df.loc[idx_boot, '日期'].values

            # 找 boot 数据中节日当天（首次出现）
            boot_h_arr = np.where(pd.Series(boot_dates).dt.normalize().values == d_str_only)[0]
            if len(boot_h_arr) == 0:
                continue
            boot_h_idx = int(boot_h_arr[0])

            # 前后 7 天内的非节日数据
            other_idx = [i for i in range(len(boot_y))
                         if i != boot_h_idx and abs(i - boot_h_idx) <= 7]
            if len(other_idx) < 4:
                continue

            effect = boot_y[boot_h_idx] - boot_y[other_idx].mean()
            diffs.append(effect)

        diffs = np.array(diffs)
        if len(diffs) == 0:
            return None

        ci_low = np.percentile(diffs, 2.5)
        ci_high = np.percentile(diffs, 97.5)
        mean_diff = diffs.mean()
        p_val = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
        ci_width = ci_high - ci_low

        return {
            '均值差': mean_diff,
            'CI下限': ci_low,
            'CI上限': ci_high,
            'CI宽度': ci_width,
            'p值': p_val,
            'n_eff': len(diffs),
        }

'''

new_content = content[:start_idx] + new_func + content[end_idx:]

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"[完成] 已替换，新文件长度: {len(new_content)} 字符（原 {len(content)}）")
