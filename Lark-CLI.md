# Lark CLI（飞书 CLI）

> 飞书/Lark 开放平台命令行工具，MIT 开源协议
> https://github.com/larksuite/cli

## 简介

字节跳动飞书官方开源的命令行工具，覆盖 11 大业务域，提供 200+ 精选命令，专为人类和 AI Agent 设计。支持 Claude Code、Cursor 等主流 Agent 工具直接调用。

## 覆盖业务域（11 个）

| 业务域 | 主要能力 |
|--------|---------|
| 📅 日历 | 查询日程、创建会议、忙闲查询、时间建议 |
| 💬 即时通讯 | 发消息、回复、管理群聊、搜索历史、下载媒体 |
| 📄 云文档 | CRUD 文档、Markdown ↔ 飞书文档互转 |
| 📁 云空间 | 上传/下载文件、搜索文档、管理评论 |
| 📊 多维表格 | 创建管理表格、字段/记录、视图、仪表盘 |
| 📈 电子表格 | 读写追加数据、数据查找、导出 |
| ✅ 任务 | 创建/查询/完成/更新任务、子任务、提醒 |
| 🧠 知识库 | 创建知识空间、维护知识节点 |
| 👥 通讯录 | 按姓名/邮箱/手机号搜索用户 |
| 📧 邮箱 | 收发邮件、搜索、草稿箱、新邮件通知 |
| 🎥 视频会议 | 会议记录、纪要、录制内容 |

## 安装 CLI

```bash
npm install -g @larksuite/cli
```

验证安装：

```bash
lark-cli --version
```

## 配置凭证

### 1. 创建飞书应用

1. 打开 [飞书开放平台](https://open.feishu.cn/app) → 创建应用
2. 获取 **App ID** 和 **App Secret**

### 2. 初始化配置

```bash
lark-cli config init --new
```

按提示输入 App ID 和 App Secret。

### 3. 登录授权

```bash
lark-cli auth login --recommend
```

支持浏览器扫码或链接授权。

## 常用命令示例

```bash
# 查看帮助
lark-cli --help

# 日历：查看今日日程
lark-cli calendar list --date today

# 消息：发送消息
lark-cli im message send --receiver user_id --content "Hello"

# 文档：创建文档
lark-cli doc create --title "周报"

# 任务：创建任务
lark-cli task create --title "完成报告" --due "2026-04-01"

# 通讯录：搜索用户
lark-cli contact search --keyword "张三"

# 邮件：发送邮件
lark-cli mail send --to user@example.com --subject "主题" --content "内容"
```

## AI Agent Skills（可选）

给 Claude Code 等 Agent 装上 19 个专用 Skills，开箱即用：

```bash
npx skills add larksuite/cli -y -g
```

装完后重启 Agent，即可通过自然语言操作飞书：
- "查看我今天有哪些会议"
- "给团队发一条周报通知"
- "创建下周的工作计划文档"

## 注意事项

- 需要 **Node.js** 环境
- 部分命令需要飞书应用开通对应权限（开放平台控制台配置）
- 敏感操作建议先在测试环境验证
