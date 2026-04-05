#!/usr/bin/env python3
"""
agent-architect 工作流向导
整合场景分类 → 动态追问 → 质量门禁 → 协作协议生成
"""

import sys
import json
import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_script(script_name: str, *args) -> dict:
    """运行子脚本并返回 JSON 结果"""
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, script_name)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"脚本执行失败: {script_name}\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def print_header(title: str):
    print("\n" + "=" * 55)
    print(f"  {title}")
    print("=" * 55)


def step1_classify(description: str):
    """第一步：场景分类"""
    print_header("Step 1/4 — 场景分类")
    result = run_script("scene_classifier.py", description)
    scene = result["scene"]
    print(f"\n场景类型: {scene['name']}")
    print(f"置信度: {scene['confidence']:.0%}")
    if scene.get("matched_keywords"):
        print(f"匹配关键词: {', '.join(scene['matched_keywords'])}")
    print(f"推荐 Agent 角色: {', '.join(scene['agents'])}")
    return result


def step2_interview(scene_result: dict, current_info: dict = None):
    """第二步：动态追问"""
    print_header("Step 2/4 — 动态追问")
    scene_json = json.dumps(scene_result["scene"])
    guide = run_script("dynamic_inquirer.py", scene_json)
    print(f"\n场景: {guide['scene_type']}  |  总追问数: {guide['total_questions']} 项\n")
    for phase in guide["interview_phases"]:
        print(f"【{phase['phase']}】")
        for item in phase["items"]:
            tag = f"[{item['priority']}]" if item["priority"] not in ["BLOCKER", "HIGH"] else ("[🚫 BLOCKER]" if item["priority"] == "BLOCKER" else f"[{item['priority']}]")
            print(f"  {tag} {item['question']}")
    return guide


def step3_gates(scene_type: str, current_info: dict):
    """第三步：质量门禁"""
    print_header("Step 3/4 — 质量门禁检查")
    info = dict(current_info)
    info["scene_type"] = scene_type
    result = run_script("quality_gate.py", json.dumps(info))
    s = result["summary"]
    print(f"\n通过: {s['passed']}/{s['total']}  |  BLOCKER: {s['blockers']}  |  警告: {s['high_warnings']}")
    if result["blockers"]:
        print(f"\n🚫 BLOCKER 项:")
        for r in result["blockers"]:
            print(f"  • {r['name']}  → {r['fix']}")
    if result["high_warnings"]:
        print(f"\n⚠️  HIGH 警告:")
        for r in result["high_warnings"]:
            print(f"  • {r['name']}  → {r['fix']}")
    print(f"\n{'✅ 质量门禁通过' if s['pass_gate'] else '🚫 质量门禁未通过 — 请修复 BLOCKER 项'}")
    return result


def step4_protocol(scene_result: dict, info: dict):
    """第四步：协作协议"""
    print_header("Step 4/4 — 协作协议生成")
    agents = scene_result["scene"].get("agents", [])
    scene_type = scene_result["scene"].get("type_id")
    protocol = run_script("collab_protocol.py", json.dumps(agents), scene_type, json.dumps(info))
    print(f"\n📋 执行顺序 ({protocol['execution']['type']}):")
    for i, name in enumerate(protocol["execution"]["order"], 1):
        print(f"  {i}. {name}")
    st = protocol["state"]
    print(f"\n💾 存储: {st['storage']}  |  {st['context_sharing']}")
    fs = protocol["failure"]["overall"]
    print(f"\n🛡️  失败策略: 重试{fs['max_retries']}次 {fs['retry_backoff']}  |  超时:{fs['timeout_behavior']}")
    print(f"\n📦 格式: {protocol['data_format']['inter_agent_format']}")
    print("\n[PROTOCOL_JSON_START]")
    print(json.dumps(protocol, ensure_ascii=False, indent=2))
    print("[PROTOCOL_JSON_END]")
    return protocol


def interactive_workflow():
    print("\n" + "=" * 55)
    print("  Agent 架构设计工作流")
    print("  场景分类 → 动态追问 → 质量门禁 → 协作协议")
    print("=" * 55)
    info = {}
    description = input("\n请描述你的 Agent 系统场景：\n> ").strip()
    if not description:
        print("场景描述不能为空。")
        return
    info["goal"] = description
    for kw in ["交易", "买入", "卖出", "炒股"]:
        if kw in description:
            info["scene_type"] = "trading_execution"
            break
    print("\n触发方式？（定时/事件/手动，直接回车跳过）\n> ", end="")
    trigger = input().strip()
    if trigger:
        info["trigger"] = trigger
    print("Token 消耗量级？（低/中/高，回车跳过）\n> ", end="")
    cost = input().strip()
    if cost:
        info["cost_level"] = cost

    scene_result = step1_classify(description)
    step2_interview(scene_result, info)
    gate_result = step3_gates(scene_result["scene"]["type_id"], info)

    print("\n" + "-" * 55)
    confirm = input("是否生成协作协议？（输入 y 确认）\n> ").strip().lower()
    if confirm == "y":
        if not gate_result["summary"]["pass_gate"]:
            print("⚠️  质量门禁未通过，继续？[y/n]: ", end="")
            if input().strip().lower() != "y":
                return
        step4_protocol(scene_result, info)


def quick_workflow(description: str):
    scene_result = step1_classify(description)
    guide = step2_interview(scene_result)
    info = {"goal": description}
    if any(kw in description for kw in ["交易", "买入", "卖出", "炒股"]):
        info["scene_type"] = "trading_execution"
    gate_result = step3_gates(scene_result["scene"]["type_id"], info)
    if gate_result["summary"]["pass_gate"] or "--force" in sys.argv:
        step4_protocol(scene_result, info)


def main():
    if "--interactive" in sys.argv or len(sys.argv) == 1:
        interactive_workflow()
    else:
        desc_args = [a for a in sys.argv[1:] if not a.startswith("--")]
        if desc_args:
            quick_workflow(" ".join(desc_args))
        else:
            print("用法:")
            print("  python3 architect_wizard.py --interactive")
            print("  python3 architect_wizard.py <场景描述>")


if __name__ == "__main__":
    main()
