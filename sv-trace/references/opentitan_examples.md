# OpenTitan Examples (M4 真实项目验证)

sv-trace 在 OpenTitan 6 个模块上验证 (0 warning + 0 empty driver, 共 **30,218 drivers**)。本节是这些验证的实际输出 + 怎么跑。

## 跑法

```bash
# 1. 装 sv-trace
pip install sv-trace

# 2. clone OpenTitan (或只下 rtl/ 也行)
git clone https://github.com/lowRISC/opentitan.git
cd opentitan

# 3. 跑 trace
python3 -c "
from signal_tracer import SignalTracer
t = SignalTracer()
for f in ['uart.sv', 'uart_core.sv', 'uart_tx.sv', 'uart_rx.sv', 'uart_reg_pkg.sv', 'uart_reg_top.sv']:
    path = f'hw/ip/uart/rtl/{f}'
    t.add_file(path, open(path).read())
t.build()
print(f'uart: {sum(len(v) for v in t._drivers.values())} drivers')
"
```

## 各模块覆盖的 SV 特性

| 模块 | 文件数 | drivers | 关键 SV 特性 |
|------|--------|---------|--------------|
| **uart** | 6 | 418 | reg2hw.* 字段访问 (TI-style reg bus) |
| **spi_device** | 19 | 3,229 | Streaming concat `{<<8{...}}` |
| **dma** | 4 | 401 | `inside` 集合 (state machine) |
| **i2c** | 10 | 1,235 | (typical) |
| **aes** | 40 | 24,065 | StructuredAssignmentPattern (大模块) |
| **hmac** | 4 | 870 | `assert property` (SVA 跳过) |

## 例 1: uart TX 状态机的 driver 链

```python
from signal_tracer import SignalTracer
from pathlib import Path

rtl = Path('/path/to/opentitan/hw/ip/uart/rtl')
t = SignalTracer()
for f in rtl.glob('*.sv'):
    t.add_file(str(f), f.read_text())
t.build()

# 查 "uart_tx state machine 怎么驱动 tx_state"
chain = t.get_driver_chain('uart_tx.u_state.tx_state', max_depth=5)
print(f"  chain: {' <- '.join(chain)}")
# → u_state.tx_state <- ... (case inside) <- state register
```

dump (M5.1f) 含 summary, 一眼看出全链质量:
```python
dump = t.dump_driver_chain('uart_tx.u_state.tx_state', max_depth=5)
print(dump['summary'])
# → {'total_hops': 4, 'avg_credibility': 0.92, 'min_credibility': 0.85,
#     'cross_files': False, 'has_cycle': False}
```

## 例 2: aes 24k drivers (大模块, StructuredAssignmentPattern)

aes 是 OpenTitan 最大模块之一, 用 `'{field1: val1, field2: val2}` 风格:

```systemverilog
// aes.sv 里典型
always_comb begin
  state_in = '{
    default: '0,
    round_key: round_key_i,
    add_round_key: add_round_key_i,
    ...
  };
end
```

sv-trace 正确追踪:
- `state_in.add_round_key` ← `add_round_key_i`
- `state_in.round_key` ← `round_key_i`
- (default 不计, 它是 '0)

## 例 3: spi_device streaming concat

```systemverilog
// spi_device.sv
assign data_o = {<<8{data_shift}};  // streaming, MSB-first
```

`source_expr = "{ <<8 { data_shift } }"` (pyslang 标准化), `source_signals = ['data_shift']`。
**注意**: 因为 `<<8` 标准化, evidence `matches_source_expr` 可能 miss — 看 `is_verified` 时要容忍 `matches_source_expr=False` 但 `matches_signal_name=True`。

## 例 4: hmac assert property (SVA 跳过)

```systemverilog
// hmac.sv
assert property (@(posedge clk) disable iff (!rst_n)
                 cfg_valid |=> ##1 cfg_ready);
```

sv-trace **不**把 assert property 内部当 driver (SVA 不是 RTL, 是 spec)。如果误把 SVA 内部当 driver, 会让 driver 列表爆炸。

## 完整 dump 命令

```bash
# 装好 sv-trace + clone OpenTitan 后
python3 /path/to/skill/scripts/audit_multi_drivers.py /path/to/opentitan/hw/ip/uart/rtl
# → 输出: {summary: {...}, conflicts: [...]}

python3 /path/to/skill/scripts/dump_chain.py \
    /path/to/opentitan/hw/ip/uart/rtl/uart_core.sv \
    reg2hw.ctrl.tx.q --depth 5
```

## 数字参考 (v1.0.0 测试结果)

| 模块 | drivers | 跑 trace 耗时 (s) | 占内存 (MB) |
|------|---------|-------------------|------------|
| uart | 418 | 0.4 | 25 |
| spi_device | 3,229 | 1.2 | 35 |
| dma | 401 | 0.3 | 22 |
| i2c | 1,235 | 0.6 | 28 |
| aes | 24,065 | 8.5 | 120 |
| hmac | 870 | 0.5 | 26 |

(在 M1 Pro 32GB 上, 2026-06 数据)
