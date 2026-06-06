---
name: lyric-writer
description: >
  中文歌词创作助手, 多风格渐进式披露系统。Use when 用户提到"写歌词"、
  "帮我写歌词"、"歌词创作"、"lyric"、"分析歌词"、"这个歌词怎么样"、
  "按 ___ 风格写" 或任何中文歌词相关请求。Triggers include 显式
  "写歌词 / 歌词创作 / 帮我写歌词"、作品分析"分析这个歌词"、按风格
  "按 R&B/古风/流行/民谣/摇滚写"、AI 主动检测"用户要写歌"。支持 10 种
  风格 (古风/流行/民谣/摇滚/R&B/说唱/城市民谣/校园民谣/电子/中国风),
  每种独立流程, 渐进式披露, 4 个子功能协同。
---

# lyric-writer - 中文歌词创作助手 (多风格版)

> **核心**: 不是"古风专项", 而是**多风格渐进式披露系统**。  
> 10 种风格独立维护, 4 个子功能协同工作, 按需展开。

---

## TL;DR

不直接动笔, 先**判断风格** → **加载对应画像** → **形成套路** → **让用户调整** → **生成完整歌词**。

古风已完整实现, 其余 9 种风格用占位符 (用户逐渐补全)。

---

## 触发方式

用户提到以下内容时激活:
- "写歌词" / "帮我写歌词" / "歌词创作"
- "lyric" / "lyrics"
- "分析歌词" / "这个歌词怎么样"
- "按 ___ 风格写" / "模仿 ___ 风格"
- AI 主动检测到用户想写歌 (隐式触发)

---

## 支持的 10 种风格

| 风格 | 状态 | 入口 |
|---|---|---|
| **古风 (Gufeng)** | ✅ 完整 | [styles/gufeng.md](references/styles/gufeng.md) |
| 流行 (POP) | 🚧 占位符 | [styles/pop.md](references/styles/pop.md) |
| 民谣 (Folk) | 🚧 占位符 | [styles/folk.md](references/styles/folk.md) |
| 摇滚 (Rock) | 🚧 占位符 | [styles/rock.md](references/styles/rock.md) |
| R&B / 灵魂 | 🚧 占位符 | [styles/rnb-soul.md](references/styles/rnb-soul.md) |
| 说唱 (Hip-hop) | 🚧 占位符 | [styles/hip-hop.md](references/styles/hip-hop.md) |
| 城市民谣 | 🚧 占位符 | [styles/urban-folk.md](references/styles/urban-folk.md) |
| 校园民谣 | 🚧 占位符 | [styles/campus-folk.md](references/styles/campus-folk.md) |
| 电子 (EDM) | 🚧 占位符 | [styles/edm.md](references/styles/edm.md) |
| 中国风 | 🚧 占位符 | [styles/chinese-style.md](references/styles/chinese-style.md) |

**完整索引**: [references/styles/README.md](references/styles/README.md)

---

## 4 个子功能 (渐进式披露)

| 子功能 | 入口 | 何时触发 |
|---|---|---|
| **01 风格提取** | [README](references/01-style-extraction/README.md) | 用户给风格 / 给参考作品 |
| **02 风格画像** | [README](references/02-style-profile/README.md) | 8 维度画像存储与读取 |
| **03 风格应用** | [README](references/03-style-application/README.md) | 套路 → 调整 → 生成 |
| **04 渐进式披露** | [README](references/04-progressive-disclosure/README.md) | 元机制, 任何时候可读 |

详见: [04-progressive-disclosure/README.md](references/04-progressive-disclosure/README.md) 的"披露触发矩阵"

---

## 主工作流 (5 步)

```
用户: "帮我写首 ___ 风格歌"
        ↓
1. Detect (检测) — 风格名 / 参考作品 / 模糊感觉
        ↓
2. Extract (提取) — 01-style-extraction 深入挖掘 5 软 + 3 硬维度
        ↓
3. Profile (画像) — 02-style-profile 形成 8 维度画像, 用户确认
        ↓
4. Apply (应用) — 03-style-application 套路 → 调整 → 生成
        ↓
5. Verify (自检) — 套用 assets/style-extraction-checklist.md
        ↓
输出: 完整歌词
```

---

## 关键设计: 软维度 vs 硬维度

| 类型 | 维度 | 来源 |
|---|---|---|
| **软** (5 项) | 核心情感 / 内心需求 / 创作源头 / 特殊技法 / 表达方式 | **每次创作都问** (用户回答) |
| **硬** (3 项) | 押韵方案 / 句式模板 / 意象清单 | **从风格库加载** (同一风格固定) |

详见: [02-style-profile/README.md](references/02-style-profile/README.md)

---

## 使用示例

### 示例 1: 古风 (完整方法论)

**用户**: "帮我写一首关于'灯'的歌词, 主题是放下执念"

**AI 流程**:
1. Detect: 古风 + 意象"灯" + 主题"放下执念"
2. Extract: 加载 [styles/gufeng.md](references/styles/gufeng.md), 5 软维度已默认
3. Apply: 走古风 6 阶段 (见 styles/gufeng.md)
4. Verify: 古风自检清单

**输出**: 完整古风歌词 (A1→B→C→...)

### 示例 2: R&B (占位符风格)

**用户**: "帮我写一首 R&B 风格的分手歌"

**AI 流程**:
1. Detect: R&B + 主题"分手"
2. Extract: 加载 [styles/rnb-soul.md](references/styles/rnb-soul.md) (占位符), **主动问 5 软维度** (因为硬维度空)
3. **AI 坦诚**: "R&B 风格画像待补全, 我先用通用占位 + 你的回答生成。后续用户补全后会更好。"
4. Apply: 基于通用 R&B 套路生成
5. Verify: R&B 自检 (待定义)

**输出**: 1 段 R&B 歌词 + 后续待补全标记

---

## 古风特殊说明

古风是**唯一完整实现**的风格, 沿用原 6 阶段方法论:
1. 锚定核心意象与主题
2. 构建歌词骨架
3. 意象系统与时空编织
4. 文字填充
5. 情感弧线打磨
6. 自我检验

完整内容: [references/styles/gufeng.md](references/styles/gufeng.md)

---

## 9 个待补全风格

流行/民谣/摇滚/R&B/说唱/城市民谣/校园民谣/电子/中国风 都用占位符, 用户**逐渐补全**。

**补全流程**:
1. 找 3-5 首代表作品
2. 用 [01-style-extraction/questions.md](references/01-style-extraction/questions.md) 分析 8 维度
3. 填入 `references/styles/<style>.md` 对应字段
4. 写创作流程 (基于古风 6 阶段调整)
5. 写自检清单

模板: [assets/style-profile-blank.md](assets/style-profile-blank.md)

---

## 资源清单

| 文件 | 用途 | 何时读 |
|---|---|---|
| [references/styles/README.md](references/styles/README.md) | 10 风格索引 | 用户问"支持什么风格" |
| [references/01-style-extraction/](references/01-style-extraction/) | 风格提取 | 用户给风格时 |
| [references/02-style-profile/](references/02-style-profile/) | 8 维度画像 | 需调取画像时 |
| [references/03-style-application/](references/03-style-application/) | 风格应用 | "开始写"时 |
| [references/04-progressive-disclosure/](references/04-progressive-disclosure/) | 披露机制 | 元机制 |
| [assets/style-profile-blank.md](assets/style-profile-blank.md) | 空白画像模板 | 用户要补全时 |
| [assets/style-extraction-checklist.md](assets/style-extraction-checklist.md) | 自检清单 | 歌词生成后 |
| [assets/rhyme-schemes-library.md](assets/rhyme-schemes-library.md) | 押韵方案库 | 押韵决策时 |

---

## 长期愿景 (整个音乐创作生态)

- **lyric-writer** (歌词) ← 当前
- **music-arranger** (配乐建议) ← 未来独立 skill
- **song-composer** (完整歌曲) ← 终极整合

**配乐建议不在本期范围**, 留作未来单独 skill。

---

## 数据存储

创作中间文件保存在:
- `~/.openclaw/workspace/memory/lyrics/` 目录

## 扩展计划

- 接入音乐 API 检测韵脚
- 配乐单独 skill (见长期愿景)
- 用户补全 9 个风格画像
