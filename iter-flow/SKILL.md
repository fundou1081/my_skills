---
name: iter-flow
description: Evidence-driven iterative engineering workflow for any task requiring multiple attempts — performance tuning, bug investigation, algorithm experiments, environment config, script debugging, infrastructure changes. Use when the user mentions "iterate", "try", "approach N", "experiment", "comparison", "A/B", "patch iteration", "试一下", "再试一次", "调一下", "脚本实验", "调参", or any multi-attempt engineering task that should not rely on memory of what was tried last time. Three non-negotiable rules: (1) scripted never raw, (2) one iter one file, (3) no review no start. Drives 5-step execution with a structured iter_NN_<title>.md template and audit trail.
---

# Iterative Engineering Flow — Skill

> **性质说明**: 这是一份**通用迭代工作流**,把任何"需要试几次"的工程任务
> (debug / 性能调优 / 算法实验 / 环境 / 脚本 / 基础设施) 收敛成可追溯的
> 实验记录系统。**通用**于 chip-debug 这种垂域 skill。
>
> - 详细 5 步: [`references/workflow.md`](references/workflow.md)
> - Debug 场景速查: [`references/workflow.md` §Debug 速查](references/workflow.md)
> - 模板 / 脚本: `assets/templates/` 和 `scripts/` 各 3 个
> - 真实示例: [`examples/debug_502_spike.md`](examples/debug_502_spike.md)

---

## 1. 不可妥协的三条死规矩

### 死规矩 #1 — 脚本化,绝不裸敲命令
> 同一件事要做第二次时, 立刻把它写成脚本。
> 所有变更、检查、部署动作必须脚本执行。

裸敲的命令**今天在屏幕上,明天就不在了**。下次重复时容易漂移。
脚本是团队资产的最小单元 —— 写一次, 永久可复现。

**具体实施**: 不直接 `bash` 跑超过 3 行的命令, 写到 `scripts/` 下。
读 / 写 / grep / awk / 提交, 多步骤的命令都进脚本。

### 死规矩 #2 — 一迭代一文件
> 每尝试一轮, 就新建一个 `iter_N_<简述>.md`, 包含:
> **目的 · 实验条件 · 检查方法 · 结果 · Findings**

iter 文件的好处:
- 一行命令 `ls iter_*` 就看出"我们试了几次"
- 文件名编号天然排序(`iter_01` → `iter_02`)
- 文件是 diff-friendly 的, 改起来不出错

### 死规矩 #3 — 无回顾不开始
> 开始下一轮之前, **必须**打开最近至少 3 轮迭代日志, 把相关结论摘入新文件的"回顾引用"段。

跳过这一步会重蹈上一轮的覆辙。3 轮的"目的 + Findings"是上下文的最小单元。

---

## 2. 触发条件 (When to enter)

**当遇到以下情况时强制使用 iter-flow**:

| 信号 | 例 |
|------|-----|
| 用户说"试试" / "再试" / "调一下" | "试一下能不能优化下内存" |
| 任务明显不是一击必中 | perf tuning、A/B 配置、bug 排查 |
| 你想用 brute-force 多参数 | grid search, hyperparameter sweep |
| 之前手工试过了, 这次再试 | "上次说改改 y, 这次试试 z" |
| 别人 / ChatGPT 给过一版方案 | "AI 出的方案跑一下看看" |
| 模糊诊断:多因素、多 module | "不知道为啥慢" |

**不**用 iter-flow 的场景:
- 一击必中的小改 (改 README typo, 1 行 fix)
- 只是提问 / 文档查询
- 单 shell 命令能完成的纯信息收集

---

## 3. 执行步骤 (5 步照做就行)

### 第 0 步 — 起手式
```bash
mkdir -p experiments/<task>/{scripts,data}
# 写卡 (task 名简明, 用 kebab-case)
```

`card.md` 内容:
- **背景**: 现象 / 影响范围 / 已知线索
- **初始假设**: N 个, 排序 "我认为最可能" → "备选"

### 第 1 步 — 写假设, 开新迭代文件
创建 `iter_01_<简述>.md`, 包含:
- 回顾引用 (首轮可空)
- 目的 (我们相信: ...)
- 实验条件 (脚本 / 环境 / 是否有代码变更)
- 检查方法 (执行: `bash scripts/xxx.sh`)
- 成功标准 / 终止条件

### 第 2 步 — 把操作写成脚本并执行
所有命令进 `scripts/`, 多步骤必须包成脚本。

### 第 3 步 — 填结果, 写 Findings, 做决策
- 结果: 关键数据(指标峰值、错误次数、时间分布)
- Findings: 这轮支持 / 推翻 / 修改了哪个假设
- 决策: 启动 iter_N+1, 或进修复轮, 或终止

### 第 4 步 — 强制回顾, 进入下一轮
**绝不** 上轮 Findings 没读完就开 iter_N+1。
打开最近 3 轮 iter 文件, 把 "目的 + Findings" 摘要写入新文件 "回顾引用" 段。

### 第 5 步 — 修复验证 (也是迭代)
修复方案**必须**再过一轮实验验证, 不能"我看着像对"。 详见 workflow.md §第 5 步。

---

## 4. 反模式 (Anti-patterns)

- ❌ 跑了一次成功就宣布结论 → **没 iter 文件 = 没发生过**
- ❌ 用 `>>` 直接追加 5 行命令到 terminal → **进 scripts/**
- ❌ 同一 iter 跑 3 次才写 Results / Findings → **当场写**
- ❌ iter 文件名写 `iter_2.md` 而非 `iter_02.md` → **零填充 (sort 友好)**
- ❌ "回顾引用"段写 "见上轮" 而非具体结论 → **复制结论摘要**
- ❌ 修复后没验证就合 → **iter_R_NNN_fix_验证.md**

---

## 5. 速查: 这场景用什么

| 场景 | 起手 | 重点 iter |
|------|------|----------|
| 生产故障 | card.md 标 S0, 实验只读 (抓 dump / metric) | iter_01 抓黄金时段数据 |
| Perf 调优 | 抓 baseline, 1 次只改 1 个变量 | iter_N 系统化 ablation |
| 算法调参 | grid / random search, 每次留 seed | iter_N_<var>=<value> |
| 环境问题 | 抓完整 config + version, 装新环境对比 | iter_N_<change> |
| Bug 排查 | 信号 + 假设 + 数据 + 反证 (5-Why 类) | 跟 chip-debug skill 接 |

---

## 6. 一句话总结

> **任何需要试几次的工程任务, 都先建 `experiments/<task>/`, 然后"开 iter_N → 写脚本 → 跑 → 写 Findings → 强制回顾 → 开 iter_N+1", 直到根因/验证完成。**
>
> 这一流程的产物不是"我做完了一个项目", 而是"我能复现自己上次怎么做完的"。
> 这才是工程能力。

---

## See also

- `references/workflow.md` — 详细 5 步 + Debug 场景速查 + 反模式 + 验收清单
- `assets/templates/card.md.template` — 任务卡模板
- `assets/templates/iter_template.md` — 单轮迭代模板
- `scripts/iter_init.py` — 创建 task 目录 + card.md
- `scripts/iter_new.py` — 生成新 iter_N, 自动添前 3 轮"回顾引用"清单
- `scripts/iter_review.py` — 查看最近 3 轮摘要 (跟死规矩 #3 配套)
- `examples/debug_502_spike.md` — 一组完整 6 轮 debug 示例

**相关 skill**:
- [`chip-debug`](../chip-debug/SKILL.md) — 通用 debug / RCA 方法学, **可以套在 iter-flow 的每一 iter 里** (chip-debug 给 5-Why + 证据链, iter-flow 给"每 5-Why 走一圈也是一次 iter")
