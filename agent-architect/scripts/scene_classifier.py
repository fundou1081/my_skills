#!/usr/bin/env python3
"""
agent-architect 场景分类器
根据用户输入的场景描述，自动识别场景类型并返回对应的追问模板和质量门禁配置
"""

import sys
import json
import re

# 场景类型定义
SCENE_TYPES = {
    "data_pipeline": {
        "name": "数据采集型",
        "keywords": ["爬取", "采集", "抓取", "监控", "采集数据", "定时获取", "数据同步"],
        "agents": ["fetcher", "parser", "storage", "scheduler"],
        "gates_critical": ["data_source", "frequency_limit", "error_handling"],
        "default_questions": [
            "数据来源的稳定性如何？是否有反爬限制？",
            "采集频率是多少？是否需要分页或增量采集？",
            "采集失败时的容错策略是什么？",
            "数据存储在哪里？格式是什么？"
        ]
    },
    "trading_execution": {
        "name": "交易执行型",
        "keywords": ["买入", "卖出", "下单", "交易", "炒股", "股票", "投资", "止损", "止盈"],
        "agents": ["data_collector", "analyzer", "risk_controller", "executor", "reporter"],
        "gates_critical": ["authorization", "position_limit", "loss_limit", "audit_log"],
        "default_questions": [
            "交易账户的授权范围是什么？单笔/日额度限制多少？",
            "止损和止盈的具体规则是什么？",
            "执行失败时的回退策略是什么？",
            "是否需要人工确认环节？",
            "所有交易操作是否需要审计日志？"
        ]
    },
    "report_delivery": {
        "name": "报告推送型",
        "keywords": ["报告", "推送", "周报", "日报", "总结", "发送", "通知", "飞书", "邮件"],
        "agents": ["data_collector", "analyzer", "formatter", "delivery"],
        "gates_critical": ["delivery_channel", "frequency", "error_notification"],
        "default_questions": [
            "报告的推送频率是什么？（每日/每周/每月）",
            "推送渠道是哪些？（飞书/邮件/钉钉）",
            "报告的受众是谁？不同受众是否需要不同格式？",
            "推送失败时是否需要备用通知渠道？"
        ]
    },
    "customer_service": {
        "name": "客服对话型",
        "keywords": ["客服", "对话", "问答", "回复", "聊天机器人", "FAQ", "答疑"],
        "agents": ["intent_classifier", "knowledge_retriever", "response_generator", "escalation"],
        "gates_critical": ["intent_coverage", "escalation_path", "privacy_check"],
        "default_questions": [
            "主要处理的意图类型有哪些？",
            "无法处理时的升级路径是什么？",
            "是否涉及用户隐私信息？有哪些脱敏要求？",
            "回复的最大延迟是多少？"
        ]
    },
    "workflow_automation": {
        "name": "流程自动化型",
        "keywords": ["审批", "流程", "自动化", "触发", "条件", "工作流", "定时任务", "CI/CD"],
        "agents": ["trigger", "condition_evaluator", "action_executor", "notifier"],
        "gates_critical": ["trigger_condition", "rollback_plan", "audit_trail"],
        "default_questions": [
            "触发条件是什么？（时间/事件/API）",
            "每个步骤的超时时间是多少？",
            "中途失败时的回滚计划是什么？",
            "关键节点是否需要人工审批？"
        ]
    },
    "generic": {
        "name": "通用型",
        "keywords": [],
        "agents": ["planner", "executor", "reviewer"],
        "gates_critical": ["goal_definition", "exit_condition", "cost_estimate"],
        "default_questions": [
            "这个 Agent 系统的最终目标是什么？",
            "什么时候算任务完成？（退出条件）",
            "每次运行的预算（token/时间）上限是多少？",
            "是否涉及外部 API 调用？成本由谁承担？"
        ]
    }
}

# 质量门禁定义（所有场景通用）
UNIVERSAL_GATES = [
    {
        "id": "goal_definition",
        "name": "目标定义",
        "description": "是否明确描述了 Agent 系统的最终目标和成功标准？",
        "severity": "BLOCKER",
        "question": "这个 Agent 系统的最终目标是什么？用一句话描述。"
    },
    {
        "id": "exit_condition",
        "name": "退出条件",
        "description": "是否定义了任务完成的判断标准？防止 Agent 死循环或无限等待。",
        "severity": "BLOCKER",
        "question": "什么情况下任务算完成？什么情况下应该停止并报告？"
    },
    {
        "id": "data_source",
        "name": "数据源可靠性",
        "description": "数据来源是否稳定？是否有 rate limit 或可用性问题？",
        "severity": "HIGH",
        "question": "数据来源是什么？稳定性如何？有没有备用数据源？"
    },
    {
        "id": "error_handling",
        "name": "异常处理",
        "description": "是否有明确的失败策略？（重试/回退/告警/人工介入）",
        "severity": "HIGH",
        "question": "某个 Agent 失败或 API 超时时的处理策略是什么？"
    },
    {
        "id": "cost_estimate",
        "name": "成本估算",
        "description": "是否估算了每次运行的 token 消耗和 API 成本？",
        "severity": "MEDIUM",
        "question": "预计每次运行的 token 消耗量级是多少？API 成本可接受吗？"
    }
]


def classify_scene(description: str) -> dict:
    """根据场景描述识别场景类型"""
    desc_lower = description.lower()

    scores = {}
    for type_id, cfg in SCENE_TYPES.items():
        if type_id == "generic":
            continue
        score = 0
        for kw in cfg["keywords"]:
            if kw.lower() in desc_lower:
                score += 1
        scores[type_id] = score

    if not scores or max(scores.values()) == 0:
        return {
            "type_id": "generic",
            "name": SCENE_TYPES["generic"]["name"],
            "confidence": 0.0,
            "matched_keywords": []
        }

    best_type = max(scores, key=scores.get)
    matched = [kw for kw in SCENE_TYPES[best_type]["keywords"]
               if kw.lower() in desc_lower]

    return {
        "type_id": best_type,
        "name": SCENE_TYPES[best_type]["name"],
        "confidence": scores[best_type] / (scores[best_type] + 1),
        "matched_keywords": matched,
        "agents": SCENE_TYPES[best_type]["agents"],
        "gates_critical": SCENE_TYPES[best_type]["gates_critical"],
        "default_questions": SCENE_TYPES[best_type]["default_questions"]
    }


def get_all_gates(scene_type_id: str = None) -> list:
    """获取质量门禁列表（含通用 + 场景特定）"""
    gates = UNIVERSAL_GATES.copy()

    if scene_type_id and scene_type_id in SCENE_TYPES:
        cfg = SCENE_TYPES[scene_type_id]
        # 找出该场景特定的门禁
        for gate_id in cfg["gates_critical"]:
            # 避免重复
            if not any(g["id"] == gate_id for g in gates):
                # 从通用门禁列表找，如果没有则添加占位
                found = next((g for g in UNIVERSAL_GATES if g["id"] == gate_id), None)
                if found:
                    gates.append(found)

    return gates


def main():
    if len(sys.argv) < 2:
        print("用法: python3 scene_classifier.py <场景描述>")
        sys.exit(1)

    description = " ".join(sys.argv[1:])
    result = classify_scene(description)
    gates = get_all_gates(result["type_id"])

    output = {
        "scene": result,
        "quality_gates": [
            {"id": g["id"], "name": g["name"], "severity": g["severity"],
             "question": g["question"]}
            for g in gates
        ]
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
