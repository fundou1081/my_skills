# 03. 风格应用 (Style Application)

> **子功能**: 把"风格画像" 变成"完整歌词"。

## 触发条件
- 风格画像已完成 (来自 [01-style-extraction](../01-style-extraction/README.md))
- 用户说"开始写" / "生成歌词" / "写一版"
- 用户已有半成品想"完善" → 进入 [refinement.md](refinement.md) 调整模式

## 工作流
3 阶段: **套路 → 调整 → 生成**
详见: [workflow.md](workflow.md)

## 调整机制
生成后, 用户可调整:
- 句级 (改某句)
- 意象级 (换意象)
- 调性级 (更现代/更文言)
- 结构级 (改段落)
- 完全重写

详见: [refinement.md](refinement.md)

## 输出
- 完整歌词 (Markdown 格式)
- 自检清单结果
- 历史版本 (保留 3-5 轮调整)

## 跟其他子功能的关系

```
01-style-extraction → 02-style-profile (画像) → 03-style-application → 输出歌词
                          ↑                                 ↓
                          └─── 调整回到 01 ←────── refinement.md
```

## 跟古风 6 阶段的关系

古风 6 阶段是 **03-style-application 的一个具体实现** (古风风格的应用流程)。  
新风格可以基于古风流程改造, 也可以完全重写。
