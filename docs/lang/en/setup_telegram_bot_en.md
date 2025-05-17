# Setting Up Telegram Bot for SecureBot

This guide will walk you through the process of creating a Telegram bot and configuring it for use with SecureBot.

## Creating a Bot with BotFather

1. **Open Telegram** and search for `@BotFather` or click on this link: [BotFather](https://t.me/botfather)

2. **Start a conversation** with BotFather by clicking "Start" or sending `/start`

3. **Create a new bot** by sending the command:
   ```
   /newbot
   ```

4. **Choose a name** for your bot when prompted. This is the display name that will appear in conversations (e.g., "SecureBot Security Monitor")

5. **Choose a username** for your bot when prompted. This must end with "bot" and be unique (e.g., "your_security_bot" or "your_company_securebot")

6. **Save your API token!** BotFather will provide you with an API token that looks like:
   ```
   123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ
   ```
   This token is crucial for SecureBot configuration and should be kept secure.

## Getting Your Chat ID

### Method 1: Using @userinfobot

1. Search for `@userinfobot` on Telegram and start a conversation
2. The bot will automatically reply with your account information, including your Chat ID

### Method 2: Using @RawDataBot

1. Search for `@RawDataBot` on Telegram and start a conversation
2. The bot will send you a JSON message containing your information
3. Look for the `"id"` field in the "from" section to find your Chat ID

### Method 3: For Group Chats

If you want to receive notifications in a group:

1. Add your new bot to the group
2. Send a message in the group
3. Visit the following URL in your browser (replace with your bot's token):
   ```
   https://api.telegram.org/bot<YourBOTToken>/getUpdates
   ```
4. Look for `"chat":{"id":-123456789,` in the response. Note that group chat IDs are typically negative numbers

## Configuring Bot Permissions

For better security, you should configure these settings with BotFather:

1. Use the `/mybots` command in BotFather
2. Select your newly created bot
3. Click "Bot Settings" > "Group Privacy"
4. Select "Disable" if your bot needs to see all messages in a group, or keep "Enable" (recommended) if it only needs to see commands addressed to it
5. You can also set a description and about section for your bot from the Bot Settings menu

## Adding Bot Admin/Viewer Permissions in SecureBot

1. Determine the Telegram User IDs of administrators and viewers
2. Edit the SecureBot configuration file (either directly or via Ansible):

```toml
[telegram]
bot_token = "YOUR_BOT_TOKEN"  # The token from BotFather
chat_id = "YOUR_CHAT_ID"      # Your user ID or group chat ID
admin_users = [123456789]     # User IDs of administrators
viewer_users = [987654321]    # User IDs of viewers
```

## Testing Your Bot Configuration

1. After configuring SecureBot with your bot token and chat ID, start the SecureBot service:
   ```bash
   sudo systemctl start securebot
   ```

2. Open your Telegram client and send the following message to your bot:
   ```
   /start
   ```

3. Your bot should respond with a welcome message if everything is configured correctly

4. Test the basic commands:
   ```
   /help
   /status
   ```

## Troubleshooting

If your bot is not responding:

1. Check the SecureBot logs:
   ```bash
   sudo journalctl -u securebot
   ```

2. Verify that your bot token is correct in the configuration file
   
3. Make sure the SecureBot service is running:
   ```bash
   sudo systemctl status securebot
   ```

4. Check that your Telegram user ID is correctly set as an admin or viewer in the configuration

5. Ensure that your bot has sufficient permissions if used in a group

## Security Considerations

- Never share your bot token publicly
- Regularly rotate your bot token if you suspect it may have been compromised
- Only add trusted users to the admin_users list
- Consider limiting the bot to a private group rather than using it in public channels

## Next Steps

After successfully setting up your Telegram bot, proceed to configure the monitoring settings in SecureBot's configuration file to start receiving security notifications.
