#!/usr/bin/env python3
"""
agent-architect 动态追问引擎
核心：信息缺口检测 + 条件触发追问逻辑
"""

import sys
import json
import os

QUESTION_TEMPLATES = {
    "goal": {
        "missing": "目标描述不够具体。请补充：预期产出是什么？谁是最终用户？",
        "vague": "【澄清】"{current}" 比较模糊，能否用一个具体例子说明？",
    },
    "trigger": {
        "none": "未说明触发方式。请问是定时触发、事件触发、还是手动触发？",
        "time_only": "定时任务已明确。是否需要支持手动触发作为补充？",
        "event_only": "事件触发已明确。是否有时间窗口限制？",
        "dual": "双重触发机制已定义。事件触发和定时任务冲突时以谁为准？"
    },
    "data_flow": {
        "missing": "数据流未描述。请说明：原始数据从哪里来？经过哪些 Agent 处理？最终产出是什么？",
        "partial": "数据链路不完整。【追问】{missing_stages} 环节的数据格式和存储方式是什么？",
    },
    "authorization": {
        "missing": "授权信息缺失。请问哪些 Agent 需要外部系统授权？授权范围和有效期？",
        "partial": "授权不完整。【追问】{missing_auths} 是否已获得正式授权？"
    },
    "fallback": {
        "missing": "回退策略缺失。请问当 {failed_component} 失败时，系统应该如何应对？",
        "partial": "部分回退策略已定义。{missing_fallbacks} 场景下的回退方案是什么？"
    },
    "cost": {
        "missing": "成本未估算。请估计每次运行的 token 消耗量级（低/中/高/未知）。",
        "high": "成本评估为【高】。请问是否有成本上限控制机制？超支时的熔断策略？"
    },
    "privacy": {
        "concern": "【隐私检查】这个场景涉及 {data_types}，是否需要脱敏处理？脱敏规则是什么？",
    }
}


def analyze_info_gaps(scene_result: dict, current_info: dict = None) -> dict:
    gaps = []
    info = current_info or {}
    scene_type = scene_result.get("type_id", "generic")

    goal = info.get("goal", "")
    if not goal or len(goal) < 20:
        gaps.append({"dim": "goal", "priority": "BLOCKER", "template_key": "missing"})
    elif any(w in goal for w in ["大概", "可能", "随便", "?"]):
        gaps.append({"dim": "goal", "priority": "HIGH", "template_key": "vague",
                      "params": {"current": goal[:50]}})

    trigger = info.get("trigger", "")
    if not trigger:
        gaps.append({"dim": "trigger", "priority": "MEDIUM", "template_key": "none"})

    agents = scene_result.get("agents", [])
    if agents and "data_flow" not in info:
        gaps.append({"dim": "data_flow", "priority": "HIGH", "template_key": "partial",
                      "params": {"missing_stages": "Agent 间"}})

    if scene_type == "trading_execution" and not info.get("authorization"):
        gaps.append({"dim": "authorization", "priority": "CRITICAL",
                      "template_key": "missing"})

    if not info.get("fallback"):
        gaps.append({"dim": "fallback", "priority": "HIGH", "template_key": "missing",
                      "params": {"failed_component": "某个 Agent"}})

    if not info.get("cost_level"):
        gaps.append({"dim": "cost", "priority": "MEDIUM", "template_key": "missing"})
    elif info.get("cost_level") == "高":
        gaps.append({"dim": "cost", "priority": "HIGH", "template_key": "high"})

    priority_order = {"CRITICAL": 0, "BLOCKER": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    gaps.sort(key=lambda x: priority_order.get(x["priority"], 3))

    return {"gaps": gaps, "scene_type": scene_type}


def resolve_template(dim: str, key: str, params: dict = None) -> str:
    template = QUESTION_TEMPLATES.get(dim, {}).get(key, f"[{dim}] {key}")
    if params:
        return template.format(**params)
    return template


def generate_interview_guide(scene_result: dict, current_info: dict = None) -> dict:
    gap_analysis = analyze_info_gaps(scene_result, current_info)
    initial_questions = scene_result.get("default_questions", [])

    gap_questions = [
        {
            "dimension": g["dim"],
            "priority": g["priority"],
            "question": resolve_template(g["dim"], g["template_key"], g.get("params")),
            "answered_as": f"✅ {g['dim']}：___"
        }
        for g in gap_analysis["gaps"][:5]
    ]

    collab_questions = [
        {"dimension": "collab_order", "priority": "HIGH",
         "question": "多个 Agent 的执行顺序是什么？是否有并行处理的需求？",
         "answered_as": "✅ 执行顺序：___"},
        {"dimension": "collab_data_format", "priority": "MEDIUM",
         "question": "Agent 之间传递的数据格式是什么？（JSON/文件/消息队列）",
         "answered_as": "✅ 数据格式：___"},
        {"dimension": "collab_state", "priority": "MEDIUM",
         "question": "中间状态存储在哪里？各 Agent 如何共享上下文？",
         "answered_as": "✅ 状态存储：___"},
        {"dimension": "collab_failure", "priority": "HIGH",
         "question": "某个 Agent 超时或失败时，通知谁？整个流程是否停止？",
         "answered_as": "✅ 失败策略：___"}
    ]

    phases = [
        {"phase": "目标定义 [BLOCKER]", "items": [
            {"dimension": "goal", "priority": "BLOCKER",
             "question": "用一句话描述这个 Agent 系统的最终目标。",
             "answered_as": "✅ 目标：___"}
        ]},
        {"phase": "场景特定澄清", "items": [
            {"dimension": "default", "priority": "HIGH",
             "question": q, "answered_as": f"✅ 已确认：___"}
            for q in initial_questions[:3]
        ]},
        {"phase": "信息缺口追问", "items": gap_questions},
        {"phase": "协作流程 [HIGH]", "items": [
            {"dimension": "exit_condition", "priority": "HIGH",
             "question": "什么情况下任务算完成？什么情况下应该停止并告警？",
             "answered_as": "✅ 退出条件：___"},
        ] + collab_questions}
    ]

    gate_names = {
        "goal_definition": "✅ 目标定义",
        "exit_condition": "✅ 退出条件",
        "error_handling": "✅ 异常处理",
        "authorization": "✅ 授权机制",
        "data_source": "✅ 数据源可靠性",
        "frequency_limit": "✅ 频率限制",
        "loss_limit": "✅ 亏损限制",
        "position_limit": "✅ 仓位限制",
        "cost_estimate": "✅ 成本估算"
    }
    all_gate_ids = list(set(
        scene_result.get("gates_critical", []) +
        ["goal_definition", "exit_condition", "error_handling", "cost_estimate"]
    ))
    gates = [{"id": gid, "display": gate_names.get(gid, f"✅ {gid}")} for gid in all_gate_ids]

    return {
        "scene_type": scene_result.get("name"),
        "total_questions": sum(len(p["items"]) for p in phases),
        "phases": phases,
        "quality_gates": gates
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python3 dynamic_inquirer.py <场景分类JSON>")
        print("示例: python3 dynamic_inquirer.py '{\"type_id\":\"data_pipeline\"}'")
        sys.exit(1)

    scene_result = json.loads(sys.argv[1])
    guide = generate_interview_guide(scene_result)
    print(json.dumps(guide, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
