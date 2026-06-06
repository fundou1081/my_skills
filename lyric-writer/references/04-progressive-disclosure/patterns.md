# 渐进式披露模式 (Patterns)

## 模式 1: 子功能分层 (Sub-function Layering)

```
SKILL.md             # L2 主入口, < 200 行
├── 01-style-extraction/  # 子功能 1
│   ├── README.md
│   ├── workflow.md
│   └── questions.md
├── 02-style-profile/     # 子功能 2
├── 03-style-application/ # 子功能 3
└── 04-progressive-disclosure/  # 子功能 4
```

每个子功能一个目录, 用 `01-` `02-` 数字前缀保证顺序。

## 模式 2: 数据/逻辑分离 (Data/Logic Separation)

| 类型 | 存放 | 说明 |
|---|---|---|
| **数据** (10 种风格) | `references/styles/<style>.md` | 静态, 多 |
| **逻辑** (4 个子功能) | `references/01-04-*/` | 动态, 少 |
| **模板** (用户填的) | `assets/<template>.md` | 空白, 用户复制 |

数据 / 逻辑 / 模板清晰分离, 互不干扰。

## 模式 3: 引用 vs 嵌入 (Reference vs Embed)

- **默认引用**: SKILL.md 用 `[link](path.md)` 指向 references/
- **不嵌入完整内容** (避免重复)
- 同一文件被多处引用时, 只维护一份

## 模式 4: 触发加载 (Trigger-based Loading)

每个子功能/风格有自己的"触发关键词"表, AI 根据对话判断加载:

```markdown
| 触发词 | 加载文件 |
|---|---|
| "古风" / "方文山" | references/styles/gufeng.md |
| "R&B" / "转音" | references/styles/rnb-soul.md |
| "开始写" | references/03-style-application/workflow.md |
| "分析风格" | references/01-style-extraction/workflow.md |
```

详见: [README.md](README.md) 的"披露触发矩阵"

## 模式 5: 降级 (Degradation)

如果某子功能文件过大, 进一步拆:

```
01-style-extraction/
├── README.md           # 入口 + 触发 (~50 行)
├── workflow.md         # 4 步流程 (~100 行)
└── questions.md        # 5 个深入挖掘问题 (~150 行)
```

子目录用 `README.md` + 多个 `.md` 拆分, 主入口永远简洁。

## 模式 6: 占位符透明 (Placeholder Transparency)

未补全的风格用占位符 + `<!-- TODO -->` 标记, AI 知道哪些是缺数据的:

```markdown
### 1. 核心情感
<!-- TODO: 用户补全 — 流行歌主要表达哪些情感? -->
```

**好处**:
- AI 不会幻觉填充
- 用户清楚知道哪里要补
- 跟完整字段视觉上区分

## 模式 7: 双轨数据 (Dual-track Data)

风格数据分两轨:
- **软维度** (每次创作都问): 核心情感 / 内心需求 / 创作源头 / 特殊技法 / 表达方式
- **硬维度** (从风格库加载): 押韵方案 / 句式模板 / 意象清单

详见: [02-style-profile/README.md](../02-style-profile/README.md)
