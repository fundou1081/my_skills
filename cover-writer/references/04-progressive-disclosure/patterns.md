# 04. 渐进式披露 (Progressive Disclosure) — 模式

> 跟 lyric-writer 的 04 同样的模式, 这里是 cover-writer 适配版。

## 3 级披露

| 级别 | 内容 | 加载时机 |
|---|---|---|
| **L1** | `name` + `description` | 始终在 context |
| **L2** | `SKILL.md` body | 触发时加载 |
| **L3** | `references/01-04/` | 按需加载 |

## 披露触发矩阵

| 子功能/数据 | 触发关键词 |
|---|---|
| **01-style-conversion** | "改编成 ___ 风格" / "改成 ___ 曲风" |
| **02-structure-variation** | "加快" / "放慢" / "加桥" / "分段" / "重复副歌" |
| **03-minimax-adapter** | 准备生成 MP3 时 |
| **04-progressive-disclosure** | (元机制, 任何时候可读) |
| **style-mapping.md** | 8 类风格, 按需展开 |

## 完整披露流程 (举例)

**用户**: "把'城市孤独'改编成交响版, 加一段桥段"

1. **L1 触发**: description 命中 cover-writer
2. **L2 加载**: `SKILL.md` 主流程
3. **进入 01-style-conversion**, AI 加载 [01-style-conversion/README.md](../01-style-conversion/README.md) + [workflow.md](../01-style-conversion/workflow.md) + [style-mapping.md](../01-style-conversion/style-mapping.md)
4. **目标风格=交响**, AI 加载 style-mapping.md 的"古典 → 交响" 段
5. **进入 02-structure-variation**, AI 加载 [02-structure-variation/patterns.md](../02-structure-variation/patterns.md) 的"加桥" 段
6. **进入 03-minimax-adapter**, AI 加载 [03-minimax-adapter/format-spec.md](../03-minimax-adapter/format-spec.md)
7. **调用 minimax-music**, 生成 MP3

每步只加载**需要的文件**。

## 模式 1: 子功能分层
- `SKILL.md` (L2)
- `references/01-04-*/` (L3)

## 模式 2: 数据/逻辑分离
- `references/01-02-*/` (逻辑: 流程)
- `assets/` (数据: 矩阵/模式库)

## 模式 3: 引用 vs 嵌入
- SKILL.md 引用 references/
- 不嵌入完整内容

## 模式 4: 触发加载
每个子功能有自己的"触发关键词"。

## 模式 5: 降级
文件过大时, 进一步拆 (如 01 已经拆成 README + workflow + style-mapping)

## 复用 lyric-writer 框架

cover-writer 跟 lyric-writer 的 04 模式**完全一致**, 但触发矩阵不同:

| 触发词类型 | lyric-writer | cover-writer |
|---|---|---|
| 风格 | "按 ___ 风格写" | "改编成 ___ 风格" |
| 结构 | (没有) | "加快/放慢/加桥" |
| 流程 | "开始写" | (自动进入) |
| 风格库 | styles/ | style-mapping.md |
