# Iterative Workflow — Detailed 5-Step Guide

> 这是 `SKILL.md` 的**操作版**。当 SKILL.md 说"做 iter_N → 写脚本 → 跑 → ...",本文件说**具体怎么做**。
>
> 上游: [`../SKILL.md`](../SKILL.md)

---

## 0. 实验目录约定 (Naming + Structure)

每个独立任务一个目录,路径必须可读 + 可 grep:

```
experiments/
└── <task_name>/                    # 用 kebab-case, 简明有信息量
    ├── card.md                     # 任务卡 (背景 + 初始假设)
    ├── iter_01_<title>.md          # 顺序编号, 零填充
    ├── iter_02_<title>.md
    ├── ...
    ├── scripts/                    # 本任务中用到的所有脚本
    │   ├── iter_01_xxx.sh
    │   ├── iter_02_yyy.py
    │   └── ...
    └── data/                       # 脚本输出 + 任何数据快照
        ├── conn_active_iter_01.json
        ├── threaddump_iter_02_01.txt
        └── ...
```

**为什么这样**:
- `experiments/` 是惯例目录名,跟 `src/` / `docs/` 同级,git 知道不该误 commit 到生产
- `card.md` 在每个 task 顶部始终可见 (`ls experiments/<task>/` 一眼)
- `iter_NN_xxx.md` 排序天然 (零填充保证 `iter_09` < `iter_10`)
- `scripts/` 和 `data/` 分离 — 脚本是"代码",数据是"输出",分开 review

---

## 第 0 步 — 起手式 (5 分钟以内)

```bash
# 1. 建任务目录
mkdir -p experiments/debug_502_spike/{scripts,data}

# 2. 写 card.md
```

`card.md` 内容最低骨架:

```markdown
# 任务: <one-line summary>

## 背景
<3-5 行说清楚: 现象 / 影响范围 / 时间窗 / 已知线索>

## 初始假设
1. <最可能的 1 个>
2. <备选>
3. <远一点的猜想>
```

### 写好 card 的准则

- **"我认为" 是核心** — card 不是设计文档, 而是作者当前 vision
- **3-5 行是上限** — 多了就是 not hypothesis 而是 survey
- **假设要可证伪** — "服务慢" 不能证伪; "P95 > 500ms 是因连接池" 可证伪

### 防退化

- ❌ 同一个 card 反复改 → 写到 iter 里,不动 card
- ❌ "我会持续更新" → **第一版定稿就够,后面 iter 反向 back-trace**

---

## 第 1 步 — 写假设, 开新 iter 文件

### 文件命名

**强约束**: `iter_NN_<kebab-case-title>.md`

- `iter_01_连接池耗尽假设.md` ✅
- `iter_1_连接池耗尽假设.md` ❌ (没零填充, sort 后 `iter_1` < `iter_10` 错排)
- `iter_01_conn_pool_hypothesis.md` ✅ (英文也行)

### 文件内容 (强模板)

每轮 iter 文件必须含这 5 段:

```
# iter_NN: <title>

## 回顾引用
<前 1-3 轮的"目的 + Findings" 摘要, 或 "首轮无" 注明>

## 目的
我们相信: <可证伪的假设陈述>.

## 实验条件
- 脚本: <scripts/xxx.sh 或 scripts/xxx.py>
- 环境: <prod / staging / local; 时间窗; 实例 id>
- 无代码变更/有代码变更: <后者必须 link commit>

## 检查方法
执行: bash scripts/xxx.sh
观察指标: <具体的 metric name 或 grep pattern>
成功标准: <可测量的 PASS 条件>
终止条件: <什么时候放弃这一假设, 转下轮>

## 结果
<执行后填, 含 raw data 摘要>

## Findings
<这一轮支持 / 推翻 / 修改了哪个假设, 给出 evidence>
```

### 常见 pitfall

- 模板没"成功标准" → 跑了不知道算 PASS 还是 FAIL
- 模板没"终止条件" → 无限挂在一个假设上
- "目的"段写得太空 → "我们相信用户变多了" / "我们相信是 race", 没具体化

---

## 第 2 步 — 把操作写成脚本

### 强约束: >3 行的 shell / 多步操作必须进 scripts/

```bash
# ❌ 这种裸敲:
$ curl -s http://prom/internal-api/metrics > /tmp/x.json
$ jq '.data[] | select(.name=="db_active")' /tmp/x.json
$ curl -s http://prom/internal-api/metrics > /tmp/y.json
$ jq '.data[] | select(.name=="db_wait")' /tmp/y.json
$ echo "Active: $(...), Wait: $(...)"

# ✅ 必须变 scripts/check_conn_pool.sh:
#!/bin/bash
set -euo pipefail
mkdir -p data
curl -s -o data/conn_active_$(date +%H%M).json "$PROM_URL/.../db_active"
curl -s -o data/conn_wait_$(date +%H%M).json "$PROM_URL/.../db_wait"
python3 scripts/summarize.py data/conn_active_*.json data/conn_wait_*.json
```

### 脚本命名建议

- `iter_NN_<动作>.sh` 或 `.py` — 一目了然
- 不要 `query.sh` / `fetch.sh` 这种通用名

### 脚本本身的质量要求

- `set -euo pipefail` ←— 失败立刻停
- `mkdir -p data/` ←— 保证输出目录存在
- 写时间戳到文件名 ←— 多次跑结果不互相覆盖

---

## 第 3 步 — 填结果 + Findings + 决策

### Results 段写什么

- 关键 **raw data** 摘要 (不是 "很多", 是 "峰值 48/50 = 96%")
- 与"成功标准"对照: 这个数据点 PASS 还是 FAIL
- 如果 FAIL, 简要说明为什么 (否则别人 6 个月后再看, 不知是想 pass 还是 ok)

### Findings 段写什么

- **支持 / 推翻 / 修改哪个假设** — 必须有 1 条对应
- 给出 evidence (是哪一行数据 / 哪一现象)
- 不是 "我觉得" — 是 "iter_01 数据表明 ..."

### 决策 (Decision)

决策有 3 类, 必须在 iter 结尾选一个:

| 决策 | 条件 |
|------|------|
| **启动 iter_N+1** | 本轮假设 **未完整验证** + 还有新假设待跑 |
| **进入修复轮** | 本轮找到 root cause + 有 fix idea |
| **终止 + 知会** | 假设 **推翻** + 上级 / 用户决策要不要继续 |

记录决策**也进 card.md 的状态字段** (维护 card 当前所处 iter)。

---

## 第 4 步 — 强制回顾, 进入下一轮

### 死规矩 #3 实施

```bash
# 用 iter_review.py 看最近 3 轮 摘要
python3 scripts/iter_review.py experiments/<task>/
```

把打印出来的 3 段 "目的 + Findings + 决策" 拷到新 iter 的"回顾引用"段。 这就是 knowledge transfer。

### 不做这一步会怎样

经典场景:
- iter_05 显示 "时序超出 setup, 改 pipeline stage"
- iter_06 写 "我们相信数据冒险是问题"
- **已经脱离了 iter_05 的结论**, 6 个月后看 iter_06 完全不懂为啥去查这里

回顾机制确保每轮的"为什么这样查"被记录。

---

## 第 5 步 — 修复验证

> **核心**: 修复方案**必须**再过一轮 iter 验证, 不可凭眼睛。

iter 文件结构 (跟普通 iter 同):

```
# iter_NN: 验证 <fix> 修复效果

## 回顾引用
<copy 把 iter_N-1 (找 RC 那轮) 关键结论>

## 目的
我们相信: <fix 后 <metric / behavior> 应当 <expected>>.

## 实验条件
- 分支: <feature/xxx>
- 环境: <prod gray / staging>
- 对比基线: main 分支或未修复版本

## 检查方法
<压测 / shadow traffic / A/B>

## 结果

## Findings
- fix 是否真有效, 数字是多少
- 副作用 / regression 有没有
```

**验证失败时回到 iter_N-1, 不抛弃原假设也不强推 fix**。

---

## Debug 场景速查

| 阶段 | iter 任务 | 重点 |
|------|-----------|------|
| 接警 | iter_00 (可选): 建实验目录 + card | 看一眼历史 task 目录, 复用模板 |
| 第一轮 | iter_01: 选最可能假设, **写 iter_01 文件 + 抓指标 / 日** | 数据优先于脑补 |
| 第二轮 | iter_02: 读 iter_01 Findings, **写 iter_02**, 抓更深一层 | "我们相信 ..." 必须链接到 iter_01 |
| 第 N 轮 | 同上 | 持续读到 iter_00 自由 |
| 修复轮 | iter_N: 验证 fix | fix 不验证 = 没 fix |
| 结案 | 全目录归档 | 进 docs/runbooks/, 方便后人 |

---

## 反模式 (完整清单)

| 反模式 | 为什么坏 | 正确做法 |
|--------|---------|---------|
| 跑了一次成功就宣布结论 | 不可重做 | iter 文件 + Find 脚本, 重做一次 |
| `>>` 直接追加 5 行 cmd | 命令组合漂移 | 进 scripts/ |
| 同一 iter 跑 3 次才写 Result | "刚才看到了啥?"  | 当场填, 用脚本输出即可 |
| iter 文件名非零填充 | sort 错乱 | `iter_01`, `iter_02`, ..., `iter_10` |
| 回顾引用只写"见上轮" | 知识断链 | 复制结论摘要, 至少 3 行 |
| 修复没验证就合 | 假装修了 | 留 iter_R_NNN_verification.md |
| 假设"用户变多了" | 不可证伪 | "P95 时延 P99 > 800ms 是因 Y" |
| iter 之间间隔 > 1 天还没 doc | 上下文蒸发 | 当 iter 写, 再跑 |
| 写到一半 commit iter 文件 | 历史混乱 | 写完一个完整 iter 才 commit |
| 用同一个 iter 文件改 | 增量 diff 难 | iter_N 一个文件, 一轮一 commit |

---

## 验收清单 (完成一个 task 之前)

- [ ] card.md 还在, 没被改坏
- [ ] 所有 iter 文件齐 (iter_01 → iter_N), 编号无 gap
- [ ] 每个 iter 文件 5 段齐全 (回顾 / 目的 / 实验条件 / 检查 / 结果 / Findings)
- [ ] 每个 iter 都在 scripts/ 下有对应脚本
- [ ] 每个脚本有 `set -euo pipefail` 或等价的错误传播
- [ ] 修复 (如有) 单独有一轮 iter 验证
- [ ] 全部 experiments/ 在 git 里 (或 .gitignore 文档化为什么不)

---

## 沉淀约定 (How to extend this doc)

增补新章节按这个格式 append (新 §11, §12, ...):

```
## §<N>: <新场景描述>

### 触发条件
- ...

### 增量模板 (跟第 1 步模板的区别)
- ...

### 反模式 (新增)
- ...
```

不要动现有 §0-§5 的骨架 — 时间已经做了约定, 改动会失去 audit value。
