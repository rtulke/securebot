# SecureBot的Telegram机器人设置指南

本指南将引导您完成创建Telegram机器人并将其配置为与SecureBot一起使用的过程。

## 使用BotFather创建机器人

1. **打开Telegram**，搜索`@BotFather`或点击此链接：[BotFather](https://t.me/botfather)

2. **开始与BotFather对话**，点击"开始"或发送`/start`

3. **创建新机器人**，发送命令：
   ```
   /newbot
   ```

4. **为您的机器人选择一个名称**。这是将在对话中显示的名称（例如，"SecureBot安全监控"）

5. **为您的机器人选择一个用户名**。这必须以"bot"结尾且具有唯一性（例如，"your_security_bot"或"your_company_securebot"）

6. **保存您的API令牌！** BotFather将提供一个类似于这样的API令牌：
   ```
   123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ
   ```
   这个令牌对于SecureBot配置至关重要，应妥善保管。

## 获取您的聊天ID

### 方法1：使用@userinfobot

1. 在Telegram中搜索`@userinfobot`并开始对话
2. 机器人将自动回复包含您的聊天ID在内的账户信息

### 方法2：使用@RawDataBot

1. 在Telegram中搜索`@RawDataBot`并开始对话
2. 机器人将发送包含您信息的JSON消息
3. 在"from"部分中查找`"id"`字段以找到您的聊天ID

### 方法3：对于群组聊天

如果您希望在群组中接收通知：

1. 将您的新机器人添加到群组
2. 在群组中发送一条消息
3. 在浏览器中访问以下URL（替换为您的机器人令牌）：
   ```
   https://api.telegram.org/bot<您的机器人令牌>/getUpdates
   ```
4. 在响应中查找`"chat":{"id":-123456789,`。请注意，群组聊天ID通常是负数

## 配置机器人权限

为了更好的安全性，您应该通过BotFather配置这些设置：

1. 在BotFather中使用`/mybots`命令
2. 选择您新创建的机器人
3. 点击"Bot Settings" > "Group Privacy"
4. 如果您的机器人需要查看群组中的所有消息，选择"Disable"；如果它只需要查看直接发给它的命令，保持"Enable"（推荐）
5. 您还可以从机器人设置菜单为您的机器人设置描述和关于部分

## 在SecureBot中添加管理员/查看者权限

1. 确定管理员和查看者的Telegram用户ID
2. 编辑SecureBot配置文件（直接编辑或通过Ansible）：

```toml
[telegram]
bot_token = "您的机器人令牌"  # 来自BotFather的令牌
chat_id = "您的聊天ID"       # 您的用户ID或群组聊天ID
admin_users = [123456789]    # 管理员用户的用户ID
viewer_users = [987654321]   # 查看者的用户ID
```

## 测试您的机器人配置

1. 使用您的机器人令牌和聊天ID配置SecureBot后，启动SecureBot服务：
   ```bash
   sudo systemctl start securebot
   ```

2. 打开Telegram客户端，向您的机器人发送以下消息：
   ```
   /start
   ```

3. 如果一切配置正确，您的机器人应该会回复一条欢迎消息

4. 测试基本命令：
   ```
   /help
   /status
   ```

## 故障排除

如果您的机器人没有响应：

1. 检查SecureBot日志：
   ```bash
   sudo journalctl -u securebot
   ```

2. 验证配置文件中的机器人令牌是否正确
   
3. 确保SecureBot服务正在运行：
   ```bash
   sudo systemctl status securebot
   ```

4. 检查您的Telegram用户ID是否在配置中正确设置为管理员或查看者

5. 如果在群组中使用，确保您的机器人具有足够的权限

## 安全考虑

- 切勿公开分享您的机器人令牌
- 如果您怀疑令牌可能已被泄露，请定期更换
- 只将受信任的用户添加到admin_users列表中
- 考虑将机器人限制在私人群组中，而不是在公共频道中使用

## 后续步骤

成功设置Telegram机器人后，继续配置SecureBot配置文件中的监控设置，开始接收安全通知。
