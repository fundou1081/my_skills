# iter_{{ITER_NUM}}: {{TITLE}}

## 回顾引用

> 这一段是**死规矩 #3** 的具体实施: 开始 iter 之前, 把前 1-3 轮的 "目的 + Findings + 决策" 摘到这里。
> 不复制 = 知识断链。

{{REVIEW_REFS}}

## 目的

我们相信: **{{HYPOTHESIS_STATEMENT}}**.

(可证伪的假设陈述 —— 简单一句, 加粗。)

## 实验条件

- 脚本: `{{SCRIPTS}}` (在 `{{SCRIPTS_DIR}}`)
- 环境: {{ENV_DESCRIPTION}}
- 时间窗: {{TIME_WINDOW}}
- 代码变更: {{CODE_CHANGE_NOTE}}   *(无 / <commit-hash> 链接 / 描述性 diff)*

## 检查方法

执行:
```bash
{{EXEC_CMD}}
```

观察指标:

- {{METRIC_1}}: 期望 (pass 阈值)
- {{METRIC_2}}: 期望
- {{METRIC_3}}: 期望

**成功标准**: {{PASS_CRITERIA}}

**终止条件**: {{TERMINATION_CRITERIA}} *(什么情况放弃这一假设, 转 iter_{{NEXT_ITER}})*

## 结果

(执行后填, 这里放 raw data 摘要, 不是"很多"而是"峰值 48/50 = 96%"。)

- {{RESULT_LINE_1}}
- {{RESULT_LINE_2}}

vs. 成功标准:

- {{METRIC_1}}: PASS / FAIL — <理由>
- 失败时: 简要说明失败原因, 否则 6 个月后再看不知是 PASS 还是 FAIL

## Findings

- 支持 / 推翻 / 修改了哪个假设: <which one, with evidence pointer>
- 新发现: <if any>
- 跟下轮 iter_N+1 的衔接点: <link or rationale>

## 决策

*选一个打勾:*

- [ ] **启动 iter_{{NEXT_ITER}}** — 本轮假设 **未完整验证**, 还有新假设待跑
- [ ] **进入修复轮** — 本轮找到 root cause + 有 fix idea
- [ ] **终止 + 知会** — 假设 **推翻**, 上级 / 用户决策要不要继续
