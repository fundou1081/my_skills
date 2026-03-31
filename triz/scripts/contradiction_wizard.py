#!/usr/bin/env python3
"""
TRIZ 矛盾识别向导
TRIZ Contradiction Identification Wizard

引导用户完成问题分析，识别：
1. 技术矛盾（Technical Contradiction）
2. 物理矛盾（Physical Contradiction）

输出：结构化的矛盾描述，供后续查矩阵/原理使用
"""

import sys
import json

# ── 39个工程参数（编号 + 中英文名称）──────────────────────────────────────────
PARAMS = {
    1: "运动物体的重量 (Weight of moving object)",
    2: "静止物体的重量 (Weight of nonmoving object)",
    3: "运动物体的长度 (Length of moving object)",
    4: "静止物体的长度 (Length of nonmoving object)",
    5: "运动物体的面积 (Area of moving object)",
    6: "静止物体的面积 (Area of nonmoving object)",
    7: "运动物体的体积 (Volume of moving object)",
    8: "静止物体的体积 (Volume of nonmoving object)",
    9: "速度 (Speed)",
    10: "力 (Force)",
    11: "应力/压力 (Tension, Pressure)",
    12: "形状 (Shape)",
    13: "物体的稳定性 (Stability of object)",
    14: "强度 (Strength)",
    15: "运动物体的耐久性 (Durability of moving object)",
    16: "静止物体的耐久性 (Durability of nonmoving object)",
    17: "温度 (Temperature)",
    18: "亮度 (Brightness)",
    19: "运动物体消耗的能量 (Energy spent by moving object)",
    20: "静止物体消耗的能量 (Energy spent by nonmoving object)",
    21: "功率 (Power)",
    22: "能量浪费 (Waste of energy)",
    23: "物质浪费 (Waste of substance)",
    24: "信息损失 (Loss of information)",
    25: "时间浪费 (Waste of time)",
    26: "物质量 (Amount of substance)",
    27: "可靠性 (Reliability)",
    28: "测量精度 (Accuracy of measurement)",
    29: "制造精度 (Accuracy of manufacturing)",
    30: "作用于物体的有害因素 (Harmful factors acting on object)",
    31: "有害副作用 (Harmful side effects)",
    32: "可制造性 (Manufacturability)",
    33: "使用便利性 (Convenience of use)",
    34: "可修复性 (Repairability)",
    35: "适应性 (Adaptability)",
    36: "装置的复杂性 (Complexity of device)",
    37: "控制的复杂性 (Complexity of control)",
    38: "自动化程度 (Level of automation)",
    39: "生产率 (Productivity)",
}


def print_params():
    print("\n" + "=" * 70)
    print("  📋 39 个通用工程参数")
    print("=" * 70)
    for i in range(1, 40):
        print(f"  {i:>2}. {PARAMS[i]}")
    print("=" * 70)


def ask_technical_contradiction():
    """收集技术矛盾信息"""
    print("\n" + "─" * 70)
    print("  🔧 步骤 1/3：识别技术矛盾")
    print("  ─" * 70)
    print("\n  技术矛盾定义：改善某个参数时，会导致另一个参数恶化。")
    print("  例如：汽车速度加快(改善) → 安全性降低(恶化)")
    print("\n  请回答以下问题：\n")

    # 改善的参数
    print("  【改善的参数】")
    print("  当你改进什么方面时，问题出现了？")
    print("  （例如：提高速度、增加强度、降低成本、减小重量……）")
    improve_desc = input("  → 改善描述: ").strip()

    print_params()

    print("\n  从上方列表中选择一个最匹配的参数编号：")
    improve_param = input("  → 改善参数编号 (1-39): ").strip()
    while improve_param not in [str(i) for i in range(1, 40)]:
        improve_param = input("  → 无效，请输入 1-39 的数字: ").strip()

    # 恶化的参数
    print("\n  【恶化的参数】")
    print("  改善上述方面时，什么变差了？")
    print("  （例如：可靠性降低、能耗增加、复杂度上升……）")
    worsen_desc = input("  → 恶化描述: ").strip()

    print_params()

    print("\n  从上方列表中选择一个最匹配的参数编号：")
    worsen_param = input("  → 恶化参数编号 (1-39): ").strip()
    while worsen_param not in [str(i) for i in range(1, 40)]:
        worsen_param = input("  → 无效，请输入 1-39 的数字: ").strip()

    return {
        "type": "technical",
        "improve_param_no": int(improve_param),
        "improve_param_name": PARAMS[int(improve_param)],
        "improve_param_desc": improve_desc,
        "worsen_param_no": int(worsen_param),
        "worsen_param_name": PARAMS[int(worsen_param)],
        "worsen_param_desc": worsen_desc,
    }


def ask_physical_contradiction():
    """收集物理矛盾信息"""
    print("\n" + "─" * 70)
    print("  🔧 步骤 2/3：识别物理矛盾")
    print("  ─" * 70)
    print("\n  物理矛盾定义：同一个参数需要同时满足两个相反的要求。")
    print("  例如：纸张需要"硬"(支撑)也需要"软"(书写舒适)")
    print("\n  请回答以下问题：\n")

    print("  【核心矛盾参数】")
    print("  哪个物理量 / 参数处于两难境地？")
    print("  （例如：温度、尺寸、重量、硬度、速度、透明度……）")
    param_desc = input("  → 矛盾参数: ").strip()

    print("\n  【正方需求】")
    print("  在某方面 / 某时刻 / 某局部，这个参数需要怎样？")
    positive = input("  → 正向需求: ").strip()

    print("\n  【反方需求】")
    print("  在另一方面 / 另一时刻 / 另一局部，这个参数需要相反的怎样？")
    negative = input("  → 反向需求: ").strip()

    # 分离原理建议
    print("\n  💡 自动建议：根据物理矛盾的时空特性，优先考虑以下分离原理：")
    suggestions = []
    if param_desc in ["温度", "压力", "速度", "力", "温度", "temperature", "pressure", "speed", "force"]:
        suggestions.append("  - 条件分离：不同条件下满足不同需求")
        suggestions.append("  - 空间分离：不同部位/位置满足不同需求")
    suggestions.append("  - 时间分离：不同时间段满足不同需求")
    suggestions.append("  - 整体与部分分离：整体一个状态，部分另一个状态")

    for s in suggestions:
        print(s)

    return {
        "type": "physical",
        "param_desc": param_desc,
        "positive": positive,
        "negative": negative,
    }


def ask_problem_context():
    """收集问题背景"""
    print("\n" + "─" * 70)
    print("  🔧 步骤 3/3：问题背景（可选）")
    print("  ─" * 70)
    print("\n  为了更精准地推荐创新原理，请补充以下信息：\n")

    print("  【系统描述】")
    print("  这个系统/产品是什么？")
    system = input("  → 系统: ").strip()

    print("\n  【遇到的具体困难】")
    print("  详细描述遇到的问题")
    detail = input("  → 详细描述: ").strip()

    print("\n  【已有尝试】（如有）")
    print("  已经试过的方案或想法")
    tried = input("  → 已尝试方案: ").strip()

    return {
        "system": system,
        "detail": detail,
        "tried": tried,
    }


def print_result(tc_result, pc_result, ctx_result):
    """打印最终输出"""
    print("\n" + "=" * 70)
    print("  📊 TRIZ 矛盾分析报告")
    print("=" * 70)

    print(f"\n  系统: {ctx_result.get('system', 'N/A')}")
    print(f"  问题: {ctx_result.get('detail', 'N/A')}")
    if ctx_result.get('tried'):
        print(f"  已尝试: {ctx_result.get('tried')}")

    print("\n  ── 技术矛盾 ──")
    if tc_result:
        print(f"  改善参数: {tc_result['improve_param_no']} - {tc_result['improve_param_name']}")
        print(f"           场景: {tc_result['improve_param_desc']}")
        print(f"  恶化参数: {tc_result['worsen_param_no']} - {tc_result['worsen_param_name']}")
        print(f"           场景: {tc_result['worsen_param_desc']}")
    else:
        print("  未识别到技术矛盾")

    print("\n  ── 物理矛盾 ──")
    if pc_result:
        print(f"  矛盾参数: {pc_result['param_desc']}")
        print(f"  正向需求: {pc_result['positive']}")
        print(f"  反向需求: {pc_result['negative']}")
    else:
        print("  未识别到物理矛盾")

    # 输出 JSON 供后续脚本使用
    result = {
        "technical_contradiction": tc_result,
        "physical_contradiction": pc_result,
        "context": ctx_result,
    }
    print("\n  ── JSON 输出（供后续工具使用）──")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=" * 70)

    return result


def main():
    print("=" * 70)
    print("  TRIZ 矛盾识别向导")
    print("  引导你完成技术矛盾和物理矛盾的分析")
    print("=" * 70)

    # 询问是否识别技术矛盾
    print("\n  是否需要识别技术矛盾？(y/n)")
    print("  技术矛盾 = 改善A时，B会变差（工程参数层面的矛盾）")
    want_tc = input("  → ").strip().lower()
    tc_result = ask_technical_contradiction() if want_tc in ["y", "yes", "是"] else {}

    # 询问是否识别物理矛盾
    print("\n  是否需要识别物理矛盾？(y/n)")
    print("  物理矛盾 = 同一个参数需要同时满足两个相反的要求")
    want_pc = input("  → ").strip().lower()
    pc_result = ask_physical_contradiction() if want_pc in ["y", "yes", "是"] else {}

    # 问题背景
    ctx_result = ask_problem_context()

    # 输出结果
    return print_result(tc_result, pc_result, ctx_result)


if __name__ == "__main__":
    result = main()
    # 输出JSON到标准输出，供调用者捕获
    print("\n[SCRIPT_OUTPUT_JSON]", json.dumps(result, ensure_ascii=False), "[/SCRIPT_OUTPUT_JSON]")
