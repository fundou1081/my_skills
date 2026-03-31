#!/usr/bin/env python3
"""
methodology_framework_generator.py
多方法论组合框架自动生成器

功能：
1. 分析用户任务
2. 评估多种方法论组合的适用性和预期结果
3. 生成对比报告供用户选择
4. 用户确认后，自动生成完整执行框架
"""

import json
import sys
from typing import List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Methodology:
    """方法论定义"""
    name: str
    category: str
    strengths: List[str]
    weaknesses: List[str]
    best_for: List[str]
    output_type: str  # 目标/分析/计划/沟通/复盘
    complexity: str  # 简单/中等/复杂
    steps: List[str]


@dataclass
class FrameworkOption:
    """框架组合方案"""
    id: str
    name: str
    methodologies: List[str]
    description: str
    expected_output: str
    pros: List[str]
    cons: List[str]
    use_cases: List[str]
    complexity: str


# 核心方法论库
METHODOLOGIES = {
    "SMART": Methodology(
        name="SMART目标法",
        category="目标设定",
        strengths=["具体可衡量", "易于对齐", "避免模糊"],
        weaknesses=["过于线性", "不擅长诊断问题", "缺乏灵活性"],
        best_for=["设定季度OKR", "个人发展规划", "项目里程碑"],
        output_type="目标",
        complexity="简单",
        steps=["Specific-具体化", "Measurable-可衡量", "Achievable-可达成", "Relevant-相关性", "Time-bound-有时限"]
    ),
    "OKR": Methodology(
        name="OKR目标管理",
        category="目标设定",
        strengths=["上下对齐", "聚焦重点", "透明可见"],
        weaknesses=["周期长", "需要组织文化支持", "KR设计难度大"],
        best_for=["公司级战略目标", "团队季度目标", "创新项目"],
        output_type="目标",
        complexity="中等",
        steps=["设定Objective", "设计Key Results", "对齐上下级", "跟踪复盘"]
    ),
    "5-Why": Methodology(
        name="5问法（5-Why）",
        category="问题诊断",
        strengths=["穿透表象", "找到根因", "简单实用"],
        weaknesses=["依赖经验", "可能误导", "不擅长复杂问题"],
        best_for=["故障分析", "根因追溯", "质量改进"],
        output_type="分析",
        complexity="简单",
        steps=["问第一个为什么", "追问深层原因", "重复5次直到找到根因", "验证并制定对策"]
    ),
    "PDCA": Methodology(
        name="PDCA循环",
        category="问题解决",
        strengths=["持续改进", "闭环管理", "易于执行"],
        weaknesses=["创新性弱", "依赖执行纪律", "长期效果慢"],
        best_for=["流程优化", "质量改进", "日常工作迭代"],
        output_type="计划",
        complexity="简单",
        steps=["Plan-计划", "Do-执行", "Check-检查", "Act-改进"]
    ),
    "金字塔原理": Methodology(
        name="金字塔原理",
        category="沟通表达",
        strengths=["逻辑清晰", "重点突出", "易于理解"],
        weaknesses=["过于正式", "创新性弱", "不擅长发散讨论"],
        best_for=["商务汇报", "邮件写作", "方案呈现"],
        output_type="沟通",
        complexity="中等",
        steps=["结论先行", "以上统下", "归类分组", "逻辑递进"]
    ),
    "RACI": Methodology(
        name="RACI责任矩阵",
        category="沟通协作",
        strengths=["职责清晰", "避免推诿", "快速对齐"],
        weaknesses=["过于刚性", "不擅长创意工作", "维护成本高"],
        best_for=["项目分工", "跨部门协作", "流程梳理"],
        output_type="计划",
        complexity="中等",
        steps=["列出任务", "确定参与者", "分配RACI角色", "确认无遗漏"]
    ),
    "GROW": Methodology(
        name="GROW教练模型",
        category="目标设定",
        strengths=["引导式", "激发潜能", "适合个人发展"],
        weaknesses=["依赖教练水平", "效率较低", "不擅长紧急问题"],
        best_for=["个人辅导", "职业规划", "绩效面谈"],
        output_type="目标",
        complexity="中等",
        steps=["Goal-目标", "Reality-现状", "Options-选择", "Will-意愿"]
    ),
    "艾森豪威尔": Methodology(
        name="艾森豪威尔矩阵",
        category="效率管理",
        strengths=["优先排序清晰", "简单直观", "提高效率"],
        weaknesses=["过于简化", "不处理依赖关系", "缺乏深度"],
        best_for=["日程安排", "任务优先级", "时间管理"],
        output_type="计划",
        complexity="简单",
        steps=["区分紧急/重要", "放入四象限", "按优先级执行"]
    ),
    "GTD": Methodology(
        name="Getting Things Done",
        category="效率管理",
        strengths=["清空大脑", "系统化管理", "减少焦虑"],
        weaknesses=["系统复杂", "初期投入大", "不够灵活"],
        best_for=["个人事务管理", "知识工作者", "多项目并行"],
        output_type="计划",
        complexity="复杂",
        steps=["收集", "处理", "组织", "回顾", "执行"]
    ),
    "5W2H": Methodology(
        name="5W2H分析法",
        category="问题诊断",
        strengths=["全面覆盖", "结构清晰", "不易遗漏"],
        weaknesses=["缺乏深度", "机械死板", "创新性弱"],
        best_for=["问题定义", "方案评估", "流程审查"],
        output_type="分析",
        complexity="简单",
        steps=["What-做什么", "Why-为什么", "Who-谁来做", "When-何时", "Where-何地", "How-怎么做", "How much-多少成本"]
    ),
    "SWOT": Methodology(
        name="SWOT分析",
        category="问题诊断",
        strengths=["全局视角", "战略思维", "平衡分析"],
        weaknesses=["过于静态", "主观性强", "难量化"],
        best_for=["战略规划", "竞争分析", "商业决策"],
        output_type="分析",
        complexity="中等",
        steps=["分析Strengths", "识别Weaknesses", "发现Opportunities", "警惕Threats", "制定策略"]
    ),
    "AAR": Methodology(
        name="After Action Review",
        category="复盘反思",
        strengths=["快速迭代", "团队学习", "实践导向"],
        weaknesses=["依赖坦诚文化", "容易流于形式", "深度不够"],
        best_for=["项目复盘", "团队学习", "敏捷回顾"],
        output_type="复盘",
        complexity="中等",
        steps=["当时预期是什么", "实际发生了什么", "为什么有差异", "下次如何改进"]
    ),
    "STAR": Methodology(
        name="STAR法则",
        category="沟通表达",
        strengths=["结构化叙事", "有说服力", "便于STAR面试"],
        weaknesses=["不够灵活", "不适合复杂故事", "重复使用会僵化"],
        best_for=["面试回答", "工作汇报", "案例展示"],
        output_type="沟通",
        complexity="简单",
        steps=["Situation-情境", "Task-任务", "Action-行动", "Result-结果"]
    ),
    "SBI": Methodology(
        name="SBI反馈模型",
        category="沟通协作",
        strengths=["客观具体", "减少冲突", "行为导向"],
        weaknesses=["不够深入", "缺乏引导", "需要练习"],
        best_for=["绩效反馈", "日常沟通", "团队协作"],
        output_type="沟通",
        complexity="简单",
        steps=["Situation-情境", "Behavior-行为", "Impact-影响"]
    ),
    "六顶思考帽": Methodology(
        name="六顶思考帽",
        category="问题解决",
        strengths=["全面思考", "避免偏见", "高效讨论"],
        weaknesses=["执行复杂", "耗时较长", "需要引导者"],
        best_for=["团队决策", "复杂问题讨论", "头脑风暴"],
        output_type="分析",
        complexity="复杂",
        steps=["白帽-信息", "红帽-情感", "黑帽-风险", "黄帽-价值", "绿帽-创意", "蓝帽-控制"]
    )
}


# 预设框架组合方案
PRESET_FRAMEWORKS = {
    "目标规划型": FrameworkOption(
        id="goal_planning",
        name="🎯 目标规划型",
        methodologies=["OKR", "SMART", "GROW"],
        description="用于设定和分解目标，从战略到执行",
        expected_output="完整的目标体系 + 关键结果 + 行动路径",
        pros=["目标清晰可衡量", "上下对齐", "便于跟踪"],
        cons=["周期较长", "需要多次对齐"],
        use_cases=["公司战略规划", "团队季度目标", "个人发展计划"],
        complexity="复杂"
    ),
    "问题诊断型": FrameworkOption(
        id="problem_diagnosis",
        name="🔍 问题诊断型",
        methodologies=["5-Why", "5W2H", "PDCA"],
        description="用于发现问题、分析原因、制定对策",
        expected_output="问题定义 + 根因分析 + 解决方案 + 实施计划",
        pros=["系统全面", "逻辑清晰", "可迭代"],
        cons=["可能过于深入细节", "耗时较长"],
        use_cases=["故障复盘", "质量改进", "流程优化"],
        complexity="中等"
    ),
    "战略分析型": FrameworkOption(
        id="strategy_analysis",
        name="📊 战略分析型",
        methodologies=["SWOT", "六顶思考帽", "金字塔原理"],
        description="用于战略规划、竞争分析、重大决策",
        expected_output="战略分析报告 + 决策建议 + 行动计划",
        pros=["全局视角", "多维度分析", "决策支持"],
        cons=["需要较多信息", "主观判断多"],
        use_cases=["商业决策", "竞争分析", "战略规划"],
        complexity="复杂"
    ),
    "沟通协作型": FrameworkOption(
        id="communication",
        name="💬 沟通协作型",
        methodologies=["RACI", "SBI", "金字塔原理"],
        description="用于跨部门协作、职责对齐、反馈沟通",
        expected_output="责任矩阵 + 沟通机制 + 汇报模板",
        pros=["职责清晰", "减少冲突", "高效协作"],
        cons=["可能过于刚性", "需要各方确认"],
        use_cases=["项目管理", "绩效面谈", "跨团队协作"],
        complexity="中等"
    ),
    "效率提升型": FrameworkOption(
        id="efficiency",
        name="⚡ 效率提升型",
        methodologies=["艾森豪威尔", "GTD", "PDCA"],
        description="用于个人/团队效率提升、任务管理",
        expected_output="优先级清单 + 执行计划 + 复盘机制",
        pros=["聚焦重点", "减少拖延", "持续改进"],
        cons=["需要自律", "初期建立习惯耗时"],
        use_cases=["日常工作管理", "多项目管理", "个人效率提升"],
        complexity="中等"
    ),
    "复盘改进型": FrameworkOption(
        id="retrospective",
        name="🔄 复盘改进型",
        methodologies=["AAR", "PDCA", "5-Why"],
        description="用于项目/事件复盘、经验沉淀、持续改进",
        expected_output="复盘报告 + 改进清单 + 经验教训库",
        pros=["快速迭代", "团队学习", "避免重复犯错"],
        cons=["依赖坦诚文化", "可能流于形式"],
        use_cases=["项目复盘", "敏捷回顾", "事故分析"],
        complexity="简单"
    )
}


def analyze_task(task: str) -> Dict[str, Any]:
    """分析用户任务，识别任务类型和关键特征"""
    task_lower = task.lower()

    indicators = {
        "is_goal_setting": any(k in task_lower for k in ["目标", "规划", "计划", "设定", "制定", "做什么", "想要"]),
        "is_problem": any(k in task_lower for k in ["问题", "故障", "错误", "失败", "出了", "不对", "原因"]),
        "is_analysis": any(k in task_lower for k in ["分析", "调研", "研究", "评估", "看看"]),
        "is_communication": any(k in task_lower for k in ["汇报", "邮件", "写", "沟通", "反馈", "面谈"]),
        "is_planning": any(k in task_lower for k in ["分工", "安排", "排期", "优先级", "怎么开始"]),
        "is_review": any(k in task_lower for k in ["复盘", "回顾", "总结", "反思", "经验"]),
        "is_urgent": any(k in task_lower for k in ["紧急", "马上", "立刻", "尽快", "deadline"]),
        "is_team": any(k in task_lower for k in ["团队", "部门", "协作", "多人", "跨部门"]),
        "is_individual": any(k in task_lower for k in ["我", "个人", "自己"]),
        "is_strategy": any(k in task_lower for k in ["战略", "竞争", "市场", "商业", "决策"])
    }

    # 判断主要任务类型
    primary_type = "general"
    if indicators["is_goal_setting"]:
        primary_type = "goal_setting"
    elif indicators["is_problem"]:
        primary_type = "problem_solving"
    elif indicators["is_analysis"]:
        primary_type = "analysis"
    elif indicators["is_review"]:
        primary_type = "retrospective"
    elif indicators["is_communication"]:
        primary_type = "communication"
    elif indicators["is_planning"]:
        primary_type = "planning"

    return {
        "indicators": indicators,
        "primary_type": primary_type,
        "is_team_oriented": indicators["is_team"],
        "is_urgent": indicators["is_urgent"],
        "needs_multiple": indicators["is_strategy"] or indicators["is_team"]
    }


def generate_framework_options(task: str) -> List[FrameworkOption]:
    """根据任务生成推荐的框架组合方案"""
    analysis = analyze_task(task)
    recommendations = []

    # 根据任务类型推荐方案
    type_to_framework = {
        "goal_setting": ["目标规划型", "效率提升型"],
        "problem_solving": ["问题诊断型", "复盘改进型"],
        "analysis": ["战略分析型", "问题诊断型"],
        "retrospective": ["复盘改进型", "问题诊断型"],
        "communication": ["沟通协作型"],
        "planning": ["效率提升型", "沟通协作型"],
        "general": ["效率提升型", "问题诊断型"]
    }

    framework_ids = type_to_framework.get(analysis["primary_type"], ["效率提升型"])

    # 添加推荐
    for fid in framework_ids:
        if fid in PRESET_FRAMEWORKS:
            recommendations.append(PRESET_FRAMEWORKS[fid])

    # 如果需要多方法论组合，添加备选
    if analysis["needs_multiple"]:
        for fid, fw in PRESET_FRAMEWORKS.items():
            if fid not in framework_ids and len(recommendations) < 4:
                recommendations.append(fw)

    return recommendations


def evaluate_methodology(m: Methodology) -> Dict[str, Any]:
    """评估单个方法论的预期结果"""
    return {
        "输出类型": m.output_type,
        "复杂度": m.complexity,
        "预计耗时": {"简单": "15-30分钟", "中等": "1-2小时", "复杂": "半天到1天"}[m.complexity],
        "适用规模": {"简单": "1-3人", "中等": "3-10人", "复杂": "10人以上"}[m.complexity],
        "预期产出": _get_expected_output(m)
    }


def _get_expected_output(m: Methodology) -> str:
    """获取方法论的预期产出描述"""
    outputs = {
        "目标": "SMART目标 / OKR体系 / 行动计划",
        "分析": "分析报告 / 根因清单 / 策略建议",
        "计划": "任务清单 / 责任矩阵 / 时间表",
        "沟通": "汇报模板 / 反馈记录 / 会议纪要",
        "复盘": "复盘报告 / 经验教训 / 改进清单"
    }
    return outputs.get(m.output_type, "结构化文档")


def generate_comparison_report(task: str, options: List[FrameworkOption]) -> str:
    """生成方法论组合对比报告"""
    analysis = analyze_task(task)

    report = f"""
## 📋 方法论组合评估报告

### 任务分析
**原始任务**: {task}

**任务特征识别**:
| 特征 | 状态 |
|------|------|
| 目标设定 | {"✅ 是" if analysis['indicators']['is_goal_setting'] else "❌ 否"} |
| 问题诊断 | {"✅ 是" if analysis['indicators']['is_problem'] else "❌ 否"} |
| 分析调研 | {"✅ 是" if analysis['indicators']['is_analysis'] else "❌ 否"} |
| 沟通协作 | {"✅ 是" if analysis['indicators']['is_communication'] else "❌ 否"} |
| 复盘反思 | {"✅ 是" if analysis['indicators']['is_review'] else "❌ 否"} |
| 团队导向 | {"✅ 是" if analysis['is_team_oriented'] else "❌ 否"} |
| 紧急任务 | {"⚠️ 是" if analysis['is_urgent'] else "❌ 否"} |

**任务类型**: {analysis['primary_type']}

---

## 🔄 推荐方案对比

### 方案A: {options[0].name}
**方法论组合**: {' + '.join(options[0].methodologies)}

**描述**: {options[0].description}

| 维度 | 评估 |
|------|------|
| **预期产出** | {options[0].expected_output} |
| **复杂度** | {options[0].complexity} |
| **优点** | {', '.join(options[0].pros)} |
| **缺点** | {', '.join(options[0].cons)} |
| **适用场景** | {', '.join(options[0].use_cases)} |

---

### 方案B: {options[1].name if len(options) > 1 else '无'}
"""
    if len(options) > 1:
        report += f"""**方法论组合**: {' + '.join(options[1].methodologies)}

**描述**: {options[1].description}

| 维度 | 评估 |
|------|------|
| **预期产出** | {options[1].expected_output} |
| **复杂度** | {options[1].complexity} |
| **优点** | {', '.join(options[1].pros)} |
| **缺点** | {', '.join(options[1].cons)} |
| **适用场景** | {', '.join(options[1].use_cases)} |

---

### 方案C: {options[2].name if len(options) > 2 else '无'}
"""
    if len(options) > 2:
        report += f"""**方法论组合**: {' + '.join(options[2].methodologies)}

**描述**: {options[2].description}

| 维度 | 评估 |
|------|------|
| **预期产出** | {options[2].expected_output} |
| **复杂度** | {options[2].complexity} |
| **优点** | {', '.join(options[2].pros)} |
| **缺点** | {', '.join(options[2].cons)} |
| **适用场景** | {', '.join(options[2].use_cases)} |
"""
    else:
        report += "无备选方案"

    report += """
---

## 🎯 请选择方案

请回复选项编号和您的选择依据：

```
A - [选择原因]
B - [选择原因]
C - [选择原因]
自定义 - [您的方法论组合]
```

或者直接说"用A"即可开始执行。

---
"""
    return report


def generate_execution_framework(option: FrameworkOption, task: str) -> str:
    """根据选择的方案生成完整的执行框架"""

    framework = f"""
# 📋 执行框架：{option.name}

## 任务
**{task}**

## 方法论组合
{' + '.join(option.methodologies)}

## 预期产出
{option.expected_output}

---

## 执行步骤

"""

    # 为每个方法论生成详细步骤
    for i, method_name in enumerate(option.methodologies, 1):
        if method_name in METHODOLOGIES:
            m = METHODOLOGIES[method_name]
            framework += f"""
### 第{i}步：{m.name}

**方法论类型**: {m.category}
**复杂度**: {m.complexity}
**预计耗时**: {evaluate_methodology(m)['预计耗时']}

#### {m.name} 的 {len(m.steps)} 个步骤：
"""
            for j, step in enumerate(m.steps, 1):
                framework += f"{j}. {step}\n"

            framework += f"""
#### 追问清单：
| # | 追问问题 | 填写 |
|---|----------|------|
"""
            # 根据方法论类型生成追问
            questions = _get_followup_questions(m)
            for j, q in enumerate(questions, 1):
                framework += f"| {j} | {q} | __________ |\n"

            framework += "\n"

    # 生成最终交付物模板
    framework += f"""
---

## 📦 最终交付物模板

### 输出物清单
- [ ] 方法论组合确认清单
- [ ] 各步骤执行记录
- [ ] 追问清单填写结果
- [ ] 最终产出物

### 交付物格式
```
# [任务标题]

## 一、[方法论1名称]
### 执行结果
[填写执行结果]

## 二、[方法论2名称]（如适用）
### 执行结果
[填写执行结果]

## 三、综合产出
[最终交付物内容]

## 四、后续行动
| 行动项 | 负责人 | 截止日期 |
|--------|--------|----------|
| ... | ... | ... |
```

---

*框架生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

    return framework


def _get_followup_questions(m: Methodology) -> List[str]:
    """根据方法论类型生成追问问题"""
    base_questions = {
        "目标设定": [
            "这个目标的最终受益人是谁？",
            "如何衡量目标是否达成？",
            "实现这个目标的主要障碍是什么？",
            "需要哪些资源支持？",
            "目标的时间约束是什么？"
        ],
        "问题诊断": [
            "问题的表现形式是什么？",
            "这个问题持续了多久？",
            "已尝试过哪些解决方案？",
            "根本原因可能是什么？",
            "解决这个问题的紧迫性如何？"
        ],
        "沟通表达": [
            "受众是谁？他们关心什么？",
            "核心信息是什么？",
            "听众可能有什么疑问？",
            "希望达到什么效果？",
            "最佳传递方式是什么？"
        ],
        "问题解决": [
            "当前状态是什么？",
            "目标状态是什么？",
            "有哪些可选方案？",
            "每个方案的优缺点？",
            "如何验证解决方案有效？"
        ],
        "效率管理": [
            "当前最紧急的任务是什么？",
            "哪些任务可以委托他人？",
            "时间约束是什么？",
            "有哪些潜在风险？",
            "如何跟踪进度？"
        ],
        "复盘反思": [
            "最初的目标是什么？",
            "实际结果与预期的差异？",
            "成功的关键因素是什么？",
            "可以改进的地方？",
            "下次如何做得更好？"
        ]
    }

    return base_questions.get(m.category, [
        "当前状态是什么？",
        "目标是什么？",
        "有哪些约束条件？",
        "如何衡量成功？",
        "下一步是什么？"
    ])


def main():
    if len(sys.argv) < 2:
        print("用法: python3 methodology_framework_generator.py <任务描述>")
        print("示例: python3 methodology_framework_generator.py \"帮我规划下季度团队目标\"")
        sys.exit(1)

    task = sys.argv[1]

    # 分析任务
    analysis = analyze_task(task)
    print(f"\n🔍 任务分析完成")
    print(f"   任务类型: {analysis['primary_type']}")
    print(f"   团队导向: {'是' if analysis['is_team_oriented'] else '否'}")
    print(f"   紧急任务: {'是' if analysis['is_urgent'] else '否'}")

    # 生成方案
    options = generate_framework_options(task)

    # 输出对比报告
    report = generate_comparison_report(task, options)
    print("\n" + "="*60)
    print(report)


if __name__ == "__main__":
    main()
