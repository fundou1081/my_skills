#!/usr/bin/env python3
"""
agent-architect 协作协议生成器
基于角色配置，自动生成 Agent 间的数据格式、存储方案、失败策略
"""

import sys
import json

# Agent 角色模板库
ROLE_TEMPLATES = {
    "fetcher": {
        "output_schema": {
            "type": "object",
            "required": ["raw_data", "source", "timestamp", "status"],
            "properties": {
                "raw_data": {"type": "string", "description": "原始数据内容"},
                "source": {"type": "string", "description": "数据来源标识"},
                "timestamp": {"type": "string", "format": "ISO8601"},
                "status": {"type": "string", "enum": ["success", "partial", "failed"]},
                "metadata": {"type": "object", "description": "额外元数据"}
            }
        },
        "failure_action": "retry_3times_with_backoff",
        "timeout_sec": 30
    },
    "analyzer": {
        "output_schema": {
            "type": "object",
            "required": ["analysis", "confidence", "timestamp", "status"],
            "properties": {
                "analysis": {"type": "string", "description": "分析结论"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "evidence": {"type": "array", "items": {"type": "string"}},
                "timestamp": {"type": "string", "format": "ISO8601"},
                "status": {"type": "string", "enum": ["success", "low_confidence", "failed"]}
            }
        },
        "failure_action": "escalate_with_evidence",
        "timeout_sec": 60
    },
    "executor": {
        "output_schema": {
            "type": "object",
            "required": ["action", "result", "timestamp", "status"],
            "properties": {
                "action": {"type": "string", "description": "执行的操作"},
                "result": {"type": "string", "description": "执行结果"},
                "timestamp": {"type": "string", "format": "ISO8601"},
                "status": {"type": "string", "enum": ["success", "pending", "failed"]},
                "audit_id": {"type": "string", "description": "审计追踪ID"}
            }
        },
        "failure_action": "stop_and_alert",
        "timeout_sec": 10
    },
    "reporter": {
        "output_schema": {
            "type": "object",
            "required": ["report", "format", "delivered_to", "status"],
            "properties": {
                "report": {"type": "string", "description": "报告内容"},
                "format": {"type": "string", "enum": ["markdown", "json", "html", "pdf"]},
                "delivered_to": {"type": "array", "items": {"type": "string"}},
                "timestamp": {"type": "string", "format": "ISO8601"},
                "status": {"type": "string", "enum": ["sent", "failed", "partial"]}
            }
        },
        "failure_action": "retry_2times_then_backup_channel",
        "timeout_sec": 15
    },
    "scheduler": {
        "output_schema": {
            "type": "object",
            "required": ["next_run", "schedule", "status"],
            "properties": {
                "next_run": {"type": "string", "format": "ISO8601"},
                "schedule": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "paused", "stopped"]}
            }
        },
        "failure_action": "keep_previous_schedule",
        "timeout_sec": 5
    },
    "risk_controller": {
        "output_schema": {
            "type": "object",
            "required": ["approved", "risk_level", "conditions", "status"],
            "properties": {
                "approved": {"type": "boolean"},
                "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "conditions": {"type": "array", "items": {"type": "string"}},
                "timestamp": {"type": "string", "format": "ISO8601"},
                "status": {"type": "string", "enum": ["approved", "rejected", "pending"]}
            }
        },
        "failure_action": "default_to_reject",
        "timeout_sec": 5
    },
    "default": {
        "output_schema": {
            "type": "object",
            "required": ["result", "timestamp", "status"],
            "properties": {
                "result": {"type": "string"},
                "timestamp": {"type": "string", "format": "ISO8601"},
                "status": {"type": "string", "enum": ["success", "failed"]}
            }
        },
        "failure_action": "log_and_skip",
        "timeout_sec": 30
    }
}

# 存储方案选项
STORAGE_OPTIONS = {
    "memory": {"use_case": "单次运行内快速共享", "persistence": "无", "cost": "零"},
    "file_temp": {"use_case": "运行间中间结果", "persistence": "运行期间", "cost": "零"},
    "file_persist": {"use_case": "需要回溯的历史数据", "persistence": "长期", "cost": "低"},
    "sqlite": {"use_case": "结构化数据+查询", "persistence": "长期", "cost": "低"},
    "redis": {"use_case": "高频读写+实时状态", "persistence": "可配置", "cost": "中"},
}


def get_role_config(role: str) -> dict:
    return ROLE_TEMPLATES.get(role, ROLE_TEMPLATES["default"])


def generate_collab_protocol(agents: list, scene_type: str = None, info: dict = None) -> dict:
    """生成完整的 Agent 协作协议"""

    # 1. 为每个 Agent 生成角色配置
    agent_configs = []
    for agent in agents:
        role = agent if agent in ROLE_TEMPLATES else "default"
        cfg = get_role_config(role)
        agent_configs.append({
            "name": agent,
            "role": role,
            "output_schema": cfg["output_schema"],
            "failure_action": cfg["failure_action"],
            "timeout_sec": cfg["timeout_sec"]
        })

    # 2. 生成执行顺序（线性链式 + 并行节点标注）
    execution_order = []
    parallel_groups = []

    if scene_type == "trading_execution":
        # 交易型固定顺序
        sequence = [a["name"] for a in agent_configs]
        execution_order = sequence
    elif scene_type == "report_delivery":
        # 报告型：采集 → 分析 → 格式化 → 推送
        execution_order = [a["name"] for a in agent_configs]
    elif scene_type == "data_pipeline":
        # 数据型：支持并行采集
        fetcher = next((a for a in agent_configs if "fetcher" in a["name"]), None)
        others = [a for a in agent_configs if "fetcher" not in a["name"]]
        if fetcher and len(others) > 2:
            parallel_groups.append([fetcher["name"]])
            execution_order = others
        else:
            execution_order = [a["name"] for a in agent_configs]
    else:
        execution_order = [a["name"] for a in agent_configs]

    # 3. 推荐存储方案
    recommended_storage = "file_temp"
    if scene_type == "trading_execution":
        recommended_storage = "file_persist"  # 需要审计日志
    elif scene_type == "report_delivery":
        recommended_storage = "file_temp"  # 单次运行够用
    elif len(agents) > 5:
        recommended_storage = "sqlite"  # 多 Agent 复杂协作

    # 4. 生成中间状态管理方案
    state_management = {
        "storage": recommended_storage,
        "key_fields": ["run_id", "agent_name", "stage", "timestamp", "status"],
        "retention": "delete after 7 days" if scene_type != "trading_execution" else "retain for audit",
        "context_sharing": "file-based context injection (Agent reads previous output from shared path)"
    }

    # 5. 生成失败策略
    failure_strategy = {
        "overall": {
            "max_retries": 3,
            "retry_backoff": "exponential (1s, 2s, 4s)",
            "timeout_behavior": "terminate_and_alert",
            "alert_targets": info.get("alert_targets", ["system_owner"]) if info else ["system_owner"]
        },
        "per_agent": [
            {
                "agent": a["name"],
                "on_timeout": a["failure_action"],
                "max_retries": 3 if "fetcher" in a["name"] or "executor" in a["name"] else 1
            }
            for a in agent_configs
        ]
    }

    # 6. 数据格式规范
    data_format = {
        "inter_agent_format": "JSON Lines (.jsonl) — 每行一个 JSON，方便流式处理和追加",
        "schema_validation": "JSON Schema draft-07 (每个 Agent 输出必须符合 schema)",
        "encoding": "UTF-8",
        "binary_handling": "Base64 编码或独立文件路径引用"
    }

    # 7. 完整通信协议
    protocol = {
        "execution": {
            "type": "sequential_chain",
            "order": execution_order,
            "parallel_groups": parallel_groups,
            "description": "线性链式执行，前一个 Agent 输出作为下一个输入"
        },
        "state": state_management,
        "failure": failure_strategy,
        "data_format": data_format,
        "agents": agent_configs
    }

    return protocol


def format_protocol_report(protocol: dict) -> str:
    lines = []
    lines.append("=" * 55)
    lines.append("  Agent 协作协议")
    lines.append("=" * 55)

    # 执行顺序
    lines.append("\n📋 执行顺序")
    lines.append(f"  类型: {protocol['execution']['type']}")
    for i, name in enumerate(protocol['execution']['order'], 1):
        lines.append(f"  {i}. {name}")

    # 存储方案
    st = protocol["state"]
    lines.append(f"\n💾 状态存储")
    lines.append(f"  推荐方案: {st['storage']}")
    lines.append(f"  上下文共享: {st['context_sharing']}")
    lines.append(f"  数据保留: {st['retention']}")

    # 失败策略
    fs = protocol["failure"]
    lines.append(f"\n🛡️  失败策略")
    lines.append(f"  最大重试: {fs['overall']['max_retries']} 次，指数退避")
    lines.append(f"  超时行为: {fs['overall']['timeout_behavior']}")
    lines.append(f"  告警对象: {', '.join(fs['overall']['alert_targets'])}")

    # 数据格式
    df = protocol["data_format"]
    lines.append(f"\n📦 数据格式")
    lines.append(f"  Agent 间格式: {df['inter_agent_format']}")
    lines.append(f"  Schema: {df['schema_validation']}")

    lines.append("\n" + "=" * 55)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 collab_protocol.py <agents_json> [scene_type]")
        print("示例: python3 collab_protocol.py '[\"fetcher\",\"analyzer\",\"reporter\"]' data_pipeline")
        sys.exit(1)

    agents = json.loads(sys.argv[1])
    scene_type = sys.argv[2] if len(sys.argv) > 2 else None
    info = None
    if len(sys.argv) > 3:
        info = json.loads(sys.argv[3])

    protocol = generate_collab_protocol(agents, scene_type, info)

    if "--json" in sys.argv:
        print(json.dumps(protocol, ensure_ascii=False, indent=2))
    else:
        print(format_protocol_report(protocol))


if __name__ == "__main__":
    main()
