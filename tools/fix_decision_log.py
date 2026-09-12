"""
DECISION_LOG.md 修复：D-011~D-016 (14:18) 中文乱码
"""
import os

DECISION_LOG = 'D:/CUMCM2026Problems/DECISION_LOG.md'

# 读取全文
with open(DECISION_LOG, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到第一行 14:18 开头的乱码条目
bad_marker = "[2026-09-12 14:18] D-011 | Q2 瀛楁缁勫悎"  # 乱码 marker
if bad_marker not in content:
    print('未找到乱码 marker，跳过')
    exit()

# 截断到乱码之前（保留所有 15:25 之前的合法内容 + 标题）
parts = content.split(bad_marker)
head = parts[0].rstrip() + '\n\n'  # 保留到 15:25 D-014 之后

# 追加正确的 14:18 内容
new_entries = """[2026-09-12 14:18] D-011 | Q2 字段组合 | (成本=消费额, 效益=CPC倒数) 锁定 | 经 4 组合稳健性验证，Cohen κ=0.003~0.294（其他 3 组合接近随机）；锁定 D-Q2-002 是 SEM 业务最经典的"成本/效益"度量（消费额=花了多少钱，CPC倒数=每元点击数）

[2026-09-12 14:18] D-012 | Q2 阈值口径 | 均匀中位数（不消费加权）| 经 3 套阈值对比验证：均匀中位数 T_cost=8.06 元（5 类均衡 431/238/240/428）；消费加权 T_cost=69706 元几乎所有有效词变低成本分类失效；行业基准 T_benefit=0.667 偏严苛（黄金 577）；选均匀中位数最贴近题面均衡语义

[2026-09-12 14:18] D-013 | 极值审计风险评级 | 业务阈值（消费>1万=高/5000-1万=中/<5000=低）| 原统计分位 p66 在 105 个高消费词里失效（全部聚集'高'）；改业务阈值后分布合理 高69/中27/低9

[2026-09-12 14:18] D-014 | 极值类型 | 重点词=保留型极值 / 问题词=削减型极值 | 业务语义清晰：重点词高消费高效益建议加码（14 词），问题词高消费低效益建议削减（91 词）；Q3 投放策略可基于此直接决策

[2026-09-12 14:18] D-015 | 异常词处理 | ghost_browsing(2 词) + truly_dead(888 词) + potential_revival(0 词) | ghost=消费=0但浏览=1（2 词，疑似爬虫/恶意）；888 三零词的跳出率全为默认填充值 0.5+平均访问时长=0 → 系统确实没分配曝光 → 无潜在激活清单；保留全部但加 异常标记 列

[2026-09-12 14:18] D-016 | Q2 重做完成 + 6 项稳健性 | 2026-09-12 14:18 完成 | 主交付物 10/10 PASS；6 项稳健性产物（阈值3对比/字段稳健性/审计v2/ghost_browsing/三零词细分/汇总报告）
"""

new_content = head + new_entries
with open(DECISION_LOG, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f'修复完成。新长度：{len(new_content)} chars')
print(f'文件最后 200 字符预览：')
print(new_content[-200:])
