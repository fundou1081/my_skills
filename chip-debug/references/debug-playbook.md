# Debug Playbook — Field Manual for Hands-On RCA

> **性质说明**: 这是一份**实操手册**, 来源于现场手动 debug 的经验沉淀。
> 不追求方法学的严密完整, 只追求"打开就能照着用"。
>
> - 上游方法学骨架: [`rca-workflow.md`](rca-workflow.md)
> - 工具合约: [`atomic-tools.md`](atomic-tools.md)
> - 准入条件清单: [`checklists.md`](checklists.md)
> - 工具桥接: [`tools-and-bridges.md`](tools-and-bridges.md)
>
> 当方法学骨架说"做逆向追踪"时, 本文件告诉你"**怎么**做逆向追踪"——比如去哪个 log 找、用什么工具搜、保留什么字段。

---

## 0. 总体循环 (Manual Debug Loop)

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

> 关键: **第 5 步如果答案是"否"**, 必须**回到第 2 步**, 而不是跳到第 1 步或第 3 步。1 步已是定锚, 3 步是执行, 中间的 2/4 才是思维劳动。

---

## 1. 从 log 定位 1st failed

### 目的
锁住**问题入口**, 给后续所有追溯一个**确定的出发时间**。

### Input
- **sim log** (VCS / Questa / Xcelium / Verilator 任一种)

### Output
四个字段, 缺一不可:

| 字段 | 含义 |
|------|------|
| **错误信息** | UVM_ERROR / UVM_FATAL / SVA fail 的完整原文 |
| **发生时间** | 仿真时间戳, 标准化到 ns |
| **涉及到的信号路径** | hier path, 如 `tb.env.scoreboard.mismatch` |
| **报错的文件及对应行数** | `dut/cpu/alu.sv:142`, 来源是 log 中的 `at <file>:<line>` 或源码反查 |

### 主要工具
- **log 读取** — `parse_uvm_log.py` (支持 VCS/Questa/Xcelium/Verilator auto-detect, 见 `references/tools-and-bridges.md`)
- **源码定位** — `sv-query trace define --path <signal>`, 拿到信号定义文件:行
- **搜索** — `grep` / IDE jump-to-definition 配合信号全路径

### 实操要点
- **找最早**, 不是找最严重。`UVM_FATAL` 通常在 `UVM_ERROR` 之后出现, 它可能是雪崩产物。
- **同一时间多错误**: 取**最深层 hier path** 作为 L1 切入点。其他同时间的错误列入"次要异常"清单。
- **没有文件:行数怎么办**: 不要硬填 "未知", 改成 `source: log:<file>:<line>` 注解 + 时间戳即可。后续再补。

### 反模式
- ❌ 只看 `grep ERROR` 不看时间, 把第一个错误的判断丢了
- ❌ 把 SVA fail 当成 log 行的副产品不重视 (它经常是早于 UVM_ERROR 的真相)
- ❌ 把 FATAL 当成 root cause 候选 (FATAL 通常是 abort 的信号, 不是问题源头)

---

## 2. 追踪信号的 trace / load / control 语义信息

### 目的
从第一步锁住的信号出发, **列出所有有因果关系的候选信号**, 构建可能的下一步追溯目标。

### Input
- 信号 path (来自步骤 1)
- 该信号的源码 (从 T02 拿到的 `definition_site`)

### Output
每个候选信号一组字段:

| 字段 | 含义 |
|------|------|
| **路径** | 因果信号的完整 hier path |
| **语义关系** | `drive` / `load` / `control` / `mux_select` / `enable` / `clock` / `reset` |
| **代码片段** | 几行关键源码, 最好能复制粘贴 |
| **文件及行数** | 定位证据 |

> 一句话: 这一步拿到的是 "**为什么这是个候选**" 的**静态证据**。

### 主要工具
- **语义提取相关** — `sv-query trace evidence` / `sv-query trace fanin` / `sv-query trace fanout`
- 也可用 `code_rels` 工具 (T04 合约)

### 实操要点
- **多驱动是常态**: 一根 net 多个 `assign` 是常事, 不要误以为是 bug 候选。
- **clock/reset 优先排除**: 如果追溯到 `clk` 或 `rst_n`, 这是**边界条件**, 不是 root cause (除非 clk 本身有问题)。
- **记录每个候选的语义类型**, 后面筛选用:

| 关系类型 | 这意味着 |
|---------|----------|
| `drive` | 写入方, 真实改变信号值的位置 |
| `load` | 读取方, 不改变值, 只对值敏感 |
| `mux_select` | 控制 driver 选择哪个数据通路的条件 |
| `enable` | 控制 driver 是否生效的门控信号 |
| `condition` | always block 的 if/case 条件 |

### 反模式
- ❌ 拿到候选列表就跳过第 3 步, 直接脑补因果 (没数据)
- ❌ 把 `load` 当作 `drive` 处理 (load 不会改变被调查的信号, 只会观察)
- ❌ 把 control/condition 类的信号优先级跟 drive 类混为一谈 (它们本质不同)

---

## 3. 在波形上找每个因果信号的最近变化 + 值

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

### 主要工具
- **波形相关** — VCD / FSDB reader (verdi nwave, gtkwave, surfer; 见 T05–T08 合约)
- **log 时间对齐** — 用 parse_uvm_log 拿到的 timestamp 作为定位锚点

### 实操要点
- **对齐时间**: 波形上信号变化时间必须**严格早于** 1st failed 时间, 否则不是可信因果源。
- **距离加权**: 离 1st failed 越近的信号变化越可疑, 但**不要只看距离**。
- **批量扫多信号**: 如果一次手动扫 5+ 信号, 用脚本批量 snapshot, 不要凭眼睛从波形图挨个读 — 容易漏掉细节。
- **X / Z 状态特殊关注**: X 是高频电平冲突或未初始化的标志, Z 是高阻。两者都强烈指示 root cause 候选。

### 反模式
- ❌ 看到信号**等于预期值**就直接跳过 (有些 bug 是"该断电时未断", 不是"值不对")
- ❌ 同一信号在多个层级反复 trace 浪费时间 (find upstream once, record it)
- ❌ 忽略 delta_ns 极小的变化 (< 1ns 在某些时钟域是 setup/hold 边界, 极重要)

---

## 4. 筛选最具有因果关系的信号

### 目的
把候选列表里的"可能相关"过滤成"**最相关**", 通常每个 hop 只挑 1-2 个继续向上追溯。

### 主要依据 (按权重)

1. **语义关系** — `drive` 比 `load` 重要, `condition` 比 `mux_select` 更上游。
2. **trace / load / condition** — 类型决定它在因果链中的"位置权重"。
3. **波形上的变化时间距离** — 越靠近 1st failed 越值得怀疑 (但不是最相关, 见下条)。
4. **系统知识 / 逻辑推理** — 比如 "这个信号在 RTL 里被 force 过, 应该排除" / "这个 reset 信号是 cold reset, 一直在稳态, 不像问题源"。

### 实操要点
- **不要只用时间距离挑选**: 一个信号离 1st failed 100ns 远但**直接驱动**目标, 比一个离 1ns 但只是 `load` 的信号更值得追。
- **找出"反例信号"**: 没变化的信号也是证据 (说明它不是这个 hop 的罪魁)。
- **逻辑推理压倒波形扫描**: 有时候靠"这个信号应该是 mux 的 select" 直接锁下一跳比扫波形快。**但推理完必须回波形验证。**

### 反模式
- ❌ "我这个模块不熟, 看起来每个都可疑" — 停下, 回去读 RTL, 画出 data flow 后再筛
- ❌ 只看时间不看语义 — 容易在下游信号浪费时间
- ❌ 只看语义不看时间 — 容易挑到一个稳态信号当突破点

---

## 5. 判断是否为真实的 root cause

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

### 反过来: root cause 是不是这个模块本身的问题?

**判定标准: 追踪的因果信号超出了当前模块。**

含义:

- 如果再往上一层就跨出了 "本模块" 的 instance boundary, 那当前模块**只是受害者**, root cause 在隔壁。
- 这种情况下,**不要**试图用本模块的 fix 来"封住"问题。RC 报告里必须标注: "RC 来自 `<other_module>`, 当前模块只是 propagation point"。

### 实操要点

- **"5 步全跑过才像 RC"**: 不是"有 X 出现" = RC, 必须 5 个判断全过一遍。
- **toggle test 是决定性的**: 不是 RC → toggle test 失败 (注入后没复现) 或反向失败 (移除后还在) 都能直接证伪。
- **承认"我可能钻错了"**: 中途发现越追越像"其他模块的活", 立刻退回上一个有意义的 hop 重选。
- **回到本模块的边界**: 模块边界外的 RC, 不要污染本模块的 fix 决定。

### 反模式
- ❌ "X 出现所以是 RC" — 还需要 toggle test
- ❌ "时间最早所以是 RC" — 时间最早 ≠ 因果最早 (earlist ≠ causal)
- ❌ "都解释了所以是 RC" — 但没解释清楚 toggle test 的对称性

---

## 6. 交叉引用: 与方法学骨架的对应

| Playbook 步骤 | rca-workflow.md 阶段 | atomic-tools.md 合约 |
|--------------|----------------------|----------------------|
| 1. log 定位 1st failed | Stage 1 (Lock entry) | (parse_uvm_log.py 是 T05/T06 的 log 端 anchor) |
| 2. 语义 trace 因果信号 | Stage 2.Lk | T01, T02, T04 |
| 3. 波形时间节点 | Stage 2.L{k+1} | T05, T06, T08 |
| 4. 筛选最相关 | Stage 2/3 决策点 | T07 (双信号对齐) |
| 5. root cause 判定 | Stage 3 / 4 / 5 | (无单独 tool, 而是用 checklists.md Section A/B/C) |

---

## 7. 增量沉淀约定 (How to add to this playbook)

当你在实战中有新心得, 按以下结构 append 到对应章节:

```
### (auto): <场景描述>
- **触发条件**: 什么样的信号/症状会让你想做这个动作
- **执行步骤**: 1-2-3
- **避免**: 反模式
- **相关工具**: 哪个原子 (T0X) 或哪个脚本
```

不要动现有的 1-5 骨架, **append** 而不是 **rewrite**, 这样以后回看能看出方法的演变。

---

## TL;DR

> **Debug 不是"找第一个看起来可疑的信号", 是"按 5 个步骤的顺序, 把每个 hop 都拿到证据, 直到不能再追为止"。**
>
> 每一步都有明确的 input / output / 工具, 任何一步跳过, 都叫 "凭感觉 debug"。
>
> 凭感觉 debug 在 80% 的 case 里能蒙对, 在剩下 20% 里浪费一整天。
