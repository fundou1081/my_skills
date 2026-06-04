"""
multi_file_hierarchical.py — 3 文件 / 3 层 instance 层次路径追踪

跑法:
    python examples/multi_file_hierarchical.py
"""
from signal_tracer import SignalTracer

TOP = """
module top (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] in_data,
    output logic [7:0] out_data
);
    mid u_mid (.clk(clk), .rst_n(rst_n), .in_data(in_data), .out_data(out_data));
endmodule
"""

MID = """
module mid (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] in_data,
    output logic [7:0] out_data
);
    leaf u_leaf (
        .clk(clk), .rst_n(rst_n),
        .in_data(in_data),
        .out_data(out_data)
    );
endmodule
"""

LEAF = """
module leaf (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] in_data,
    output logic [7:0] out_data
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            out_data <= 8'h00;
        else
            out_data <= in_data + 8'h01;
    end
endmodule
"""

t = SignalTracer()
t.add_file("top.sv", TOP)
t.add_file("mid.sv", MID)
t.add_file("leaf.sv", LEAF)
t.build()

print("=== SignalTracer (3-file, 3-tier hierarchy) ===\n")
print(f"  files: {len(t._files)}")
print(f"  total drivers: {sum(len(v) for v in t._drivers.values())}")
print()

# 1. 完全层次路径
print("1. t.trace('top.u_mid.u_leaf.out_data')")
r1 = t.trace("top.u_mid.u_leaf.out_data")
print(f"   drivers: {len(r1.drivers)}")
for d in r1.drivers:
    print(f"     {d.source_expr} @ {d.file.split('/')[-1]}:{d.line}  hier={d.hierarchical_path}")

print()

# 2. 后缀匹配 — 聚合所有 *.out_data
print("2. t.trace('out_data')  (suffix match, cross-instance aggregate)")
r2 = t.trace("out_data")
print(f"   drivers: {len(r2.drivers)}")
for d in r2.drivers:
    print(f"     {d.source_expr} @ {d.file.split('/')[-1]}:{d.line}  hier={d.hierarchical_path}")
