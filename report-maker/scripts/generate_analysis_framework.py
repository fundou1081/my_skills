#!/usr/bin/env python3
"""
Report-Maker Analysis Framework Generator
生成分析框架的待办清单，确保深度和广度的系统性追问
"""

import json
import argparse
import sys
from typing import List, Dict, Optional

def generate_5w1h_framework(topic: str) -> List[Dict]:
    """生成 5W1H 分析框架"""
    framework = [
        {
            "id": "5w1h-1",
            "dimension": "What（什么）",
            "prompt": f"关于「{topic}」，具体是什么内容或现象？",
            "follow_up": [
                f"「{topic}」的核心要素有哪些？",
                f"「{topic}」涉及的关键变量是什么？",
                f"这些要素之间有什么关系？"
            ],
            "deep_drill": [
                f"「{topic}」的本质定义是什么？",
                f"如果不处理「{topic}」，会有什么后果？",
                f"「{topic}」的边界在哪里？哪些不在范围内？"
            ]
        },
        {
            "id": "5w1h-2",
            "dimension": "Why（为什么）",
            "prompt": f"为什么「{topic}」值得关注/重要？",
            "follow_up": [
                f"「{topic}」产生的根本原因是什么？",
                f"哪些因素驱动了「{topic}」的形成？",
                f"「{topic}」背后有哪些驱动力量？"
            ],
            "deep_drill": [
                f"「{topic}」的第一性原理是什么？",
                f"如果解决了这个问题，会释放什么价值？",
                f"这个问题不解决，长期会有什么积累效应？"
            ]
        },
        {
            "id": "5w1h-3",
            "dimension": "Who（谁）",
            "prompt": f"「{topic}」涉及哪些利益相关方？",
            "follow_up": [
                f"每个相关方的核心诉求是什么？",
                f"相关方之间的利益关系是什么？",
                f"谁是最关键的决策者/影响者？"
            ],
            "deep_drill": [
                f"各方在这个事件中扮演什么角色？",
                f"不同相关方的立场冲突点在哪里？",
                f"如何平衡各方利益？"
            ]
        },
        {
            "id": "5w1h-4",
            "dimension": "When（何时）",
            "prompt": f"「{topic}」的时间维度是怎样的？",
            "follow_up": [
                f"「{topic}」从何时开始出现？",
                f"「{topic}」的发展阶段如何划分？",
                f"关键时间节点是什么时候？"
            ],
            "deep_drill": [
                f"「{topic}」是否有周期性规律？",
                f"未来趋势预测：3个月/1年/3年后会怎样？",
                f"现在是否是关键介入时机？"
            ]
        },
        {
            "id": "5w1h-5",
            "dimension": "Where（何地）",
            "prompt": f"「{topic}」发生在什么场景/环境？",
            "follow_up": [
                f"不同地域/场景下「{topic}」有差异吗？",
                f"环境因素如何影响「{topic}」？",
                f"哪些场景是核心，哪些是边缘？"
            ],
            "deep_drill": [
                f"场景切换时，「{topic}」会如何变化？",
                f"是否存在最佳/最差场景？",
                f"场景创新是否能带来突破？"
            ]
        },
        {
            "id": "5w1h-6",
            "dimension": "How（如何）",
            "prompt": f"「{topic}」应该如何解决/处理？",
            "follow_up": [
                f"目前有哪些解决路径？",
                f"各路径的优缺点是什么？",
                f"实施步骤是什么？"
            ],
            "deep_drill": [
                f"路径选择的判断标准是什么？",
                f"如何验证方案的有效性？",
                f"失败的风险点和应对策略？"
            ]
        }
    ]
    return framework


def generate_5why_chain(topic: str, initial_problem: str) -> List[Dict]:
    """生成 5Why 追问链条"""
    chain = []
    base_prompts = [
        f"为什么「{initial_problem}」？",
        f"为什么这个原因会存在？",
        f"为什么这个条件会形成？",
        f"为什么这个系统会如此运作？",
        f"根本原因是什么？"
    ]
    
    for i, prompt in enumerate(base_prompts):
        chain.append({
            "id": f"5why-{i+1}",
            "level": f"第{i+1}层追问",
            "prompt": prompt,
            "expected_answer_format": "【原因陈述】→ 【证据/数据支撑】",
            "if_no_answer": "如果无法回答，说明需要更多信息或已触及认知边界"
        })
    return chain


def generate_5question_framework(topic: str) -> List[Dict]:
    """生成 5问法框架"""
    return [
        {
            "id": "5q-1",
            "question": f"「{topic}」的本质问题是什么？",
            "sub_questions": [
                f"我们真的理解「{topic}」吗？",
                f"表面问题和深层问题有什么区别？"
            ],
            "completion_criteria": "能用一句话概括核心问题"
        },
        {
            "id": "5q-2",
            "question": f"为什么现在需要解决「{topic}」？",
            "sub_questions": [
                "紧迫性来自哪里？",
                "如果不处理，时间成本是什么？"
            ],
            "completion_criteria": "明确优先级和驱动因素"
        },
        {
            "id": "5q-3",
            "question": f"「{topic}」有哪些可能的解决方案？",
            "sub_questions": [
                "头脑风暴：至少列出5个方案",
                "各方案的可行性评分？"
            ],
            "completion_criteria": "方案列表完整，优劣分析清晰"
        },
        {
            "id": "5q-4",
            "question": f"判断「{topic}」最佳方案的标准是什么？",
            "sub_questions": [
                "成本-收益分析维度",
                "风险-收益分析维度"
            ],
            "completion_criteria": "建立决策矩阵或评分体系"
        },
        {
            "id": "5q-5",
            "question": f"如何衡量「{topic}」的解决效果？",
            "sub_questions": [
                "KPI/OKR 是什么？",
                "验证周期多长？"
            ],
            "completion_criteria": "定义可量化的成功指标"
        }
    ]


def generate_7question_framework(topic: str) -> List[Dict]:
    """生成 7问法框架（5问 + 2问扩展）"""
    base = generate_5question_framework(topic)
    extension = [
        {
            "id": "7q-6",
            "question": f"解决「{topic}」存在哪些风险和障碍？",
            "sub_questions": [
                "内部风险：资源、能力、优先级",
                "外部风险：政策、市场、竞争",
                "最坏情况是什么？"
            ],
            "completion_criteria": "风险矩阵 + 应对预案"
        },
        {
            "id": "7q-7",
            "question": f"解决「{topic}」需要哪些资源和条件？",
            "sub_questions": [
                "人力资源需求",
                "财务资源需求",
                "技术/工具需求",
                "外部合作需求"
            ],
            "completion_criteria": "资源清单 + 获取计划"
        }
    ]
    return base + extension


def generate_expert_perspectives(topic: str, domain: str = "通用") -> List[Dict]:
    """生成专家视角清单"""
    # 根据领域动态选择专家组合
    expert_templates = {
        "技术": ["技术架构师", "安全专家", "性能工程师", "运维专家", "数据工程师"],
        "商业": ["战略顾问", "财务分析师", "市场研究员", "运营专家", "风险控制官"],
        "产品": ["产品经理", "用户体验设计师", "数据分析师", "行业专家", "竞品分析师"],
        "管理": ["项目经理", "HR专家", "变革管理专家", "流程优化专家", "领导力教练"],
        "政策": ["政策分析师", "法律顾问", "经济学家", "社会学家", "行业监管专家"],
        "通用": ["行业专家", "数据分析师", "创新顾问", "执行专家", "评审专家"]
    }
    
    experts = expert_templates.get(domain, expert_templates["通用"])
    
    return [
        {
            "id": f"expert-{i+1}",
            "role": expert,
            "focus_questions": [
                f"从{expert}视角看「{topic}」的核心关注点是什么？",
                f"这个视角下有哪些容易被忽视的细节？",
                f"基于此视角的最佳实践建议？"
            ],
            "expected_output": "3-5条关键洞察 + 1-2条建议"
        }
        for i, expert in enumerate(experts)
    ]


def generate_todo_list(framework_type: str, topic: str, options: Dict) -> Dict:
    """生成完整的待办清单"""
    result = {
        "meta": {
            "topic": topic,
            "framework": framework_type,
            "generated_at": "auto"
        },
        "phases": []
    }
    
    # 广度探索：5W1H
    if options.get("include_5w1h", True):
        result["phases"].append({
            "phase": "广度探索 - 5W1H 六维度分析",
            "description": "从六个维度全面了解问题全貌",
            "type": "breadth",
            "todo_items": generate_5w1h_framework(topic),
            "completion_check": "每个维度至少完成基础回答，理想情况下完成追问"
        })
    
    # 深度探索：5Why
    if options.get("include_5why", False):
        result["phases"].append({
            "phase": "深度探索 - 5Why 追问链条",
            "description": "连续追问5层，挖掘根本原因",
            "type": "depth",
            "todo_items": generate_5why_chain(topic, options.get("initial_problem", topic)),
            "completion_check": "每层追问都需要回答，直到找到根本原因"
        })
    
    # 系统探索：5问/7问
    if options.get("include_5q", True):
        if options.get("extended_7q", False):
            result["phases"].append({
                "phase": "系统探索 - 7问法完整框架",
                "description": "从问题定义到资源规划的系统性分析",
                "type": "systematic",
                "todo_items": generate_7question_framework(topic),
                "completion_check": "7个问题全部回答，形成完整解决方案"
            })
        else:
            result["phases"].append({
                "phase": "系统探索 - 5问法核心框架",
                "description": "从问题定义到效果衡量的核心分析",
                "type": "systematic",
                "todo_items": generate_5question_framework(topic),
                "completion_check": "5个问题全部回答，形成初步解决方案"
            })
    
    # 专家视角：多角度审视
    if options.get("include_experts", True):
        result["phases"].append({
            "phase": "多视角审视 - 专家角色分析",
            "description": "邀请多位专家从不同角度审视问题",
            "type": "perspective",
            "todo_items": generate_expert_perspectives(topic, options.get("domain", "通用")),
            "completion_check": "至少3位专家视角，每位提供3+洞察"
        })
    
    return result


def print_framework_as_markdown(todo_list: Dict) -> str:
    """将待办清单格式化为 Markdown"""
    md = []
    md.append(f"# 📋 分析框架待办清单\n")
    md.append(f"**主题**: {todo_list['meta']['topic']}\n")
    md.append(f"**框架**: {todo_list['meta']['framework']}\n\n")
    
    for i, phase in enumerate(todo_list["phases"], 1):
        md.append(f"---\n\n")
        md.append(f"## Phase {i}: {phase['phase']}\n\n")
        md.append(f"📌 {phase['description']}\n\n")
        
        for item in phase.get("todo_items", []):
            # 基础信息
            item_id = item.get("id", "")
            if "dimension" in item:
                # 5W1H 格式
                md.append(f"### ☐ {item['dimension']}\n\n")
                md.append(f"**追问**: {item['prompt']}\n\n")
                if item.get("follow_up"):
                    md.append(f"**追问补充**:\n")
                    for q in item["follow_up"]:
                        md.append(f"- {q}\n")
                    md.append(f"\n")
                if item.get("deep_drill"):
                    md.append(f"**🔍 深度追问**:\n")
                    for q in item["deep_drill"]:
                        md.append(f"- {q}\n")
                    md.append(f"\n")
                    
            elif "level" in item:
                # 5Why 格式
                md.append(f"### ☐ {item['level']}\n\n")
                md.append(f"**追问**: {item['prompt']}\n\n")
                md.append(f"**回答格式**: {item['expected_answer_format']}\n\n")
                md.append(f"**⚠️ 若无法回答**: {item['if_no_answer']}\n\n")
                
            elif "question" in item:
                # 5问/7问格式
                md.append(f"### ☐ {item['question']}\n\n")
                if item.get("sub_questions"):
                    md.append(f"**子问题**:\n")
                    for q in item["sub_questions"]:
                        md.append(f"- {q}\n")
                    md.append(f"\n")
                md.append(f"**✅ 完成标准**: {item['completion_criteria']}\n\n")
                
            elif "role" in item:
                # 专家视角格式
                md.append(f"### ☐ 【{item['role']}】\n\n")
                md.append(f"**关注问题**:\n")
                for q in item["focus_questions"]:
                    md.append(f"- {q}\n")
                md.append(f"\n")
                md.append(f"**📝 期望输出**: {item['expected_output']}\n\n")
        
        md.append(f"\n**✅ 阶段完成标准**: {phase['completion_check']}\n\n")
    
    return "".join(md)


def main():
    parser = argparse.ArgumentParser(description="生成报告分析框架的待办清单")
    parser.add_argument("topic", help="报告主题")
    parser.add_argument("--framework", "-f", default="full",
                        choices=["full", "5w1h", "5why", "5q", "7q"],
                        help="分析框架类型")
    parser.add_argument("--depth-level", "-d", default="L3",
                        choices=["L1", "L2", "L3", "L4"],
                        help="调研深度级别")
    parser.add_argument("--domain", help="领域类型(技术/商业/产品/管理/政策/通用)")
    parser.add_argument("--initial-problem", "-i", help="5Why的初始问题")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown",
                        help="输出格式")
    
    args = parser.parse_args()
    
    # 根据深度级别决定包含哪些模块
    depth_options = {
        "L1": {"include_5w1h": True, "include_5q": True, "include_experts": False},
        "L2": {"include_5w1h": True, "include_5q": True, "include_experts": True},
        "L3": {"include_5w1h": True, "include_5why": True, "include_5q": True, "include_experts": True},
        "L4": {"include_5w1h": True, "include_5why": True, "include_5q": True, 
               "include_experts": True, "extended_7q": True}
    }
    
    # 根据框架类型调整
    framework_map = {
        "5w1h": {"include_5w1h": True, "include_5why": False, "include_5q": False, "include_experts": False},
        "5why": {"include_5w1h": False, "include_5why": True, "include_5q": False, "include_experts": False},
        "5q": {"include_5w1h": False, "include_5why": False, "include_5q": True, "include_experts": False, "extended_7q": False},
        "7q": {"include_5w1h": False, "include_5why": False, "include_5q": True, "include_experts": False, "extended_7q": True},
        "full": depth_options.get(args.depth_level, depth_options["L3"])
    }
    
    options = framework_map.get(args.framework, framework_map["full"])
    options["domain"] = args.domain or "通用"
    if args.initial_problem:
        options["initial_problem"] = args.initial_problem
    
    todo_list = generate_todo_list(args.framework, args.topic, options)
    
    if args.format == "json":
        output = json.dumps(todo_list, ensure_ascii=False, indent=2)
    else:
        output = print_framework_as_markdown(todo_list)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"✅ 已保存到: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
