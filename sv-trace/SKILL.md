---
name: sv-trace
description: SystemVerilog 信号追踪器 — 给一个信号名, 返回该信号在 RTL 源码中所有的 driver (驱动) 和 load (负载), 含文件位置、scope 源码、时钟/复位、条件栈、层次路径、跨模块端口连接。每个 trace 都带**可证伪的代码证据链 (M5.1)**： 读回实际文件验证 source_expr/signal_name 真在该行, 输出 credibility_score (0-1) 和 is_verified 标记 — 让 LLM 和人能反查、决定要不要信。基于 pyslang 语义层分析, 支持多文件项目、Interface/Modport、跨模块层次路径、Streaming concat / StructuredAssignmentPattern / `inside` 等高级 SV 特性, 已验证 OpenTitan 30,218 drivers 0 warning。Use when (1) 用户给出 SV 代码片段, 问“这个信号被谁驱动 / 谁在读这个信号, (2) 调试 RTL 时需要查信号在哪个 always 块里被赋值, (3) 自动生成 driver/load 列表喂给 LLM 做代码理解, (4) 在大型 SV 项目 (OpenTitan 等) 中跨模块追踪信号, (5) 检测多驱动冲突 (always_ff 多次写同一信号) 并附证据, (6) 递归查 driver 链 / load 链, 链上每跳都带 evidence, (7) 验证 LLM 写的 SV 行为对不对 (credibility_score 量化), (8) 一次 dump 整个链为 JSON 喂 LLM (含 summary)。不要用 sv-trace 做 CDC / 面积功耗 / Lint / FSM 提取 / 约束分析 / 覆盖率建议 — 那些不在本项目范围。
---

# sv-trace — SystemVerilog Signal Tracer

给一个 SystemVerilog 信号名, 找出它所有的 driver / load, 加完整上下文 + 证据链, 喂给 LLM 或人用。

底层依赖: `pyslang >= 10.0` (兼容 10.x 和 11.x, 自动 fallback)

---

## Quick Start

### 安装

```bash
pip install sv-trace
# 验证
python -c "from signal_tracer import SignalTracer, trace_signal, __version__; print(__version__)"
```

### 最小示例 (单文件)

```python
from signal_tracer import trace_signal

sv = """
module counter (
    input  logic       clk, rst_n,
    input  logic [7:0] data_in,
    output logic [7:0] count
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) count <= 8'h00;
        else        count <= count + data_in;
    end
endmodule
"""

result = trace_signal("count", sv, "counter.sv")
for d in result.drivers:
    print(f"{d.source_expr} @ line {d.line} | clock={d.clock} reset={d.reset}")
    print(f"  cond={d.condition_stack}")
    print(f"  scope: {d.scope_text}")
```

输出:
```
8'h00 @ line 9 | clock=clk reset=rst_n
  cond=['!rst_n']
  scope: always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n) count <= 8'h00;
            else        count <= count + data_in;
        end
count + data_in @ line 10 | clock=clk reset=rst_n
  cond=['!rst_n']
  scope: ...
```

### 多文件 + 跨模块层次路径

```python
from signal_tracer import SignalTracer

t = SignalTracer()
t.add_file('top.sv', open('top.sv').read())
t.add_file('sub.sv', open('sub.sv').read())
t.build()

# 完全路径: 直查 top.u_mid.dout
r1 = t.trace('top.u_mid.dout')

# 后缀匹配: 聚合所有 *.dout (跨 instance)
r2 = t.trace('dout')
```

---

## When to Use

✅ **用 sv-trace**:
- 用户说"这个信号被谁驱动 / 谁在读"
- 调试 RTL bug, 找 driver 链 / load 链
- 喂 LLM: 自动生成 driver/load 列表当 context
- 多驱动检测 (always_ff 多次写同一信号 = 竞态)
- 验证 LLM 写的 SV 行为对不对
- 跨模块追踪 (top → sub → leaf)

❌ **不要用 sv-trace**:
- CDC (跨时钟域) 分析 → 那是 lint/CDC 工具
- 面积/功耗/时序估算 → 那是 synthesis 工具
- Lint / 静态检查 → 那是 verilator/iverilog
- FSM 提取 / 约束分析 / 覆盖率建议 → 不在范围
- TB 评分 / 代码质量评分 → 不在范围

---

## Core API (按场景分组)

### 1. 单文件 / 一次性 — `trace_signal()`

```python
from signal_tracer import trace_signal

result = trace_signal("sig", sv_code, "test.sv")
# result.drivers: List[TraceResult] — 所有 driver
# result.loads:   List[TraceResult] — 所有 load
```

### 2. 多文件 / 跨模块 — `SignalTracer`

```python
from signal_tracer import SignalTracer

t = SignalTracer()
t.add_file('top.sv', top_code)
t.add_file('sub.sv', sub_code)
t.build()  # 必须先 build 才能 trace

# 4 步匹配: 完全 → 数组前缀 → 后缀 → cross-module
result = t.trace('top.u_mid.signal_name')  # 全路径
result = t.trace('signal_name')            # 后缀匹配
```

### 3. 多驱动检测 (M1.5 + M5.1b)

```python
multi = t.find_multi_drivers()
# → Dict[signal_name, List[TraceResult]]
# 同一信号被 >1 个 scope 驱动 = 潜在 race condition
# 默认 verify=True, 每个 driver 的 _evidence_override 已自动填充
for sig, drivers in multi.items():
    print(f"⚠ {sig} 被 {len(drivers)} 个 scope 驱动")
    for d in drivers:
        ctx = d.to_context()
        print(f"   @ {d.file.split('/')[-1]}:{d.line}  credibility={ctx.to_dict()['credibility_score']}")

# 不要 evidence: t.find_multi_drivers(verify=False)
```

### 4. Driver 链 / Load 链 (M1.5 / M5.1c / M5.1e)

```python
# 上游 driver 链: 这个信号的 driver 用什么信号, 那个又用什么
chain = t.get_driver_chain('data_out', max_depth=10)
# → List[str]: ['data_out', 'c', 'b', 'a'] (含 cycle detection)
# 默认 verify=True, 链上每跳的 _evidence_override 已自动填充

# 下游 load 链: 谁读了它, 又被谁读 (与 driver chain 对称)
load_chain = t.get_load_chain('reg2hw', max_depth=10)

# 不要 evidence: t.get_driver_chain('data_out', verify=False)
```

### 5. 一次 dump 整个链 (M5.1f) — LLM 友好

```python
dump = t.dump_driver_chain('tx_enable')  # 默认含 hops + context_window
# dump 是 1 个 dict: {signal_name, direction, hops[...], summary{avg, min, cross_files, ...}}
# summary 让 LLM 5 个数字就判断全链质量
print(json.dumps(dump, indent=2))

summary_only = t.dump_driver_chain('tx_enable', summary_only=True)
load_dump = t.dump_load_chain('reg2hw')  # 下游链同样可 dump
```

### 6. 多驱动 dump (M5.1g) — 一次 dump 全部冲突

```python
multi_dump = t.dump_multi_drivers()
# 2 顶层字段:
#   summary: {total_signals, total_conflicts, total_drivers, avg_credibility, cross_files}
#   conflicts: [{signal, drivers: [...]}, ...]
print(json.dumps(multi_dump, indent=2))
```

### 7. 代码证据链 (M5.1) — 让 trace 自证

**核心问题**: trace 之前只是元数据, "信不信由你"。M5.1 让每个 trace 都能"自证"。

```python
from signal_tracer import trace_signal
result = trace_signal('count', sv_code, 'counter.sv')
for ctx in result.to_contexts(file_content=sv_code):  # 传 file_content 让 evidence 读回
    d = ctx.to_dict()
    print(f"  credibility={d['credibility_score']}  is_verified={d['is_verified']}")
    print(f"  snippet: {d['evidence_snippet']}")
    print(ctx.code_evidence.to_evidence_string())  # LLM-friendly 多行格式
```

输出 (含上下 2 行 + 评分细节):
```
  credibility=1.0  is_verified=True
  snippet: if (!rst_n) count <= 8'h00;
Evidence for always_ff @(posedge clk ...) @ counter.sv:9
  file_readable: True
  snippet: if (!rst_n) count <= 8'h00;
  matches: source_expr match: ✓, signal_name match: ✓
  credibility: 1.00/1.0 (VERIFIED)
     8 |     always_ff @(posedge clk or negedge rst_n) begin
     9 > if (!rst_n) count <= 8'h00;
    10 |         else        count <= count + data_in;
    11 |     end
```

**可信度评分** (0-1):
- `file_readable` (+0.2) — 文件能读
- `snippet_present` (+0.2) — line 存在
- `matches_source_expr` (+0.4) — 文本里真找到 source_expr
- `matches_signal_name` (+0.2) — 文本里真找到 signal_name

**多文件项目**: 用 `trace_verified()` 自动用 in-memory 内容填充 evidence (避免磁盘 I/O):
```python
t = SignalTracer()
t.add_file('top.sv', top_code)
t.add_file('sub.sv', sub_code)
t.build()
result = t.trace_verified('top.u_sub.signal')  # 自动用 self._files 填充
```

### 8. ContextBundle (M2) — 打包给 LLM

```python
result = trace_signal("count", sv_code, "counter.sv")
for ctx in result.to_contexts():
    # ctx 是 ContextBundle, frozen, 可哈希, 可 JSON 序列化
    print(ctx.summary())                # 'counter.sv:10 (always_ff) clock=clk reset=rst_n cond=[!rst_n]'
    print(json.dumps(ctx.to_dict()))    # 给 LLM 一次性看全所有上下文
```

### 9. 单独用 trace_drivers / trace_loads (M5.1d)

```python
drivers = t.trace_drivers('tx_enable')  # 默认 verify=True
loads = t.trace_loads('reg2hw')         # 默认 verify=True
# 不需要 evidence: t.trace_loads('reg2hw', verify=False)
```

---

## TraceResult 关键字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `signal_name` | str | 信号名 (如 `'count'`) |
| `source_expr` | str | 完整驱动表达式 (如 `"count + 1"` 或 `"reg2hw.ctrl.tx.q"`) |
| `source_signals` | List[str] | 表达式中读到的信号 |
| `file` / `line` | str / int | 实际文件 + 行号 (跨文件精确, M4 plan A 修复) |
| `scope_text` | str | 完整 always_ff/always_comb/assign 块源码 |
| `scope_kind` | ScopeKind | `ALWAYS_FF` / `ALWAYS_COMB` / `CONTINUOUS_ASSIGN` |
| `clock` / `reset` | str | 提取的时钟/复位信号 (M1.5) |
| `condition_stack` | List[str] | 嵌套条件栈 (如 `['!rst_n', 'data_in[7]']`) |
| `hierarchical_path` | str | 模块实例路径 (如 `'top.u_mid'`) |

---

## 典型工作流 (Agent 调用)

### 工作流 A: 用户给 SV 代码 → 跑 trace → 喂回 LLM

```python
from signal_tracer import trace_signal
import json

# 1. 用户给代码片段
sv = user_provided_code  # 用户粘贴或文件读入

# 2. trace 目标信号
result = trace_signal(target_signal, sv, "user_input.sv")

# 3. 转成 LLM-friendly JSON
contexts = [ctx.to_dict() for ctx in result.to_contexts(file_content=sv)]
output = json.dumps(contexts, indent=2, ensure_ascii=False)

# 4. 喂给 LLM: "这些是该信号的 driver, 请解释行为 / 找 bug / 写 SVA"
```

### 工作流 B: 大型项目调试 (OpenTitan 风格)

```python
from signal_tracer import SignalTracer
from pathlib import Path

# 1. 收集项目源文件
rtl_dir = Path('/path/to/opentitan/hw/ip/uart/rtl')
t = SignalTracer()
for f in rtl_dir.glob('*.sv'):
    t.add_file(str(f), f.read_text())
t.build()

# 2. 递归查上游链
chain = t.get_driver_chain('reg2hw.ctrl.tx.q', max_depth=5)
print(f"Chain: {' <- '.join(chain)}")  # → LLM: 解释中断怎么来的

# 3. 检查多驱动
multi = t.find_multi_drivers()
for sig, drivers in multi.items():
    if 'reg2hw' in sig or 'tl' in sig:
        print(f"⚠ 关键信号 {sig} 多驱动:")
        for d in drivers:
            ctx = d.to_context().to_dict()
            print(f"   {ctx['file'].split('/')[-1]}:{ctx['line']}  cred={ctx['credibility_score']}")
```

### 工作流 C: 验证 LLM 写的 SV

```python
# 1. LLM 生成新代码
new_sv = llm_generated_code  # LLM 写的 always_ff

# 2. trace + 自证
result = trace_signal("target_reg", new_sv, "llm_output.sv")
for ctx in result.to_contexts(file_content=new_sv):
    d = ctx.to_dict()
    if d['credibility_score'] < 0.8:
        # 0.8 以下: file 读不到 / line 不准 / expr 不匹配
        # 可能是 LLM 编的或我们 trace 有 bug, 拿给用户看
        print(f"⚠ 可信度低 ({d['credibility_score']}): {d['evidence_snippet']}")
```

### 工作流 D: 批量 dump 多驱动 (喂 LLM)

```python
multi_dump = t.dump_multi_drivers()
# → {summary: {total_signals: 5, total_conflicts: 2, ...},
#    conflicts: [{signal: 'tx_data', drivers: [...]}, ...]}

# summary_only=True 只拿 5 个数字, 快速给 LLM 概览
summary = t.dump_multi_drivers(summary_only=True)
# 喂 LLM: "这个模块有 2 个多驱动信号, 平均可信度 0.85, 是否在 cross-file"
```

---

## 已知限制 (提前告诉用户)

- **modport direction** (input/output) 区分 driver/load 尚未实现 (现在都被当 driver)
- **不支持**: virtual interface / Clocking block / Property-Sequence 内部 / System task ($cast, $readmemh) 中的信号
- **evidence `matches_source_expr`** 是**字面量**子串匹配 — pyslang 文本格式
  (如 `count Add data_in`) 与源码 (`count + data_in`) 不完全一致时, 命中率会降。
  反映在 credibility_score 上, **不会静默接受**。

---

## 已验证 SV 特性 (M4 能力覆盖)

| 特性 | 例子 |
|------|------|
| 基础 | `assign`, `always_ff`, `always_comb`, ternary `?:` |
| 数组 | bit-select `[7:0]`, part-select `[3:0]`, 数组索引 |
| 层次 | `reg2hw.ctrl.tx.q` (reg2hw 是 struct 数组) |
| Concatenation | `{a, b, c}`, nested `{8'h00, 8'hFF}` |
| Streaming | `{<<8{data}}` (OpenTitan spi_device) |
| Inside | `data inside {IDLE, ACTIVE}` (OpenTitan dma) |
| Struct/Pattern | StructuredAssignmentPattern (OpenTitan aes 24k drivers) |
| 跨文件 | 3 文件 / 3 层 instance (top → mid → leaf) |
| Interface/Modport | `bus.data = bus.data + 1` |
| SVA | `assert property` 块**跳过** (不当 driver) |

**OpenTitan 验证数据** (全部 0 warning + 0 empty driver):
| 模块 | drivers | 关键覆盖特性 |
|------|---------|--------------|
| uart | 418 | reg2hw.* 字段访问 |
| spi_device | 3,229 | Streaming concat `{<<8{...}}` |
| dma | 401 | `inside` 集合 |
| i2c | 1,235 | |
| aes | 24,065 | StructuredAssignmentPattern |
| hmac | 870 | `assert property` (SVA 跳过) |

总计 **30,218 drivers, 0 warning, 0 empty**。

---

## 不要做的事

❌ **不要**把 sv-trace 当 lint 工具用 — 它不报 warning, 只 trace
❌ **不要**对同一信号名跑跨不相关模块 — 层次路径要写全
❌ **不要**expect modport direction 区分 — 目前 modport input/output 都被当 driver
❌ **不要**用于 HDL 之外的代码 (Verilog/VHDL 也行但 SV 优化)
❌ **不要**循环 import 多次 build 同一个 tracer — 缓存即可

---

## References (按需加载)

- `references/api_reference.md` — 完整 API 签名 + 所有 dataclass 字段
- `references/evidence_guide.md` — credibility_score 算法 + 何时信 / 不信
- `references/opentitan_examples.md` — OpenTitan 6 模块的 driver dump 实例
- `references/limitations.md` — 已知不支持的 SV 特性 + 失败模式

## Examples (可直接 copy 跑)

- `examples/single_file_trace.py` — 最小单文件 trace
- `examples/multi_file_hierarchical.py` — 3 文件 / 3 层 instance
- `examples/multi_driver_check.py` — 多驱动检测 + dump
- `examples/llm_context_pipeline.py` — trace → ContextBundle → 喂 LLM 模板

## Scripts (可独立 run)

- `scripts/trace_one.py <file.sv> <signal>` — CLI: 跑 trace 输出 JSON
- `scripts/audit_multi_drivers.py <dir>` — 目录: 扫所有 .sv 的多驱动
- `scripts/dump_chain.py <file.sv> <signal> --depth 5` — 递归 dump driver 链
