"""
multi_driver_check.py — 多驱动检测 + dump (M1.5 + M5.1b + M5.1g)

跑法:
    python examples/multi_driver_check.py
"""
import json
from signal_tracer import SignalTracer

# 一个故意多驱动的例子:
# - data 在 mode==0 时被写 0xAA
# - data 在 mode==1 时被写 0x55
# (这是 RTL bug: 同一信号两个 always_ff 写, 取决于 mode 是不是 1-hot)
SV = """
module buggy (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       mode,
    output logic [7:0] data
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (rst_n && mode == 1'b0)
            data <= 8'hAA;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (rst_n && mode == 1'b1)
            data <= 8'h55;
    end
endmodule
"""

t = SignalTracer()
t.add_file("buggy.sv", SV)
t.build()

print("=== find_multi_drivers() ===\n")
multi = t.find_multi_drivers()
print(f"Found {len(multi)} multi-driver signal(s):\n")
for sig, drivers in multi.items():
    print(f"⚠ {sig}  has {len(drivers)} driver(s):")
    for d in drivers:
        ctx = d.to_context()
        d_dict = ctx.to_dict()
        print(f"   {d.file.split('/')[-1]}:{d.line}")
        print(f"     {d.source_expr}")
        print(f"     credibility={d_dict['credibility_score']}  verified={d_dict['is_verified']}")
        print(f"     snippet: {d_dict['evidence_snippet']}")
        print(f"     cond: {d.condition_stack}")
        print()

print("=== dump_multi_drivers() (LLM-friendly JSON) ===\n")
dump = t.dump_multi_drivers()
print(json.dumps(dump, indent=2, ensure_ascii=False))
