# SSH Key 创建与配置

## 1. 生成 SSH Key

```bash
ssh-keygen -t ed25519 -C "fundou1081@outlook.com"
```

交互提示：
- **保存路径**：直接回车，用默认路径 `~/.ssh/id_ed25519`
- **passphrase**：设一个密码（也可以直接回车留空）

## 2. 复制公钥

```bash
cat ~/.ssh/id_ed25519.pub | pbcopy
```

## 3. 添加到 GitHub

1. 打开 https://github.com/settings/keys
2. 点击 **New SSH key**
3. Title 随便填，比如 `MacBook Air`
4. Key 粘贴刚才复制的内容
5. 点击 **Add SSH key**

## 4. 验证

```bash
ssh -T git@github.com
```

看到以下内容即成功：

```
Hi fundou1081! You've successfully authenticated, but GitHub does not provide shell access.
```

## 补充

- 公钥文件：`~/.ssh/id_ed25519.pub`
- 私钥文件：`~/.ssh/id_ed25519`（不要外传）
- 如果已有 key，可以跳过生成步骤，直接用现有的 `.pub` 文件添加
