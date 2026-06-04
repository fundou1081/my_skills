"""
llm_context_pipeline.py — trace → ContextBundle → 喂 LLM 模板

跑法:
    python examples/llm_context_pipeline.py
"""
import json
from signal_tracer import trace_signal

SV = """
module fifo_ctrl (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       wr_en,
    input  logic       rd_en,
    input  logic [7:0] wr_data,
    output logic [7:0] rd_data,
    output logic       full,
    output logic       empty
);
    logic [7:0] mem [0:255];
    logic [7:0] wr_ptr, rd_ptr;
    logic [7:0] count;

    assign full  = (count == 8'd255);
    assign empty = (count == 8'd0);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= 8'd0;
            rd_ptr <= 8'd0;
            count  <= 8'd0;
        end else begin
            if (wr_en && !full) begin
                mem[wr_ptr] <= wr_data;
                wr_ptr <= wr_ptr + 8'd1;
            end
            if (rd_en && !empty) begin
                rd_ptr <= rd_ptr + 8'd1;
            end
            if ((wr_en && !full) && !(rd_en && !empty))
                count <= count + 8'd1;
            else if (!(wr_en && !full) && (rd_en && !empty))
                count <= count - 8'd1;
        end
    end

    assign rd_data = mem[rd_ptr];
endmodule
"""

print("=== Pipeline: trace → ContextBundle → JSON for LLM ===\n")

# 1. 跑 trace
result = trace_signal("count", SV, "fifo_ctrl.sv")

# 2. 转 ContextBundle (frozen, hashable, JSON-serializable)
contexts = list(result.to_contexts(file_content=SV))

# 3. 每条 driver 一份 LLM-ready dict
llm_input = {
    "signal": "count",
    "file": "fifo_ctrl.sv",
    "total_drivers": len(contexts),
    "contexts": [ctx.to_dict() for ctx in contexts],
}

# 4. JSON 序列化
out = json.dumps(llm_input, indent=2, ensure_ascii=False)

print(out[:2000])
print(f"\n... (truncated; full JSON: {len(out)} bytes)")

# 5. 一行 summary
print("\n=== One-line summary per driver ===\n")
for ctx in contexts:
    print(f"  {ctx.summary()}")

# 6. 喂 LLM 的 prompt 模板
print("\n=== LLM prompt (给到 GPT/Claude) ===\n")
print(f"""
你是一个 SystemVerilog 验证工程师。
信号 `{llm_input['signal']}` 在 `{llm_input['file']}` 里有 {llm_input['total_drivers']} 个 driver:

{chr(10).join(f"- {ctx.summary()}" for ctx in contexts)}

请回答:
1. 这个 FIFO 计数器在 reset 后, 正常 wr_en/rd_en 交替时的行为
2. 有没有 race condition (e.g. 同时 wr 和 rd 时 count 怎么办)
3. 写 2 个 SVA 验证 count 不会越界
""")
