# SecureBot - Telegram Security Bot

A Telegram bot for monitoring SSH logins and managing fail2ban across multiple systems.

## Features

- Monitor SSH logins locally and on remote servers
- Track fail2ban events (bans/unbans)
- Manage fail2ban (list jails, ban/unban IPs)
- Remote server monitoring via SSH
- Real-time notifications
- Configurable notification settings
- Access control (admin/viewer roles)

## Requirements

- Python 3.8+
- Fail2ban
- Telegram Bot Token

## Preconditions Setup Telegram Bot

Before we start installing the bot, you need a API Token within Telegram which we will use later for the configuration.

Read the following instructions if you don't know what to do ;-).

- [Telegram Bot Setup (English)](docs/setup_telegram_bot_en.md)
- [Telegram Bot Setup (Deutsch)](docs/setup_telegram_bot_de.md)
- [Telegram Bot Setup (Español)](docs/setup_telegram_bot_es.md)
- [Telegram Bot Setup (Française)](docs/setup_telegram_bot_fr.md)
- [Telegram Bot Setup (Português)](docs/setup_telegram_bot_pt.md)
- [Telegram Bot Setup (Italiano)](docs/setup_telegram_bot_it.md)
- [Telegram Bot Setup (Русский)](docs/setup_telegram_bot_ru.md)
- [Telegram Bot Setup (اللغة العربية)](docs/setup_telegram_bot_ar.md)
- [Telegram Bot Setup (机器人设置指南（中文）)](docs/setup_telegram_bot_zh.md)
- [Telegram Bot Setup (टेलीग्राम बॉट सेटअप गाइड (हिंदी))](docs/setup_telegram_bot_hi.md)
- [Telegram Bot Setup (ボットセットアップガイド（日本語）)](docs/setup_telegram_bot_ja.md)

Read also the documentation about Telegram.
- [Telegram](https://telegram.org)
- [Download App](https://telegram.org/apps)
- [Telegram API](https://telegram.org/api)

## Installation

### Using the Ansible Playbook (Recommended)

Install Ansible & Git on your device if you want to deploy to your local system

## Preconditions for debian based OS

So that you can automatically install the securebot on your local or other Linux servers with the Ansible role, you first need the packages `ansible` and `git` on your workstation. You also have the option of installing SecureBot on the same workstation.

1. Install packages on you workstation or server:
   ```bash
   sudo apt update && apt upgrade
   sudo apt install ansible git -y
   ```

2. Clone this repository:
   ```bash
   git clone https://github.com/rtulke/securebot.git
   cd securebot
   ```

3. Edit the `inventory.yml` file to specify your servers:
   ```yaml
   all:
     hosts:
       localhost:
         ansible_connection: local             # For local installation on the same host
     ## Activate this part if you want to install on other computers:
     # web_server:
     #   ansible_host: webserver.example.com
     #   ansible_user: admin                   # The user requires extended authorizations p.e. /etc/sudoers so that he can carry out the automatic configuration.
     # db_server:
     #   ansible_host: db.example.com
     #   ansible_user: admin                   # The user requires extended authorizations p.e. /etc/sudoers so that he can carry out the automatic configuration.
   ```

3. Edit the `group_vars/all.yml` file to customize your deployment:
   ```yaml
   telegram_bot_token: "YOUR_BOT_TOKEN"
   telegram_chat_id: "YOUR_CHAT_ID"
   admin_users:
     - 123456789 # Your Telegram User ID
   ```

4. Run the Ansible playbook:
   ```bash
   ansible-playbook -i inventory.yml deploy.yml
   ```

### Manual Installation (on one single system or for multiple systems)

1. Install required packages:
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-venv fail2ban
   ```

2. Create a dedicated user for securebot:
   ```bash
   sudo useradd -r -s /bin/false securebot
   sudo mkdir -p /etc/securebot/keys
   sudo mkdir -p /var/lib/securebot
   ```

3. Set up a Python virtual environment:
   ```bash
   sudo python3 -m venv /var/lib/securebot/venv
   sudo /var/lib/securebot/venv/bin/pip install --upgrade pip
   sudo /var/lib/securebot/venv/bin/pip install -r requirements.txt
   ```

4. Generate a configuration file:
   ```bash
   sudo /var/lib/securebot/venv/bin/python securebot.py -g -c /etc/securebot.conf
   ```

5. Edit the configuration file:
   ```bash
   sudo nano /etc/securebot.conf
   ```

6. Create SSH keys for remote access:
   ```bash
   sudo -u securebot ssh-keygen -t ed25519 -f /etc/securebot/keys/securebot_key -N ""
   ```

7. Create a systemd service file:
   ```bash
   sudo nano /etc/systemd/system/securebot.service
   ```
   
   Add the following content:
   ```
   [Unit]
   Description=SecureBot a Telegram Security Bot
   After=network.target

   [Service]
   Type=simple
   User=securebot
   Group=securebot
   ExecStart=/var/lib/securebot/venv/bin/python /usr/local/sbin/securebot -d -c /etc/securebot.conf
   Restart=on-failure
   RestartSec=5s

   [Install]
   WantedBy=multi-user.target
   ```

8. Install the SecureBot script:
   ```bash
   sudo cp securebot.py /usr/local/sbin/securebot
   sudo chmod +x /usr/local/sbin/securebot
   sudo chown securebot:securebot /usr/local/sbin/securebot
   ```

9. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable securebot
   sudo systemctl start securebot
   ```

## Configuration

SecureBot uses a TOML configuration file. A default configuration can be generated with:

```bash
securebot.py -g
```

### Configuration File Structure

```toml
[general]
local_only = false
log_level = "INFO"  # DEBUG, INFO, WARNING, ERROR
notification_delay = 10  # Seconds between notifications

[telegram]
bot_token = "YOUR_BOT_TOKEN"
chat_id = "YOUR_CHAT_ID"
admin_users = [123456789, 987654321]  # Telegram User IDs
viewer_users = []  # View-only access

[local]
ssh_log = "/var/log/auth.log"
fail2ban_log = "/var/log/fail2ban.log"
audit_log = "/var/log/audit/audit.log"

[servers]
  [servers.webserver]
  hostname = "webserver.example.com"
  ip = "192.168.1.10"
  ssh_user = "monitor"
  ssh_key_path = "/etc/securebot/keys/webserver_key"
  ssh_port = 22
  host_key_path = "/etc/securebot/known_hosts/webserver"
  logs = { ssh = "/var/log/auth.log", fail2ban = "/var/log/fail2ban.log" }

[notifications]
ssh_login = true
fail2ban_block = true
server_unreachable = true

[customization]
date_format = "%Y-%m-%d %H:%M:%S"
resolve_hostnames = true
show_ipinfo_link = true
```

## Command Line Options

```
-d, --daemon          Run as a daemon
-c, --config FILE     Specify the configuration file
-g, --generate-config Generate a default configuration file
-v, --verbose         Increase verbosity
-t, --test            Run in test mode (no actual actions)
--version             Show version information
-l, --log FILE        Specify a log file
--setup               Run interactive setup
```

## Telegram Commands

- `/help` - Show help information
- `/status` - Show status of all monitored servers
- `/login_history [n]` - Show the last n login events
- `/server list` - List all configured servers
- `/server status NAME` - Show status of a specific server
- `/mute [minutes]` - Mute notifications temporarily
- `/unmute` - Unmute notifications

Admin commands:
- `/fail2ban list [server]` - List fail2ban jails
- `/fail2ban status JAIL [server]` - Show banned IPs in a jail
- `/fail2ban ban IP JAIL [server]` - Ban an IP in a jail
- `/fail2ban unban IP JAIL [server]` - Unban an IP from a jail

## Remote Server Setup

To monitor remote servers:

1. Create a monitor user on the remote server:
   ```bash
   sudo useradd -r -m -s /bin/bash monitor
   ```

2. Set up sudo permissions for fail2ban commands:
   ```bash
   echo "monitor ALL=NOPASSWD: /usr/bin/fail2ban-client status, /usr/bin/fail2ban-client status *" | sudo tee /etc/sudoers.d/monitor-fail2ban
   ```

3. Add SecureBot's SSH key to the remote server:
   ```bash
   sudo mkdir -p /home/monitor/.ssh
   sudo cat /path/to/securebot_key.pub >> /home/monitor/.ssh/authorized_keys
   sudo chown -R monitor:monitor /home/monitor/.ssh
   sudo chmod 700 /home/monitor/.ssh
   sudo chmod 600 /home/monitor/.ssh/authorized_keys
   ```

## Security Considerations

- The monitor user on remote servers should have minimal permissions
- Restrict the bot to only authorized Telegram users
- Regularly update SSH keys
- Consider using IP restrictions for SSH access
- Review fail2ban logs periodically

## Troubleshooting

- Check the logs: `journalctl -u securebot`
- Verify the bot can connect to Telegram API
- Ensure proper permissions for log files
- Test SSH connections manually
- Validate the configuration file
