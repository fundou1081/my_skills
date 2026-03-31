# my_skills

WorkBuddy Agent Skills 集合，统一版本管理。

## Skills

| Skill | 版本 | 说明 |
|---|---|---|
| [adr-recorder](adr-recorder/) | v1.0.0 | 架构决策记录（ADR）管理 |
| [methodology-compass](methodology-compass/) | v1.0.0 | 元方法论导航系统 |
| [report-maker](report-maker/) | v1.0.0 | 专业报告制作 |
| [triz](triz/) | v1.0.0 | TRIZ 发明问题解决理论 |
| [first-principles](first-principles/) | v1.0.0 | 第一性原理思维 |

## 同步规则

- **源目录**：`~/.workbuddy/skills/`
- **发布目录**：`~/my_skills/`
- **更新流程**：修改源目录 → 删旧版 → 重新复制 → commit & push

```bash
# 同步示例
for skill in adr-recorder methodology-compass report-maker triz first-principles; do
  rm -rf ~/my_skills/$skill
  cp -r ~/.workbuddy/skills/$skill ~/my_skills/
done
cd ~/my_skills && git add -A && git commit -m "update" && git push
```

## 协作工作流

```
第一性原理（定义问题）
  ↓
TRIZ（解决技术矛盾）
  ↓
methodology-compass（选择执行框架）
  ↓
report-maker（输出结构化报告）
  ↓
adr-recorder（记录架构决策）
```
