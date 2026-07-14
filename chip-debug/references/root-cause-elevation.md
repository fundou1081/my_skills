# Root Cause Elevation — From "This Bug" to "Class of Bugs"

> **性质说明**: 这是一份**事后升华手册**。
> RCA 主线给出"**这一个 bug 的根因 + 一个 fix**"。
> Elevation 给出"**这一类 bug 的根** —— 把 fix 升到设计、架构、风格、外推四层"。
>
> 上游: [`SKILL.md`](../SKILL.md) ·
> [`rca-workflow.md`](rca-workflow.md) ·
> [`debug-playbook-enhanced.md`](debug-playbook-enhanced.md) ·
> [`checklists.md`](checklists.md) ·
> [`output-artifacts-and-discipline.md`](output-artifacts-and-discipline.md)

---

## 0. 为什么需要这层

RCA 找 RC 是**横向的**: 在一个 bug 内部向上追因。

Elevation 是**纵向的**: 从这一个 RC 出发,**往上抽到** 几个更高层的根:

| 维度 | 回答问题 |
|------|---------|
| **Design** | 这个 RC 是不是模块设计意图本身不清? |
| **Architecture** | 这个 RC 是不是组件分工/接口/数据流的结构性问题? |
| **Style / Convention** | 有没有一条 coding rule / 静态检查能阻止这类 bug 复发? |
| **Generalization** | 这个 bug 类是不是跨 IP / 跨 project 都可能存在, 需要做 audit? |

> 不做 Elevation 的后果: 修了这一处, 下次同类 bug 在别的 IP 重新出现, 又得重新 RCA 一遍。
>
> 做了 Elevation 的好处: 这个 fix 变成"防御一类 bug"的杠杆。

---

## 1. 触发条件 (When to elevate)

RC 报告完稿后, 默认**不**强制做 Elevation。在以下场景**应**做:

- RC 触发 CI / blocked release (S0 / S1)
- 同类 bug 在过去 6 个月**出现过第二次**
- 设计团队对 RC 的根因表态"没想到" / "这不应该"
- 修复后, 团队其他人表达"我记得另一处可能也有"

否则, 可以选择不做, 但**至少在 §5 (Suggested Fix) 旁加一行 note**:

> "Elevation skipped — not Severity S0/S1; no recurrence; not architecturally interesting." *签上日期 + 决定人*

---

## 2. 4 个维度详解

每个维度都按**输入 / 核心问题清单 / 输出**三段式展开。

### 2.1 Design (设计意图不清)

#### 输入
- 已完成的 chain.json
- 被调查模块的 spec / 设计文档
- RC 处的代码上下文

#### 核心问题 (问自己)

1. **设计意图是否清楚?** "这个信号在 reset 后应当 X" 这种 spec 是否写得清楚? 如果 RC 是由 spec 模糊引起, 那是 design 缺陷。
2. **边界是否定义?** 信号的有效值域 / 边界条件 / 错误状态是否在 spec 里明确?
3. **错误状态是否有 sink?** 信号出错(X/Z/未初始化)应该被谁观察到? 设计上有没有这个监督位?
4. **行为是否可预测?** 给一段波形/spec, 一个新人能否推断出每个 cycle 的预期状态?

#### 输出 (Design 维度)

```yaml
design_elevation:
  issue_is_design_rooted: yes | no | partial
  spec_gaps:
    - "valid region for ADDR not declared"
    - "no constraint doc for randomization policy"
  design_proposal:
    - text: "Add addr validity check + monitor"
      where: dut/apb_slave.sv::addr_valid_o
      optional: false
  intent_clear_post_fix: yes | no
```

### 2.2 Architecture (架构层次)

#### 输入
- RC 涉及的多个模块 (跨模块追踪结果)
- 系统架构图 / 模块依赖
- 已有 verification infrastructure (scoreboard / monitor / agent)

#### 核心问题

1. **这是 propagation point 还是 root?** RC 报告里明确标了 boundary。如果 RC 不在本模块, 是上层哪个?
2. **谁应该 catch?** 是否有更早的模块应该 catch / 反应 / 上报? 如果没, 是架构缺位。
3. **接口契约清晰吗?** 跨模块边界传递的参数 / 状态, 是否有明确定义和检查?
4. **monitor / scoreboard 完备吗?** 有没有 missing coverage — 这是 E0 没能被早期 sensor 抓住的原因?
5. **dependency direction 对吗?** 上层不该依赖下层。如果颠倒, 是架构债。

#### 输出 (Architecture 维度)

```yaml
architecture_elevation:
  rc_is_local: yes | no
  rc_propagation_path: [src_module, ... , impact_module]   # RC 在 src, 但在 impact 被观察
  monitor_or_check_missed_at:
    - "no addr_valid_o in dut.apb_slave"
    - "no cross-IP reserved-region check"
  architectural_proposal:
    - text: "Add global reserved-region policy + monitor"
      scope: design | infrastructure | tooling
      optional: false
  debt_register_entry:
    - "DEBT-XXX: APB reserved-region audit (tracked in TODO)"
```

### 2.3 Style / Convention (风格与约定)

#### 输入
- 项目的 coding style 文档
- 类似 bug 在历史 fix 里用什么 idiom 修的
- lint 工具配置 (verible, slang, surelog, etc.)

#### 核心问题

1. **是否有 lint 规则能 catch?** 这次 bug 是否能加进 lint 静态检查?
2. **是否有命名约定让人警觉?** 比如"所有 X 类信号必须以 `_vld` / `_q` 结尾", 这种约定能否帮新人避开?
3. **是否有 template / boilerplate?** 写新 component 时有没有现成的约束模板? 这次 bug 是不是没模板导致的?
4. **review checklist 是否 capture?** PR review 的 checklist 是否有这一类? 没有的话要加。
5. **是否进入 oncall / regression playbook?** 这类 bug 的 RCA 应该出现在 playbook 里, 让下个 oncall 一眼看到。

#### 输出 (Style 维度)

```yaml
style_elevation:
  bug_class: "constraint over-broad"  # 类别, 用于 lint/style rule
  static_check_rule:                   # 提议的可加 lint rule
    - kind: sv_constraint_audit
      rule: "all `inside {...}` should not span multiple disjoint ranges unless justified"
      tool: verible-lint | custom
  convention_suggestion:
    - text: "addr constraints use `inside {[BASE:TOP]}` only; reserved regions asserted in check_phase"
  template_or_boilerplate:
    - target: new_apb_test.sv
      add: "`addr_vld_check()` boilerplate"
  review_checklist_addition:
    - "PR template: 'Are randomization constraints tightened?'"
  playbook_addition:
    - "Debug Playbook §<X>: 'APB addr miscompare'"

### 2.4 Generalization (外推: 这类 bug 多大概率在别处)

#### 输入
- RC 的"信号类型 / 数据路径 / 抽象层"
- 项目 / 组织里相似组件清单
- grep / lint scan 的能力

#### 核心问题

1. **这个 bug 类的"指纹"是什么?** 用一句话/正则能 grep 出来?
2. **在哪些组件重复存在?** 用 fingerprint 去扫 `代码库` 标出 suspect。
3. **修复后, 是否需要 cross-cutting cleanup?** fix 是局部还是系统性的?
4. **风险评估**: 假设同类 bug 已经在别处触发, 影响范围多大?

#### 输出 (Generalization 维度)

```yaml
generalization_elevation:
  bug_fingerprint:
    regex: "addr\s+inside\s*\{[^}]*\[[0-9]+'[hH][0-9a-fA-F]+:[0-9]+'[hH][0-9a-fA-F]+\]"
    description: "constraint with multiple disjoint bit-range slices"
  audit_plan:
    - command: "grep -rE '<regex>' tb/ tests/"
      scope: tb/, tests/
      out_file: tools/audit_results/addr_constraint_audit_<date>.txt
    - command: "<other scan tool>"
      scope: <which dirs>
  cross_component_suspect:
    - component: <other_ip_with_similar_pattern>
      risk_level: high | medium | low
  remediation_plan: see §5 below
```

---

## 3. Elevation 输入 / 输出 (Summary)

### 输入

| 项 | 来源 |
|----|------|
| 已完成的 RCA (chain.json) | `1_evidence/evidence_chain.json` |
| 已锁定的 RC | `chain.nodes[RC]` |
| 模块 spec / 架构图 | (项目自带) |
| lint / style 工具配置 | (项目自带) |
| Coding style 文档 | (项目自带) |

### 输出

| 产物 | 落点 |
|------|------|
| **elevation_report.md** (或 .yaml) | `9_output/elevation_report.md` |
| **RC_file.yaml 加 `elevation` section** | 由 `build_rc_file.py` 渲染时合并 |
| **chain_report.md 加 "Elevation" 章节** | 模板升级后填入 |
| **audit_search_plan.md** (可选, 来自 §2.4) | `9_output/audit_search_plan.md` |

---

## 4. Elevation 操作纪律 (Mandatory invariants)

跟 RCA 主线一致,**绝不编造, 必须源出**。

| 纪律 | 含义 |
|------|------|
| ❌ "我觉得其他 IP 也可能有" — 不算证据 | 必须用 §2.4 的 grep / lint 扫出。 |
| ❌ "加个 lint rule 就好了" — 没指定 rule 怎么写 | 必须给 lint rule 的 kind/pattern/tool 三件套。 |
| ❌ "架构上重新设计" — 没写影响面 | 必须给 scope (local / subsystem / global)。 |
| ✅ 每条 elevation 都要可证伪 | 比如 "audit grep" 跑出 empty 则结论作废。 |
| ✅ 跟 RCA 主线一致 | 不能超过已确认的 chain 范围。 |

---

## 5. Worked Example (APB `addr in reserved region`)

取 [`debug-playbook.md`](debug-playbook.md) + [`debug-playbook-enhanced.md`](debug-playbook-enhanced.md)
里的 APB 案例, 升华一下:

### Design 维度
- **设计 gap**: apb_slave 没有声明"合法 addr region"。 Spec 写了 addr 总线宽度, 但没写 "ADDR 为 0x0–0xFF"。
- **proposal**: 加 `addr_vld_o`, 在 spec 里明确 valid region。

### Architecture 维度
- **monitor 缺位**: 整个 TB 没有"reserved region 触发" 的 monitor。 这个 bug 是 E0 (scoreboard) 才发现, 太晚了。
- **proposal**: 在 `tb/agents/apb_addr_monitor.sv` 加一个 cross-cutting monitor,
  每个 APB IP 都 instantiate 一份, 既报 reserved-region hit 也报 scoreboard 错。
- **DEBT-XXX**: [架构债] 全 TB 没有统一的 reserved-region policy。

### Style 维度
- **bug class**: "constraint over-broad"。
- **lint rule** (kind: sv_constraint_audit):
  - verible: `--lint_rule SV-RAND-WIDE-REGION` (示意名, 实际命名以 lint tool 为准)
  - 规则: "`addr inside {}` 内**禁止**多段不相邻 range,除非注释解释。"
- **review checklist**:
  - PR template 加 "Are randomization constraints tightened for reserved regions?"
- **playbook**: 在 debug-playbook 加 §X.1 "APB Addr Reserved Region Miscompare" 子章节。

### Generalization 维度
- **fingerprint**: `addr\s+inside\s*\{[^}]*\[[0-9a-f]+\][^}]*\[[0-9a-f]+\]`
- **audit plan**:
  ```bash
  grep -rnE "addr\s+inside" tb/ tests/ \
      > tools/audit_results/addr_constraint_audit_2026-07-14.txt
  ```
- **risk**:
  - 中等。在 sv-query 跑过的 8 个 IP 中, 5 个有类似 pattern;其中 1 个 (axi_master) 已有 cyan suspicious 注释, 极可能 latent。
- **remediation**: 跑 audit 出 ≤ 5 个结果, 则逐个 review;出 > 10 个, 则:

### 最终输出 (Elevation summary, 进 RC_file.yaml)

```yaml
elevation:
  when: 2026-07-14
  decided_by: <author>
  design:        { ... 上面 ... }
  architecture:  { ... 上面 ... }
  style:         { ... 上面 ... }
  generalization:
    audit_run: <command + output path>
    findings:
      - file: <p>
        line: <n>
        risk: <level>
    action_items:
      - "<action 1>"
      - "<action 2>"
```

---

## 6. Anti-Patterns in Elevation

| 反模式 | 为什么不好 |
|--------|-----------|
| 把"fix 改成 bigger refactor" | 不是 Elevation, 是改架构; 单独走 design review。 |
| 写"应该加 lint rule" 但不指明 rule kind/tool/pattern | 等于没写。 |
| "其他 IP 可能也有" 但不跑 grep | 跟 "无证据猜" 没区别。 |
| Elevation 写完后没人 follow up | 写完就进 DEBT tracker (`tools/debt_tracker.md` 或 jira), 并写明 owner + due。 |
| 把 Elevation 当 RCA review 的一部分要求签字 | Elevation 是 best-effort 升华, 不是 gate; 让作者决定是否做。 |

---

## 7. 跟其他 references 的关系

```
rca-workflow.md (5 阶段)
   → 提供 RC (Stage 5 deliverable)
debug-playbook-enhanced.md (5 步实操)
   → 提供 hop-level "why"
checklists.md (RC 准入)
   → 提供 discrimination + self-check
output-artifacts-and-discipline.md (3 产物 + 5 纪律)
   → 提供产物标准 + hard rules
output-artifacts-and-discipline.md §4 time-monotonic
   → 跟本次"时间单调不变量" 是同一篇
root-cause-elevation.md (本文, ★ NEW)
   → 把 RC 升到 4 层 (design / arch / style / generalize)
```

---

## 8. 沉淀约定

按以下结构 append 到末尾 (§9 之后):

```
## <新维度>: <场景描述>

### 触发条件
- ...

### 输入 / 输出
- ...

### 反模式
- ...

### 示例
- ...
```

不要动现有 2.1–2.4 章节骨架, **append 而不是 rewrite**。

---

## TL;DR

> **RCA 找出 RC, Elevation 抽出"一类 bug 的根"。**
> 4 维:
> - **Design** — 设计意图不清晰? 增补 spec。
> - **Architecture** — 监控缺位 / 接口不清 / 监督错位? 加 monitor, 入 debt。
> - **Style** — 加 lint rule + review checklist + playbook。
> - **Generalization** — 跑 audit grep, 标出 latent suspects, 入 remediation。
>
> Elevation 不是必须的; 但每次重大 RC 都做一次, 半年内同类 bug 数量会显著下降。
