---
name: "adr-recorder"
version: "1.0.0"
description: "This skill should be used when users want to create, manage, or review Architecture Decision Records (ADRs) for tracking code architecture evolution. Triggers include: 创建 ADR、架构决策记录、ADR、架构演进记录、记录架构变化、架构评估、架构审查、architecture decision record、架构决策追踪"
---

# ADR Recorder Skill

Architecture Decision Records (ADR) 用于系统性地记录和追踪代码架构的演进与决策。

## ADR 核心结构

每个 ADR 必须包含以下七个部分：

### 1. 标题 (Title)
简洁描述决策的核心内容，一句话说明"做什么"或"选择什么方案"。

### 2. 状态 (Status)
ADR 的生命周期状态：
- `Proposed` - 已提议，待评审
- `Accepted` - 已接受，正在实施
- `Superseded` - 已被取代
- `Deprecated` - 已废弃

### 3. 背景 (Context)
说明做出此决策的原因：
- 当前架构/方案的现状是什么？
- 存在什么问题或局限性？
- 为什么要进行这次决策？
- 有哪些约束条件？

### 4. 决策 (Decision)
核心决策内容：
- 做了什么决定？
- 选择该方案的理由是什么？
- 与其他方案的对比分析
- 考虑的替代方案及其被否决的原因

### 5. 后果 (Consequences)
决策带来的影响：
- 积极影响（benefits）
- 消极影响（drawbacks）
- 需要迁移的工作
- 技术债务的处理

### 6. 合规性 (Compliance)
确保决策被正确执行：
- 如何验证决策被遵循？
- 代码审查要点
- 技术债务追踪
- 与其他 ADR 的关联

### 7. 备注 (Notes)
元数据和附加信息：
- 作者 (Author)
- 创建日期 (Date)
- 评审人 (Reviewers)
- 关联的 issue/PR
- 版本号
- 有效期

## ADR 工作流程

### 创建新 ADR

1. **分析需求**：理解需要记录的架构决策背景
2. **收集信息**：与技术负责人、团队成员讨论
3. **撰写草稿**：按七部分结构编写 ADR
4. **评审流程**：
   - 创建 PR 或发起讨论
   - 至少一名技术负责人批准
   - 合并后状态更新为 `Accepted`

### ADR 编号规则

ADR 编号格式：`ADR-{序号}-{简短标题}`

示例：
- `ADR-001-monorepo-migration`
- `ADR-042-database-sharding-strategy`

序号使用三位数，从 001 开始递增。

### ADR 存储位置

项目级 ADR 存储在项目根目录：
```
docs/adr/
├── ADR-001-title.md
├── ADR-002-title.md
└── README.md (ADR 索引)
```

## ADR 索引维护

在 `docs/adr/README.md` 中维护 ADR 索引表：

```markdown
# Architecture Decision Records Index

| ID | Title | Status | Date | Author |
|----|-------|--------|------|--------|
| ADR-001 | 标题 | Accepted | 2026-03-30 | 张三 |
| ADR-002 | 标题 | Proposed | 2026-03-30 | 李四 |

## 最近更新

- 2026-03-30: ADR-001 已接受
```

## 执行指南

### 当用户要求创建 ADR 时

1. 确定 ADR 编号（检查现有 ADR 数量）
2. 询问或推断决策的核心内容
3. 按照七部分结构引导用户完善内容
4. 生成 Markdown 格式的 ADR 文件
5. 更新 ADR 索引（如存在）

### 当用户提供详细信息时

直接生成完整的 ADR 文件，包含：
- 完整的七部分内容
- 适当的 Markdown 格式化
- 合理的默认值（如日期、作者等）

### 当信息不完整时

可使用模板占位符，在用户确认后替换：
```markdown
> **待确认**: [具体内容]
```

## ADR 质量标准

一个好的 ADR 应该：
- ✅ 清晰描述问题和解决方案
- ✅ 解释"为什么"而非仅描述"是什么"
- ✅ 记录被否决的替代方案及原因
- ✅ 预见并记录潜在后果
- ✅ 包含可验证的合规性检查项
- ✅ 具有足够的上下文供未来阅读者理解

## 参考模板

详细的 ADR 模板可在 `references/adr-template.md` 中找到，包含每部分的详细指导。
