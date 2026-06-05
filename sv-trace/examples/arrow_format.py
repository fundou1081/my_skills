"""
arrow_format.py — M5.1j 人类友好箭头式输出示例

跑法:
    python examples/arrow_format.py
"""
from signal_tracer import (
    trace_signal, SignalTracer,
    format_driver, format_load, format_all,
    format_driver_chain, format_multi_driver,
    ARROW_DRIVER, ARROW_LOAD,
)


SINGLE_FILE_SV = """
module counter (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] data_in,
    output logic [7:0] count
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) count <= 8'h00;
        else        count <= count + data_in;
    end
endmodule
"""


MULTI_SV = """
module buggy (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       mode,
    output logic [7:0] data
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (rst_n && mode == 1'b0) data <= 8'hAA;
    end
    always_ff @(posedge clk or negedge rst_n) begin
        if (rst_n && mode == 1'b1) data <= 8'h55;
    end
endmodule
"""


def demo_single_file():
    print("=" * 60)
    print("1. Single file: TraceSummary.to_arrow()")
    print("=" * 60)
    result = trace_signal("count", SINGLE_FILE_SV, "counter.sv")
    print(result.to_arrow())


def demo_per_trace():
    print()
    print("=" * 60)
    print("2. Per trace: TraceResult.to_arrow()")
    print("=" * 60)
    result = trace_signal("count", SINGLE_FILE_SV, "counter.sv")
    for d in result.drivers:
        print(f"  {d.to_arrow()}")


def demo_context_bundle():
    print()
    print("=" * 60)
    print("3. Context bundle: ContextBundle.to_arrow()")
    print("=" * 60)
    result = trace_signal("count", SINGLE_FILE_SV, "counter.sv")
    for ctx in result.to_contexts(file_content=SINGLE_FILE_SV):
        print(f"  {ctx.to_arrow()}")


def demo_multi_driver():
    print()
    print("=" * 60)
    print("4. Multi-driver: SignalTracer.multi_drivers_to_arrow()")
    print("=" * 60)
    t = SignalTracer()
    t.add_file("buggy.sv", MULTI_SV)
    t.build()
    print(t.multi_drivers_to_arrow())


def demo_chain():
    print()
    print("=" * 60)
    print("5. Driver chain: SignalTracer.chain_to_arrow()")
    print("=" * 60)
    t = SignalTracer()
    t.add_file("counter.sv", SINGLE_FILE_SV)
    t.build()
    out = t.chain_to_arrow("count", direction="driver", max_depth=5)
    print(f"  driver: {out}")


def demo_dump():
    print()
    print("=" * 60)
    print("6. Dump to arrow: SignalTracer.dump_to_arrow()")
    print("=" * 60)
    t = SignalTracer()
    t.add_file("counter.sv", SINGLE_FILE_SV)
    t.build()
    print(t.dump_to_arrow("count", direction="driver", max_depth=5))


def demo_formatter_functions():
    print()
    print("=" * 60)
    print("7. Direct formatter functions")
    print("=" * 60)
    result = trace_signal("count", SINGLE_FILE_SV, "counter.sv")
    print(f"  format_driver: {format_driver(result.drivers[0])}")
    print(f"  format_all:")
    for line in format_all(result).split("\n"):
        print(f"    {line}")
    print(f"  ARROW_DRIVER: {ARROW_DRIVER!r}")
    print(f"  ARROW_LOAD:   {ARROW_LOAD!r}")


def demo_long_expr_truncation():
    print()
    print("=" * 60)
    print("8. Long expression truncation")
    print("=" * 60)
    long_sv = """
module m;
    logic [31:0] a, b, c, d, e, f, g, h;
    assign a = b + c + d + e + f + g + h + 1 + 2 + 3;
endmodule
"""
    result = trace_signal("a", long_sv, "long.sv")
    print(f"  default (max_expr_len=40):")
    print(f"    {result.drivers[0].to_arrow()}")
    print(f"  short (max_expr_len=10):")
    print(f"    {result.drivers[0].to_arrow(max_expr_len=10)}")


# === M5.1k: tree / vertical / ascii 风格 demo ===

CHAIN_SV = """module top (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] ext_in_data,
    output logic [7:0] ext_out_data
);
    mid u_mid (.clk(clk), .rst_n(rst_n), .in_data(ext_in_data), .out_data(ext_out_data));
endmodule"""
CHAIN_MID = """module mid (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] in_data,
    output logic [7:0] out_data
);
    leaf u_leaf_a (.clk(clk), .rst_n(rst_n), .in_data(in_data), .out_data(out_data));
endmodule"""
CHAIN_LEAF = """module leaf (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] in_data,
    output logic [7:0] out_data
);
    logic [7:0] mid_data;
    assign mid_data = in_data + 8'h01;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) out_data <= 8'h00;
        else        out_data <= mid_data + 8'hAA;
    end
endmodule"""


def demo_chain_styles():
    """M5.1k: 链追踪的 5 种风格 (arrow/tree/ascii/vertical/all)"""
    print()
    print("=" * 60)
    print("9. Chain styles (M5.1k): arrow/tree/ascii/vertical/all")
    print("=" * 60)

    t = SignalTracer()
    t.add_file("top.sv", CHAIN_SV)
    t.add_file("mid.sv", CHAIN_MID)
    t.add_file("leaf.sv", CHAIN_LEAF)
    t.build()

    sig = "top.u_mid.u_leaf_a.out_data"

    for style in ["arrow", "tree", "ascii", "vertical", "all"]:
        print()
        print(f"  --- style='{style}' ---")
        out = t.chain_to_arrow(sig, direction="driver", max_depth=5, style=style)
        for line in out.split("\n"):
            print(f"  {line}")


def demo_dump_styles():
    """M5.1k: dump 的 4 种风格"""
    print()
    print("=" * 60)
    print("10. Dump styles (M5.1k): arrow/tree/ascii/vertical")
    print("=" * 60)

    t = SignalTracer()
    t.add_file("top.sv", CHAIN_SV)
    t.add_file("mid.sv", CHAIN_MID)
    t.add_file("leaf.sv", CHAIN_LEAF)
    t.build()

    sig = "top.u_mid.u_leaf_a.out_data"

    for style in ["arrow", "tree", "ascii", "vertical"]:
        print()
        print(f"  --- dump_to_arrow(style='{style}') ---")
        out = t.dump_to_arrow(sig, direction="driver", max_depth=5, style=style)
        for line in out.split("\n"):
            print(f"  {line}")


def demo_alias_methods():
    """M5.1k: alias 方法 (chain_to_tree / chain_to_vertical / dump_to_tree)"""
    print()
    print("=" * 60)
    print("11. Alias methods (M5.1k)")
    print("=" * 60)

    t = SignalTracer()
    t.add_file("top.sv", CHAIN_SV)
    t.add_file("mid.sv", CHAIN_MID)
    t.add_file("leaf.sv", CHAIN_LEAF)
    t.build()

    sig = "top.u_mid.u_leaf_a.out_data"

    print()
    print("  --- chain_to_tree(use_box=True) ---")
    out = t.chain_to_tree(sig, use_box=True)
    for line in out.split("\n"):
        print(f"  {line}")

    print()
    print("  --- chain_to_tree(use_box=False) ---")
    out = t.chain_to_tree(sig, use_box=False)
    for line in out.split("\n"):
        print(f"  {line}")

    print()
    print("  --- chain_to_vertical() ---")
    out = t.chain_to_vertical(sig)
    for line in out.split("\n"):
        print(f"  {line}")


if __name__ == "__main__":
    demo_single_file()
    demo_per_trace()
    demo_context_bundle()
    demo_multi_driver()
    demo_chain()
    demo_dump()
    demo_formatter_functions()
    demo_long_expr_truncation()
    demo_chain_styles()
    demo_dump_styles()
    demo_alias_methods()
    print()
    print("=" * 60)
    print("All 11 demos OK")
    print("=" * 60)
