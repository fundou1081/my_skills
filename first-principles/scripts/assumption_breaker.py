#!/usr/bin/env python3
"""
假设爆破矩阵 (Assumption Breaker Matrix)
将问题中的所有假设分类为：
  A. 物理/数学约束（不可改变）
  B. 行业惯例（可质疑）
  C. 历史遗留（可改变）
  D. 个人偏见（应审视）

使用方式：
  python3 assumption_breaker.py "你的问题描述"
  python3 assumption_breaker.py --domain software "为什么微服务比单体好"
"""

import sys
import json

# ============================================================
# 各领域的常见假设库
# ============================================================

DOMAIN_ASSUMPTIONS = {
    "engineering": [
        ("硬件必须遵循现有供应链，用现成零件", "B"),
        ("产品必须满足现有测试标准", "B"),
        ("设计周期至少要N个月", "C"),
        ("材料选型必须参考竞品", "C"),
        ("物理定律（热力学、牛顿力学）", "A"),
        ("制造公差有物理下限", "A"),
        ("成本越低质量越差", "D"),
        ("复杂功能意味着复杂结构", "D"),
    ],
    "software": [
        ("代码必须向后兼容", "B"),
        ("数据库必须用关系型", "C"),
        ("系统必须24×7不停机更新", "B"),
        ("微服务比单体架构更好", "D"),
        ("性能优化必须以牺牲可读性为代价", "D"),
        ("布林定律：软件复杂度随功能指数增长", "A"),
        ("CAP定理：一致性/可用性/分区容忍三选二", "A"),
        ("所有系统都需要高可用", "D"),
        ("重写不如重构", "D"),
    ],
    "product": [
        ("用户需要更多功能", "D"),
        ("竞品有的功能我们也必须有", "C"),
        ("更好的用户体验需要更多开发时间", "D"),
        ("用户不愿意付出学习成本", "D"),
        ("产品必须满足所有用户需求", "D"),
        ("用户痛点必须通过产品功能解决", "B"),
        ("人类认知资源有限（米勒定律：7±2）", "A"),
        ("用户决策受默认选项影响（行为经济学）", "A"),
    ],
    "business": [
        ("行业利润率有固定上限", "C"),
        ("市场份额只能靠价格战", "D"),
        ("规模越大成本越低", "B"),
        ("进入壁垒必须依靠专利或资金", "C"),
        ("供需关系决定价格（经济学基本规律）", "A"),
        ("边际成本递减规律", "A"),
        ("创业需要大量初始资本", "D"),
        ("增长依赖广告投放", "C"),
    ],
    "process": [
        ("会议是协作的最佳方式", "C"),
        ("审批流程必须经过N个层级", "C"),
        ("文档越详细越好", "D"),
        ("任务必须串行执行", "C"),
        ("变更必须经过漫长测试周期", "B"),
        ("人工处理比自动化更可靠（某些场景）", "D"),
        ("信息传递有延迟（通信基本规律）", "A"),
        ("人类处理信息有带宽上限（认知规律）", "A"),
    ]
}

ASSUMPTION_CATEGORIES = {
    "A": ("🔒 物理/数学约束", "不可改变，需绕过或利用"),
    "B": ("📋 行业标准/规范",  "可以质疑，有时可以突破"),
    "C": ("🏛️ 历史遗留/惯例", "通常可以改变，只是没人尝试"),
    "D": ("💭 个人/集体偏见", "应该重点审视和挑战"),
}


def print_banner():
    print("\n" + "="*60)
    print("  假设爆破矩阵 (Assumption Breaker Matrix)")
    print("  识别 → 分类 → 质疑 → 保留真正的约束")
    print("="*60 + "\n")


def show_categories():
    print("假设分类说明：\n")
    for k, (name, desc) in ASSUMPTION_CATEGORIES.items():
        print(f"  [{k}] {name}：{desc}")
    print()


def analyze_domain(domain: str, problem: str):
    """分析指定领域的常见假设"""
    assumptions = DOMAIN_ASSUMPTIONS.get(domain, [])
    if not assumptions:
        print(f"未找到领域 '{domain}' 的预设假设库，使用通用分析模式。")
        return

    print(f"\n问题：{problem}")
    print(f"领域：{domain}\n")
    print("以下是该领域常见的假设，请逐一判断哪些与你的问题相关：\n")

    categorized = {"A": [], "B": [], "C": [], "D": []}
    for assumption, category in assumptions:
        categorized[category].append(assumption)

    result_data = {"problem": problem, "domain": domain, "assumptions": {}}

    for cat in ["A", "B", "C", "D"]:
        name, desc = ASSUMPTION_CATEGORIES[cat]
        items = categorized[cat]
        if not items:
            continue
        print(f"\n{name}（{desc}）：")
        result_data["assumptions"][cat] = {"name": name, "desc": desc, "items": items}
        for i, item in enumerate(items, 1):
            print(f"  {i}. {item}")

    print("\n[SCRIPT_OUTPUT_JSON]" + json.dumps(result_data, ensure_ascii=False) + "[/SCRIPT_OUTPUT_JSON]")


def custom_analysis(problem: str):
    """通用假设分析引导"""
    print(f"\n问题：{problem}\n")
    print("请针对你的问题，思考以下4类假设：\n")

    questions_by_cat = {
        "A": [
            "这个问题中有哪些物理/数学定律是绝对约束？",
            "什么是从基础科学/工程原理上不可绕过的限制？",
        ],
        "B": [
            "行业内大家都遵循哪些标准或规范？",
            "这些标准是法规要求，还是只是惯例？",
        ],
        "C": [
            "历史上是如何演变到现在这个做法的？",
            "最初的设计约束现在还存在吗？",
            "如果重新设计，现在会不会做不同的选择？",
        ],
        "D": [
            "团队或自己有哪些'理所当然'的信念？",
            "哪些观点从未被认真质疑过？",
            "有没有偏见来自过去的成功经验？",
        ]
    }

    output_data = {"problem": problem, "questions": {}}
    for cat, questions in questions_by_cat.items():
        name, desc = ASSUMPTION_CATEGORIES[cat]
        print(f"\n{name}（{desc}）：")
        output_data["questions"][cat] = {"name": name, "questions": questions}
        for q in questions:
            print(f"  • {q}")

    print("\n[SCRIPT_OUTPUT_JSON]" + json.dumps(output_data, ensure_ascii=False) + "[/SCRIPT_OUTPUT_JSON]")


def main():
    args = sys.argv[1:]
    print_banner()
    show_categories()

    if not args:
        print("用法：")
        print("  python3 assumption_breaker.py '你的问题'")
        print("  python3 assumption_breaker.py --domain software '为什么微服务比单体好'")
        print(f"\n可用领域：{', '.join(DOMAIN_ASSUMPTIONS.keys())}")
        return

    if args[0] == "--domain" and len(args) >= 3:
        domain = args[1]
        problem = " ".join(args[2:])
        analyze_domain(domain, problem)
    elif args[0] == "--domain" and len(args) == 2:
        domain = args[1]
        print("请提供问题描述。")
        problem = input("问题: ").strip()
        analyze_domain(domain, problem)
    else:
        problem = " ".join(args)
        custom_analysis(problem)


if __name__ == "__main__":
    main()
