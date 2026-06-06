# 04. 渐进式披露 (Progressive Disclosure)

> **子功能**: 决定 skill 内容如何按需加载, 不一次性塞给 AI。

## 核心思想

**SKILL.md 只写主流程 + 触发词**, 详细内容 (每个子功能, 每种风格) 按需展开。

## 3 级披露

| 级别 | 内容 | 大小 | 加载时机 |
|---|---|---|---|
| **L1** | `name` + `description` (frontmatter) | ~100 词 | 始终在 context |
| **L2** | `SKILL.md` body (主流程) | < 200 行 | 触发时加载 |
| **L3** | `references/<子功能>/` 详细 | 不限 | 按需加载 |

详见: [patterns.md](patterns.md)

## 披露触发矩阵

每个子功能都有自己的触发条件, AI 根据用户输入判断读哪个。

| 子功能/数据 | 触发关键词 |
|---|---|
| **01-style-extraction** | "想写 ___ 风格" / "按 ___ 写" / "分析风格" |
| **02-style-profile** | 风格相关问题, 需调取画像 |
| **03-style-application** | "开始写" / "生成歌词" / "写一版" |
| **04-progressive-disclosure** | (本子功能, 任何时候可读) |
| **styles/古风** | "古风" / "方文山" / "传统意象" / "时空折叠" |
| **styles/流行** | "流行" / "hook" / "易传唱" |
| **styles/民谣** | "民谣" / "赵雷" / "朴树" |
| **styles/摇滚** | "摇滚" / "呐喊" / "力量" |
| **styles/R&B** | "R&B" / "转音" / "律动" |
| **styles/说唱** | "说唱" / "rap" / "flow" |
| **styles/城市民谣** | "城市民谣" / "李志" / "都市" |
| **styles/校园民谣** | "校园民谣" / "青春" / "毕业" |
| **styles/电子** | "电子" / "EDM" / "drop" |
| **styles/中国风** | "中国风" / 待用户定义 |

## 完整披露流程 (举例)

**用户**: "帮我写一首 R&B 风格的分手歌"

1. **L1 触发**: description 命中 `lyric-writer` (触发词: 写歌词/R&B)
2. **L2 加载**: `SKILL.md` 主流程
3. **进入 01-style-extraction**, AI 加载 [01-style-extraction/workflow.md](../01-style-extraction/workflow.md) + [questions.md](../01-style-extraction/questions.md)
4. **风格初判为 R&B**, AI 加载 [styles/rnb-soul.md](../styles/rnb-soul.md)
5. **深入挖掘 5 软维度** (Q1-Q5)
6. **形成画像**, 用户确认
7. **进入 03-style-application**, AI 加载 [03-style-application/workflow.md](../03-style-application/workflow.md)
8. **生成歌词**, AI 加载 [assets/style-extraction-checklist.md](../../assets/style-extraction-checklist.md) 自检
9. **输出完整歌词**

每一步只加载**需要的文件**, 节省 context。

## 好处

- **context 友好** (不一次性塞所有内容)
- **可维护** (改一个子功能不影响其他)
- **易扩展** (新风格加文件即可)
