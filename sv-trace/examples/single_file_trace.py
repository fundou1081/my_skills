"""
single_file_trace.py — 最小单文件 trace 示例

跑法:
    python examples/single_file_trace.py
"""
from signal_tracer import trace_signal

sv_code = """
module counter (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] data_in,
    output logic [7:0] count
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 8'h00;
        else
            count <= count + data_in;
    end
endmodule
"""

result = trace_signal("count", sv_code, "counter.sv")

print(f"=== trace_signal('count', 'counter.sv') ===\n")
print(f"drivers: {len(result.drivers)}")
print(f"loads:   {len(result.loads)}\n")

for d in result.drivers:
    print(f"DRIVER: {d.source_expr}")
    print(f"  file/line: {d.file}:{d.line}")
    print(f"  scope_kind: {d.scope_kind}")
    print(f"  clock={d.clock}  reset={d.reset}")
    print(f"  cond_stack: {d.condition_stack}")
    print(f"  scope_text:")
    for line in d.scope_text.split("\n"):
        print(f"    {line}")
    print()

if result.loads:
    print(f"LOADS (found {len(result.loads)}):")
    for ld in result.loads:
        print(f"  {ld.source_expr} @ {ld.file}:{ld.line}")
