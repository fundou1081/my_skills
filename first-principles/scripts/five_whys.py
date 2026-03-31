#!/usr/bin/env python3
"""
五问法深挖工具 (5-Why Deep Dive)
对任何问题连续追问5次"为什么"，找到根本原因
支持多条追问路径（树状分析）

使用方式：
  python3 five_whys.py "为什么testbench难以维护"
  python3 five_whys.py --depth 7 "为什么电池价格高"
"""

import sys
import json

# ============================================================
# 各阶段的引导提示
# ============================================================

WHY_PROMPTS = [
    "为什么会这样？（直接原因）",
    "那为什么会导致上面那个原因？（往上一层）",
    "继续往上追：这个原因的根源是什么？",
    "越来越接近根本了。再问一次：更深的原因是什么？",
    "这就是根本原因吗？还能继续追问吗？",
    "（深层6）如果还能继续追，继续问：",
    "（深层7）接近物理/系统底层了，最终原因是什么？",
]

STOP_SIGNALS = [
    "人类认知限制", "物理定律", "资源有限", "时间有限",
    "无法改变", "基本事实", "根本无法", "天然属性"
]


def print_banner():
    print("\n" + "="*60)
    print("  五问法深挖工具 (5-Why Deep Dive)")
    print("  目标：穿透症状，找到可干预的根本原因")
    print("="*60 + "\n")


def is_root_cause(answer: str) -> bool:
    """启发式判断是否已到达根本原因"""
    for signal in STOP_SIGNALS:
        if signal in answer:
            return True
    return False


def run_five_whys(initial_problem: str, max_depth: int = 5, auto_mode: bool = False):
    """运行五问法分析"""
    print(f"初始问题：{initial_problem}\n")

    chain = [{"level": 0, "question": initial_problem, "answer": ""}]

    for depth in range(1, max_depth + 1):
        prev_answer = chain[-1]["question"] if depth == 1 else chain[-1]["answer"]

        prompt = WHY_PROMPTS[min(depth - 1, len(WHY_PROMPTS) - 1)]
        print(f"第{depth}次追问（{prompt}）")
        print(f"  基于：「{prev_answer[:60]}{'...' if len(prev_answer) > 60 else ''}」")

        if auto_mode:
            # 自动模式：输出问题框架供 AI 分析
            answer = f"[待回答-第{depth}层]"
        else:
            answer = input("  → 你的回答: ").strip()
            if not answer:
                answer = "(跳过)"

        chain.append({
            "level": depth,
            "question": f"为什么：{prev_answer[:80]}",
            "answer": answer
        })
        print()

        if is_root_cause(answer):
            print(f"  ✅ 检测到根本原因信号，可以在此停止追问。")
            break

        if answer == "q" or answer == "quit":
            break

    return chain


def format_chain(chain: list, problem: str) -> str:
    """格式化输出追问链"""
    lines = [f"# 五问法分析：{problem}\n"]
    lines.append("```")
    lines.append(f"初始问题：{problem}")
    for item in chain[1:]:
        level = item["level"]
        indent = "  " * level
        lines.append(f"{indent}Why {level}: {item['question']}")
        lines.append(f"{indent}  → {item['answer']}")
    lines.append("```")

    # 找出根本原因（最后一个有实质答案的节点）
    root = next(
        (c for c in reversed(chain) if c["answer"] and c["answer"] != "(跳过)"),
        None
    )
    if root:
        lines.append(f"\n## 根本原因\n> {root['answer']}")
        lines.append(
            "\n## 建议\n"
            "- 针对根本原因制定解决方案，而非只修复表层症状\n"
            "- 检查：这个根本原因是**可干预的**，还是物理约束？\n"
            "- 如果是物理约束，考虑用第一性原理重新设计绕过它\n"
        )

    return "\n".join(lines)


def quick_framework(problem: str, depth: int = 5):
    """快速输出框架（不交互，供 AI 使用）"""
    print(f"问题：{problem}\n")
    print("五问法框架（请逐层思考）：\n")

    output = {"problem": problem, "why_chain": []}
    for i in range(1, depth + 1):
        prompt = WHY_PROMPTS[min(i - 1, len(WHY_PROMPTS) - 1)]
        print(f"Why {i}：{prompt}")
        output["why_chain"].append({"level": i, "prompt": prompt})

    print("\n关键判断：")
    print("  • 根本原因是什么？（最终可干预的节点）")
    print("  • 哪些是物理/系统约束？（不可改变，需绕过）")
    print("  • 哪些是人为决策？（可以改变）")

    print("\n[SCRIPT_OUTPUT_JSON]" + json.dumps(output, ensure_ascii=False) + "[/SCRIPT_OUTPUT_JSON]")


def main():
    args = sys.argv[1:]
    print_banner()

    depth = 5
    auto = False
    problem = None

    i = 0
    while i < len(args):
        if args[i] == "--depth" and i + 1 < len(args):
            depth = int(args[i + 1])
            i += 2
        elif args[i] == "--auto":
            auto = True
            i += 1
        elif args[i] == "--quick":
            i += 1
            problem = " ".join(args[i:]) if i < len(args) else None
            break
        else:
            problem = " ".join(args[i:])
            break

    if not problem:
        print("请输入要分析的问题：")
        problem = input("> ").strip()

    if auto or "--quick" in sys.argv:
        quick_framework(problem, depth)
    else:
        chain = run_five_whys(problem, max_depth=depth)
        report = format_chain(chain, problem)
        print("\n" + "=" * 60)
        print(report)
        print("\n[SCRIPT_OUTPUT_JSON]" + json.dumps({"problem": problem, "chain": chain}, ensure_ascii=False) + "[/SCRIPT_OUTPUT_JSON]")


if __name__ == "__main__":
    main()
