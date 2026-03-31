# Architecture Decision Records (ADR)

> 架构决策记录索引 - 追踪项目中所有重要的技术决策

## ADR 状态说明

| 状态 | 说明 |
|------|------|
| `Proposed` | 已提议，待评审 |
| `Accepted` | 已接受，正在实施或已完成 |
| `Superseded` | 已被新 ADR 取代 |
| `Deprecated` | 已废弃，不再适用 |

## ADR 索引

| ID | 标题 | 状态 | 日期 | 作者 |
|----|------|------|------|------|
| [ADR-001](./ADR-001-template.md) | 标题 | Accepted | 2026-03-30 | 张三 |
| | | | | |
| | | | | |

## 按状态分类

### Proposed（待评审）
（暂无）

### Accepted（已接受）
（暂无）

### Superseded（已取代）
（暂无）

## 按类别分类

### 架构模式
（暂无）

### 技术栈
（暂无）

### 开发流程
（暂无）

### 基础设施
（暂无）

## 最近更新

| 日期 | 变更 |
|------|------|
| 2026-03-30 | ADR-001 已接受 |

## 创建新 ADR

在项目中创建新的 ADR：

```bash
# 在 docs/adr/ 目录下创建
touch docs/adr/ADR-XXX-title.md
```

ADR 编号使用三位数，从 001 开始递增。

## ADR 生命周期

1. **提议 (Proposed)** → 创建 ADR 文档，启动评审
2. **评审讨论** → 团队讨论，可能修改方案
3. **接受 (Accepted)** → 评审通过，纳入正式文档
4. **实施** → 按 ADR 执行技术变更
5. **后续追踪** → 如有新决策，可 Superseded 旧 ADR

## 相关资源

- [ADR 模板详细指南](../references/adr-template.md)
- [ADR 最佳实践](https://adr.github.io/)
