#!/usr/bin/env python3
"""
第一性原理分析向导
引导用户完成：问题解构 → 假设识别 → 根本原理提取 → 方案重建 → 压力测试
"""
import sys
import json

# ============================================================
# 数据模型
# ============================================================

DOMAINS = {
    "engineering": "工程/硬件设计",
    "software":    "软件/系统架构",
    "product":     "产品/功能设计",
    "business":    "商业/战略决策",
    "process":     "流程/工作方式",
    "other":       "其他"
}

# 苏格拉底提问集——每个阶段的引导问题
SOCRATIC_QUESTIONS = {
    "clarify": [
        "用一句话描述你想解决的问题是什么？",
        "这个问题在什么场景下出现？（产品？流程？设计？）",
        "它的衡量标准是什么？你怎么知道它被解决了？",
        "它的边界在哪里？什么不在问题范围内？",
    ],
    "assumptions": [
        "你目前的做法基于哪些前提？",
        "业界的惯例是什么？为什么大家都这么做？",
        "你认为有哪些约束是无法改变的？",
        "有没有你从未质疑过的规则？",
        "如果没有历史包袱，你会怎么做？",
    ],
    "first_principles": [
        "把问题分解到最小单元——物理层面/逻辑层面的基本事实是什么？",
        "哪些约束是物理/数学法则决定的（不可改变）？",
        "哪些约束只是行业惯例或历史选择（可以改变）？",
        "这个问题最本质的目标是什么（用户真正需要的是什么）？",
        "从材料/能量/信息的角度，最理想的解法在物理上可行吗？",
    ],
    "rebuild": [
        "基于以上第一性原理，如果从零设计，你会怎么做？",
        "有没有其他领域已经解决了类似的基础问题？",
        "能不能跳过中间层，直接实现核心目标？",
        "最简单的解法是什么？复杂性是在哪里引入的？",
    ],
    "stress_test": [
        "这个新方案在极限条件下还成立吗？",
        "如果规模扩大10倍/缩小10倍，方案还有效吗？",
        "这个方案依赖哪些外部条件？如果这些条件不存在？",
        "最大的已知风险是什么？如何缓解？",
    ]
}

# 各阶段的解释文本
STAGE_DESCRIPTIONS = {
    "clarify":         "阶段1：问题澄清 —— 确保我们在解决正确的问题",
    "assumptions":     "阶段2：假设暴露 —— 把隐形的假设变成可见的，再逐一质疑",
    "first_principles":"阶段3：第一性原理提取 —— 找到不可再分的基本真理",
    "rebuild":         "阶段4：方案重建 —— 基于第一性原理从零构建解法",
    "stress_test":     "阶段5：压力测试 —— 验证新方案的鲁棒性",
}

STAGE_ORDER = ["clarify", "assumptions", "first_principles", "rebuild", "stress_test"]


def print_banner():
    print("\n" + "="*60)
    print("  第一性原理分析向导 (First Principles Wizard)")
    print("  基于苏格拉底提问法 + 马斯克五步框架")
    print("="*60 + "\n")


def print_stage_header(stage: str):
    desc = STAGE_DESCRIPTIONS.get(stage, stage)
    print(f"\n{'─'*60}")
    print(f"  {desc}")
    print(f"{'─'*60}\n")


def interactive_mode(problem: str = None):
    """交互式向导模式"""
    print_banner()

    if not problem:
        print("请输入你想分析的问题（一句话描述）：")
        problem = input("> ").strip()
        if not problem:
            problem = "未指定"

    print(f"\n✅ 问题已记录：「{problem}」\n")
    print("接下来我们将通过5个阶段，系统拆解这个问题。\n")
    print("提示：每个阶段的问题，你可以直接思考并记录，也可以口头回答。")

    results = {"problem": problem, "stages": {}}

    for stage in STAGE_ORDER:
        print_stage_header(stage)
        questions = SOCRATIC_QUESTIONS[stage]
        stage_results = []

        for i, q in enumerate(questions, 1):
            print(f"Q{i}: {q}")
            ans = input("   → ").strip()
            if ans:
                stage_results.append({"question": q, "answer": ans})
            else:
                stage_results.append({"question": q, "answer": "(跳过)"})
            print()

        results["stages"][stage] = stage_results

    return results


def guided_output(results: dict) -> str:
    """生成结构化输出报告"""
    lines = []
    lines.append("# 第一性原理分析报告")
    lines.append(f"\n## 问题：{results['problem']}\n")

    stage_titles = {
        "clarify":         "一、问题澄清",
        "assumptions":     "二、暴露的假设",
        "first_principles":"三、第一性原理（基本真理）",
        "rebuild":         "四、重建方案",
        "stress_test":     "五、压力测试结论",
    }

    for stage in STAGE_ORDER:
        lines.append(f"\n## {stage_titles.get(stage, stage)}\n")
        for item in results["stages"].get(stage, []):
            lines.append(f"**{item['question']}**")
            lines.append(f"> {item['answer']}\n")

    return "\n".join(lines)


def quick_mode(problem: str):
    """快速模式：只打印关键提问，不需要交互"""
    print_banner()
    print(f"问题：{problem}\n")
    print("以下是各阶段的核心引导问题，请逐一思考：\n")

    for stage in STAGE_ORDER:
        print_stage_header(stage)
        for i, q in enumerate(SOCRATIC_QUESTIONS[stage], 1):
            print(f"  {i}. {q}")

    # 输出 JSON 供 AI 解析
    output = {
        "problem": problem,
        "stages": {}
    }
    for stage in STAGE_ORDER:
        output["stages"][stage] = SOCRATIC_QUESTIONS[stage]

    print("\n[SCRIPT_OUTPUT_JSON]" + json.dumps(output, ensure_ascii=False) + "[/SCRIPT_OUTPUT_JSON]")


def main():
    args = sys.argv[1:]

    if not args:
        # 交互式模式
        results = interactive_mode()
        report = guided_output(results)
        print("\n" + "="*60)
        print("分析完成！以下是结构化报告：")
        print("="*60)
        print(report)
        # 输出 JSON
        print("\n[SCRIPT_OUTPUT_JSON]" + json.dumps(results, ensure_ascii=False) + "[/SCRIPT_OUTPUT_JSON]")

    elif args[0] == "--quick" and len(args) >= 2:
        problem = " ".join(args[1:])
        quick_mode(problem)

    elif args[0] == "--interactive":
        problem = " ".join(args[1:]) if len(args) > 1 else None
        results = interactive_mode(problem)
        report = guided_output(results)
        print("\n" + "="*60)
        print(report)
        print("\n[SCRIPT_OUTPUT_JSON]" + json.dumps(results, ensure_ascii=False) + "[/SCRIPT_OUTPUT_JSON]")

    else:
        problem = " ".join(args)
        quick_mode(problem)


if __name__ == "__main__":
    main()
