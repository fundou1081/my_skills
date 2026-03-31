---
name: first-principles
version: "1.0.0"
description: "第一性原理思维技能，用于从底层基本真理出发解决问题、突破惯例约束、进行颠覆性创新。当用户需要打破思维定势、从零重新设计系统、质疑行业惯例、分析成本结构根本原因、发现隐藏假设、解决传统方法无法突破的瓶颈，或提到第一性原理、底层逻辑、本质思考、根本原因、从零开始设计、为什么要这样做、有没有更根本的解法等场景时触发此技能。"
---

# First Principles Thinking Skill

## 概述

第一性原理思维（First Principles Thinking）是一种从最基础的、不可再分的真理出发进行推理的思维方法。由亚里士多德提出，由马斯克推广践行。它的核心是：**不用类比，从底层基本真理重新构建解决方案**。

**与 TRIZ 的协同关系**：
- **第一性原理**：发现问题本质，识别真正的约束 vs. 可突破的假设
- **TRIZ**：在确定了真正的矛盾后，系统化地生成解决方案
- **推荐工作流**：先用第一性原理定义问题 → 再用 TRIZ 解决矛盾

---

## 核心工具（Scripts）

位于 `~/.workbuddy/skills/first-principles/scripts/`

### 1. fp_wizard.py — 完整分析向导
```bash
# 交互式五阶段完整分析
python3 ~/.workbuddy/skills/first-principles/scripts/fp_wizard.py

# 快速框架模式（列出所有引导问题，不需要交互）
python3 ~/.workbuddy/skills/first-principles/scripts/fp_wizard.py --quick "问题描述"

# 指定问题的交互式模式
python3 ~/.workbuddy/skills/first-principles/scripts/fp_wizard.py --interactive "问题描述"
```

### 2. assumption_breaker.py — 假设爆破矩阵
```bash
# 通用假设分析
python3 ~/.workbuddy/skills/first-principles/scripts/assumption_breaker.py "问题描述"

# 领域专属假设库（自动识别该领域的常见假设）
python3 ~/.workbuddy/skills/first-principles/scripts/assumption_breaker.py --domain software "问题"
python3 ~/.workbuddy/skills/first-principles/scripts/assumption_breaker.py --domain engineering "问题"
python3 ~/.workbuddy/skills/first-principles/scripts/assumption_breaker.py --domain product "问题"
python3 ~/.workbuddy/skills/first-principles/scripts/assumption_breaker.py --domain business "问题"
python3 ~/.workbuddy/skills/first-principles/scripts/assumption_breaker.py --domain process "问题"
```

### 3. five_whys.py — 五问法深挖
```bash
# 标准五问法（交互式）
python3 ~/.workbuddy/skills/first-principles/scripts/five_whys.py "问题描述"

# 指定追问深度
python3 ~/.workbuddy/skills/first-principles/scripts/five_whys.py --depth 7 "问题描述"

# 快速框架（非交互）
python3 ~/.workbuddy/skills/first-principles/scripts/five_whys.py --quick "问题描述"
```

---

## AI 执行 SOP（标准操作程序）

当用户提出需要第一性原理分析的问题时，**必须按以下五个阶段完整执行**：

### Phase 1：问题澄清
**运行**：`python3 ~/.workbuddy/skills/first-principles/scripts/fp_wizard.py --quick "用户的问题"`

输出：关键澄清问题列表，以及对问题的精确定义

**AI 补充**：
- 用一句话精确描述问题的本质
- 明确成功标准（问题被解决的衡量方式）
- 识别问题所属领域（engineering/software/product/business/process）

---

### Phase 2：假设暴露
**运行**：`python3 ~/.workbuddy/skills/first-principles/scripts/assumption_breaker.py --domain [领域] "问题描述"`

**AI 执行**：
1. 列出该领域相关的所有假设
2. 对每个假设进行分类：
   - 🔒 物理/数学约束（不可改变）
   - 📋 行业标准/规范（可质疑）
   - 🏛️ 历史遗留/惯例（重点挑战）
   - 💭 个人/集体偏见（必须验证）
3. 标记哪些假设**可以被打破**

---

### Phase 3：第一性原理提取
**运行**：`python3 ~/.workbuddy/skills/first-principles/scripts/five_whys.py --quick "问题描述"`

**AI 执行**：
1. 从物理维度找到基本约束（能量、材料、空间、时间）
2. 从经济维度拆解成本结构（谁在承担成本？为什么？）
3. 从行为维度识别人的约束（认知、决策、动机）
4. 总结：什么是真正不可改变的 vs. 可以改变的

**关键输出**：
```markdown
## 第一性原理（基本真理）

| 类型 | 内容 | 是否可改变 |
|------|------|-----------|
| 物理约束 | ... | 否（需绕过） |
| 行业惯例 | ... | 是（重点突破） |
| 真正的用户需求 | ... | 是判断基准 |
```

---

### Phase 4：方案重建
基于 Phase 3 识别的第一性原理，从零构建方案

**AI 执行**：
1. **跨域迁移**：其他领域是否已经解决了类似的基础问题？
2. **消除中间层**：能否直接实现核心目标，跳过中间环节？
3. **反向设计**：从理想结果反推所需条件
4. 生成 3-5 个基于第一性原理的候选方案

如果方案涉及技术矛盾，**切换到 TRIZ**：
```
识别到技术矛盾：[改善参数] vs [恶化参数]
→ python3 ~/.workbuddy/skills/triz/scripts/matrix_lookup.py [参数A编号] [参数B编号]
→ 使用推荐的发明原理生成具体方案
```

---

### Phase 5：压力测试
对 Phase 4 的方案进行鲁棒性验证

**AI 执行**：
1. 规模测试：方案在 10×规模下是否仍有效？
2. 极限测试：最坏情况下方案的表现？
3. 依赖测试：方案依赖什么外部条件？
4. 第二阶效应：实施后会引发哪些连锁反应？
5. **给出明确建议**：推荐方案 + 主要风险 + 缓解策略

---

## 参考资料

- `references/fp_manual.md` — 完整操作手册（含所有工具使用指南）
- `references/case_library.md` — 经典案例库（SpaceX、Tesla、iPhone 等8个案例）

---

## 踩坑经验

（由 AI 在实际使用中积累，请勿手动删除）

- 运行脚本时需要指定完整路径 `~/.workbuddy/skills/first-principles/scripts/`
- `--quick` 模式适合 AI 分析场景，不需要用户交互
- 当问题涉及技术矛盾时，Phase 4 后应切换 TRIZ Skill 处理矛盾解法
