# Findings 段 — 写作模板

> 这一段是 iter 文件的**结论段**。让 6 个月后的自己 / 同事能一读就懂"这一轮发生了什么"。

## 单假设的 Findings 模板

```markdown
## Findings

- **假设 X** (本轮目的): 支持 ✓ / 推翻 ✗ / 部分支持 △
  - 证据: <具体哪一行数据 / 哪一现象>
  - 见 iter 文件: `iter_NN` 段 §结果
- **副观察** (如有): <意外发现, 不一定跟本轮假设相关>
- **衔接点** (如果 OK 进 iter_N+1): <下轮要做什么>
```

## 多候选检验的 Findings 模板

当一轮 iter 同时看多个候选 hypothesis 时:

```markdown
## Findings

| Hypothesis | Verdict | Evidence |
|------------|---------|----------|
| H1: 连接池耗尽 | ✗ 推翻 | 峰值 48/50 = 96% 但 502 数不达预期相关 |
| H2: 慢 SQL 阻塞 | ✓ 支持 | thread dump 中 12/15 持锁等一条 query |
| H3: 网卡流量 | △ 待证 | 25% 突发, 但 memcached 命中率同时间掉 |

**下轮重点**: H2 方向深入 (线程栈 + SQL 慢日志)
```

## 走记 (Walk-through) Findings 模板

当 chain-style 深入 (debug, RCA) 时:

```markdown
## Findings

- E0: `tb.env.sc.mismatch @ 8450 ns` (`expected=0xCAFEBABE actual=0xDEADBEEF`)
- E1 → L1: `apb.rdata == wrong @ 8444 ns`, 通过 `T06 wave_prev_change` 取证
- L1 → L2: `apb.mem_addr == 0x3FF (期望 0x080)`
- L2 → RC: `tb.tests/apb_test.sv:47 constraint over-broad`
- **RC 结论**: 约束覆盖了 reserved region `0x3F0..0x3FF`, 允许 addr=0x3FF
- **toggle test**: inject 改窄 → mismatch 消失, remove → 复现
```

> 这种 chain 是 iter-flow + chip-debug skill 联用的产物: iter 框架记录"做了什么",
> chip-debug 给"为什么这样推导"。
