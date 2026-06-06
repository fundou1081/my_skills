# 02. 风格画像 (Style Profile)

> **子功能**: 8 维度的风格结构化档案, 是"风格套路" 的载体。

## 8 维度

| # | 维度 | 类型 | 说明 |
|---|---|---|---|
| 1 | **核心情感** | 软 | 风格主要表达的情感 |
| 2 | **内心需求** | 软 | 听众听完的预期反应 |
| 3 | **创作源头** | 软 | 风格的灵感来源 |
| 4 | **特殊技法** | 软 | 风格的独特手法 |
| 5 | **表达方式** | 软 | 直白 / 含蓄 / 呐喊 |
| 6 | **押韵方案** | 硬 | 押韵密度 + 位置 |
| 7 | **句式模板** | 硬 | 主歌/副歌/桥段句式 |
| 8 | **意象清单** | 硬 | 常用物象 (10-20 个) |

**软维度** = 每次创作都问 (诉求不同)  
**硬维度** = 从风格库加载 (同一风格相同)

## 模板
详见: [template.md](template.md) (空白模板, 复制填入)

## 怎么用

1. 每个风格 (古风/流行/民谣/...) 都有自己的"风格画像", 存在 [styles/](../styles/README.md) 目录
2. 风格画像是"套路", 用户可以基于画像生成歌词
3. 用户可以修改画像的任何字段 (AI 不死守原画像)

## 补全指南

补全新风格画像的步骤:
1. **找 3-5 首代表作品**
2. **逐首分析 8 维度** (用 [01-style-extraction/questions.md](../01-style-extraction/questions.md) 的问题)
3. **提取共性**, 写入画像对应字段
4. **把画像存到** `styles/<style>.md`
5. **写创作流程** (基于古风 6 阶段, 调整) — 见 [03-style-application/workflow.md](../03-style-application/workflow.md)
6. **写自检清单** — 见 [assets/style-extraction-checklist.md](../../assets/style-extraction-checklist.md)

## 跟其他子功能的关系

```
01-style-extraction → 02-style-profile (画像) → 03-style-application
                          ↓
                     styles/<style>.md (库)
```

- 01 输出画像
- 02 存储画像
- 03 消费画像
- styles/ 是画像库 (10 种风格)
- 04-progressive-disclosure 决定画像何时加载
