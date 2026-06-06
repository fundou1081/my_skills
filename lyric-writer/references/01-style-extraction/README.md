# 01. 风格提取 (Style Extraction)

> **子功能**: 深入挖掘用户给出的风格, 形成完整的"风格画像"。

## 触发条件
- 用户说"我想写一首 ___ 风格的歌词"
- 用户说"按 ___ 风格写" / "模仿 ___ 风格"
- 用户给出参考作品 ("像《青花瓷》一样") → 提取风格标签
- 用户说"分析这首歌像什么风格" → 倒推画像

## 工作流
详见: [workflow.md](workflow.md)

## 深入挖掘问题
详见: [questions.md](questions.md)

## 输出
风格画像 (基于 8 维度), 写入 [02-style-profile/template.md](../02-style-profile/template.md)

## 下一步
提取完成后, 进入 [03-style-application](../03-style-application/README.md) 应用画像生成歌词。

## 不触发
- 用户已直接给意象/主题 (如"用'灯'写首古风") → 跳过本子功能, 直接进 03
- 用户要"通用" (不指定风格) → 用问题清单引导用户选风格
