# Output Artifacts & Operational Discipline

> **本文件是质量约束层**。前面的 references / playbooks 说"做什么",本文件规定
> "**交付什么 / 怎么交付 / 不能交付什么**"。
>
> 上游: [`SKILL.md`](../SKILL.md) (硬规则) ·
> [`rca-workflow.md`](rca-workflow.md) (5 阶段) ·
> [`debug-playbook-enhanced.md`](debug-playbook-enhanced.md) (5 步实操) ·
> [`evidence-chain.md`](evidence-chain.md) (节点 schema) ·
> [`atomic-tools.md`](atomic-tools.md) (8 原子合约)

---

## 0. 为什么需要这层

RCA 流程跑完最大的复盘痛点不是"找不到 RC",而是:

- RC report 写完了, **但证据在哪?**
- 半年后有人 review, **说不清"你怎么想到的"**。
- 关掉 IDE 之后想继续, **前一步 trace 的工具输出没了**。
- 同样的 bug 再出现, **上次怎么定位的全记不清**。

这层文件解决的就是上面 4 个痛点。**三个固定产物 + 五条操作纪律**,缺一条就是"凭手感 debug",看起来完成,实际上下次还得重做一遍。

---

## 1. 三个输出产物 (Deliverables)

每个完成的 RCA 必须落地**这三个**产物,缺一不可。

### 1.1 RC File (供 review 的"真凶 + 因果链"摘要)

| 属性 | 值 |
|------|-----|
| 文件路径 | `9_output/RC_file.yaml` |
| 形式 | YAML (review-friendly, 支持 diff) |
| 生成方式 | **必须由脚本生成** (见 `scripts/build_rc_file.py`) |
| 模板 | `assets/templates/RC_file.yaml.template` |
| 大小 | 通常 80–400 行,取决于链长 |
| 读者 | 人 (reviewer / 未来自己 / 同事) |
| 时效 | RC 阶段结束后写入, 后续若链再变化, 重新生成 v2 |

**核心字段**

```yaml
session_id:        rca_session_20260714_091500
locked_entry:      # E0 节点
  time, signal, actual, expected, source
root_cause:        # RC 节点
  node_id, signal, file:line, snippet
causal_signals:    # 所有因果信号 (核心!)
  - path, role, in_chain_as, hop_count,
    semantic_relations (drive/load/control),
    source_location (file:line),
    observed_value, expected_value,
    waveform_changes (time + value)
constraints:       # 代码约束 / SV 表达式
reproducer:        # 最小复现 recipe
toggle_test:       # 反向验证
```

#### 关键约束 (针对 causal_signals)

1. **每个 hop 一个条目, 不能漏 E0 也不能多**。
2. **`hop_count` 必须从 E0 算起**: E0 = 0, E0 的直接 drive = 1, drive 的 drive = 2, ...
3. **`semantic_relations` 至少一个**: `drive` / `load` / `mux_select` / `enable` / `condition` / `clock` / `reset`。
4. **`source_location` 是文件:行, 不是 log 行号**, 因为日志的位置不可靠。
5. **`waveform_changes` 是列表**, 不止写最终值, 有几次变化写几次 (time + value)。

### 1.2 证据链报告 (chain report, 工具辅助生成的 markdown)

| 属性 | 值 |
|------|-----|
| 文件路径 | `9_output/chain_report.md` |
| 形式 | Markdown |
| 生成方式 | **必须工具辅助** (见 §6 Roadmap) |
| 模板 | `assets/templates/RC_report.md.template` (骨架, 渲染时填入) |
| 大小 | 通常 100–500 行 |
| 读者 | 人 (review, 跨模块沟通) |

**核心内容**

- 1 段摘要 (TL;DR)
- 因果链 ASCII 图 (从 RC 推回到 E0)
- 每个 hop 一段, 含 **observed value / expected value / source pointer / code snippet / waveform excerpt / 决策引用**
- Toggle test 结果
- Module boundary 判定
- 所有的 secondary anomalies 与哪个 hop 解释的映射表

> 这是"讲一个完整故事", 不是"列出原始数据"。
> 跟 RC file 不重: RC file 给 reviewer 跑去看一眼, chain_report 给人读完整故事。

### 1.3 探索结果记录 (exploration state, 落地到本地, 可恢复)

| 属性 | 值 |
|------|-----|
| 文件路径 | `2_decisions/decision_log.json` + `1_evidence/evidence_chain.json` + `1_evidence/signal_snapshots/` + `3_repro/` |
| 形式 | 多个 JSON + 目录 |
| 生成方式 | `evidence_chain.py` + `decision_log.py` + raw outputs |
| 读者 | 自己 (continue 时) + 同伴 (audit 时) |

**核心特点**

- 这是 RCA 的"机器可解析"真值源, **人不需要读**, 但**机器能完全重建过程**。
- 半年后打开 session 目录, 不需要回去读 sim log, 也不需要回去翻 wave, **从 chain.json 一路打开就能复现**。
- 每个 evidence node 必须能**反向追溯到一个 raw 工具输出 + 一个 source code 行** (§4 详述)。

---

## 2. 产物形式规范

### 2.1 RC File — fields × types

| field | type | required | 来源 | 例子 |
|-------|------|----------|------|------|
| `session_id` | string | Y | evidence_chain.json | `rca_session_20260714_091500` |
| `locked_entry` | object | Y | chain.locked_entry | E0 节点 |
| `root_cause` | object | Y | chain.nodes[RC] | `{node_id:"RC", signal, file, line, snippet}` |
| `causal_signals[]` | array | Y | chain.nodes (除 E0 和 RC) | 见上 |
| `constraints[]` | array | N | 手动标出 / 自动提取 | SV 表达式 |
| `reproducer` | object | Y | 手动 + 自动 | `{seeds, sequence, expected_outcome}` |
| `toggle_test` | object | Y | toggle test 输出 | `{ran, inject_result, remove_result, iterations}` |

### 2.2 Chain Report — sections × 内容

| section | 内容来源 |
|---------|---------|
| Symptom Summary | chain.locked_entry + chain.nodes[E0] |
| Causal Chain | chain.nodes 排序 (RC → E0) |
| Per-hop Evidence | 每个 chain node + 引用 tool output / code snippet |
| Falsification Evidence | decision_log (accept entries with tag=stage4.*) + 3_repro/ artifacts |
| Secondary Anomaly Coverage | decision_log (park entries) → 与 chain.node.id 关联 |
| Module Boundary | decision_log (tag=stage5.module_boundary) |
| Suggested Fix | 手动 review 后定 |
| Self-Check Checklist | checklists.md Section B + C |

### 2.3 Exploration State — 文件结构

```
rca_session_<ts>/
├── 0_input/                       # 原始 log / wave / script
├── 1_evidence/
│   ├── evidence_chain.json        # 主链
│   ├── signal_snapshots/          # 每个 hop 的 raw outputs
│   │   ├── L1_<t>.json
│   │   ├── L2_<t>.json
│   │   └── ...
│   └── log_summary.json           # parse_uvm_log 结果
├── 2_decisions/
│   └── decision_log.json          # 所有 hypothesis 的 verdict
├── 3_repro/                      # toggle test 跑过 / 准备跑
│   ├── inject_patch.diff
│   ├── remove_patch.diff
│   └── run_*.log
└── 9_output/
    ├── RC_file.yaml
    ├── chain_report.md
    └── exploration.md
```

> **任何一个目录缺失 = RCA 不可逆, 下次接不上。**

---

## 3. 五条操作纪律 (Operational Discipline)

这一节是硬约束, 跟 `SKILL.md` 里的"硬规则"是同一层, 但更具体。

### 3.1 所有已探索过程记录到本地 (含详细内容)

**约束**: 每走一步, 落盘一步, 内容含**原始 tool output**, 不只是 chain.json 的总结。

**做法**:

```bash
# Step 2: 跑完 trace 之后, 立刻保存 raw
atom T04 code_rels --path $P > 1_evidence/raw_T04_<signal>.json

# Step 3: 跑完 wave 之后, 立刻保存 raw
atom T06 wave_prev_change --path $P --ref_time $T > 1_evidence/raw_T06_<signal>.json

# Step 2 add node 时, source 字段必须指向 raw file
python3 evidence_chain.py add ... --source "raw:1_evidence/raw_T04_<signal>.json"
```

**反例**: "我看了下是 X" — **不接受**。

### 3.2 使用完整增量脚本 (从第一个 error 出发)

**关键 invariant**: **信号提取脚本每次都要从 E0 出发**, 不能"接着上一次 trace 的尾巴继续"。

**理由**:

- 接尾巴的 script 隐式依赖某次执行的内存状态, 不可重现。
- 从 E0 重新跑, 每次都是"完整拼图", 保证:
  - 任何 hop 都可以独立重跑
  - 中间数据丢了, 可以从 E0 重建
  - RC 改变后重跑, 可以增量 diff

**实施**:

- `scripts/build_chain.py <session_dir>` — 从 0_input 重新跑出整个 chain (用于"resume"和"verify")。
- 不要写"chain.append"的脚本, 只写"chain.replay(from=E0)"的脚本。

### 3.3 依赖工具实现所有细节的记录, 不要编造

**约束**: 任何写入 chain.json 的字段, 必须能从 `1_evidence/raw_*.json` / 源码 / 波形工具输出**机械追溯**。

**具体禁止**:

- ❌ "I recall this signal had a problem" — 必须有 tool output。
- ❌ "大概文件是这个" — 必须是 `T02 code_define` 的实际输出。
- ❌ "应该会有这个变化" — 必须是 `T06 wave_prev_change` 的实际输出。

**例外**:

- `note` 字段是 "tag"性质的, 可主观。
- `confidence` 是评分, 不强制 100% 来源于 tool (但应该 argue)。

### 3.4 所有细节都能反向追溯

**约束**: 给定任何字段, 都能"反向定位"回原始材料。

| 字段 | 反向追溯目标 |
|------|------------|
| `signal` | sv-query `trace define` 输出 |
| `file:line` | 源文件 `cat -n` |
| `time` | log 行或 wave snapshot |
| `value` | wave dump 的原始记录 |
| `relation` | RTL 代码段 (3-5 行上下文) |
| `decision verdict` | decision_log 的一条 entry |
| `RC report 一段话` | chain_report.md 的模板渲染 |
| `RC_file.yaml 一行` | chain.json node + tool output |

**验收命令**:

```bash
# 给定一个 RC file 里的因果信号, 能不能逆向找到 chain node + tool output?
grep "<signal>" 9_output/RC_file.yaml | \
  xargs -I {} grep -l {} 1_evidence/evidence_chain.json
```

### 3.5 使用脚本产生 RC 文件

**约束**: 任何最终交付的 `RC_file.yaml` / `chain_report.md`, 必须由脚本从 chain.json + decision_log.json 生成, **禁止手写后保存**。

**理由**:

- 手写容易遗漏 hop
- 手写跟 chain.json 容易脱节
- 脚本保证**单点真值** (chain.json), RC file 是 derived view

**实施**:

```bash
# 验证 RC file 是脚本生成的:
python3 scripts/build_rc_file.py <session_dir> --out 9_output/RC_file.yaml \
  --verify  # 确保 out 跟脚本输出 byte-identical
```

(见 `scripts/build_rc_file.py` / `scripts/test_build_rc.py`)

---

## 4. 反向追溯链路图 (Bi-directional Traceability)

### 4.1 主链 (Forward: Symptoms → Tools → RC)

```
[sim log]                                              [波形 .fsdb]
    │                                                       │
    ▼                                                       ▼
parse_uvm_log.py                                       atom T05/T06/T08
    │                                                       │
    ▼                                                       ▼
E0 (chain.nodes[0])  ─────►  L1 (chain.nodes[1])   ─────►  L2 ...
                                                                            ▲
                                                                            │
                                                            (semantic trace from T04)
                                                                            │
                                              sv-query T01/T02/T04  ◄───────┘
                                                            │
                                                            ▼
                                                  code: file:line
```

### 4.2 反向链 (Backward: From any artifact → raw data)

| 你想从哪儿出发 | 应该能反查到 |
|----------------|------------|
| `RC_file.yaml` 里一行 | chain.json 的对应 node + tool output (`1_evidence/raw_*.json`) |
| `chain.json` 一个 node | tool output + source file:line |
| `decision_log.json` 一个 decision | chain.json 中的 evidence_ref + tool output |
| `chain_report.md` 一段话 | chain.json + tool output 的具体编号 |
| `signal_snapshots/<file>.json` | tool 调用的 command + raw output |

### 4.3 强制性 Schema Invariants (脚本自动校验)

| Invariant | 校验方法 |
|-----------|---------|
| 每个 chain node 有 source | `evidence_chain.py validate` |
| 每个非 E0/RC node 有 relation | `evidence_chain.py forward-check` |
| 每个 decision 有 hypothesis + evidence_ref + verdict + reason | `decision_log.py validate` |
| **时间单调性** (RC → ... → E0 方向, 时间非递减) | `evidence_chain.py time-check` (NEW) |
| 每个 source 是 file 存在 | `evidence_chain.py validate --check-files` (TODO) |
| RC file 是脚本生成 | `build_rc_file.py --verify` |
| 链中无 "改写历史", 旧版本入 `_history/` | 文件系统 invariant |

### 4.4 时间单调不变量 (Time-Unidirectional Invariant) — NECESSARY

> **最后一句必读**: 当节点从 RC 到 E0 排列时, 仿真时间必须**单调非递减**。

文字上:
- 沿证据链**从症状向根因**走: 时间应该**递减或相等**。
- 沿证据链**从根因向症状**走: 时间应该**递增或相等**。

任何反序就是一个数据 bug — 要么 timestamp 写错, 要么 relation 错位, 要么 layering 反了。

**作为必要条件**: 不满足 time-monotonic 的链可能只是巧合相关, 不是因果。

**调用方式**:
```bash
python3 scripts/evidence_chain.py time-check <chain.json>
```

输出长这样 (3 个 timestamped hops):

```
   NODE  LAYER        TIME       DELTA  STATUS
  ------------------------------------------------------------
     L2      2      8430.0           —  head
     L1      1      8444.0         +14  OK
     E0      0      8450.0          +6  OK
```

反例 (L2 时间错写晚于 E0):

```
     L2      2      9000.0           —  head
     L1      1      8444.0        -556  VIOLATION
     E0      0      8450.0          +6  OK

# INVARIANT VIOLATIONS:
  L2 -> L1: time DECREASES by 556 ns
exit=1
```

**作为 gate**: 在 CI / pre-merge 时跑 `time-check`, 不通过则不发 RC 报告。

---

## 5. 反模式 (这些行为直接拉低产物质量)

| 反模式 | 后果 | 怎么改 |
|--------|------|--------|
| 在 chat 里"我看出" RC, 不写工具调用 | 不可复现 | 每次写 `:tool_call → :observation` 入 chain |
| chain.json 只存"结论", 不存 `raw output` | 半年后无法 verify | 每个 node 的 `source` 指向 raw json, 不只是 "log:..." |
| RC file 手写一遍, 跟 chain.json 不一致 | 单一真值被破坏 | 用 build_rc_file.py 生成 |
| 给同事 review RC report, 但没附 `decision_log.json` | 不解释"为什么排除这个" | 交付包必须包含 decision_log |
| toggle test 只跑一个 seed 就说 "RC 稳了" | 漏掉 race condition | 至少 3 seed + 2 build mode |
| 探索到一半, "先 commit 再继续", 没存 discovery state | commit 之后接不上 | 任何 commit 之前先把 session 归档 |
| "我觉得是这个, 不用验证" | 不是 RC, 是猜测 | toggle test 必须跑 |
| 用 IDE 自己看波形图, 不存 snapshot | raw 数据蒸发 | 任何波形观察必须 snapshot 到 `1_evidence/signal_snapshots/` |

---

## 6. scripts 实现状态 / TODO

| 产物 | 模板 | 生成脚本 | 测试 |
|------|------|---------|------|
| `RC_file.yaml` (新版, rich fields) | ✅ `RC_file.yaml.template` (升级) | ✅ `scripts/build_rc_file.py` (实现) | ✅ `scripts/test_build_rc.py` |
| `chain_report.md` | ✅ `RC_report.md.template` | ⏸ 待实现 `scripts/build_chain_report.py` | ⏸ |
| `exploration.md` | ✅ `exploration.md.template` | ⏸ 待实现 `scripts/build_exploration_log.py` | ⏸ |

**当前已 ship 的脚本**:

- `scripts/parse_uvm_log.py` — log 端 anchor 提取
- `scripts/evidence_chain.py` — chain CRUD + 校验
- `scripts/decision_log.py` — decision log CRUD + 校验
- `scripts/build_rc_file.py` — RC_file.yaml 生成 (新)
- `scripts/test_sanity.py` — 基础单测
- `scripts/test_build_rc.py` — RC file 生成测试 (新)

**未 ship 的**:

- `scripts/atom.py` — 8 原子合约的真正实现 (T01-T08)
- `scripts/build_chain_report.py` — markdown 报告渲染
- `scripts/build_exploration_log.py` — exploration 报告
- `scripts/replay.py` — 从 E0 完整重跑

---

## 7. 增量沉淀约定

当 RCA 跑出新的产物 schema 或新的纪律时, 按以下结构 append:

```
## <新章节>: <场景描述>

### 触发条件
- ...

### 新产物 / 新纪律
- ...

### 反向追溯约束
- ...
```

不要动现有章节骨架, **append 而不是 rewrite**。

---

## 8. 与其他章节的关系

| 本文件 | 引用 |
|--------|------|
| §1 三个产物 | → templates + scripts in this skill |
| §3.5 脚本生成 RC file | → `scripts/build_rc_file.py` |
| §4.4 时间单调不变量 | → `references/evidence-chain.md` §Validation rules · `evidence_chain.py time-check` |
| (NEW) §5 RC 升华 | → `references/root-cause-elevation.md` |
| §6 反模式 | → `debug-playbook-enhanced.md` §5/10 各 Step 的反模式 |

---

## TL;DR

> **RCA 不是"找到一个 RC 就完事", 而是"交付 3 个产品 + 守 5 条纪律"**。
>
> 3 个产品:
> 1. **RC_file.yaml** — 给 reviewer 一眼看因果, **脚本生成**;
> 2. **chain_report.md** — 给读者完整故事, **工具辅助生成**;
> 3. **exploration state** — 给未来的自己 / 同伴, **可重建可恢复**。
>
> 5 条纪律:
> 1. **每一步落盘** raw output, 不能丢;
> 2. **从 E0 重跑**, 不接尾巴;
> 3. **依赖工具**, 不编造;
> 4. **全字段可反向追溯**;
> 5. **脚本产生 RC file**, 不手写。
>
> 缺一条 = 凭手感 debug, 看着完成实则下次还得重做。
