# 需求澄清表模板 (Clarification Table Template)

> 本文件是 better-act-skill 在 **Step 4 (Clarify)** 输出的需求澄清表模板。  
> AI 按选定框架的字段填表, 让用户确认后进入 Step 5。

---

## 通用结构

```markdown
# 需求澄清表

**框架**: [TIDD-EC / ICDO / CRISPE / BROKE / CO-STAR / 万能公式]
**生成时间**: [ISO 时间戳]
**状态**: ⏳ 待用户确认 / ✅ 已确认

## 核心要素

| 框架要素 | 用户填写 | AI 备注 |
|---|---|---|
| T (Task) | ... | ... |
| I (Instructions) | ... | ... |
| D (Details) | ... | ... |
| D (Data) | ... | ... |
| E (Examples) | ... | ... |
| C (Constraints) | ... | ... |

## 补充说明

- **任务类型**: [数据分析 / 内容创作 / 代码 / ...]
- **目标受众**: [...]
- **风格**: [...]
- **预计输出**: [...]

## 确认选项

- [ ] ✅ 确认无误, 进入 Step 5 生成 prompt
- [ ] ✏️ 修改某几项 (请注明)
- [ ] ❌ 换框架
- [ ] 🛑 算了, 直接干
```

---

## 5 框架专用模板

### TIDD-EC 模板

```markdown
# 需求澄清表 (TIDD-EC)

| 要素 | 内容 |
|---|---|
| **T** (Task) | [一句话任务目标] |
| **I** (Instructions) | [详细执行步骤] |
| **D** (Details) | [受众/语气/长度等背景] |
| **D** (Data) | [原始材料/数据] |
| **E** (Examples) | [1-3 个期望样例] |
| **C** (Constraints) | [字数/禁用词/必含项/格式] |

## 关键确认
- [ ] T 清晰可执行?
- [ ] I 步骤可落地?
- [ ] D (Data) 真实可靠?
- [ ] E 能让 AI 学到风格?
- [ ] C 无歧义?
```

### ICDO 模板

```markdown
# 需求澄清表 (ICDO)

| 要素 | 内容 |
|---|---|
| **I** (Instruction) | [具体任务] |
| **C** (Context) | [背景信息] |
| **C** (Constraints) | [格式/风格限制] |
| **O** (Output) | [输出要求] |

## 关键确认
- [ ] I 明确无歧义?
- [ ] C (Context) 够 AI 理解?
- [ ] C (Constraints) 可执行?
- [ ] O 描述具体?
```

### CRISPE 模板

```markdown
# 需求澄清表 (CRISPE)

| 要素 | 内容 |
|---|---|
| **C** (Capacity) | [AI 角色] |
| **R** (Request/Insight) | [任务背景/数据] |
| **S** (Statement) | [具体意图] |
| **P** (Personality) | [写作风格] |
| **E** (Experiment) | [是否允许 AI 反问] |
| **O** (Output) | [最终产出形式] |

## 关键确认
- [ ] C 角色定位合适?
- [ ] R 背景信息够用?
- [ ] S 意图清晰?
- [ ] P 风格一致?
- [ ] E 反问范围明确?
- [ ] O 输出可衡量?
```

### BROKE 模板

```markdown
# 需求澄清表 (BROKE)

| 要素 | 内容 |
|---|---|
| **B** (Background) | [任务背景] |
| **R** (Role) | [AI 角色] |
| **O** (Objectives) | [成功标准] |
| **K** (Key Results) | [具体产出] |
| **E** (Evolve) | [迭代方式] |

## 关键确认
- [ ] B 背景完整?
- [ ] R 角色匹配?
- [ ] O 可衡量?
- [ ] K 具体可见?
- [ ] E 迭代节奏合理?
```

### CO-STAR 模板

```markdown
# 需求澄清表 (CO-STAR)

| 要素 | 内容 |
|---|---|
| **C** (Context) | [任务背景] |
| **O** (Objective) | [任务目的] |
| **S** (Style) | [写作风格] |
| **T** (Tone) | [情感基调] |
| **A** (Audience) | [目标读者] |
| **R** (Response) | [输出结构/长度] |

## 关键确认
- [ ] C 背景清楚?
- [ ] O 目的明确?
- [ ] S 风格统一?
- [ ] T 基调合适?
- [ ] A 受众精准?
- [ ] R 结构具体?
```

---

## 通用万能公式模板 (兜底)

```markdown
# 需求澄清表 (万能公式)

请作为 **[角色]**,
根据 **[背景信息]**,
帮我完成 **[具体任务]**。
要求满足 **[约束 1]**、**[约束 2]**。
最终以 **[输出格式]** 呈现。

## 关键确认
- [ ] 角色定位合适?
- [ ] 背景信息够用?
- [ ] 任务清晰可执行?
- [ ] 约束无歧义?
- [ ] 输出格式具体?
```

---

## 输出示例

### 示例 1: TIDD-EC 完整填表

```markdown
# 需求澄清表 (TIDD-EC)

**生成时间**: 2026-06-05 23:30 GMT+8
**状态**: ⏳ 待用户确认

| 要素 | 用户填写 | AI 备注 |
|---|---|---|
| T (Task) | 设计一个"元提示词" skill, 帮用户用提示词框架理清需求 | ✅ 清晰 |
| I (Instructions) | 检测→选框架→引导提问→需求澄清表→生成 prompt | ✅ 5 步可落地 |
| D (Details) | 受众=所有人; 语气=顾问; 触发=显式+隐式 | ✅ 完整 |
| D (Data) | 5 个内置框架 (TIDD-EC/ICDO/CRISPE/BROKE/CO-STAR) | ✅ 资料齐 |
| E (Examples) | 暂无, 按 sv-trace 风格 | ⚠️ 标记, AI 默认 |
| C (Constraints) | 符合 AgentSkills 规范; name 小写连字符; description 必填含触发词 | ✅ 明确 |

## 补充说明

- **任务类型**: 工具型 skill (元提示词)
- **目标受众**: 所有人 (开发者优先)
- **风格**: 顾问, 简洁, 一次 1-2 问
- **预计输出**: SKILL.md + references/ + assets/

## 确认选项

- [ ] ✅ 确认无误, 进入 Step 5 生成 prompt
- [ ] ✏️ 修改某几项 (请注明)
- [ ] ❌ 换框架
- [ ] 🛑 算了, 直接干
```

---

## 标记约定

| 标记 | 含义 |
|---|---|
| ✅ | 完整且清晰 |
| ⚠️ | 部分缺失, 但可工作 |
| ❌ | 关键缺失, 必须补 |
| (未提供) | 用户没填 |
| (AI 默认) | AI 自动填, 用户可改 |

---

## 配套产出物 (Step 5)

确认需求澄清表后, AI 应该:

1. **生成完整 prompt** (用 [框架] + 用户填的要素)
2. **给出执行路径** (下一步要做什么)
3. **明确完成标准** (什么算"做完了")

### 生成 prompt 范例 (基于上面的示例)

```markdown
请作为资深 Skill 设计师,
根据 AgentSkills 规范和元提示词方法论,
帮我创建一个名为 `better-act-skill` 的 skill。

任务 (T):
- 帮用户在动手前用提示词框架理清真实需求, 再正式开工

指令 (I):
1. 检测信息不足信号
2. 选最合适的框架 (默认 TIDD-EC)
3. 用框架字段引导用户 (一次 1-2 问, 顾问语气)
4. 输出需求澄清表让用户确认
5. 生成完整 prompt 进入正式工作

细节 (D):
- 目标受众: 所有人 (优先开发者)
- 语气: 顾问 (专业、简洁、不寒暄)
- 触发: 显式 ("用 X 框架") + 隐式 (AI 主动判断)
- 存放位置: ~/.openclaw/workspace/skills/better-act-skill/

资料 (D):
- 5 个内置框架定义: TIDD-EC / ICDO / CRISPE / BROKE / CO-STAR
- 范例参考: ~/.openclaw/workspace/skills/sv-trace/

约束 (C):
- 符合 AgentSkills 规范
- name 必须小写连字符
- description 必须含触发词
- SKILL.md < 500 行
- 必须有 references/ 和 assets/ 目录

输出 (O):
- SKILL.md (主文件)
- references/frameworks.md (5 框架定义)
- references/triggers.md (触发信号)
- references/flow.md (对话流程范例)
- references/examples.md (好坏对比)
- assets/clarification-table.md (需求澄清表模板)
- 用 package_skill.py 打包验证
```
