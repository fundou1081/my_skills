# Limitations — 已知不支持的 SV 特性 + 失败模式

## 暂时不支持 (会 silently skip / wrong)

| 特性 | 状态 | 影响 |
|------|------|------|
| modport direction (input/output) | ❌ 不区分 | input port 上的 driver 也会被当 driver (应该当 load) |
| virtual interface | ❌ | trace 不到 |
| Clocking block 内部 | ❌ | CB 内的同步信号不算 |
| Property/Sequence 内部 | ❌ | SVA body 内的局部 var 不当 driver |
| System task 内部 | ❌ | `$cast`, `$readmemh`, `$randomize` 等内的 signal |
| `defparam` | ⚠ 部分 | 旧写法, sv-trace 用新参数传递, 可能拿到错的 module |
| UDP (User Defined Primitive) | ❌ | 不在 SV 标准 pyslang 完整支持 |
| Config DB (`uvm_config_db`) | ❌ | UVM 动态配置不 trace |
| Generate block 内分层 | ⚠ | 同 instance 名跨 generate 块会撞名 |

## 已知 false / edge cases

### 1. modport input/output 暂未区分

**问题**: interface 里的 modport 定义 input / output 方向, 但 sv-trace v1.0.0 暂未解析方向:

```systemverilog
interface bus_if;
  logic [7:0] data;
  modport master(output data, input valid);
  modport slave(input data, output valid);
endinterface

// m 是 master, 写 m.data 是 driver
// s 是 slave, 读 s.data 是 load
// 但 sv-trace 都当 driver
```

**M5.1 缓解**: evidence + credibility 仍能区分 (driver 通常是 assign/always_ff, load 是读取 expression)。

**未来**: M5.2+ 加 modport direction 区分。

### 2. `for` loop 内的 driver, line 标在 for 头

```systemverilog
for (int i = 0; i < 4; i++) begin
  arr[i] <= arr[i] + 1;  // 实际 driver
end
```

**当前**: `line` 指向 `arr[i] <= ...` (for body 内部), 正确。
**风险**: 如果 for body 只有 statement (无 begin/end), pyslang 可能回退到 for 头, 此时 evidence 仍可能 verify (因为 for 头也有 `arr`)。

### 3. 跨 generate 块的 instance 撞名

```systemverilog
genvar i;
generate
  for (i = 0; i < 2; i++) begin : g
    sub u_sub (.clk(clk), .data(data[i]));
  end
endgenerate
// 两个 u_sub 实例: g[0].u_sub, g[1].u_sub
```

**当前**: 后缀匹配 `t.trace('data')` 会聚合两个, 没问题。
**风险**: 完全路径 `t.trace('g[0].u_sub.data')` — pyslang 解析 `[0]` / `[1]` 可能不规范, 失败。

**未来**: M5.2+ 修复 generate 路径。

### 4. 大模块 (aes 24k drivers) 慢 + 占内存

- **耗时**: ~8.5s build
- **内存**: ~120MB

**应对**: 用 `get_driver_chain(target)` 代替 `trace()` — 链追踪只展开必要 driver。

### 5. evidence `matches_source_expr` 在 streaming / pattern 处 false-negative

详见 [evidence_guide.md](evidence_guide.md)。

## 怎么报告 bug

跑下面的命令, 把 JSON 输出贴到 issue:

```python
import json
from signal_tracer import SignalTracer, _set_source_manager

t = SignalTracer()
t.add_file('bug.sv', open('bug.sv').read())
t.build()
# 把当前 SourceManager 给 evidence 用
import pyslang
sm = t._comp.sourceManager
_set_source_manager(sm)

result = t.trace('signal_in_question')
output = {
    "drivers": [d.to_context().to_dict() for d in result.drivers],
    "loads":   [l.to_context().to_dict() for l in result.loads],
}
print(json.dumps(output, indent=2))
```

## 升级 pyslang 时

```bash
make test-cross-version  # 在 skill 目录
# 或:
python -m venv /tmp/sv-pyslang-11
/tmp/sv-pyslang-11/bin/pip install "pyslang>=11.0" pytest
/tmp/sv-pyslang-11/bin/pip install sv-trace
/tmp/sv-pyslang-11/bin/python -m pytest <your-tests>
```

## 不在范围 (做这些就改用别的工具)

| 任务 | 替代 |
|------|------|
| CDC (跨时钟域) 分析 | verilator --lint-only, SpyGlass, Real Intent |
| Lint / 静态检查 | verilator, iverilog -Wall |
| FSM 提取 | slang 自带 `--ast-json` 后处理, 或 svlint |
| 面积/功耗估算 | Yosys + synthesis tool |
| 时序分析 | OpenSTA, PrimeTime |
| 覆盖率建议 | Verilator coverage, VCS |
| SVA 自动生成 | JasperGold, Onespin (商业) |
| TB 复杂度评分 | vsc (Verilog SystemC lint) |
| 依赖图 | slang `--ast-json` + graphviz |

sv-trace 故意**只**做"信号追踪 + 上下文召回", 因为这层最常用, 也最容易被 LLM 接住。
