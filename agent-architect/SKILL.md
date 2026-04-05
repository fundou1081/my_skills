---
name: agent-architect
version: "1.0.0"
description: |
  AI Agent 架构设计技能。帮助用户从零搭建多 Agent 协作系统，提供场景分类、动态追问、质量门禁、协作协议生成全流程支持。

  触发场景：
  - 帮我设计一个 Agent 系统 / Agent 团队
  - 我想搭一个 XX 场景的 Agent，需要哪些角色？
  - 多 Agent 协作怎么设计？
  - 设计一个 Agent 工作流
  - 评估一下我的 Agent 架构方案
  - agent architecture、agent team design、agent workflow

  核心特点：
  - 场景自动分类（数据采集/交易执行/报告推送/客服对话/流程自动化/通用）
  - 动态追问引擎（基于信息缺口检测，智能追问）
  - 质量门禁机制（BLOCKER 级禁止通过，HIGH 级强制确认）
  - 协作协议自动生成（数据格式/存储方案/失败策略）
---

# Agent Architect Skill

## 定位

帮助用户从"有一个想法"到"输出一份可执行的 Agent 系统设计"。

**不是**教用户学 Agent 理论，**是**帮用户快速完成架构设计。

## 核心价值

| 原版痛点 | 优化后 |
|---------|--------|
| 用户填 80% → 模板只记录 | 用户只填核心信息 → Skill 动态追问补完 |
| 缺少退出条件 → Agent 可能死循环 | BLOCKER 门禁强制检查退出条件 |
| 缺少容错 → 单点故障全崩 | 协作协议自动生成失败策略 |
| 缺少成本估算 → 上线后人傻了 | HIGH 级门禁强制确认成本量级 |

## 工作流（4 步）

```
场景描述
  ↓
Step 1: 场景分类（自动识别场景类型 + 推荐 Agent 角色）
  ↓
Step 2: 动态追问（信息缺口检测 + 条件触发追问）
  ↓
Step 3: 质量门禁检查（BLOCKER 不通过禁止继续）
  ↓
Step 4: 协作协议生成（数据格式 + 存储 + 失败策略）
```

## 脚本说明

| 脚本 | 作用 | 触发时机 |
|------|------|---------|
| `architect_wizard.py` | 主工作流向导，整合全流程 | 入口 |
| `scene_classifier.py` | 场景分类 + Agent 角色推荐 | Step 1 |
| `dynamic_inquirer.py` | 信息缺口检测 + 追问生成 | Step 2 |
| `quality_gate.py` | 质量门禁检查（BLOCKER/HIGH） | Step 3 |
| `collab_protocol.py` | 协作协议自动生成 | Step 4 |

## 使用方法

### 交互模式（推荐新手）

```bash
python3 ~/.workbuddy/skills/agent-architect/scripts/architect_wizard.py --interactive
```

### 快速模式（AI 直接调用）

```bash
# 传入场景描述，自动执行全流程
python3 ~/.workbuddy/skills/agent-architect/scripts/architect_wizard.py "我想搭一个每天分析A股、推荐5支股票的Agent团队"
```

### 单独使用各脚本

```bash
# Step 1: 场景分类
python3 ~/.workbuddy/skills/agent-architect/scripts/scene_classifier.py "每天自动抓取A股数据生成报告"

# Step 2: 动态追问（传入分类结果）
python3 ~/.workbuddy/skills/agent-architect/scripts/dynamic_inquirer.py '{"type_id":"data_pipeline","name":"数据采集型","agents":["fetcher","parser","storage"],"default_questions":["数据来源稳定性？"]}'

# Step 3: 质量门禁检查
python3 ~/.workbuddy/skills/agent-architect/scripts/quality_gate.py '{"goal":"每天分析A股","scene_type":"trading_execution","exit_condition":"有明确推荐结果","fallback":"记录错误告警"}'

# Step 4: 协作协议生成
python3 ~/.workbuddy/skills/agent-architect/scripts/collab_protocol.py '["fetcher","analyzer","risk_controller","executor"]' data_pipeline
```

## 质量门禁清单

### 🚫 BLOCKER 级（必须全部通过）

| 门禁 ID | 名称 | 说明 |
|---------|------|------|
| goal_definition | 目标定义 | 最终目标和成功标准是否明确（≥15字） |
| exit_condition | 退出条件 | 任务完成/终止判断标准是否定义 |
| error_handling | 异常处理 | 每个关键 Agent 是否有失败策略 |
| authorization* | 授权机制 | 交易场景必须明确授权范围和限额 |
| loss_limit* | 亏损限制 | 交易场景必须设置硬止损线 |

*仅交易执行型场景

### ⚠️ HIGH 级（强烈建议通过）

| 门禁 ID | 名称 | 说明 |
|---------|------|------|
| data_source | 数据源可靠性 | 数据来源可用性是否验证 |
| audit_log* | 审计日志 | 交易操作是否记录完整日志 |
| cost_estimate | 成本估算 | token 消耗量级是否确认 |
| privacy_check | 隐私合规 | PII 数据是否有脱敏方案 |
| delivery_channel† | 推送通道 | 报告型是否定义主备通道 |

*仅交易执行型 †仅报告推送型

## 场景类型与对应配置

| 场景类型 | 识别关键词 | 关键门禁 | 推荐 Agent |
|---------|-----------|---------|-----------|
| data_pipeline | 爬取、采集、监控、数据同步 | data_source, frequency_limit | fetcher, parser, storage |
| trading_execution | 交易、炒股、买入卖出、下单 | authorization, loss_limit, audit_log | data_collector, analyzer, risk_controller, executor |
| report_delivery | 报告、推送、周报、日报、飞书 | delivery_channel | fetcher, analyzer, formatter, deliverer |
| customer_service | 客服、问答、FAQ、对话 | intent_coverage, escalation_path | intent_classifier, knowledge_retriever, escalation |
| workflow_automation | 审批、流程自动化、CI/CD | trigger_condition, rollback_plan | trigger, condition_evaluator, action_executor |
| generic | 其他 | goal_definition, exit_condition | planner, executor, reviewer |

## 输出物

完整执行后，Skill 输出：

1. **场景分类报告**：类型 + 置信度 + 推荐 Agent 列表
2. **追问清单**：分阶段的信息缺口追问（BLOCKER → HIGH → MEDIUM 排序）
3. **质量门禁报告**：逐项检查结果 + 修复建议
4. **协作协议**：执行顺序 + 存储方案 + 失败策略 + JSON Schema

## 参考文档

- `references/quality-gates.md` — 质量门禁完整清单和使用指南
- `references/role-templates.md` — 各角色模板（输入/输出 schema + 超时配置）
