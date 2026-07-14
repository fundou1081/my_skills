# Debug Playbook (Enhanced) — Field Manual for Hands-On Chip RCA

> **本文件是 raw 版 [`debug-playbook.md`](debug-playbook.md) 的 enhanced 版**。
> raw 版保留作为对话快照 / 最小可用版。
>
> 当你**第一次**来 debug, 看 raw 版。
> 当你已经**踩过坑**想要细节、命令、决策矩阵, 跳到本文件。
>
> 上游: [`rca-workflow.md`](rca-workflow.md) (方法学骨架) · [`atomic-tools.md`](atomic-tools.md) (8 原子合约) · [`checklists.md`](checklists.md) (RC 准入) · [`tools-and-bridges.md`](tools-and-bridges.md) (接到现有工具)

---

## 0. Changelog (vs raw 版)

| 章节 | raw 版 | enhanced 版 | 增量 |
|------|--------|-------------|------|
| §1 三种 debug 模式 | 不存在 | NEW | 4 种进入模式 (full / log-only / wave-only / headless), 各自进退条件 + 步骤裁剪 |
| §2 总体循环 | 简笔 ASCII 图 | 同 | ASCII 图保留, 加上"何时该回哪一步"的决策规则 |
| §3 Step 1: log 定位 | input / output / 工具 / 要点 / 反模式 | **+ 触发条件** / **+ 决策矩阵** / **+ 命令模板** / **+ 中间产物模板** / **+ tier-1 红线** | ~3× 行数 |
| §4 Step 2: 语义 trace | 同上 | **+ 控制信号的优先级矩阵** / **+ 多驱动归纳模板** / **+ clock/reset 边界判据** | ~2.5× |
| §5 Step 3: 波形 trace | 同上 | **+ 批量 snapshot 脚本框架** / **+ X/Z delta_ns 特殊规则** / **+ log-wave 对齐错位排查** | ~2.5× |
| §6 Step 4: 筛选 | 4 依据 | **+ 4-维评分矩阵** / **+ "明显不相关" 反例库** | ~2× |
| §7 Step 5: RC 判定 | 是/否/模块边界 | **+ 决策树 ASCII 图** / **+ 模块边界判定的细化类型** / **+ toggle test 多 seed 标准** | ~3× |
| §8 Per-step self-check | 不存在 | NEW | 每步完成后 2-3 个 yes/no sanity check |
| §9 跨时钟域 / 异步处理 | 不存在 | NEW | CDC / reset race / metastability / X-prop 专章 |
| §10 加速技巧 | 不存在 | NEW | 缓存/批处理/哪些步骤可并行 |
| §11 增量沉淀 | 简版 append 模板 | 同 raw | (无变动) |

---

## 1. 三种 debug 模式 (Debug Modes)

**何时读这一节** — 一上来就问自己"我现在手上有哪几样东西", 决定走哪种模式。

| Mode | 资源 | 启动信号 |
|------|------|----------|
| **full** | log + wave + 源码 都有 | CI 跑出 failed, 你能开 Verdi / GTKWave |
| **log-only** | log + 源码, **无 wave** | 回归跑的机时紧, 没开 dump |
| **wave-only** | wave + 源码, **log 极少** | simulator 跑完直接出 fsdb, 但命令行没打印 |
| **headless** | 静态资料 + issue tracker | 你在看别人提的 bug, 自己没跑过 sim |

### full mode (默认)
所有 5 步全跑, 无任何绕过。这是 §3-§7 描述的默认流程。

### log-only mode
- **跳过 §5 Step 3 (波形 trace)** 主体, 改为**从 log 时间戳反推**。
- **新增 §5b** — log 反推: 用 `parse_uvm_log.py --all-errors` 拿到所有错误的相对时序, 用 log 中的 `$display` / `\`uvm_info` 拼凑出信号值时序。
- **关键工具**: `parse_uvm_log.py --include-warnings` 收集所有 $display / $monitor 行。
- **要做的事**: 用 $display 替代波形, 多 dump 点关键信号, 必要时改 RTL 重跑。

### wave-only mode
- **跳过 §3 Step 1 (log 定位 1st failed)**, 改为**"在波形上肉眼找一个 suspicious 事件"**。
- **怎么找**: 用 Verdi / GTKWave 的 search, 找 X / Z / 不连续变化。
- **L1 起步**: 从波形上异常处反推 log 应有的输出, 但**log 没打**, 自己**主动补** `assert`/`$display` 重跑一次。
- **陷阱**: wave-only 模式**不能**做 toggle test 的反向 (因为没有 driver 反推链), 需要回到 full mode 才能做完整 RC 判定。

### headless mode
- **只读 RTL + issue 描述**, 不跑 sim。
- **干啥**: 静态走查、code review、生成 hypothesis 清单。
- **限制**: 这种模式下你不能"声明 RC", 只能"列出疑点"。
- **典型用法**: 别人给你的 sanity check, 或者需要列出可能候选让你后续自己跑 sim 验证。

### 模式互转 (Mode Switcher)

| 从 → 到 | 触发条件 |
|---------|---------|
| log-only → full | 你有 wave dump 没注意 (重新跑 sim 打开 dump) |
| full → log-only | wave dump 文件损坏 / 未生成, 但 log 完整 |
| wave-only → full | 需要 toggle test 反向 |
| headless → 任意 | 你拿到了 sim 运行权限 |

---

## 2. 总体循环 (Manual Debug Loop)

整个 debug 流程在手动执行时大致这样循环:

```
   ┌──────────────────────────────────────────────────────────┐
   │                                                          │
   ▼                                                          │
[1. log 定位 1st failed]  →  [2. 语义 trace 因果信号]  →  │
   │                                                          │
   ▼                                                          │
[3. 波形找最近变化+值]  →  [4. 筛选最相关因果信号]  →  │
   │                                                          │
   ▼                                                          │
[5. 判定是否 root cause]  ─── 否 ───► 回到 [2]                │
   │                                                          │
   ▼ 是                                                        │
[交付 RC 报告]                                                │
```

### 循环回退规则

| 你在哪一步发现 | 回退到 | 原因 |
|---------------|-------|------|
| Step 2 中发现自己 pin 在错误信号 | Step 1 (重锁) | L0 定错了, 一切都白做 |
| Step 3 中发现波形跟 log 时间对不上 | Step 1 (重锁时间) | log/wave 时间轴错位 |
| Step 4 找不到 strong candidate | Step 2 (重新 gather signals) | 收集面太窄 |
| Step 5 中发现 RC 在其他模块 | Stop, 转交隔壁模块 | **不要污染本模块 fix 决定** |
| Toggle test 在方向 A 通过,方向 B 失败 | Stop, 重审 (回到 Step 3 复核数据) | data 不一致 |

> **关键**: 第 5 步如果答案是"否", 必须**回到第 2 步**, 而不是跳到第 1 步或第 3 步。1 步已是定锚, 3 步是执行, 中间的 2/4 才是思维劳动。

---

## 3. Step 1 — 从 log 定位 1st failed

### 触发条件 (When to enter this step)
- CI / regression 跑出 `FAIL`。
- 手动跑 sim,看到 `$finish` 但不知道为啥。
- 别人说"这跑挂了", 把 log/wave 给你。

### 目的
锁住**问题入口**, 给后续所有追溯一个**确定的出发时间**。

### Input
- **sim log** (VCS / Questa / Xcelium / Verilator 任一种, 大小通常 1MB – 1GB)

### Output (四个字段, 缺一不可)

| 字段 | 含义 | 缺它会怎样 |
|------|------|-----------|
| **错误信息** | UVM_ERROR / UVM_FATAL / SVA fail 的完整原文 | L1 失去锚点 |
| **发生时间** | 仿真时间戳, 标准化到 ns | 时间对齐全失 |
| **涉及到的信号路径** | hier path, 如 `tb.env.scoreboard.mismatch` | L1 无法 trace |
| **报错的文件及对应行数** | `dut/cpu/alu.sv:142` | 失去静态证据 |

### 决策矩阵 — 找不到文件:行怎么办

| 情况 | 处理 |
|------|------|
| log 有 `at <file>:<line>` | 直接用, 没毛病 |
| log 提到 `<signal>` 但无 file:line | 跳到 T02 `code_define` 反查 |
| 只有 UVM id (e.g. `SCOREBOARD_ERROR`) | grep RTL 找 `uvm_error("SCOREBOARD_ERROR", ...)` 拿到 source:line |
| 完全没有信息 (空行 ERROR) | 这种 ERROR 通常是从 DPI 出来, 标记 `source: log:<file>:<line>:DPI` 注明, 后续补 |

### 命令模板

```bash
# 默认 (text 格式, 最常用)
python3 scripts/parse_uvm_log.py <log> --first-error

# 拿所有错误 + 上下文(用于多 anchor 分析)
python3 scripts/parse_uvm_log.py <log> --all-errors --context 5

# JSON 输出 (喂给 chain init)
python3 scripts/parse_uvm_log.py <log> --first-error --format json

# 含 warning (log-only 模式常用)
python3 scripts/parse_uvm_log.py <log> --include-warnings --all-errors

# simulator auto-detect
python3 scripts/parse_uvm_log.py <log> --detect        # 只打印 simulator 类型
```

### 中间产物模板 (E0 node)

```yaml
- node_id: E0
  time: "8450 ns"           # ALWAYS 标准化成 ns, 带单位
  signal: "tb.env.apb_mst.scoreboard"
  actual: "expected=0xCAFEBABE actual=0xDEADBEEF"
  expected: "0xCAFEBABE"
  source: "log:run.log:1247"
  evidence_kind: log_line
```

### 主要工具
- **log 读取** — `parse_uvm_log.py` (auto-detect VCS / Questa / Xcelium / Verilator)
- **源码定位** — sv-query `trace define --path <signal>` (T02)
- **搜索** — `grep -nE "uvm_error|uvm_fatal|\$error" <dir>` 配合信号全路径

### 实操要点
- **找最早**, 不是找最严重。`UVM_FATAL` 通常在 `UVM_ERROR` 之后出现, 它可能是雪崩产物。
- **同一时间多错误**: 取**最深层 hier path** 作为 L1 切入点。其他同时间的错误列入"次要异常"清单 (在 `2_decisions/decision_log.json` 里)。
- **没有文件:行数怎么办**: 不要硬填 "未知", 改成 `source: log:<file>:<line>` 注解 + 时间戳即可。后续再补。
- **log 噪声**: 大 log 几 GB 时直接 grep `UVM_ERROR\|UVM_FATAL` 切一段出来再喂, 别直接 `python3 *.py < 50GB`。

### Tier-1 红线 (Step 1 离开前必查)

1. **时间戳单调性** — 同一 simulator 不同时钟域不该有时间倒流, 看到倒流:**立刻怀疑 simulator bug 或 test 用 `+fsdb+force_dumpfile`**。
2. **多次重试** — 看到 `[REPLAY]`/`[RAND_RESET]`, 这是 retry 路径, 取**最后一次出现的 1st failed**, 而不是第一次。
3. **隐式 rerun** — log 里 `Stopping simulation due to assertion failure at t = ...` 跟接下来 `Simulation finished at t = ...` 时间对不上,**说明 sim 中途被 abort**, 时间戳已无意义。

### 反模式
- ❌ 只看 `grep ERROR` 不看时间, 把第一个错误的判断丢了
- ❌ 把 SVA fail 当成 log 行的副产品不重视 (它经常是早于 UVM_ERROR 的真相)
- ❌ 把 FATAL 当成 root cause 候选 (FATAL 通常是 abort 的信号, 不是问题源头)
- ❌ log 太大就用 `tail -100`, 失去 log 早期部分 — 早期部分可能有**早期错 ERROR** 比 mid-run 的更接近 RC

---

## 4. Step 2 — 追踪信号的 trace / load / control 语义信息

### 触发条件
- 你已经知道 E0 的信号路径。
- 你需要在它**上游**找候选, 不要去 hop 下游 (下游是 load/observer, 改变不了信号)。

### 目的
从第一步锁住的信号出发, **列出所有有因果关系的候选信号**, 构建可能的下一步追溯目标。

### Input
- 信号 path (E0)
- 该信号的源码 (从 T02 拿到的 `definition_site`)

### Output
每个候选信号一组字段:

| 字段 | 含义 |
|------|------|
| **路径** | 因果信号的完整 hier path |
| **语义关系** | `drive` / `load` / `control` / `mux_select` / `enable` / `clock` / `reset` |
| **代码片段** | 几行关键源码, 最好能复制粘贴 |
| **文件及行数** | 定位证据 |

### 决策矩阵 — 候选信号分类

| 语义类型 | 对应下一步动作 | 权重 (Step 4 用) |
|---------|-------------|------------------|
| `drive` (唯一的) | 上游追溯到 driver 的 source, **优先级 1** | HIGH |
| `drive` (多个, net) | 看哪个 assign 在 t 范围内 active | MEDIUM |
| `mux_select` | **这就是一个 hop**, 因为它切换数据源 | HIGH |
| `enable` / `gate` | 类似 mux_select, 是控制 gate | MEDIUM |
| `condition` (always block if/case) | 可能是 root cause 的"条件入口" | HIGH |
| `load` | **不在追溯路径上**, 只放 secondary anomalies 清单 | NONE |
| `clock` | **边界条件**, 优先排除 (除非 clk 自身有问题) | LOW |
| `reset` (局部) | **边界条件**, 优先排除 (除非 reset vector 错) | LOW |
| `reset` (全局) | 几乎**不是 RC**, 是 propagation point | NONE |

### 命令模板 (sv-query 风格)

```bash
# 信号定义
sv-query trace define --path <path>

# 上游追溯 (drive)
sv-query trace fanin --path <path> --depth 5

# 下游追溯 (load, 当作 secondary)
sv-query trace fanout --path <path> --depth 3

# 完整证据 (含代码片段)
sv-query trace evidence --path <path> --context 5

# 模块结构
sv-query arch --module <module>
```

### 中间产物模板 (L_{k} node 的 code-side evidence)

```json
{
  "node_id": "L1",
  "stage": "Stage2.5Why",
  "hop": "5-Why-L1",
  "relation": "Scoreboard samples rdata 1 cycle after PRDATA rises",
  "evidence_kind": "wave_dump",     /* code-side 这里给 code_inspection */
  "source": "code:tb/dut/apb_slave.sv:142"
}
```

### 主要工具
- **语义提取** — `sv-query trace evidence` / `sv-query trace fanin` / `sv-query trace fanout`
- 也可用 T04 `code_rels` 合约

### 实操要点
- **多驱动是常态**: 一根 net 多个 `assign` 是常事, 不要误以为是 bug 候选。**多驱动 ≠ 多 RC**, 多数时候是 design 的合理 mux 结构。
- **clock/reset 优先排除**: 如果追溯到 `clk` 或 `rst_n`, 这是**边界条件**, 不是 root cause (除非 clk 本身有问题)。
- **控制信号的优先顺序是 `condition > mux_select > enable`**, 因为 condition 是 always 块顶层 if/case 条件, 比 mux 控制更上游。
- **跳过 load**: 除非你想知道"为什么这个错被观察到", 否则 load 不进追溯链。

### 跨时钟域处理 — Step 2 起步就要知道

| 跨域情形 | 处理 |
|---------|------|
| 候选信号在异步 clock domain | 标记 `cdc_domain: true`, 进入 §9 CDC 专章 |
| 候选信号通过 handshake 跨域 | 优先看 handshake 两侧**同时**变化 |
| 候选信号通过 `(* async *)` 属性 | 加 `cdc_marker: yes` 进 chain.json |

### 反模式
- ❌ 拿到候选列表就跳过第 3 步, 直接脑补因果 (没数据)
- ❌ 把 `load` 当作 `drive` 处理 (load 不会改变被调查的信号, 只会观察)
- ❌ 把 control/condition 类的信号优先级跟 drive 类混为一谈 (它们本质不同)
- ❌ "信号有 50 个 driver, 一定有问题" — design 上多 driver = mux, 不一定 bug

---

## 5. Step 3 — 在波形上找每个因果信号的最近变化 + 值

### 触发条件
- 你已经从 Step 2 拿到候选信号列表。
- 你有 wave dump (full / wave-only 模式)。
- (log-only 模式: 转 §5b "log-only 反推")

### 目的
把第 2 步拿到的"候选关系"落实成"**真实时间链**", 这是 5-Why 的每一跳的**动态证据**。

### Input
- 步骤 2 的因果信号列表

### Output
对每个因果信号一项:

| 字段 | 含义 |
|------|------|
| **变化时间** | 该信号**最近一次变化**的时间 (T06 `wave_prev_change` 或 T08 `wave_nearest_change`) |
| **数值** | 该次变化之后的值 |
| **与第 1 步时间的关系** | 比 `first_failed` 早多少 ns? |

### 命令模板 (假设原子工具已实现)

```bash
# 拿到信号在特定时间的值
atom T05 wave_value_at --path <path> --time "8440 ns"

# 拿到信号在参考时间前的最近变化
atom T06 wave_prev_change --path <path> --ref_time "8440 ns" --n 1

# 拿到信号在参考时间附近的最近变化 (双向)
atom T08 wave_nearest_change --path <path> --ref_time "8440 ns" --direction both

# 对比两个信号在时间窗口内的变化 (event 模式 / sequence 模式)
atom T07 wave_diff --path_a <a> --path_b <b> --time_from "8000 ns" --time_to "9000 ns" --mode event
atom T07 wave_diff --path_a <a> --path_b <b> --mode sequence
```

### 批量 snapshot 脚本框架 (Step 3 加速)

```bash
#!/usr/bin/env bash
# 用法: ./trace_candidates.sh "<candidate_paths>" <ref_time> <out_dir>
PATHS=$1
REF_TIME=$2
OUT=$3
mkdir -p "$OUT"
echo "$PATHS" | tr ',' '\n' | while read -r p; do
  safe=$(echo "$p" | tr '.' '_')
  atom T06 wave_prev_change --path "$p" --ref_time "$REF_TIME" --n 1 \
    > "$OUT/${safe}.json"
done
```

> 跑完一次就能在一个目录拿到所有候选的"过去最近变化", 然后 Step 4 用脚本批量评分。

### 主要工具
- **波形相关** — VCD / FSDB reader (verdi `nwave`, `gtkwave`, `surfer`, 见 T05–T08 合约)
- **log 时间对齐** — `parse_uvm_log.py` 拿到的 timestamp 作为定位锚点

### 实操要点
- **对齐时间**: 波形上信号变化时间必须**严格早于** 1st failed 时间, 否则**不是可信因果源** (可能是 virus propagation)。
- **距离加权**: 离 1st failed 越近的信号变化越可疑, 但**不要只看距离**。
- **批量扫多信号**: 一次手动扫 5+ 信号, 用脚本批量 snapshot, 不要凭眼睛从波形图挨个读 — 容易漏掉细节。
- **X / Z 状态特殊关注**:
  - **X** — 高频电平冲突或未初始化。最强 candidate 信号。
  - **Z** — 高阻, 通常是 bus 没有 driver 选中。
  - 两者**都强烈指示 root cause 候选**, 比错误的 0/1 更指向"结构性问题"。

### log-wave 对齐错位排查 (Tier-1)

| 现象 | 原因 | 处理 |
|------|------|------|
| wave 显示一个变化, log 没记录 | 这个信号没被 $display / monitor 覆盖 | 加 $monitor 重跑, 或退到 log-only 推断 |
| log 报错但 wave 没显示对应异常 | log 是 dump moment snapshot, wave 已经是没问题的状态 | 重新切回 E0 时间, 找完整 wave |
| 时钟域差异: log 显示时间 A, wave 显示变化 A+10ns | wave clock period = 10ns, log 步进到秒 | 时间单位对齐 (ps vs ns vs simstep) |
| 双 sim 跑同一 test, log/time 完全不同 | reseed 不同 / 跑环境 `uvm_test_top` 改了 | 用 `--include-warnings --all-errors` 比对 |

### delta_ns 特别规则

| delta_ns 范围 | 含义 | 关注度 |
|--------------|------|--------|
| **< 1 ns** | 同 cycle 内, setup/hold 边界 | **极高** — CDC / metastability 嫌疑 |
| 1 ns — 10 ns | 1 个 cycle 内 (取决于 clk) | 高 |
| 10 ns — 100 ns | 跨几个 cycle, 普通因果链 | 中 |
| **> 1000 ns** | 跨很大, 中间可能漏了信号 | **回 Step 2 加粗收集面** |

### 反模式
- ❌ 看到信号**等于预期值**就直接跳过 (有些 bug 是"该断电时未断", 不是"值不对")
- ❌ 同一信号在多个层级反复 trace 浪费时间 (find upstream once, record it)
- ❌ 忽略 delta_ns 极小的变化 (< 1ns 在某些时钟域是 setup/hold 边界, 极重要)
- ❌ 在波形图上**只盯着那个失败的 E0 信号**, 不去找上游 — 浪费 80% 时间

---

## 6. Step 4 — 筛选最具有因果关系的信号

### 触发条件
- Step 3 已经输出**所有**候选信号的"最近变化 + 时间"。
- 你面对的可能是一个列表, 需要挑出 hop 的下一个起点。

### 目的
把候选列表里的"可能相关"过滤成"**最相关**", 通常每个 hop 只挑 1-2 个继续向上追溯。

### 主要依据 (按权重)

1. **语义关系** — `drive` 比 `load` 重要, `condition` 比 `mux_select` 更上游。
2. **trace / load / condition** — 类型决定它在因果链中的"位置权重"。
3. **波形上的变化时间距离** — 越靠近 1st failed 越值得怀疑 (但不是最相关, 见下条)。
4. **系统知识 / 逻辑推理** — 比如 "这个信号在 RTL 里被 force 过, 应该排除" / "这个 reset 信号是 cold reset, 一直在稳态, 不像问题源"。

### 决策矩阵 — 4 维评分

每个候选信号按下面 4 个维度打分 (0–3, 总分 12):

| 维度 | 0 分 | 1 分 | 2 分 | 3 分 |
|------|------|------|------|------|
| **语义相关性** | `load` 单纯观察 | `enable` / `gate` | `mux_select` | `drive` (唯一) / `condition` |
| **时间距离** | > 1000 ns | 100–1000 ns | 10–100 ns | < 10 ns |
| **逻辑深度** | 同层 / 下游 (load) | 同模块上游 | 跨模块上游 | **跨模块但属于关键上游** |
| **系统知识** | 我不熟的模块, 看不见 | 静态推测可疑 | **已知**有 bug history | 已知是 problem child |

**总分 ≥ 9**: 强相关, hop 继续往上追
**总分 6–8**: 中等, 可作为对比候选
**总分 ≤ 5**: 收集面窄的话可追, 不然优先 9 分以上的

### 决策矩阵 — 明显不相关 (反例库)

| 候选长这样 | 直接排除 |
|----------|---------|
| reset 信号在整个 sim 时间窗里**恒为 0** | 不是它的活 |
| 候选信号**直到 E0 之后才变化** (病毒传播) | 不是因果源 |
| clk 类信号 | 是边界, 不是 RC |
| 候选信号的值 = 预期值, 但**变化频率远低于 E0** | 不是主因 |
| 候选信号在两个 driver 都被 X (悬空) | 两个 driver 都不是, 真实 driver 在更上游 |
| 候选信号的 load 含 E0 自身 | 这只是 back-edge, 不是新信息 |

### 实操要点
- **不要只用时间距离挑选**: 一个信号离 1st failed 100ns 远但**直接驱动**目标, 比一个离 1ns 但只是 `load` 的信号更值得追。
- **找出"反例信号"**: 没变化的信号也是证据 (说明它不是这个 hop 的罪魁)。
- **逻辑推理压倒波形扫描**: 有时候靠"这个信号应该是 mux 的 select" 直接锁下一跳比扫波形快。**但推理完必须回波形验证。**
- **多 hop 评估**: 不止评估这一个 hop 的所有候选, 还要评估**上一 hop 的 1-2 个候选是否给了下一 hop 的两条线索**。

### 反模式
- ❌ "我这个模块不熟, 看起来每个都可疑" — 停下, 回去读 RTL, 画出 data flow 后再筛
- ❌ 只看时间不看语义 — 容易在下游信号浪费时间
- ❌ 只看语义不看时间 — 容易挑到一个稳态信号当突破点
- ❌ "我觉得 80% 是它" 但 RC 候选给出 7 分不 9 分 — 思路不打开, 永远停在一个低分信号上

---

## 7. Step 5 — 判断是否为真实的 root cause

### 触发条件
- 你有 1 个强 RC 候选 (Step 4 出来 ≥ 9 分), 想正式判定。
- 或者, 你已经从 Step 5 第一次判定失败, 现在是再次尝试。

### 怎么判断**是** root cause?

满足下列**任意一个或多个**就强候选:

1. **波形上对比出明确差异**
   - RC 引入/移除前后, E0 的值出现/消失。
   - 通常是 toggle test 的正向证据。
2. **不预期的数值 (X / Z / 错常量)**
   - 该信号在设计意图下不应出现 X, 但出现了。
   - 不应 Z 但出现 Z。
   - 不应是某个固定值但出现了 (例如 reset vector 错)。
3. **5-Why 追踪到了信号最早的变化时间, 波形的尽头**
   - 已经追到 reset / boot / test sequence 起点, 没东西可追了, 这就是 RC。
   - 这种情况下, RC 通常是个 initial value 错、parameter 错、generate 条件错。

### 怎么判断**不是** root cause?

满足下列**任意一个**就不是:

1. **还有可继续追的因果信号**
   - 当前节点还有 driver 或 upstream 候选, 优先继续。
2. **还有更早的因果信号变化**
   - 当前解释不是最早的, 之前的某段时间还有 input 变化没解释。
3. **从设计意图出发, 信号行为不符合预期**
   - 例如: 在 reset 撤销后某信号应该 held 1 cycle, 但实际立刻翻转。说明有更早的 driver 干扰。

### 决策树 (Decision Tree)

```
当前候选 H 是 RC 吗?
│
├── 在 t < E0 时间, H 出现"对的值"吗?
│   │
│   ├── 否 → 不是 RC, 它在 E0 时间还没就绪, 还有上游要追
│   └── 是 → 继续
│
├── 在 t < E0 时间, H 出现"错的值" 或 "X/Z" 吗?
│   │
│   ├── 否 → 退化到"无辜" 信号, 在更上游追因
│   └── 是 → 继续
│
├── 反向测试: 把 H 改成 expected, E0 消失吗?
│   │
│   ├── 否 → H 不是 (不是 sufficiency), 退到更上游
│   └── 是 → 继续
│
├── 正向测试: 把 H 改成 broken, E0 出现吗?
│   │
│   ├── 否 → H 不是 (不是 necessity), 退到更上游
│   └── 是 → 强 RC 候选!
│
└── 跨越本模块边界了吗?
    │
    ├── 是 → RC 在隔壁模块, 转交
    └── 否 → 强 RC, 准备交付
```

### 反过来: root cause 是不是这个模块本身的问题?

**判定标准: 追踪的因果信号超出了当前模块。**

含义:

- 如果再往上一层就跨出了 "本模块" 的 instance boundary, 那当前模块**只是受害者**, root cause 在隔壁。
- 这种情况下,**不要**试图用本模块的 fix 来"封住"问题。RC 报告里必须标注: "RC 来自 `<other_module>`, 当前模块只是 propagation point"。

**模块边界判定 — 类型细化**

| 边界类型 | 表现 | 处理 |
|---------|------|------|
| **物理边界** | 候选信号在 `other_module/foo` | 立刻转交 |
| **interface / modport 边界** | 候选信号是 modport 信号 | 看 interface body 在哪个模块, 跟随那个模块 |
| **package 边界** | 候选信号是 typedef / parameter | 通常**不是**模块问题, 而是 packaging / build issue |
| **generate 边界** | 候选信号在 generate 内, 当前跳转不出去 | 加 `generate_id` 进 chain, 单独 block |
| **DPI 边界** | 候选信号来自 C 调用 | 跳过 C 内部, 标记 `kind: dpi_call`, RC 转交 |
| **跨时钟域** | 候选信号跨到另一个 clk 域 | 进入 §9 处理, 不一定是物理"模块"问题 |

### toggle test 标准 (修订版)

| 维度 | 标准 |
|------|------|
| **Inject** | 修改 RC 处一行代码 (注释 / no-op / 强行覆盖) |
| **Inject result** | 跑 sim, E0 必须**重现** (或同等错误) |
| **Remove** | revert 修改 |
| **Remove result** | E0 必须**消失** |
| **Iterations** | **至少 3 个不同 seed**, 都需通过 |
| **Build variation** | **至少 2 种 build 模式** (debug, release) 验证 |
| **Counter-example search** | 主动找 "条件在但 RC 不在" 的情形, 否定必要性 |

### 实操要点

- **"5 步全跑过才像 RC"**: 不是"有 X 出现" = RC, 必须 5 个判断全过一遍。
- **toggle test 是决定性的**: 不是 RC → toggle test 失败 (注入后没复现) 或反向失败 (移除后还在) 都能直接证伪。
- **承认"我可能钻错了"**: 中途发现越追越像"其他模块的活", 立刻退回上一个有意义的 hop 重选。
- **回到本模块的边界**: 模块边界外的 RC, 不要污染本模块的 fix 决定。

### 反模式
- ❌ "X 出现所以是 RC" — 还需要 toggle test
- ❌ "时间最早所以是 RC" — 时间最早 ≠ 因果最早 (earlist ≠ causal)
- ❌ "都解释了所以是 RC" — 但没解释清楚 toggle test 的对称性
- ❌ toggle test 只跑 1 个 seed 就宣布 RC — 重现性可疑
- ❌ 把 module boundary 外的 RC 当本模块 bug 修 — 跨模块污染

---

## 8. Per-step Self-Check (NEW)

每个 step 完成后跑这个检查, 不要跳。

### Step 1 完成后

- [ ] E0 节点的 4 个字段都有 (错误信息 / 时间 / 信号路径 / 文件:行)?
- [ ] E0 时间**早于**所有后续证据节点的时间?
- [ ] 有保存 chain.json 索引的最早时间戳?

### Step 2 完成后

- [ ] 候选信号 ≥ 1 个?
- [ ] 每个候选都有语义类型 (`drive` / `control` / `load` / 其他)?
- [ ] 至少发现 1 个 `drive` 或 `condition` 类信号?
- [ ] 没有把 clk/reset 当成待追溯的 signal?

### Step 3 完成后

- [ ] 每个候选都有"最近变化时间 + 值"?
- [ ] 时间**严格早于** E0?
- [ ] X/Z 信号已经**特殊标记**?
- [ ] 把所有这些中间产物 snapshotted 到 `1_evidence/signal_snapshots/`?

### Step 4 完成后

- [ ] 至少 1 个 RC 候选分数 ≥ 9?
- [ ] 排除了"明显不相关"反例库中的所有项?
- [ ] 逻辑推理用了**至少 1 个**系统知识 (不是纯看时间 + 语义)?

### Step 5 完成后 (最终交付前)

- [ ] RC 决策树每个分支都走过?
- [ ] toggle test 通过 (Inject 重现, Remove 消除) ≥ 3 seeds?
- [ ] 至少 2 个 build 模式验证?
- [ ] 模块边界判定明确了 (本模块 / 跨模块)?
- [ ] Section B (Discrimination) + Section C (Self-Check) 从 `checklists.md` 全 Yes?

---

## 9. 跨时钟域 / 异步处理 (NEW)

> 这一章在 Step 2 和 Step 3 之间用, 把"是不是 CDC 问题"这个判断提前, 节省时间。

### 9.1 什么时候进入 CDC 路径

| 信号 | 标记 |
|------|------|
| 候选 S 在域 A, E0 在域 B, A ≠ B | `cdc: A → B` |
| 候选 S 通过两级 flop CDC | `cdc: sync_flop` |
| 候选 S 通过 handshake (req/ack) 跨域 | `cdc: handshake` |
| 候选 S 本身就是 reset 但 reset 在多个时钟域 | `reset: cdc_pair` |
| 候选 S 直接连到 X-propagation 链 | `xprop: true` |

### 9.2 CDC 场景下的 RCA 姿势

普通 RCA 假设"信号变化 → E0 沿时间链传播"。
CDC 场景下需要补:

1. **在 S 域和 E0 域**分别跑一次时间对齐, 看 S 的变化**真的能传到 E0 的域**吗?
2. **async reset 撤销 race** — 跨域信号在 reset 撤销的瞬间可能正好命中 E0 域的 setup/hold 窗口, 产生 metastability, 不一定同步。
3. **handshake 的 req 跨域被 ack 错配** — req 在 S 域拉高, ack 在 E0 域拍回, 但 ack 路径走了一条没有被 sync 的 combinational path。
4. **复位路径在 reset 之后**还有 S 域在 toggle, 但 E0 域不采样 → 这是**普通跨域不是 RC**, 排除。

### 9.3 X-propagation (X-prop) 专项

X 出现的典型路径:

- `uninitialized flip-flop` (没被 reset 清)
- `bus 多 driver 冲突`
- `case 没有 default, 落了 don't-care`
- `function 调用返回 X (没实现)`
- `DPI 调用失败 + 没 return 值`

**X-propagation 是顶级 RC 候选**, 因为它经常是"为什么所有相关信号都变 X" 的真相, 而不是某根信号单独错。

### 9.4 Reset race 专项

Reset race 的特征:

- 同一信号被两个 reset 序列先后清, 后到的覆盖先到的, 但先后顺序**因 seed 而异**。
- 这种 RC **必须 toggle test 多个 seed**, 1 seed 命中不代表全部命中。

### 9.5 Metastability 边界

不要试图从波形上**直接观察** metastability:

- Metastability 在波形上看起来像 `X`, 但 `X` 可能是别的来源。
- 区分方法: 看 X 的**分布** — metastability 通常只影响 1-2 个 flop, X-prop 可能影响整链。
- 真正的 metastability 要用 formal CDC 工具证明, 不是一个 sim 能确诊的。

---

## 10. 加速技巧 (NEW)

### 10.1 缓存策略

| 数据 | 什么时候缓存 | 缓存位置 |
|------|-------------|---------|
| parse_uvm_log 结果 | 一次跑 8+ 遍时 | `1_evidence/log_summary.json` |
| sv-query trace 结果 | 跨多个 hop 复用 | `1_evidence/trace_cache/<path>.json` |
| waveform snapshot | 跨 hop 复用 | `1_evidence/signal_snapshots/<node_id>_<time>.json` |
| 决策日志 | 不重复加, append | `2_decisions/decision_log.json` (append-only) |

### 10.2 批处理

**最值得批处理的步骤**: Step 2 (sv-query trace) + Step 3 (wave 批量 trace)。

```bash
# Step 2 批处理示例: 一次跑 10 个候选的 fanin
for p in $(echo "$CANDIDATES" | tr ',' '\n'); do
  sv-query trace fanin --path "$p" --depth 3 &
done
wait

# Step 3 批处理示例: 上面 §5 给的 trace_candidates.sh
```

### 10.3 可并行 / 不可并行

| 步骤 | 可并行? |
|------|---------|
| Step 1 + Step 2 同跑 | OK (跑 log parse + 第一个 sv-query trace 不冲突) |
| Step 3 多个候选并行 trace | OK (原子工具都是无副作用的) |
| Step 4 评分 | 不能并行 — 评分本身是思考过程 |
| Step 5 toggle test | 不能并行 — 互相依赖 A→B→A 的因果 |

### 10.4 早期退出

| 信号 | 退出方式 |
|------|---------|
| Step 1 中发现 log 啥都没 (但你说 sim 挂了) | **问题在 simulator / testbench, 不是 DUT**, 退出 RCA 流程 |
| Step 2 中没有任何信号能 trace 上游 (候选 = 0) | 候选是顶层 input, 退出 (转 interaction 错误, 不是 DUT 错) |
| Step 3 中所有候选都没变化 | **RC 是 X-prop**, 直接进 §9.3 |
| Step 4 评分都 ≤ 5 | **收集面不够**, 加收集面回到 Step 2 |
| Step 5 决定 RC 在别的模块 | **转交, 不要硬 fix 本模块**, 转过去 |

### 10.5 减速场景 (避免这些)

| 减速陷阱 | 怎么办 |
|---------|--------|
| 在波形图上来回扫几十次 | 用脚本批量 snapshot |
| sv-query 每次重 build index | sv-query 在 `~` 有 cache, 第一次慢, 之后走 cache |
| 跨 n 个模块追一个 signal | **模块边界规则**约束你, 跨出去就停下 |
| 用 strings / grep 在 1GB log 找东西 | 用 `parse_uvm_log.py --first-error` 跳过全文 |

---

## 11. 增量沉淀约定 (How to add to this playbook)

跟 raw 版一样, 但 enhanced 版鼓励**附录式**追加:

```
## <新章节>: <场景描述>

### 触发条件
- ...

### 输入 / 输出 (与 §N 的差异)
- ...

### 实操要点 / 反模式
- ...
```

新章节加在 §10 之后, §11 (本文) 之前, 让结构保持稳定。

---

## TL;DR

> **Debug 不是"找第一个看起来可疑的信号", 是"按 5 个步骤的顺序, 把每个 hop 都拿到证据, 直到不能再追为止"。**
>
> Enhanced 版在 raw 版基础上加了:
> - **§1 三种 debug 模式** — 决定你从哪儿出发;
> - **每步的触发条件 / 决策矩阵 / 命令模板 / 中间产物模板** — 复制即可用;
> - **§8 Per-step self-check** — 5 个 step 完成后做 2-3 个 yes/no, 防止跳步;
> - **§9 跨时钟域 / 异步** — CDC / X-prop / metastability 专项;
> - **§10 加速技巧** — 缓存 / 批处理 / 早期退出。
>
> 凭感觉 debug 在 80% 的 case 里能蒙对, 在剩下 20% 里浪费一整天。

## Output Artifacts & Discipline

> 交付物 + 操作纪律( **3 个产物 + 5 条纪律** )不在本手册范围, 见 [`output-artifacts-and-discipline.md`](output-artifacts-and-discipline.md)。
> 该文件定义了 "RC_file.yaml 必须脚本生成" 等硬约束,跟本手册的"现场实操"互补。
