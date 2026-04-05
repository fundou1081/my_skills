#!/usr/bin/env python3
"""
agent-architect 质量门禁检查器
BLOCKE R级门禁不通过 → 禁止进入下一阶段
HIGH级门禁不通过 → 警告但允许继续
"""

import sys
import json

GATE_DEFINITIONS = {
    "goal_definition": {
        "name": "目标定义",
        "severity": "BLOCKER",
        "description": "Agent 系统的最终目标和成功标准必须明确",
        "check": lambda info: len(info.get("goal", "")) >= 15,
        "fix": "用一句话描述系统目标，包含：谁、做什么、产出什么。"
    },
    "exit_condition": {
        "name": "退出条件",
        "severity": "BLOCKER",
        "description": "必须定义任务完成的判断标准和终止条件",
        "check": lambda info: bool(info.get("exit_condition")),
        "fix": "明确定义：正常完成的标志 + 超时处理 + 死循环防护。"
    },
    "error_handling": {
        "name": "异常处理",
        "severity": "BLOCKER",
        "description": "必须为每个关键 Agent 定义失败策略",
        "check": lambda info: bool(info.get("fallback")) or bool(info.get("error_handling")),
        "fix": "为每个 Agent 定义：失败时做什么？（重试次数 / 回退方案 / 告警对象）"
    },
    "data_source": {
        "name": "数据源可靠性",
        "severity": "HIGH",
        "description": "数据来源必须经过可用性验证",
        "check": lambda info: bool(info.get("data_source")) and bool(info.get("data_source", {}).get("reliable")),
        "fix": "确认数据源稳定性、反爬限制、是否有 rate limit。"
    },
    "authorization": {
        "name": "授权机制",
        "severity": "BLOCKER",
        "description": "交易/支付类场景必须明确授权范围和限额",
        "check": lambda info: not info.get("scene_type") == "trading_execution" or bool(info.get("authorization")),
        "fix": "明确：哪个 Agent 有权限做什么？单笔/日额度？授权有效期？"
    },
    "loss_limit": {
        "name": "亏损限制",
        "severity": "BLOCKER",
        "description": "交易执行场景必须设置硬止损线",
        "check": lambda info: not info.get("scene_type") == "trading_execution" or bool(info.get("loss_limit")),
        "fix": "必须设定：单笔最大亏损比例、日亏损熔断线。"
    },
    "position_limit": {
        "name": "仓位限制",
        "severity": "HIGH",
        "description": "交易执行场景必须设置仓位上限",
        "check": lambda info: not info.get("scene_type") == "trading_execution" or bool(info.get("position_limit")),
        "fix": "必须设定：单票最大仓位、总仓位上限。"
    },
    "audit_log": {
        "name": "审计日志",
        "severity": "HIGH",
        "description": "交易类操作必须记录完整操作日志",
        "check": lambda info: not info.get("scene_type") == "trading_execution" or bool(info.get("audit_log")),
        "fix": "所有交易操作必须记录：时间、agent、操作内容、结果、耗时。"
    },
    "cost_estimate": {
        "name": "成本估算",
        "severity": "HIGH",
        "description": "必须估算 token 消耗量和 API 成本",
        "check": lambda info: bool(info.get("cost_level")),
        "fix": "估计每次运行的 token 消耗（低<10万/中<50万/高>50万）和成本上限。"
    },
    "privacy_check": {
        "name": "隐私合规",
        "severity": "HIGH",
        "description": "涉及用户数据时必须有脱敏和合规方案",
        "check": lambda info: not info.get("has_pii") or bool(info.get("privacy_plan")),
        "fix": "明确：涉及哪些 PII 数据？脱敏规则？合规依据（GDPR/个保法）？"
    },
    "frequency_limit": {
        "name": "频率限制",
        "severity": "MEDIUM",
        "description": "数据采集/定时任务必须设置合理的频率上限",
        "check": lambda info: not info.get("scene_type") == "data_pipeline" or bool(info.get("frequency")),
        "fix": "设定合理的采集频率，考虑目标服务器限制和成本。"
    },
    "delivery_channel": {
        "name": "推送通道",
        "severity": "HIGH",
        "description": "报告推送类场景必须定义主备推送通道",
        "check": lambda info: not info.get("scene_type") == "report_delivery" or bool(info.get("delivery_channel")),
        "fix": "明确主推送通道（如飞书）和备用通道（如邮件），并定义失败时的通知策略。"
    }
}


def check_gates(info: dict) -> dict:
    """执行所有门禁检查，返回结果"""
    results = []
    blocker_count = 0
    high_count = 0

    for gate_id, gate in GATE_DEFINITIONS.items():
        passed = gate["check"](info)
        if not passed:
            status = "FAIL"
            if gate["severity"] == "BLOCKER":
                blocker_count += 1
            elif gate["severity"] == "HIGH":
                high_count += 1
        else:
            status = "PASS"

        results.append({
            "id": gate_id,
            "name": gate["name"],
            "severity": gate["severity"],
            "status": status,
            "fix": gate["fix"] if status == "FAIL" else None
        })

    # 按严重性分组
    blockers = [r for r in results if r["severity"] == "BLOCKER"]
    highs = [r for r in results if r["severity"] == "HIGH"]
    mediums = [r for r in results if r["severity"] == "MEDIUM"]

    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]

    return {
        "summary": {
            "total": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "blockers": blocker_count,
            "high_warnings": high_count,
            "pass_gate": blocker_count == 0
        },
        "blockers": blockers,
        "high_warnings": highs,
        "medium_notes": mediums,
        "all_results": results
    }


def format_report(check_result: dict) -> str:
    """生成可读的质量门禁报告"""
    summary = check_result["summary"]
    lines = []

    lines.append("=" * 50)
    lines.append("  质量门禁检查报告")
    lines.append("=" * 50)
    lines.append(f"  总计: {summary['total']} 项  |  "
                 f"通过: {summary['passed']}  |  "
                 f"阻塞: {summary['blockers']}  |  "
                 f"警告: {summary['high_warnings']}")
    lines.append("=" * 50)

    if summary["blockers"] > 0:
        lines.append(f"\n🚫 BLOCKER ({summary['blockers']} 项) — 必须修复才能继续")
        for r in check_result["blockers"]:
            lines.append(f"  [{r['status']}] {r['name']}")
            if r["fix"]:
                lines.append(f"      修复方案: {r['fix']}")

    if check_result["high_warnings"]:
        lines.append(f"\n⚠️  HIGH ({summary['high_warnings']} 项) — 强烈建议修复")
        for r in check_result["high_warnings"]:
            lines.append(f"  [{r['status']}] {r['name']}")
            if r["fix"]:
                lines.append(f"      修复方案: {r['fix']}")

    if check_result["medium_notes"]:
        lines.append(f"\n📋 MEDIUM ({len(check_result['medium_notes'])} 项)")
        for r in check_result["medium_notes"]:
            lines.append(f"  [{r['status']}] {r['name']}")

    lines.append("\n" + "=" * 50)
    if summary["pass_gate"]:
        lines.append("  ✅ 质量门禁通过 — 可以进入下一阶段")
    else:
        lines.append("  🚫 质量门禁未通过 — 请修复 BLOCKER 项后重试")
    lines.append("=" * 50)

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 quality_gate.py <info_json>")
        print("示例: python3 quality_gate.py '{\"goal\":\"每天自动分析A股\",\"scene_type\":\"trading_execution\"}'")
        sys.exit(1)

    info = json.loads(sys.argv[1])
    result = check_gates(info)

    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))


if __name__ == "__main__":
    main()
