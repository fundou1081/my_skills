# 风格应用工作流 (3 阶段)

## 阶段 1: 套路 (Draft)

**输入**: 风格画像 (8 维度) + 用户给的意象/主题/情感  
**输出**: 1 段套路歌词 (基于画像的句式 + 押韵 + 意象)

### 流程

```python
def apply_style(profile: StyleProfile, theme: str, emotion: str) -> Draft:
    # 从 profile 提取硬数据
    template = profile.sentence_template      # 句式模板
    rhyme_scheme = profile.rhyme_scheme       # 押韵方案
    imagery = profile.imagery                 # 意象清单
    
    # 软维度作为生成约束
    constraints = {
        "core_emotion": profile.core_emotion,
        "expression": profile.expression,
        "techniques": profile.special_techniques,
    }
    
    # 用 theme + emotion 填充
    draft = generate_draft(template, rhyme_scheme, imagery, 
                          theme, emotion, constraints)
    return draft
```

### 输出示例 (古风)

```
【A1 段: 灯起】
长夜冷 孤灯照影 (4+4)
却照不透心中霜雪 (7)
灯花落 瘦尽灯芯 (4+4)
燃到极致化成灰烬 (7)
```

## 阶段 2: 调整 (Refine)

展示 draft, 让用户调整。常见调整:

| 类型 | 示例 |
|---|---|
| 句级 | "第 3 句改成..." |
| 意象级 | "潮 改成 风" |
| 调性级 | "更现代点" / "更文言点" |
| 结构级 | "不要桥段" / "A1 改 A2 的内容" |
| 完全重写 | "完全不要这版, 重写" |

详见: [refinement.md](refinement.md)

## 阶段 3: 生成 (Complete)

基于调整后的 draft, 生成完整歌词:

```
A1 (主歌1) → B (预副歌) → C (副歌) → A2 (主歌2) → B2 → C2 → D (桥段) → C3 (升华副歌)
```

套用 [assets/style-extraction-checklist.md](../../assets/style-extraction-checklist.md) 自检。

## 输出

```markdown
# <歌曲名>

## 创作信息
- 风格: 古风
- 主题: 灯 → 放下执念
- 情感弧线: 执念燃烧 → 燃尽看破 → 化光前行

## 完整歌词

A1: ...
B: ...
C: ...
...

## 自检结果
- [x] 核心意象出现 3+ 次
- [x] 至少 3 句矛盾式金句
- [x] 情感弧线完整
- ...
```

## 关键原则

- **保留历史版本** (3-5 轮), 方便回退
- **调整超过 3 轮**, 建议回到 [01-style-extraction](../01-style-extraction/README.md) 重新对画像
- **不要硬塞意象**, 套用画像的意象库, 但允许 AI 根据主题创造新意象
