---
name: cover-writer
description: >
  改编曲生成 skill, 平行于 lyric-writer, 专注"曲风转换"和"结构变奏"。
  Use when 用户说"把这首歌改编成电子/交响/民调..."、"remix 一下"、
  "换个曲风"、"把古风改成 EDM"、"加一段桥段"、"加快/放慢"、
  "分段"、"重复副歌"。核心: 歌词基本保持不变, 只调整适配新结构
  的部分, 输出新歌词 + minimax-music description, 直接生成 MP3。
  支持 8 类目标风格 (电子/古典/民乐/西方/摇滚/流行变体/东方/现代)
  + 5 种结构变奏 (加快/放慢/加桥/分段/重复副歌)。
  Triggers include 显式"改编成 ___ 风格"、"remix"、"加桥段"、"加快"、
  "放慢" 以及 AI 主动检测"用户想改编歌曲"。
---

# cover-writer - 改编曲生成助手

> **核心**: 把原曲改成新曲风 (电子/交响/民调...), **歌词基本不变**。  
> 平行于 lyric-writer, 复用 8 维度框架, 输出新歌词 + minimax-music 描述, 直接生成 MP3。

---

## TL;DR

不重写歌词, 只**重做编曲**。  
输入: 原曲 (歌词 + 风格)  
处理: 选目标风格 + 选变奏方式  
输出: 新歌词 (适配新结构) + description → minimax-music → MP3

---

## 触发方式

用户说以下时激活:
- "把这首歌改编成 ___ (电子/交响/民调...)"
- "remix 一下" / "换个曲风"
- "把古风改成 EDM" / "把民谣改成 R&B"
- "加一段桥段" / "加快" / "放慢" / "分段" / "重复副歌"
- AI 主动检测到"改编"意图

---

## 4 个子功能 (渐进式披露)

| 子功能 | 入口 | 何时触发 |
|---|---|---|
| **01 曲风转换** | [README](references/01-style-conversion/README.md) + [workflow](references/01-style-conversion/workflow.md) + [style-mapping](references/01-style-conversion/style-mapping.md) | 用户指定目标风格 |
| **02 结构变奏** | [README](references/02-structure-variation/README.md) + [patterns](references/02-structure-variation/patterns.md) | 用户指定变奏方式 |
| **03 minimax 适配** | [README](references/03-minimax-adapter/README.md) + [format-spec](references/03-minimax-adapter/format-spec.md) | 准备输出时 |
| **04 渐进式披露** | [patterns](references/04-progressive-disclosure/patterns.md) | 元机制 |

---

## 主工作流 (5 步)

```
原曲 (歌词 + 风格)
    ↓
1. Detect — 原曲类型识别 (用 8 维度画像)
    ↓
2. Analyze — 提取原曲结构 (段落标记 + 风格)
    ↓
3. Choose — 用户选: 曲风转换? 结构变奏? 两者?
    ↓
4. Apply — 应用改编 (调 description, 微调歌词适配新结构)
    ↓
5. Generate — 输出新歌词 + description → minimax-music
    ↓
MP3
```

---

## 8 类目标风格

| 类型 | 风格 |
|---|---|
| **电子** | EDM / Synthwave / Lo-fi / Dubstep / House |
| **古典** | 交响 / 弦乐四重奏 / 钢琴独奏 / 室内乐 |
| **民乐** | 民调 / 古筝 / 二胡 / 笛箫 / 琵琶 |
| **西方** | 爵士 / 雷鬼 / 拉丁 / Bossa Nova / 蓝草 |
| **摇滚** | 摇滚 / 朋克 / 重金属 / 后摇 |
| **流行变体** | 抒情 Ballad / R&B / 灵魂 Soul / 放克 |
| **东方** | 中国风 / 和风 / 印度风 / 阿拉伯风 |
| **现代** | 民谣 Acoustic / 城市民谣 / Indie / Dream Pop |

详见: [references/01-style-conversion/style-mapping.md](references/01-style-conversion/style-mapping.md)

---

## 5 种结构变奏

| 变奏 | 适用场景 |
|---|---|
| **加快** (Tempo Up) | 把抒情改成舞曲, BPM +30% |
| **放慢** (Tempo Down) | 把快歌改成抒情, BPM -30% |
| **加桥** (Add Bridge) | 增强叙事, 插入 D 段 |
| **分段** (Section Split) | 长副歌拆成两段, 制造对比 |
| **重复副歌** (Chorus Repeat) | 强化记忆点, 副歌 ×2-3 |

详见: [references/02-structure-variation/patterns.md](references/02-structure-variation/patterns.md)

---

## 关键约束

- **歌词基本保持不变** — 核心是改编曲, 不是改词
- **结构变了, 歌词要适配** (例如: 加快 → 删冗余句; 重复副歌 → 复制副歌段)
- **不改主题/不改视角** (这是 lyric-writer 的活)

---

## 使用示例

### 示例 1: 古风 → 电子

**用户**: "把'沧海飞尘'改编成电子版"

**AI 流程**:
1. Detect: 古风
2. Analyze: A1→B→C 结构, 30 句
3. Choose: 曲风转换 (电子 EDM) + 加快 (BPM +50%)
4. Apply: 调 description 为"古风 + EDM, 加快节奏, 强化副歌"
5. Generate: 输出 [verse] [chorus] [verse] [chorus] + description

**输入 minimax-music**:
- lyrics: (微调, 加强 hook 重复)
- description: "古风元素 + EDM, 快节奏, 强劲 drop, 男女合唱, 5 分钟"

### 示例 2: 民谣 → 交响

**用户**: "把'城市孤独'改编成交响版"

**AI 流程**:
1. Detect: 民谣
2. Analyze: verse-chorus-verse-chorus 结构
3. Choose: 曲风转换 (交响) + 加桥 (D 段)
4. Apply: description 改为"交响乐, 加弦乐四重奏, 加 D 段桥段"
5. Generate: 输出新歌词 (加 D 段)

### 示例 3: 加快 + 重复副歌

**用户**: "把'城市孤独'加快一点, 副歌重复 3 次"

**AI 流程**:
1. Detect: 民谣
2. Analyze: verse-chorus-verse-chorus
3. Choose: 加快 + 重复副歌
4. Apply: 删 A2, 副歌 ×3
5. Generate: 输出 [verse] [chorus] [chorus] [chorus]

---

## 跟 lyric-writer 的关系

| 维度 | lyric-writer | cover-writer |
|---|---|---|
| **核心** | 写歌词 | 改编曲 |
| **输入** | 用户需求/参考作品 | 原曲 (歌词 + 风格) |
| **输出** | 新歌词 | 改编版歌词 + minimax description |
| **下游** | minimax-music | minimax-music |
| **关系** | 平级 | 平级 (不嵌入) |

**复用**: 8 维度框架, 但**独立维护** (不互相 import, 避免耦合)。

---

## 资源清单

| 文件 | 用途 |
|---|---|
| [references/01-style-conversion/](references/01-style-conversion/) | 曲风转换 (3 文件) |
| [references/02-structure-variation/](references/02-structure-variation/) | 结构变奏 (2 文件) |
| [references/03-minimax-adapter/](references/03-minimax-adapter/) | minimax 适配 (2 文件) |
| [references/04-progressive-disclosure/patterns.md](references/04-progressive-disclosure/patterns.md) | 披露机制 |
| [assets/style-conversion-matrix.md](assets/style-conversion-matrix.md) | 风格转换矩阵 |
| [assets/structure-patterns-library.md](assets/structure-patterns-library.md) | 结构模式库 |

---

## 长期愿景 (整个音乐创作生态)

- **lyric-writer** (写歌词) ✅ v2.0
- **cover-writer** (改编曲) ← 当前
- **music-arranger** (配乐建议, 人工) — 未来
- **song-composer** (完整歌曲生成) — 终极整合
