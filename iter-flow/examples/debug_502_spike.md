# 完整 demo: 订单服务间歇 502 (5-轮 RCA + 1-轮 fix 验证)

> 这是 iter-flow 在**生产故障**场景下的完整应用。展示 6 个 iter 文件 (5 调查 + 1 验证)。
> 配套 `assets/templates/iter_template.md` 的 6 段模板。
>
> **注意**: 这里是**叙事**,不是真实复盘, 但是**模板该怎么填、回顾引用该怎么接、Findings 该怎么写**的演示。

---

## 0. 起手式 (第 0 步)

```bash
mkdir -p experiments/debug_502_spike/{scripts,data}
python3 scripts/iter_init.py debug_502_spike \
    --background "订单服务在 14:00-14:30 间歇性 502, 用户感知 1% 错误率. P99 latency 800ms+ vs 平时 200ms." \
    --time-window "14:00-14:30 GMT+8" \
    --scope "prod i-0a1b, 单实例" \
    --user-perception "客户端看到 502, 后端无 5xx 日志" \
    --hypotheses "连接池耗尽|慢 SQL 阻塞|网路抖动|NGINX upstream 超时"
```

生成:
```
experiments/debug_502_spike/
├── card.md                            # 任务卡
├── scripts/
└── data/
```

---

## 1. iter_01 — 验证连接池假设 (PROM 抓取)

```markdown
# iter_01: 验证连接池耗尽假设

## 回顾引用
- 首轮 iter, 无历史回顾.

## 目的
我们相信: **当请求量 > 5000/min 时, 订单服务的 db 连接池活跃数达到上限, 获取连接超时, 触发 502.**

## 实验条件
- 脚本: scripts/check_conn_pool.sh
- 环境: prod i-0a1b, 时间窗 14:00-14:30 GMT+8
- 无代码变更

## 检查方法
执行: `bash scripts/check_conn_pool.sh`
观察:
- 活跃连接数 / 最大连接数
- 连接等待时间 (P50 / P95 / P99)
- 502 计数 vs 连接池 utilization 关联
成功标准: 502 尖峰时刻连接池利用率 > 95% **且** 等待时间急剧上升
终止条件: data 拉到 ⟶ 即可. 只读.

## 结果
- 活跃连接数峰值 48/50 (96%) — 但未完全耗尽
- 连接等待时间从 2ms 升至 800ms
- 502 计数 121 次

## Findings
- 假设**部分成立**: 不是 "完全耗尽" (有 2/50 剩余), 而是**等待时间过长导致超时**
- 推测: 业务线程持有连接过久 → 排队 → 接口 P99 > 中间件容忍阈值 → 502
- 下一步: 抓线程 dump, 验证 "业务线程持有连接过久" 假设

## 决策
- [ ] **启动 iter_02** — 连接池假设未完整验证, 需查 "持有过久" 的原因
```

---

## 2. iter_02 — 验证 "线程持有过久"

```markdown
# iter_02: 验证线程持有过久 → 慢 SQL 阻塞假设

## 回顾引用
- iter_01: 连接池 utilization 96% 但**未耗尽**; 等待时间 2ms → 800ms. 结论: 不是真耗尽, 是等待时间过长. 推测业务线程持有连接过久.

## 目的
我们相信: **存在慢 SQL 导致业务线程阻塞, 连接持有时间 > 500ms, 引发排队超时 → 502.**

## 实验条件
- 脚本: scripts/capture_threaddump.sh (连续抓 3 次, 时间窗 14:00-14:30)
- 分析: scripts/find_blocked_sql.py (分析栈找 SQL 阻塞)
- 环境: prod i-0a1b

## 检查方法
执行: `bash scripts/capture_threaddump.sh && python3 scripts/find_blocked_sql.py`
观察:
- 持锁状态线程数 / 总线程数
- 持锁线程所在的 SQL 文本
- 持锁时间长度分布
成功标准: 持锁线程 ≥ 5 个 **且** 它们都因同一条 query 在等
终止条件: 1 小时没抓出 SQL → 转 "应用层锁" / "外部 API 调用" 假设

## 结果
- 抓 3 次 thread dump, 共 12/15 持锁线程因 sql 阻塞
- 全部 12 个线程都在等同一条 query:
  ```sql
  SELECT * FROM orders
    WHERE user_id = ? AND status = 'PAID'
    AND created_at BETWEEN ? AND ?
  ```
- 平均持锁 600ms, P95 1.2s

## Findings
- **假设支持 ✓**: 12/15 持锁线程 = 同一条 query → root cause 候选
- query 是 `orders` 表上 `user_id + status + created_at` 过滤, 但**没有对应索引**
- 没有 index → 全表扫描 → 600ms+
- iter_01 等待时间的 800ms 主要来自这里

## 决策
- [ ] **启动 iter_03** — 验证 query 真的没 index, EXPLAIN 确认
```

---

## 3. iter_03 — EXPLAIN 验证 query 走全表扫

```markdown
# iter_03: 验证 iter_02 找到的 SQL 走的是全表扫

## 回顾引用
- iter_01: 96% utilization, 等待时间飙升
- iter_02: 12/15 持锁线程因同一条 SELECT orders query 等, 600ms+. iter_02 推测: `orders` 表无合适索引.

## 目的
我们相信: **`SELECT * FROM orders WHERE user_id=? AND status='PAID' AND created_at BETWEEN ? AND ?` 在生产 `orders` 表上做全表扫描.**

## 实验条件
- 脚本: scripts/explain_query.sh (在 prod replica 上 EXPLAIN)
- 表: orders (~6M 行)

## 检查方法
执行: `bash scripts/explain_query.sh`
观察 EXPLAIN ANALYZE 输出
成功标准: output 含 "Seq Scan on orders" **或** 走了一个 unusable index
终止条件: 跑 explain → 跑成功 → 不管 output 是 / 否 seq scan, 都能进 iter_04

## 结果
EXPLAIN ANALYZE:
```
Seq Scan on orders  (cost=0.00..183456.00 rows=5200 width=180) (actual time=42..620 rows=5183 loops=1)
  Filter: ((user_id = 1) AND (status = 'PAID') AND (created_at >= '2026-06-01') AND (created_at <= '2026-07-14'))
  Rows Removed by Filter: 6484217
Planning Time: 0.15 ms
Execution Time: 620.341 ms
```

## Findings
- **假设 100% 确认 ✓**: 6.5M 行表, 6.4M 被 filter 掉, 只返回 5.2k 行
- 浪费时间 99.92%
- 这是 "业务表长大, 索引没跟上" 的典型表现

## 决策
- [ ] **进入修复轮 (iter_04)** — root cause 确认. 加 composite index `(user_id, status, created_at)`.
```

---

## 4. iter_04 — 修复方案设计 (idx_composite)

```markdown
# iter_04: 加 composite index (user_id, status, created_at)

## 回顾引用
- iter_01: 96% utilization, 等待飙到 800ms
- iter_02: 12/15 thread 阻塞, 同一条 SELECT 全表扫
- iter_03: EXPLAIN 确认 Seq Scan, 99.92% row 被 filter 掉

## 目的
我们相信: **加 idx_orders_user_status_created (user_id, status, created_at) 可让 ORDER BY 走 index scan, single query 从 620ms 降到 < 10ms.**

## 实验条件
- DDL: `CREATE INDEX CONCURRENTLY idx_orders_user_status_created ON orders (user_id, status, created_at);`
- 环境: staging first, then prod gray
- 数据量: 6.5M

## 检查方法
- 在 staging 重跑 iter_03 的同一 query, EXPLAIN
- 比 execution time vs iter_03 的 620ms
成功标准: execution time < 50ms **且** plan 含 "Index Scan using idx_orders_user_status_created"
终止条件: DDL 报错 → 转 "online schema migration 兼容性" 假设

## 结果
- DDL 跑成功 (CONCURRENTLY 不锁表), 1m24s
- EXPLAIN ANALYZE 后:
  ```
  Index Scan using idx_orders_user_status_created on orders  (cost=0.42..45.6 rows=5200 width=180) (actual time=0.05..7.8 rows=5183 loops=1)
  ```
- execution time: **7.8ms** (vs 620ms)

## Findings
- **假设支持 ✓**: 79x 加速, 完美的 index-driven plan
- 没改变 query 文本 → 上层逻辑零影响
- 注意: index size 约 240MB, 内存占用 +12% — 监控 memory pressure

## 决策
- [ ] **进入修复验证 (iter_05)** — 必须 staging + gray 跑真实流量确认整体 P99
```

---

## 5. iter_05 — 修复验证 (灰度发布 P99 监控)

```markdown
# iter_05: 灰度发布 idx, 验证 prod P99

## 回顾引用
- iter_04: staging EXPLAIN 从 620ms 降到 7.8ms, 但需 prod 真实流量验证
- iter_03: 原 query Seq Scan 620ms
- iter_02: 持锁 12/15 线程

## 目的
我们相信: **prod gray 50% 流量走新 index 后, 502 错误 14:00-14:30 时间窗接近 0, P99 latency < 200ms.**

## 实验条件
- 灰度: 50% 流量, 实例 i-0a1b, 时间 14:00-15:00
- 对照组: i-0a2b (无 index, 同样 50% 流量)

## 检查方法
比较时间窗内两组数据:
- 502 计数
- P50/P99 latency
- threaddump 中持锁线程数
成功标准:
- 502 计数 **< 5** (跟 baseline 121 比 -95%)
- P99 latency < 250ms (从 800+ 降到 baseline)
- threaddump 中持锁线程 < 5

## 结果
- 时间窗 14:00-15:00 GMT+8:
  | 指标           | gray  (有 index) | control (无 index) |
  |----------------|------------------|---------------------|
  | 502 计数       | **3**            | 124                 |
  | P50 latency    | 35 ms            | 220 ms              |
  | P99 latency    | **180 ms**       | 870 ms              |
  | 持锁线程数     | **1**            | 14                  |

## Findings
- **假设支持 ✓✓**: 灰度全面优于 control, all 4 个指标超越成功标准
- 修复彻底解决 root cause, 无副作用

## 决策
- [ ] **关闭 task, 进入 docs/runbooks/ 归档**
```

---

## 6. 全任务归档

```bash
# 1. 全目录 commit
git add experiments/debug_502_spike/
git commit -m "fix(orders): add idx_orders_user_status_created, P99 870ms → 180ms"

# 2. 归档到 runbooks
cp -r experiments/debug_502_spike/ docs/runbooks/orders_p99_2026-07-14/

# 3. 全员 broadcast
# "orders 服务 502 排查记录在 docs/runbooks/orders_p99_2026-07-14/ ,
#   关键结论: 加 idx_orders_user_status_created, 79x 加速;
#   排查过程: 5 个 iter, 全程脚本化 + 文案化, 任何人 1 天内能复现整条调查."
```

---

## 这个 demo 想强调的几点

1. **每轮 iter 都是 data-driven**, 不是 "我觉得" / "我猜的".
2. **脚本化**:iter_01 抓 conn pool, iter_02 抓 thread dump, iter_03 EXPLAIN, iter_04 DDL, iter_05 monitor. 每轮都有 `scripts/xxx.sh` 可以重跑.
3. **回顾引用是真的复制结论**: iter_02 把 iter_01 的 "96% utilization 没耗尽" 拷到 §回顾引用, 不是写 "见 iter_01".
4. **修复单独成 iter**: iter_04 设计 fix, iter_05 跑 fix 验证. 不混.
5. **决策明确勾选**: 5 轮都从 3 个 option 中二选一, 不用 "我觉得下一步" 来过渡.

---

## 反例 (这个 demo 没踩但实际常踩)

- ❌ iter_02 直接说 "我们相信是连接泄漏" 不读 iter_01 data
- ❌ iter_03 用 `head -100 orders_table` 大致看, 而不跑 EXPLAIN
- ❌ iter_04 直接 prod 100% 切换, 不 staging 不灰度
- ❌ iter_05 看 502 减少了就宣布 "好了", 不检查 P99 / thread state

---

## 文件结构 (对照)

```
experiments/debug_502_spike/
├── card.md
├── scripts/
│   ├── check_conn_pool.sh
│   ├── capture_threaddump.sh
│   ├── find_blocked_sql.py
│   ├── explain_query.sh
│   └── bench_gray.sh
├── data/
│   ├── conn_active_iter_01.json
│   ├── threaddump_iter_02_01.txt
│   ├── ...
└── iter_*.md  (6 个)
```
