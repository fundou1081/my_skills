# 风格库索引

lyric-writer 支持 **10 种**创作风格, 每种独立维护。

## ✅ 完整实现
| 风格 | 文件 | 状态 |
|---|---|---|
| 古风 | [gufeng.md](gufeng.md) | ✅ 从原 SKILL.md 6 阶段迁移, 重组为 8 维度格式 |

## 🚧 占位符 (待补全)
| 风格 | 文件 | 备注 |
|---|---|---|
| 流行 (POP) | [pop.md](pop.md) | 主流, 易传唱 |
| 民谣 (Folk) | [folk.md](folk.md) | 叙事, 朴实 |
| 摇滚 (Rock) | [rock.md](rock.md) | 力量, 反叛 |
| R&B / 灵魂 (R&B-Soul) | [rnb-soul.md](rnb-soul.md) | 律动, 转音 |
| 说唱 (Hip-hop) | [hip-hop.md](hip-hop.md) | 押韵密集, flow |
| 城市民谣 (Urban Folk) | [urban-folk.md](urban-folk.md) | 现代都市叙事 |
| 校园民谣 (Campus Folk) | [campus-folk.md](campus-folk.md) | 青春, 回忆 |
| 电子 (EDM) | [edm.md](edm.md) | 重复, hook |
| 中国风 (Chinese Style) | [chinese-style.md](chinese-style.md) | 现代流行化古风 (与古风的区别待定) |

## 占位符结构 (所有风格统一)

每个 `<style>.md` 包含:
1. **风格定义** + 边界
2. **8 维度画像**:
   - 核心情感
   - 内心需求
   - 创作源头
   - 特殊技法
   - 表达方式
   - 押韵方案
   - 句式模板
   - 意象清单
3. **代表作品** 分析 (3-5 首)
4. **创作流程** (基于 [03-style-application](../03-style-application/workflow.md))
5. **自检清单** (基于 [assets/style-extraction-checklist.md](../../assets/style-extraction-checklist.md))

## 补全指南

要补全某个风格, 顺序:
1. **找代表作品** (3-5 首)
2. **逐首分析 8 维度**
3. **提取共性** → 写入对应字段
4. **写创作流程** (基于古风的 6 阶段, 调整)
5. **写自检清单** (古风 6 阶段检验 → 风格化调整)

详细补全方法: [02-style-profile/README.md](../02-style-profile/README.md)
