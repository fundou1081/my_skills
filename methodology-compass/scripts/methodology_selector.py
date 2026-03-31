#!/usr/bin/env python3
"""
方法论选择器脚本 - Methodology Selector
根据任务描述自动推荐最合适的方法论组合
"""

import argparse
import json
import sys
from typing import List, Dict, Tuple

# 方法论数据库
METHODOLOGIES = {
    "SMART": {
        "name": "SMART 目标设定",
        "适用场景": ["目标模糊", "指标不清晰", "考核标准不明确", "任务验收困难"],
        "复杂度": 1,
        "步骤数": 5,
        "关键词": ["目标", "指标", "KPI", "达成", "验收", "标准"]
    },
    "5W2H": {
        "name": "5W2H 信息完整性",
        "适用场景": ["任务布置不清晰", "需求理解模糊", "方案不完整", "信息遗漏"],
        "复杂度": 1,
        "步骤数": 7,
        "关键词": ["做什么", "为什么", "谁来做", "何时", "何地", "怎么", "多少"]
    },
    "OKR": {
        "name": "OKR 战略对齐",
        "适用场景": ["团队目标管理", "季度规划", "战略分解", "目标对齐"],
        "复杂度": 2,
        "步骤数": 8,
        "关键词": ["季度", "团队", "战略", "对齐", "Objective", "Key Result"]
    },
    "PDCA": {
        "name": "PDCA 持续改进",
        "适用场景": ["流程优化", "质量管理", "问题整改", "项目迭代"],
        "复杂度": 2,
        "步骤数": 4,
        "关键词": ["优化", "改进", "迭代", "质量", "流程", "检查", "标准化"]
    },
    "金字塔原理": {
        "name": "金字塔原理 表达结构",
        "适用场景": ["汇报材料", "邮件写作", "文档撰写", "演讲准备", "说服他人"],
        "复杂度": 1,
        "步骤数": 3,
        "关键词": ["汇报", "邮件", "说服", "总结", "结论", "论点", "结构"]
    },
    "GTD": {
        "name": "GTD 个人任务管理",
        "适用场景": ["待办事项多", "效率低下", "工作焦虑", "任务遗漏"],
        "复杂度": 2,
        "步骤数": 5,
        "关键词": ["待办", "效率", "管理", "清单", "执行", "任务", "收集"]
    },
    "STAR": {
        "name": "STAR 复盘与面试",
        "适用场景": ["项目复盘", "面试准备", "绩效面谈", "案例写作", "经验总结"],
        "复杂度": 1,
        "步骤数": 4,
        "关键词": ["复盘", "面试", "经历", "结果", "情境", "任务", "行动"]
    },
    "GROW": {
        "name": "GROW 教练式辅导",
        "适用场景": ["员工辅导", "目标对话", "发展规划", "问题讨论"],
        "复杂度": 1,
        "步骤数": 4,
        "关键词": ["辅导", "发展", "规划", "目标", "现状", "选择", "意愿"]
    },
    "RACI": {
        "name": "RACI 角色与职责",
        "适用场景": ["跨部门协作", "项目分工", "责任不清", "推诿扯皮"],
        "复杂度": 2,
        "步骤数": 4,
        "关键词": ["分工", "职责", "谁负责", "跨部门", "协作", "责任人"]
    },
    "艾森豪威尔": {
        "name": "艾森豪威尔矩阵 优先级",
        "适用场景": ["任务太多", "优先级混乱", "时间不够", "紧急重要判断"],
        "复杂度": 1,
        "步骤数": 4,
        "关键词": ["优先级", "紧急", "重要", "时间不够", "太多任务"]
    },
    "SBI": {
        "name": "SBI 反馈模型",
        "适用场景": ["绩效反馈", "建设性批评", "表扬肯定", "沟通辅导"],
        "复杂度": 1,
        "步骤数": 3,
        "关键词": ["反馈", "批评", "表扬", "绩效", "表现", "影响"]
    },
    "AAR": {
        "name": "AAR 行动后反思",
        "适用场景": ["项目结束", "关键事件后", "团队学习", "经验萃取"],
        "复杂度": 1,
        "步骤数": 5,
        "关键词": ["复盘", "反思", "经验", "改进", "发生了什么", "下次"]
    },
    "5-Why": {
        "name": "5-Why 根因分析",
        "适用场景": ["问题排查", "故障分析", "根本原因", "追责分析"],
        "复杂度": 2,
        "步骤数": 5,
        "关键词": ["为什么", "原因", "问题", "故障", "根本", "追溯"]
    },
    "预-mortem": {
        "name": "预-mortem 事前验尸",
        "适用场景": ["项目启动", "方案评审", "风险预防", "决策分析"],
        "复杂度": 2,
        "步骤数": 3,
        "关键词": ["失败", "风险", "预防", "项目启动", "假设", "避免"]
    },
    "决策矩阵": {
        "name": "决策矩阵 方案选型",
        "适用场景": ["方案选型", "资源分配", "供应商选择", "优先级排序"],
        "复杂度": 3,
        "步骤数": 4,
        "关键词": ["选择", "对比", "评估", "哪个好", "决策", "方案"]
    }
}

# 任务类型与推荐方法论
TASK_TYPES = {
    "目标设定类": {
        "优先级": ["SMART", "OKR"],
        "备选": ["决策矩阵", "艾森豪威尔"]
    },
    "信息收集类": {
        "优先级": ["5W2H", "RACI"],
        "备选": ["金字塔原理"]
    },
    "问题解决类": {
        "优先级": ["5-Why", "PDCA"],
        "备选": ["预-mortem", "AAR"]
    },
    "表达汇报类": {
        "优先级": ["金字塔原理", "STAR"],
        "备选": ["SBI", "SMART"]
    },
    "效率管理类": {
        "优先级": ["GTD", "艾森豪威尔"],
        "备选": ["OKR", "PDCA"]
    },
    "沟通反馈类": {
        "优先级": ["SBI", "GROW"],
        "备选": ["STAR", "AAR"]
    },
    "角色职责类": {
        "优先级": ["RACI", "5W2H"],
        "备选": ["GROW"]
    },
    "复盘反思类": {
        "优先级": ["AAR", "STAR"],
        "备选": ["5-Why", "PDCA"]
    },
    "决策选型类": {
        "优先级": ["决策矩阵", "预-mortem"],
        "备选": ["金字塔原理", "OKR"]
    }
}


def analyze_task(task_description: str) -> Tuple[List[str], str]:
    """
    分析任务描述，返回推荐方法论列表和任务类型
    """
    task_lower = task_description.lower()

    # 关键词匹配
    matches = {}
    for method_id, method in METHODOLOGIES.items():
        score = 0
        for keyword in method["关键词"]:
            if keyword.lower() in task_lower:
                score += 2
        # 检查适用场景
        for scenario in method["适用场景"]:
            if scenario.lower() in task_lower:
                score += 1
        if score > 0:
            matches[method_id] = score

    # 按匹配度排序
    sorted_matches = sorted(matches.items(), key=lambda x: x[1], reverse=True)

    # 确定任务类型
    task_type = "信息收集类"  # 默认
    type_scores = {}
    for t_type, methods in TASK_TYPES.items():
        score = 0
        for m in methods["优先级"] + methods["备选"]:
            if m in matches:
                score += matches[m]
        type_scores[t_type] = score

    if type_scores:
        task_type = max(type_scores.items(), key=lambda x: x[1])[0]

    # 返回推荐方法论（最多3个）
    recommended = [m[0] for m in sorted_matches[:3]]

    # 如果没有匹配，添加默认推荐
    if not recommended:
        recommended = ["5W2H", "金字塔原理"]

    return recommended, task_type


def generate_questionnaire(methods: List[str], task_type: str) -> str:
    """
    根据推荐方法论生成问卷清单
    """
    output = []
    output.append(f"## 任务诊断\n")
    output.append(f"**任务类型**：{task_type}\n")
    output.append(f"**推荐方法论**：{' + '.join(methods)}\n")
    output.append(f"\n---\n\n")

    for i, method_id in enumerate(methods, 1):
        method = METHODOLOGIES.get(method_id, {})
        output.append(f"### {i}. {method.get('name', method_id)}\n")

        if method_id == "SMART":
            output.append("请回答以下问题来明确你的目标：\n\n")
            output.append("| 维度 | 问题 |\n|------|------|\n")
            output.append("| **S - Specific（具体）** | 具体要达成什么？目标的核心是什么？ |\n")
            output.append("| **M - Measurable（可衡量）** | 如何衡量目标是否达成？有哪些量化指标？ |\n")
            output.append("| **A - Achievable（可达成）** | 现有资源（人/钱/时间）是否足够？有哪些障碍？ |\n")
            output.append("| **R - Relevant（相关）** | 这个目标与更大的战略/团队目标有什么关系？ |\n")
            output.append("| **T - Time-bound（有时限）** | 截止日期是什么时候？阶段性里程碑是什么？ |\n")

        elif method_id == "5W2H":
            output.append("请回答以下7个问题确保信息完整：\n\n")
            output.append("| 维度 | 问题 |\n|------|------|\n")
            output.append("| **What（什么）** | 具体要做什么事？交付物是什么？ |\n")
            output.append("| **Why（为什么）** | 为什么要做这件事？有什么价值或紧迫性？ |\n")
            output.append("| **Who（谁）** | 谁来做？谁受益？谁配合？ |\n")
            output.append("| **When（何时）** | 什么时候开始？什么时候完成？ |\n")
            output.append("| **Where（何地）** | 在哪里执行？线上还是线下？ |\n")
            output.append("| **How（如何）** | 具体怎么做？执行步骤是什么？ |\n")
            output.append("| **How much（多少）** | 需要多少预算/人手/资源？ |\n")

        elif method_id == "PDCA":
            output.append("让我们用PDCA循环来推进：\n\n")
            output.append("| 阶段 | 问题 |\n|------|------|\n")
            output.append("| **Plan（计划）** | 目标是什么？要达到什么标准？计划怎么执行？ |\n")
            output.append("| **Do（执行）** | 谁在执行？执行进度如何？有没有发现新问题？ |\n")
            output.append("| **Check（检查）** | 结果符合预期吗？差距在哪里？成功因素是什么？ |\n")
            output.append("| **Act（行动）** | 标准化成功的做法？针对差距制定什么改进措施？ |\n")

        elif method_id == "OKR":
            output.append("请设定你的OKR：\n\n")
            output.append("#### O - Objective（目标）\n")
            output.append("- 描述一个激励性的目标（1-2句话）：\n\n")
            output.append("#### KR - Key Results（关键结果）\n")
            output.append("请列出2-4个可量化的关键结果：\n\n")
            output.append("| KR# | 关键结果 | 衡量指标 | 目标值 |\n")
            output.append("|-----|---------|---------|-------|\n")
            output.append("| KR1 | | | |\n")
            output.append("| KR2 | | | |\n")
            output.append("| KR3 | | | |\n")

        elif method_id == "金字塔原理":
            output.append("请按金字塔结构组织你的内容：\n\n")
            output.append("#### 结论先行（一句话）\n")
            output.append("- 你的核心观点是什么？\n\n")
            output.append("#### 分论点支撑（2-3个）\n")
            output.append("- **分论点1**：[标题]\n  - 支撑事实/数据：\n\n")
            output.append("- **分论点2**：[标题]\n  - 支撑事实/数据：\n\n")
            output.append("- **分论点3**：[标题]\n  - 支撑事实/数据：\n\n")

        elif method_id == "GTD":
            output.append("用GTD整理你的待办事项：\n\n")
            output.append("#### 1. 收集（Inbox）\n")
            output.append("把所有想到的待办写下来（不要分类）：\n")
            output.append("1. \n2. \n3. \n\n")
            output.append("#### 2. 处理决定\n")
            output.append("| 待办 | 下一步行动 | 分类 |\n|------|-----------|------|\n")
            output.append("| | | ☐项目 ☐等待 ☐日程 ☐委托 |\n")
            output.append("| | | ☐项目 ☐等待 ☐日程 ☐委托 |\n")

        elif method_id == "RACI":
            output.append("请填写RACI矩阵：\n\n")
            output.append("| 任务/决策 | 角色1 | 角色2 | 角色3 | 角色4 |\n")
            output.append("|-----------|-------|-------|-------|-------|\n")
            output.append("| 任务1 | | | | |\n")
            output.append("| 任务2 | | | | |\n")
            output.append("| 任务3 | | | | |\n")
            output.append("\n**R**=执行 **A**=审批 **C**=咨询 **I**=知会\n")

        elif method_id == "5-Why":
            output.append("连续追问5个\"为什么\"找到根本原因：\n\n")
            output.append("| 层级 | 为什么 | 答案 |\n|------|--------|------|\n")
            output.append("| 问题陈述 | 发生了什么？ | |\n")
            output.append("| 第1问 | 为什么发生？ | |\n")
            output.append("| 第2问 | 为什么那样？ | |\n")
            output.append("| 第3问 | 为什么当时没发现？ | |\n")
            output.append("| 第4问 | 根本原因是什么？ | |\n")
            output.append("| 第5问（可选） | 如何防止再次发生？ | |\n")

        elif method_id == "决策矩阵":
            output.append("请列出你的选项并进行评估：\n\n")
            output.append("#### 选项列表\n")
            output.append("- 选项A：\n")
            output.append("- 选项B：\n")
            output.append("- 选项C：\n\n")
            output.append("#### 评估维度\n")
            output.append("请确定2-4个最重要的评估维度（如：成本、质量、风险、速度）：\n")
            output.append("1. \n2. \n3. \n\n")
            output.append("#### 加权评分表\n")
            output.append("| 维度 | 权重(%) | 选项A | 选项B | 选项C |\n")
            output.append("|------|---------|-------|-------|-------|\n")
            output.append("| 维度1 | | | | |\n")
            output.append("| 维度2 | | | | |\n")
            output.append("| 维度3 | | | | |\n")
            output.append("| **加权总分** | 100% | | | |\n")

        elif method_id == "SBI":
            output.append("用SBI模型提供反馈：\n\n")
            output.append("#### S - Situation（情境）\n")
            output.append("在什么具体场景/时间点？\n\n")
            output.append("#### B - Behavior（行为）\n")
            output.append("具体做了什么/说了什么？\n\n")
            output.append("#### I - Impact（影响）\n")
            output.append("产生了什么影响（正面/负面）？\n\n")

        elif method_id == "AAR":
            output.append("行动后反思（AAR）：\n\n")
            output.append("| 问题 | 回答 |\n|------|------|\n")
            output.append("| 1. 现在实际发生了什么？ | |\n")
            output.append("| 2. 预期应该发生什么？ | |\n")
            output.append("| 3. 差异原因是什么？ | |\n")
            output.append("| 4. 下次如何改进？ | |\n")
            output.append("| 5. 经验如何分享给团队？ | |\n")

        elif method_id == "预-mortem":
            output.append("事前验尸 - 假设项目失败了：\n\n")
            output.append("#### 假设失败场景\n")
            output.append("请描述项目最可能的失败方式：\n\n")
            output.append("#### 可能原因分析\n")
            output.append("| 类别 | 可能原因 |\n|------|----------|\n")
            output.append("| 技术风险 | |\n")
            output.append("| 人力风险 | |\n")
            output.append("| 资源风险 | |\n")
            output.append("| 外部风险 | |\n")
            output.append("| 管理风险 | |\n")
            output.append("\n#### 预防措施\n")
            output.append("针对上述风险，制定预防措施：\n\n")

        elif method_id == "艾森豪威尔":
            output.append("用四象限矩阵管理任务：\n\n")
            output.append("| | **紧急** | **不紧急** |\n")
            output.append("|------|---------|----------|\n")
            output.append("| **重要** | **Ⅰ 立即执行** |\n")
            output.append("| | 危机、截止日期 |\n")
            output.append("| | |\n")
            output.append("| | |\n")
            output.append("|------|---------|----------|\n")
            output.append("| **不重要** | **Ⅲ 委托他人** |\n")
            output.append("| | Interruptions |\n")
            output.append("| | |\n")
            output.append("| | |\n")

        elif method_id == "STAR":
            output.append("用STAR结构描述经历：\n\n")
            output.append("#### S - Situation（情境）\n")
            output.append("背景是什么？当时的情况是怎样的？\n\n")
            output.append("#### T - Task（任务）\n")
            output.append("你面临的任务/挑战是什么？你的职责是什么？\n\n")
            output.append("#### A - Action（行动）\n")
            output.append("你采取了什么具体行动？为什么？\n\n")
            output.append("#### R - Result（结果）\n")
            output.append("结果如何？学到了什么？量化成果？\n\n")

        elif method_id == "GROW":
            output.append("用GROW模型进行教练对话：\n\n")
            output.append("| 阶段 | 问题 |\n|------|------|\n")
            output.append("| **G - Goal（目标）** | 你想达成什么？具体目标是什么？ |\n")
            output.append("| **R - Reality（现状）** | 当前情况如何？已经做了什么？ |\n")
            output.append("| **O - Options（选择）** | 有哪些可选方案？还有什么可能？ |\n")
            output.append("| **W - Will（意愿）** | 下一步做什么？什么时候开始？ |\n")

        output.append("\n---\n\n")

    return "".join(output)


def generate_comparison_table() -> str:
    """生成方法论对比速查表"""
    output = []
    output.append("## 方法论对比速查表\n\n")

    scenarios = [
        ("目标模糊/不清晰", "SMART", "OKR", "避免单独用PDCA"),
        ("任务布置不清楚", "5W2H", "RACI", "避免直接执行"),
        ("问题排查/故障", "5-Why", "AAR", "避免急于下结论"),
        ("流程需要优化", "PDCA", "GTD", "避免大而全"),
        ("汇报/邮件/说服", "金字塔原理", "SBI", "避免信息堆砌"),
        ("跨部门协作", "RACI", "5W2H", "避免职责重叠"),
        ("时间管理/优先级", "艾森豪威尔", "GTD", "避免什么都做"),
        ("决策/方案选型", "决策矩阵", "预-mortem", "避免拍脑袋"),
        ("团队目标管理", "OKR", "SMART", "避免目标与战略脱节"),
        ("绩效反馈/辅导", "SBI", "GROW", "避免评价式反馈"),
        ("项目/事件复盘", "AAR", "STAR", "避免只追责任"),
        ("员工发展规划", "GROW", "SMART", "避免说教"),
    ]

    output.append("| 场景 | 首选 | 备选 | 避免 |\n")
    output.append("|------|------|------|------|\n")
    for scenario, primary, backup, avoid in scenarios:
        output.append(f"| {scenario} | {primary} | {backup} | {avoid} |\n")

    return "".join(output)


def main():
    parser = argparse.ArgumentParser(
        description="方法论选择器 - 根据任务描述推荐合适的方法论"
    )
    parser.add_argument("task", nargs="?", help="任务描述")
    parser.add_argument("--task-type", "-t", help="指定任务类型")
    parser.add_argument("--compare", "-c", action="store_true", help="显示方法论对比表")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有方法论")
    parser.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown", help="输出格式")

    args = parser.parse_args()

    # 列出所有方法论
    if args.list:
        print("## 可用方法论库\n")
        for method_id, method in sorted(METHODOLOGIES.items()):
            print(f"### {method_id}: {method['name']}")
            print(f"**适用场景**：{', '.join(method['适用场景'])}")
            print(f"**步骤数**：{method['步骤数']}")
            print()
        return

    # 显示对比表
    if args.compare:
        print(generate_comparison_table())
        return

    # 交互式选择任务类型
    if not args.task:
        print("请输入任务描述，或使用以下选项：")
        print("  --list     列出所有方法论")
        print("  --compare  显示方法论对比表")
        print()
        print("任务类型示例：")
        for task_type in TASK_TYPES.keys():
            print(f"  - {task_type}")
        print()
        print("快速启动（指定任务类型）：")
        print("  python3 methodology_selector.py -t '目标设定类'")
        return

    # 分析任务
    recommended, task_type = analyze_task(args.task)

    # 生成问卷
    questionnaire = generate_questionnaire(recommended, task_type)

    if args.format == "json":
        result = {
            "task": args.task,
            "task_type": task_type,
            "recommended": recommended,
            "questionnaire": questionnaire
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(questionnaire)


if __name__ == "__main__":
    main()
