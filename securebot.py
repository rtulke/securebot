#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SecureBot - Telegram Security Bot
A Telegram bot for monitoring SSH logins and managing fail2ban
"""

import os
import sys
import argparse
import logging
import signal
import time
import re
import socket
import json
import asyncio
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Set
import tomli
import tomli_w
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes, 
    CallbackContext,
    MessageHandler,
    filters
)
import paramiko
import pyinotify

__version__ = "1.0.1"

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "general": {
        "local_only": False,
        "log_level": "INFO",
        "notification_delay": 10
    },
    "telegram": {
        "bot_token": "YOUR_BOT_TOKEN",
        "chat_id": "YOUR_CHAT_ID",
        "admin_users": [],
        "viewer_users": []
    },
    "permanent_bans": {
        
    },  
    "local": {
        "ssh_log": "/var/log/auth.log",
        "fail2ban_log": "/var/log/fail2ban.log",
        "audit_log": "/var/log/audit/audit.log"
    },
    "servers": {
        "example_server": {
            "hostname": "server.example.com",
            "ip": "192.168.1.10",
            "ssh_user": "monitor",
            "ssh_key_path": "/etc/securebot/keys/server_key",
            "ssh_port": 22,
            "host_key_path": "/etc/securebot/known_hosts/server",
            "logs": {
                "ssh": "/var/log/auth.log",
                "fail2ban": "/var/log/fail2ban.log"
            }
        }
    },
    "notifications": {
        "ssh_login": True,
        "fail2ban_block": True,
        "server_unreachable": True
    },
    "customization": {
        "date_format": "%Y-%m-%d %H:%M:%S",
        "resolve_hostnames": True,
        "show_ipinfo_link": True
    }
}

# Global variables
CONFIG = {}
BOT_INSTANCE = None
NOTIFICATION_MUTED = False
MUTE_UNTIL = 0
SSH_CLIENTS = {}
WATCH_MANAGERS = {}
NOTIFIERS = {}
KNOWN_EVENTS = set()
RUNNING = True


class NetworkUtils:
    """Network-related utility functions"""
    
    @staticmethod
    async def get_ip_info(ip: str) -> Dict[str, Any]:
        """Get detailed information about an IP address using ipinfo.io"""
        url = f"https://ipinfo.io/{ip}/json"
        
        try:
            # Verwende httpx, da es bereits für Telegram verwendet wird
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                
            if response.status_code == 200:
                data = response.json()
                # Erweitere mit Emoji-Flagge, wenn Land verfügbar
                if "country" in data:
                    country_code = data["country"]
                    # Konvertiere Ländercode zu Emoji-Flagge (Unicode-Trick)
                    flag = "".join(chr(ord(c) + 127397) for c in country_code)
                    data["flag"] = flag
                return data
            else:
                logger.warning(f"Failed to get IP info for {ip}: Status code {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error getting IP info: {e}")
            return {}

class DateUtils:
    """Date and time utility functions"""
    
    @staticmethod
    def format_timestamp(timestamp: str) -> str:
        """Format a timestamp according to configuration"""
        try:
            # check if timestamp is in the format YYYY-MM-DD HH:MM:SS,sss
            if ',' in timestamp:  # 2025-05-18 17:36:28,767
                dt_format = "%Y-%m-%d %H:%M:%S,%f"
             
                if timestamp.split(',')[1] and len(timestamp.split(',')[1]) > 3:
                    timestamp = timestamp.split(',')[0] + ',' + timestamp.split(',')[1][:3]
            else:  # May 18 17:36:28
                dt_format = "%b %d %H:%M:%S"
            
            # convert to datetime object
            dt = datetime.datetime.strptime(timestamp, dt_format)
            
            # uee custom date format from config
            custom_format = CONFIG.get("customization", {}).get("date_format", "%d. %B %Y, %H:%M:%S")
            return dt.strftime(custom_format)
        except Exception as e:
            logger.warning(f"Failed to format timestamp {timestamp}: {e}")
            return timestamp  # return original timestamp if formatting fails

class ConfigManager:
    """Handle configuration loading, saving and validation"""
    
    @staticmethod
    def load_config(config_path: str) -> dict:
        """Load configuration from a TOML file"""
        try:
            with open(config_path, "rb") as f:
                config = tomli.load(f)
                logger.info(f"Configuration loaded from {config_path}")
                return config
        except FileNotFoundError:
            logger.warning(f"Configuration file {config_path} not found")
            return {}
        except tomli.TOMLDecodeError as e:
            logger.error(f"Error parsing configuration file: {e}")
            return {}
    
    @staticmethod
    def save_config(config: dict, config_path: str) -> bool:
        """Save configuration to a TOML file"""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, "wb") as f:
                tomli_w.dump(config, f)
                logger.info(f"Configuration saved to {config_path}")
            
            # Set proper permissions for the config file
            if config_path.startswith('/etc/'):
                subprocess.run(['sudo', 'chmod', '640', config_path], check=True)
                subprocess.run(['sudo', 'chown', 'root:securebot', config_path], check=True)
            else:
                os.chmod(config_path, 0o600)  # Only user can read/write
            
            return True
        except Exception as e:
            logger.error(f"Error saving configuration file: {e}")
            return False
    
    @staticmethod
    def validate_config(config: dict) -> Tuple[bool, List[str]]:
        """Validate configuration structure and essential values"""
        errors = []
        
        # Check for required top-level sections
        required_sections = ["general", "telegram", "local"]
        for section in required_sections:
            if section not in config:
                errors.append(f"Missing required section: {section}")
        
        # Validate telegram section
        if "telegram" in config:
            if not config["telegram"].get("bot_token") or config["telegram"]["bot_token"] == "YOUR_BOT_TOKEN":
                errors.append("Telegram bot token is not configured")
            if not config["telegram"].get("chat_id") or config["telegram"]["chat_id"] == "YOUR_CHAT_ID":
                errors.append("Telegram chat ID is not configured")
        
        # Validate servers section if not local_only
        if "general" in config and not config["general"].get("local_only", False):
            if "servers" not in config or not config["servers"]:
                errors.append("No servers defined while local_only is False")
            else:
                for server_name, server_config in config["servers"].items():
                    required_server_keys = ["hostname", "ssh_user", "ssh_key_path"]
                    for key in required_server_keys:
                        if key not in server_config:
                            errors.append(f"Missing required key {key} for server {server_name}")
        
        return len(errors) == 0, errors

    @staticmethod
    def generate_config() -> dict:
        """Generate a default configuration"""
        return DEFAULT_CONFIG.copy()

class SSHManager:
    """Manage SSH connections to remote servers"""
    
    @staticmethod
    async def connect_to_server(server_name: str, server_config: dict) -> Optional[paramiko.SSHClient]:
        """Establish SSH connection to a remote server"""
        try:
            client = paramiko.SSHClient()
            
            # Set up host key policy
            if os.path.exists(server_config["host_key_path"]):
                client.load_host_keys(server_config["host_key_path"])
            else:
                # If no host keys found, use system known_hosts or auto-add
                client.load_system_host_keys()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to the server
            client.connect(
                hostname=server_config["hostname"],
                port=server_config.get("ssh_port", 22),
                username=server_config["ssh_user"],
                key_filename=server_config["ssh_key_path"],
                timeout=10
            )
            
            logger.info(f"Successfully connected to {server_name}")
            return client
        except paramiko.AuthenticationException:
            logger.error(f"Authentication failed for {server_name}")
        except paramiko.SSHException as e:
            logger.error(f"SSH error for {server_name}: {e}")
        except socket.timeout:
            logger.error(f"Connection timeout for {server_name}")
        except Exception as e:
            logger.error(f"Error connecting to {server_name}: {e}")
        
        # Notify about connection failure if configured
        if CONFIG["notifications"].get("server_unreachable", True):
            await notify_telegram(f"⚠️ Could not connect to server {server_name}")
        
        return None
    
    @staticmethod
    async def execute_command(
        server_name: str, 
        command: str, 
        client: Optional[paramiko.SSHClient] = None
    ) -> Tuple[bool, str]:
        """Execute command on remote server"""
        close_after = False
        
        try:
            # Wenn server_name 'localhost' oder None ist, führe lokal aus
            if server_name is None or server_name == "localhost":
                try:
                    result = subprocess.check_output(
                        command, 
                        shell=True, 
                        text=True,
                        stderr=subprocess.PIPE
                    ).strip()
                    return True, result
                except subprocess.CalledProcessError as e:
                    error_msg = e.stderr.strip() if hasattr(e, 'stderr') and e.stderr else str(e)
                    logger.error(f"Error executing local command: {error_msg}")
                    return False, error_msg
            
            # Für entfernte Server
            if client is None:
                if server_name not in CONFIG["servers"]:
                    return False, f"Unknown server: {server_name}"
                
                client = await SSHManager.connect_to_server(
                    server_name, 
                    CONFIG["servers"][server_name]
                )
                close_after = True
                
                if client is None:
                    return False, f"Could not connect to {server_name}"
            
            # Execute the command
            stdin, stdout, stderr = client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                result = stdout.read().decode('utf-8').strip()
                return True, result
            else:
                error = stderr.read().decode('utf-8').strip()
                logger.error(f"Command failed on {server_name}: {error}")
                return False, error
        
        except Exception as e:
            logger.error(f"Error executing command on {server_name}: {e}")
            return False, str(e)
        
        finally:
            if close_after and client:
                client.close()
    
    @staticmethod
    async def get_file_content(
        server_name: str, 
        file_path: str, 
        client: Optional[paramiko.SSHClient] = None
    ) -> Tuple[bool, str]:
        """Get content of a file from remote server"""
        close_after = False
        
        try:
            # If no client provided, establish a new connection
            if client is None:
                if server_name not in CONFIG["servers"]:
                    return False, f"Unknown server: {server_name}"
                
                client = await SSHManager.connect_to_server(
                    server_name, 
                    CONFIG["servers"][server_name]
                )
                close_after = True
                
                if client is None:
                    return False, f"Could not connect to {server_name}"
            
            # Get the file content
            sftp = client.open_sftp()
            with sftp.open(file_path, 'r') as f:
                content = f.read().decode('utf-8')
            
            return True, content
        
        except Exception as e:
            logger.error(f"Error getting file content from {server_name}: {e}")
            return False, str(e)
        
        finally:
            if close_after and client:
                client.close()
    
    @staticmethod
    async def tail_file(
        server_name: str, 
        file_path: str, 
        lines: int = 10, 
        client: Optional[paramiko.SSHClient] = None
    ) -> Tuple[bool, str]:
        """Get the last n lines of a file from remote server"""
        return await SSHManager.execute_command(
            server_name, 
            f"tail -n {lines} {file_path}", 
            client
        )

class Fail2BanManager:
    """Manage fail2ban operations"""
    @staticmethod
    async def ban_ip_permanently(ip: str, reason: str = "Manual permanent ban", user_id: int = None) -> Tuple[bool, str]:
        """Ban an IP permanently across all servers and jails"""
        logger.info(f"Banning IP {ip} permanently")
        
        # Speichere in Konfiguration
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if "permanent_bans" not in CONFIG:
            CONFIG["permanent_bans"] = {}
        
        CONFIG["permanent_bans"][ip] = {
            "timestamp": timestamp,
            "reason": reason,
            "banned_by": user_id
        }
        
        # Konfiguration speichern
        config_path = os.environ.get("SECUREBOT_CONFIG", "/etc/securebot.conf")
        ConfigManager.save_config(CONFIG, config_path)
        
        # IP in allen lokalen Jails sperren
        success = True
        error_messages = []
        
        # 1. Lokale Jails
        local_success, jails = await Fail2BanManager.list_jails()
        if local_success and jails:
            for jail in jails:
                ban_success, result = await Fail2BanManager.ban_ip(ip, jail)
                if not ban_success:
                    success = False
                    error_messages.append(f"Failed to ban in local jail {jail}: {result}")
        
        # 2. Remote Server Jails
        if not CONFIG["general"].get("local_only", False) and "servers" in CONFIG:
            for server_name, server_config in CONFIG["servers"].items():
                server_success, server_jails = await Fail2BanManager.list_jails(server_name)
                if server_success and server_jails:
                    for jail in server_jails:
                        ban_success, result = await Fail2BanManager.ban_ip(ip, jail, server_name)
                        if not ban_success:
                            success = False
                            error_messages.append(f"Failed to ban in {server_name} jail {jail}: {result}")
        
        # Optional: Zusätzlich iptables-Regel für noch robustere Sperrung hinzufügen
        try:
            command = f"sudo iptables -A INPUT -s {ip} -j DROP"
            subprocess.check_output(command, shell=True, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Could not add iptables rule for {ip}: {e}")
        
        if success:
            return True, f"Successfully banned {ip} permanently across all servers and jails"
        else:
            return False, f"Partial permanent ban for {ip}. Errors: {', '.join(error_messages)}"
    
    @staticmethod
    async def list_permanent_bans() -> Dict[str, Dict[str, Any]]:
        """List all permanent bans"""
        return CONFIG.get("permanent_bans", {})
    
    @staticmethod
    async def remove_permanent_ban(ip: str) -> Tuple[bool, str]:
        """Remove a permanent ban"""
        if "permanent_bans" not in CONFIG or ip not in CONFIG["permanent_bans"]:
            return False, f"IP {ip} is not permanently banned"
        
        # Aus Konfiguration entfernen
        del CONFIG["permanent_bans"][ip]
        
        # Konfiguration speichern
        config_path = os.environ.get("SECUREBOT_CONFIG", "/etc/securebot.conf")
        ConfigManager.save_config(CONFIG, config_path)
        
        # Optional: iptables-Regel entfernen
        try:
            command = f"sudo iptables -D INPUT -s {ip} -j DROP"
            subprocess.check_output(command, shell=True, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            pass
        
        return True, f"Removed permanent ban for {ip}"

    @staticmethod
    async def ensure_permanent_bans() -> Tuple[bool, str]:
        """Ensure all permanent bans are active across all systems"""
        logger.info("Verifying permanent bans are active")
        
        if "permanent_bans" not in CONFIG or not CONFIG["permanent_bans"]:
            logger.info("No permanent bans configured")
            return True, "No permanent bans configured"
        
        success = True
        errors = []
        
        # Re-apply all permanent bans
        for ip, ban_data in CONFIG["permanent_bans"].items():
            logger.info(f"Ensuring IP {ip} is banned (reason: {ban_data.get('reason', 'Permanent ban')})")
            
            # 1. Lokale Jails
            local_success, jails = await Fail2BanManager.list_jails()
            if local_success and jails:
                for jail in jails:
                    ban_success, result = await Fail2BanManager.ban_ip(ip, jail)
                    if not ban_success:
                        success = False
                        errors.append(f"Failed to ban in local jail {jail}: {result}")
            
            # 2. Remote Server Jails
            if not CONFIG["general"].get("local_only", False) and "servers" in CONFIG:
                for server_name, server_config in CONFIG["servers"].items():
                    server_success, server_jails = await Fail2BanManager.list_jails(server_name)
                    if server_success and server_jails:
                        for jail in server_jails:
                            ban_success, result = await Fail2BanManager.ban_ip(ip, jail, server_name)
                            if not ban_success:
                                success = False
                                errors.append(f"Failed to ban in {server_name} jail {jail}: {result}")
            
            # 3. Optional: iptables-Regel hinzufügen
            try:
                command = f"sudo iptables -A INPUT -s {ip} -j DROP"
                subprocess.check_output(command, shell=True, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                logger.warning(f"Could not add iptables rule for {ip}: {e}")
        
        if success:
            return True, "Successfully verified all permanent bans"
        else:
            return False, f"Errors while verifying permanent bans: {', '.join(errors)}"
    
    # command /fail2ban all
    @staticmethod
    async def get_all_banned_ips(server_name: Optional[str] = None) -> Dict[str, List[str]]:
        """Get all banned IPs from all jails"""
        success, jails = await Fail2BanManager.list_jails(server_name)
        
        if not success or not jails:
            return {}
        
        results = {}
        for jail in jails:
            success, ips = await Fail2BanManager.get_banned_ips(jail, server_name)
            if success and ips:
                results[jail] = ips
        
        return results 
    
    # command /fail2ban list
    @staticmethod
    async def list_jails(server_name: Optional[str] = None) -> Tuple[bool, List[str]]:
        """List all fail2ban jails"""
        command = "sudo fail2ban-client status | grep 'Jail list' | sed -E 's/^[^:]+:[ \t]+//g'"
        
        if server_name:
            success, result = await SSHManager.execute_command(server_name, command)
        else:
            # Execute locally
            try:
                result = subprocess.check_output(
                    command, 
                    shell=True, 
                    text=True
                ).strip()
                success = True
            except subprocess.CalledProcessError as e:
                logger.error(f"Error listing fail2ban jails: {e}")
                success = False
                result = str(e)
        
        if not success:
            return False, []
        
        # Parse the comma-separated list of jails
        jails = [jail.strip() for jail in result.split(",")]
        return True, jails
    
    # command /fail2ban status JAIL
    @staticmethod
    async def get_banned_ips(jail: str, server_name: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Get list of IPs banned in a specific jail"""
        command = f"sudo fail2ban-client status {jail} | grep 'Banned IP list' | sed -E 's/^[^:]+:[ \t]+//g'"
        
        if server_name:
            success, result = await SSHManager.execute_command(server_name, command)
        else:
            # Execute locally
            try:
                result = subprocess.check_output(
                    command, 
                    shell=True, 
                    text=True
                ).strip()
                success = True
            except subprocess.CalledProcessError as e:
                logger.error(f"Error getting banned IPs for jail {jail}: {e}")
                success = False
                result = str(e)
        
        if not success:
            return False, []
        
        # Parse the space-separated list of IPs
        if not result:
            return True, []
            
        ips = [ip.strip() for ip in result.split()]
        return True, ips
    
    # command /fail2ban banip IP JAIL
    @staticmethod
    async def ban_ip(ip: str, jail: str, server_name: Optional[str] = None) -> Tuple[bool, str]:
        """Ban an IP in a specific jail"""
        command = f"sudo fail2ban-client set {jail} banip {ip}"
        
        if server_name:
            return await SSHManager.execute_command(server_name, command)
        else:
            # Execute locally
            try:
                subprocess.check_output(command, shell=True, text=True)
                return True, f"Successfully banned {ip} in {jail}"
            except subprocess.CalledProcessError as e:
                logger.error(f"Error banning IP {ip} in jail {jail}: {e}")
                return False, str(e)
    
    # command /fail2ban unbanip IP JAIL
    @staticmethod
    async def unban_ip(ip: str, jail: str, server_name: Optional[str] = None) -> Tuple[bool, str]:
        """Unban an IP from a specific jail"""
        command = f"sudo fail2ban-client set {jail} unbanip {ip}"
        logger.debug(f"Executing command: {command}")
        
        if server_name:
            return await SSHManager.execute_command(server_name, command)
        else:
            # Execute locally (direkt ausführen, nicht über SSH-Manager)
            try:
                output = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.PIPE)
                logger.info(f"Successfully unbanned {ip} from {jail}")
                return True, f"Successfully unbanned {ip} from {jail}"
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.strip() if e.stderr else str(e)
                logger.error(f"Error unbanning IP {ip} from jail {jail}: {error_msg}")
                return False, error_msg

class LogParser:
    """Parse various log formats"""
    
    # SSH Login Pattern
    SSH_LOGIN_PATTERN = re.compile(
        r'(\w{3}\s+\d+\s+\d+:\d+:\d+).*sshd\[\d+\]:\s+Accepted\s+(?:publickey|password|keyboard-interactive/pam)\s+for\s+(\S+)\s+from\s+(\S+)'
    )
    
    # fail2ban Patterns old and new
    FAIL2BAN_BAN_PATTERN_OLD = re.compile(
        r'(\w{3}\s+\d+\s+\d+:\d+:\d+).*fail2ban\.actions\[\d+\]:\s+NOTICE\s+\[([^\]]+)\]\s+Ban\s+(\S+)'
    )
    
    FAIL2BAN_BAN_PATTERN_NEW = re.compile(
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+)\s+fail2ban\.actions\s+\[\d+\]:\s+NOTICE\s+\[([^\]]+)\]\s+Ban\s+(\S+)'
    )
    
    # Unban Patterns old and new
    FAIL2BAN_UNBAN_PATTERN_OLD = re.compile(
        r'(\w{3}\s+\d+\s+\d+:\d+:\d+).*fail2ban\.actions\[\d+\]:\s+NOTICE\s+\[([^\]]+)\]\s+Unban\s+(\S+)'
    )
    
    FAIL2BAN_UNBAN_PATTERN_NEW = re.compile(
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+)\s+fail2ban\.actions\s+\[\d+\]:\s+NOTICE\s+\[([^\]]+)\]\s+Unban\s+(\S+)'
    )
    
    # Already Banned Patterns old and new
    FAIL2BAN_ALREADY_BANNED_PATTERN_OLD = re.compile(
        r'(\w{3}\s+\d+\s+\d+:\d+:\d+).*fail2ban\.actions\[\d+\]:\s+(?:NOTICE|WARNING)\s+\[([^\]]+)\]\s+(\S+)\s+already\s+banned'
    )
    
    FAIL2BAN_ALREADY_BANNED_PATTERN_NEW = re.compile(
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+)\s+fail2ban\.actions\s+\[\d+\]:\s+(?:NOTICE|WARNING)\s+\[([^\]]+)\]\s+(\S+)\s+already\s+banned'
    )
    
    # Found IP Patterns old and new
    FAIL2BAN_FOUND_IP_PATTERN_OLD = re.compile(
        r'(\w{3}\s+\d+\s+\d+:\d+:\d+).*fail2ban\.filter\[\d+\]:\s+INFO\s+\[([^\]]+)\]\s+Found\s+(\S+)\s+-\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}'
    )
    
    FAIL2BAN_FOUND_IP_PATTERN_NEW = re.compile(
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+)\s+fail2ban\.filter\s+\[\d+\]:\s+INFO\s+\[([^\]]+)\]\s+Found\s+(\S+)\s+-\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}'
    )
    
    
    @staticmethod
    async def parse_ssh_log_line(line: str, server_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Parse SSH log line for successful logins"""
        match = LogParser.SSH_LOGIN_PATTERN.match(line)
        if not match:
            return None
        
        timestamp, username, ip = match.groups()
        
        # Create a unique event ID to prevent duplicate notifications
        event_id = f"ssh_login_{server_name}_{ip}_{username}_{timestamp}"
        if event_id in KNOWN_EVENTS:
            return None
        
        KNOWN_EVENTS.add(event_id)
        
        # Resolve hostname if configured
        hostname = None
        if CONFIG["customization"].get("resolve_hostnames", True):
            try:
                hostname = socket.gethostbyaddr(ip)[0]
            except (socket.herror, socket.gaierror):
                hostname = None
        
        event = {
            "type": "ssh_login",
            "timestamp": timestamp,
            "username": username,
            "ip": ip,
            "hostname": hostname,
            "server": server_name or "localhost"
        }
        
        return event
    
    @staticmethod
    async def parse_fail2ban_log_line(line: str, server_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Parse fail2ban log line for ban/unban events"""
        ban_match_old = LogParser.FAIL2BAN_BAN_PATTERN_OLD.match(line)
        ban_match_new = LogParser.FAIL2BAN_BAN_PATTERN_NEW.match(line)
        unban_match_old = LogParser.FAIL2BAN_UNBAN_PATTERN_OLD.match(line)
        unban_match_new = LogParser.FAIL2BAN_UNBAN_PATTERN_NEW.match(line)
        already_banned_old = LogParser.FAIL2BAN_ALREADY_BANNED_PATTERN_OLD.match(line)
        already_banned_new = LogParser.FAIL2BAN_ALREADY_BANNED_PATTERN_NEW.match(line)
        found_ip_old = LogParser.FAIL2BAN_FOUND_IP_PATTERN_OLD.match(line)
        found_ip_new = LogParser.FAIL2BAN_FOUND_IP_PATTERN_NEW.match(line)
        
        if ban_match_old:
            timestamp, jail, ip = ban_match_old.groups()
            event_type = "ban"
        elif ban_match_new:
            timestamp, jail, ip = ban_match_new.groups()
            event_type = "ban"
        elif unban_match_old:
            timestamp, jail, ip = unban_match_old.groups()
            event_type = "unban"
        elif unban_match_new:
            timestamp, jail, ip = unban_match_new.groups()
            event_type = "unban"
        elif already_banned_old:
            timestamp, jail, ip = already_banned_old.groups()
            event_type = "already_banned"
        elif already_banned_new:
            timestamp, jail, ip = already_banned_new.groups()
            event_type = "already_banned"
        elif found_ip_old:
            timestamp, jail, ip = found_ip_old.groups()
            event_type = "found"
        elif found_ip_new:
            timestamp, jail, ip = found_ip_new.groups()
            event_type = "found"
        else:
            logger.debug(f"No match for fail2ban log line: {line}")
            return None
        
        # Create a unique event ID to prevent duplicate notifications
        event_id = f"fail2ban_{event_type}_{server_name}_{ip}_{jail}_{timestamp}"
        if event_id in KNOWN_EVENTS:
            logger.debug(f"Duplicate event skipped: {event_id}")
            return None
        
        KNOWN_EVENTS.add(event_id)
        logger.debug(f"New event detected: {event_id}")
        
        # Resolve hostname if configured
        hostname = None
        if CONFIG["customization"].get("resolve_hostnames", True):
            try:
                hostname = socket.gethostbyaddr(ip)[0]
            except (socket.herror, socket.gaierror):
                pass
        
        event = {
            "type": f"fail2ban_{event_type}",
            "timestamp": timestamp,
            "jail": jail,
            "ip": ip,
            "hostname": hostname,
            "server": server_name or "localhost"
        }
        
        logger.debug(f"Created event: {event}")
        
        return event

class FileWatcher:
    """Watch log files for changes"""
    
    class EventHandler(pyinotify.ProcessEvent):
        """Handle file modification events"""
        
        def __init__(self, file_path: str, callback, server_name: Optional[str] = None):
            self.file_path = file_path
            self.callback = callback
            self.server_name = server_name
            self.last_position = 0
            
            # Initialize last_position to current file size
            try:
                self.last_position = os.path.getsize(file_path)
            except OSError:
                pass
        
        def process_IN_MODIFY(self, event):
            """Handle file modification event"""
            if event.pathname == self.file_path:
                try:
                    with open(self.file_path, 'r') as f:
                        f.seek(self.last_position)
                        new_content = f.read()
                        self.last_position = f.tell()
                    
                    # Process each new line
                    for line in new_content.splitlines():
                        if line.strip():
                            # Wir verwenden hier einen einfacheren Ansatz mit einem Thread-Pool
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(self.callback(line, self.server_name))
                            finally:
                                loop.close()
                                
                except Exception as e:
                    logger.error(f"Error processing file change: {e}")
       
    @staticmethod
    def start_watching(file_path: str, callback, server_name: Optional[str] = None) -> Optional[pyinotify.WatchManager]:
        """Start watching a file for changes"""
        try:
            wm = pyinotify.WatchManager()
            handler = FileWatcher.EventHandler(file_path, callback, server_name)
            notifier = pyinotify.ThreadedNotifier(wm, handler)
            wm.add_watch(file_path, pyinotify.IN_MODIFY)
            notifier.start()
            
            # Store references to prevent garbage collection
            if server_name not in WATCH_MANAGERS:
                WATCH_MANAGERS[server_name] = []
                NOTIFIERS[server_name] = []
            
            WATCH_MANAGERS[server_name].append(wm)
            NOTIFIERS[server_name].append(notifier)
            
            logger.info(f"Started watching {file_path} on {server_name or 'localhost'}")
            return wm
        
        except Exception as e:
            logger.error(f"Error setting up file watcher for {file_path}: {e}")
            return None
    
    @staticmethod
    def stop_watching(server_name: Optional[str] = None):
        """Stop watching files"""
        if server_name and server_name in NOTIFIERS:
            for notifier in NOTIFIERS[server_name]:
                try:
                    notifier.stop()
                except:
                    pass
            
            NOTIFIERS[server_name] = []
            WATCH_MANAGERS[server_name] = []
            logger.info(f"Stopped watching files on {server_name}")
        
        elif server_name is None:
            # Stop all notifiers
            for server, notifiers in NOTIFIERS.items():
                for notifier in notifiers:
                    try:
                        notifier.stop()
                    except:
                        pass
            
            NOTIFIERS.clear()
            WATCH_MANAGERS.clear()
            logger.info("Stopped all file watchers")

async def setup_remote_watcher(server_name: str, server_config: dict):
    """Set up remote log monitoring via SSH"""
    client = await SSHManager.connect_to_server(server_name, server_config)
    if client is None:
        return
    
    SSH_CLIENTS[server_name] = client
    
    # Start periodic log checking in the background
    logs = server_config.get("logs", {})
    
    if "ssh" in logs and logs["ssh"]:
        asyncio.create_task(
            periodic_check_log(
                server_name, 
                logs["ssh"], 
                process_ssh_log_line, 
                interval=10
            )
        )
    
    if "fail2ban" in logs and logs["fail2ban"]:
        asyncio.create_task(
            periodic_check_log(
                server_name, 
                logs["fail2ban"], 
                process_fail2ban_log_line, 
                interval=10
            )
        )

async def periodic_check_log(server_name: str, log_path: str, process_func, interval: int = 10):
    """Periodically check a remote log file for new entries"""
    last_size = 0
    
    while RUNNING and server_name in SSH_CLIENTS:
        try:
            client = SSH_CLIENTS[server_name]
            if not client or client.get_transport() is None or not client.get_transport().is_active():
                # Reconnect if the connection is down
                logger.info(f"Reconnecting to {server_name}...")
                client = await SSHManager.connect_to_server(
                    server_name, 
                    CONFIG["servers"][server_name]
                )
                
                if client is None:
                    await asyncio.sleep(interval)
                    continue
                
                SSH_CLIENTS[server_name] = client
            
            # Get file size
            size_cmd = f"stat -c %s {log_path}"
            success, size_str = await SSHManager.execute_command(server_name, size_cmd, client)
            
            if not success:
                await asyncio.sleep(interval)
                continue
            
            current_size = int(size_str.strip())
            
            if current_size > last_size:
                # File has grown, get new content
                if last_size == 0:
                    # First run, just get the last few lines
                    success, content = await SSHManager.tail_file(server_name, log_path, 5, client)
                else:
                    # Get only the new content
                    cmd = f"tail -c +{last_size + 1} {log_path}"
                    success, content = await SSHManager.execute_command(server_name, cmd, client)
                
                if success:
                    # Process each new line
                    for line in content.splitlines():
                        if line.strip():
                            await process_func(line, server_name)
                    
                    last_size = current_size
            
            # Check for log rotation (file size decreased)
            elif current_size < last_size:
                # File was rotated, reset
                last_size = 0
        
        except Exception as e:
            logger.error(f"Error checking log on {server_name}: {e}")
        
        await asyncio.sleep(interval)

async def process_ssh_log_line(line: str, server_name: Optional[str] = None):
    """Process a new SSH log line"""
    event = await LogParser.parse_ssh_log_line(line, server_name)
    
    if event and CONFIG["notifications"].get("ssh_login", True):
        # Check if notifications are muted
        if NOTIFICATION_MUTED and time.time() < MUTE_UNTIL:
            return
        
        ip = event["ip"]
        username = event["username"]
        server = event["server"]
        hostname = event["hostname"] or ip
        
        message = (
            f"🔐 SSH Login\n"
            f"User: {username}\n"
            f"From: {hostname} ({ip})\n"
            f"Server: {server}\n"
            f"Time: {event['timestamp']}"
        )
        
        # Add IPinfo link if configured
        if CONFIG["customization"].get("show_ipinfo_link", True):
            message += f"\nMore Info: https://ipinfo.io/{ip}"
        
        await notify_telegram(message)

async def process_fail2ban_log_line(line: str, server_name: Optional[str] = None):
    """Process a new fail2ban log line"""
    logger.debug(f"Processing fail2ban log line: {line}")
    event = await LogParser.parse_fail2ban_log_line(line, server_name)
    
    logger.debug(f"Parsed event: {event}")
    
    if event:
        # Handle regular ban events
        if event["type"] == "fail2ban_ban" and CONFIG["notifications"].get("fail2ban_block", True):
            # Check if notifications are muted
            if NOTIFICATION_MUTED and time.time() < MUTE_UNTIL:
                logger.info(f"Found ban event but notifications are muted: {event}")
                return
            
            ip = event["ip"]
            jail = event["jail"]
            server = event["server"]
            hostname = event["hostname"] or ip
            
            logger.info(f"Sending notification for ban event: {ip} in {jail} on {server}")
            
            # Erweiterte IP-Informationen abrufen
            ip_info = await NetworkUtils.get_ip_info(ip)
            
            # Formatierte Zeit
            formatted_time = DateUtils.format_timestamp(event['timestamp'])
            
            # Nachricht mit erweiterter Formatierung erstellen
            message = f"🛑 *IP Banned by fail2ban*\n\n"
            
            # Basisdaten
            message += f"*IP:* {hostname} ({ip})\n"
            message += f"*Jail:* {jail}\n"
            message += f"*Server:* {server}\n"
            message += f"*Time:* {formatted_time}\n\n"
            
            # Erweiterte Informationen hinzufügen, wenn verfügbar
            if ip_info:
                message += "📍 *IP Details:*\n"
                
                # Land mit Flagge
                if "country" in ip_info and "flag" in ip_info:
                    message += f"*Country:* {ip_info['flag']} {ip_info.get('country', '')}"
                    if "region" in ip_info:
                        message += f", {ip_info['region']}"
                    message += "\n"
                
                # Stadt
                if "city" in ip_info:
                    message += f"*City:* {ip_info['city']}"
                    if "postal" in ip_info:
                        message += f" ({ip_info['postal']})"
                    message += "\n"
                
                # Timezone & lokale Zeit
                if "timezone" in ip_info:
                    tz_name = ip_info["timezone"]
                    message += f"*Timezone:* {tz_name}\n"
                    
                    # Lokale Zeit berechnen
                    try:
                        from datetime import datetime
                        import pytz
                        local_time = datetime.now(pytz.timezone(tz_name))
                        message += f"*Local Time:* {local_time.strftime('%H:%M:%S')}\n"
                    except:
                        pass
                
                # ASN und Unternehmen
                if "org" in ip_info:
                    message += f"*Organization:* {ip_info['org']}\n"
                
                # Missbrauchskontakt
                if "abuse" in ip_info:
                    message += f"*Abuse Contact:* {ip_info.get('abuse', {}).get('email', 'N/A')}\n"
                
                # Koordinaten und Maps-Link
                if "loc" in ip_info:
                    coords = ip_info["loc"]
                    message += f"*Coordinates:* {coords}\n"
                    message += f"*[View on Google Maps](https://www.google.com/maps?q={coords})*\n"
            
            # IPinfo Link hinzufügen
            if CONFIG["customization"].get("show_ipinfo_link", True):
                message += f"\n[More Details on IPinfo.io](https://ipinfo.io/{ip})"
            
            buttons = [
                [
                    InlineKeyboardButton(
                        f"Unban {ip}", 
                        callback_data=f"unban_{server}_{jail}_{ip}"
                    ),
                    InlineKeyboardButton(
                        f"Permanent {ip}", 
                        callback_data=f"perm_ban_{server}_{jail}_{ip}"
                    )
                ]
            ]
            
            # Da wir Markdown-Formatierung verwenden
            await notify_telegram(message, buttons, parse_mode="Markdown")
        
        # Handle "already banned" events
        elif event["type"] == "fail2ban_already_banned" and CONFIG["notifications"].get("fail2ban_block", True):
            # Check if notifications are muted
            if NOTIFICATION_MUTED and time.time() < MUTE_UNTIL:
                return
            
            ip = event["ip"]
            jail = event["jail"]
            server = event["server"]
            hostname = event["hostname"] or ip
            
            # Erweiterte IP-Informationen abrufen
            ip_info = await NetworkUtils.get_ip_info(ip)
            
            # Formatierte Zeit
            formatted_time = DateUtils.format_timestamp(event['timestamp'])
            
            logger.info(f"Sending notification for already banned event: {ip} in {jail} on {server}")
            
            message = f"⚠️ *Repeated Access Attempt*\n\n"
            message += f"*IP:* {hostname} ({ip}) attempted access while already banned\n"
            message += f"*Jail:* {jail}\n"
            message += f"*Server:* {server}\n"
            message += f"*Time:* {formatted_time}\n"
            
            # Erweiterte Informationen hinzufügen, wenn verfügbar (kompaktere Form)
            if ip_info:
                message += "\n📍 *IP Details:*\n"
                
                # Land und Stadt
                if "country" in ip_info and "flag" in ip_info:
                    message += f"*Location:* {ip_info['flag']} "
                    if "city" in ip_info:
                        message += f"{ip_info['city']}, "
                    message += f"{ip_info.get('country', '')}\n"
                
                # Organisation
                if "org" in ip_info:
                    message += f"*Organization:* {ip_info['org']}\n"
            
            # IPinfo Link hinzufügen
            if CONFIG["customization"].get("show_ipinfo_link", True):
                message += f"\n[More Details on IPinfo.io](https://ipinfo.io/{ip})"
            
            buttons = [
                [InlineKeyboardButton(
                    f"Unban {ip}", 
                    callback_data=f"unban_{server}_{jail}_{ip}"
                )]
            ]
            
            await notify_telegram(message, buttons, parse_mode="Markdown")
        
        # Handle "found" events (optional)
        elif event["type"] == "fail2ban_found" and CONFIG.get("notifications", {}).get("fail2ban_found", False):
            # Diese Ereignisse sind sehr häufig, daher standardmäßig deaktiviert
            # Check if notifications are muted
            if NOTIFICATION_MUTED and time.time() < MUTE_UNTIL:
                return
            
            ip = event["ip"]
            jail = event["jail"]
            server = event["server"]
            hostname = event["hostname"] or ip
            
            # Formatierte Zeit
            formatted_time = DateUtils.format_timestamp(event['timestamp'])
            
            logger.info(f"Found potential attack attempt: {ip} in {jail} on {server}")
            
            message = f"🔍 *Suspicious Activity Detected*\n\n"
            message += f"*IP:* {hostname} ({ip}) was found in logs\n"
            message += f"*Jail:* {jail}\n"
            message += f"*Server:* {server}\n"
            message += f"*Time:* {formatted_time}\n"
            
            # IPinfo Link hinzufügen
            if CONFIG["customization"].get("show_ipinfo_link", True):
                message += f"\n[More Details on IPinfo.io](https://ipinfo.io/{ip})"
            
            await notify_telegram(message, parse_mode="Markdown")

async def notify_telegram(message: str, buttons: Optional[List[List[InlineKeyboardButton]]] = None, parse_mode: Optional[str] = None):
    """Send a notification to the configured Telegram chat"""
    bot = BOT_INSTANCE
    chat_id = CONFIG["telegram"].get("chat_id")
    
    if not bot or not chat_id:
        logger.error("Telegram bot not initialized or chat_id not configured")
        return
    
    try:
        logger.debug(f"Sending message to chat_id: {chat_id}")
        logger.debug(f"Message content: {message[:100]}...")  # Log part of the message
        
        if buttons:
            markup = InlineKeyboardMarkup(buttons)
            # send directly using bot.send_message instead of do_post
            await bot.send_message(chat_id=chat_id, text=message, reply_markup=markup, parse_mode=parse_mode)
        else:
            # send directly using bot.send_message instead of do_post
            await bot.send_message(chat_id=chat_id, text=message, parse_mode=parse_mode)
        
        logger.info("Notification sent successfully")
    
    except telegram.error.BadRequest as e:
        # specific error handling for BadRequest
        logger.error(f"Telegram API error (BadRequest): {e}")
        if "Chat not found" in str(e):
            logger.error(f"Chat ID '{chat_id}' not found. Make sure your chat_id is correct and the bot has been started in this chat.")
    except telegram.error.Forbidden as e:
        # bot was removed from the chat or doesn't have permission to send messages
        logger.error(f"Telegram API error (Forbidden): {e}")
        logger.error("Bot may have been removed from the chat or doesn't have permission to send messages.")
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        logger.error(f"Full error type: {type(e)}")
        # full traceback for debugging
        import traceback
        logger.debug(f"Exception traceback: {traceback.format_exc()}")

async def start_command(update: Update, context: CallbackContext) -> None:
    """Handle the /start command"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized access. Contact the bot administrator.")
        return
    
    await update.message.reply_text(
        "👋 Welcome to SecureBot - your security monitoring assistant!\n\n"
        "Use /help to see available commands."
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Handle the /help command"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized access. Contact the bot administrator.")
        return
    
    is_admin = is_admin_user(user_id)
    
    help_text = (
        "📋 Available commands:\n\n"
        "/help - Show this help message\n"
        "/status - Show status of all monitored servers\n"
        "/login_history [n] - Show last n login events\n"
        "/server list - List all configured servers\n"
        "/server status NAME - Show status of a specific server\n"
        "/mute [minutes] - Mute notifications temporarily\n"
        "/unmute - Unmute notifications\n"
    )
    
    # Add admin-only commands if user is admin
    if is_admin:
        help_text += (
            "\n📊 Admin commands:\n"
            "/fail2ban all - Show all banned IPs across all jails\n"
            "/fail2ban all_ips - Show all banned IPs (alias for 'all')\n"
            "/fail2ban list [server] - List fail2ban jails\n"
            "/fail2ban status JAIL [server] - Show banned IPs in a jail\n"
            "/fail2ban ban IP JAIL [server] - Ban an IP in a jail\n"
            "/fail2ban unban IP JAIL [server] - Unban an IP from a jail\n"
            "\n🔒 Permanent ban management (new):\n"
            "/perm_bans list - List all permanent bans\n"
            "/perm_bans add IP [reason] - Add a permanent ban\n"
            "/perm_bans remove IP - Remove a permanent ban\n"
        )
    
    await update.message.reply_text(help_text)

async def status_command(update: Update, context: CallbackContext) -> None:
    """Handle the /status command"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message = f"Debug Info:\nUser ID: {user_id}\nChat ID: {chat_id}\n\n"
    await update.message.reply_text(message)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized access. Contact the bot administrator.")
        return
    
    message = "📊 System Status\n\n"
    
    # Check local system status
    message += "🖥 Local System:\n"
    
    # Check if fail2ban is running
    try:
        subprocess.check_output(["systemctl", "is-active", "fail2ban"], text=True)
        message += "- fail2ban: ✅ Running\n"
    except subprocess.CalledProcessError:
        message += "- fail2ban: ❌ Not running\n"
    
    # Check SSH service
    try:
        subprocess.check_output(["systemctl", "is-active", "ssh"], text=True)
        message += "- SSH: ✅ Running\n"
    except subprocess.CalledProcessError:
        message += "- SSH: ❌ Not running\n"
    
    # Check remote servers status
    if not CONFIG["general"].get("local_only", False) and "servers" in CONFIG:
        message += "\n🌐 Remote Servers:\n"
        
        for server_name, server_config in CONFIG["servers"].items():
            client = SSH_CLIENTS.get(server_name)
            
            if client and client.get_transport() and client.get_transport().is_active():
                message += f"- {server_name}: ✅ Connected\n"
            else:
                message += f"- {server_name}: ❌ Disconnected\n"
    
    # Add notification status
    message += f"\n🔔 Notifications: {'🔇 Muted' if NOTIFICATION_MUTED else '🔊 Active'}"
    
    if NOTIFICATION_MUTED and time.time() < MUTE_UNTIL:
        mute_remaining = int(MUTE_UNTIL - time.time()) // 60  # Minutes remaining
        message += f" (for {mute_remaining} more minutes)"
    
    await update.message.reply_text(message)

async def login_history_command(update: Update, context: CallbackContext) -> None:
    """Handle the /login_history command"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized access. Contact the bot administrator.")
        return
    
    # Parse arguments
    args = context.args
    lines = 5  # Default
    
    if args and args[0].isdigit():
        lines = min(int(args[0]), 20)  # Limit to 20 lines
    
    message = f"📜 Last {lines} SSH logins:\n\n"
    
    # Get local login history
    command = f"grep 'Accepted' /var/log/auth.log | tail -n {lines}"
    
    try:
        local_logins = subprocess.check_output(command, shell=True, text=True).strip()
        
        if local_logins:
            message += "🖥 Local System:\n"
            
            for line in local_logins.splitlines():
                event = await LogParser.parse_ssh_log_line(line)
                if event:
                    message += (
                        f"User: {event['username']}\n"
                        f"From: {event['ip']}\n"
                        f"Time: {event['timestamp']}\n\n"
                    )
        else:
            message += "No recent logins found on local system.\n"
    
    except subprocess.CalledProcessError:
        message += "Could not retrieve local login history.\n"
    
    # Get remote servers login history
    if not CONFIG["general"].get("local_only", False) and "servers" in CONFIG:
        for server_name, server_config in CONFIG["servers"].items():
            ssh_log = server_config.get("logs", {}).get("ssh")
            if not ssh_log:
                continue
            
            success, log_content = await SSHManager.execute_command(
                server_name, 
                f"grep 'Accepted' {ssh_log} | tail -n {lines}"
            )
            
            if success and log_content:
                message += f"\n🌐 {server_name}:\n"
                
                for line in log_content.splitlines():
                    event = await LogParser.parse_ssh_log_line(line, server_name)
                    if event:
                        message += (
                            f"User: {event['username']}\n"
                            f"From: {event['ip']}\n"
                            f"Time: {event['timestamp']}\n\n"
                        )
    
    await update.message.reply_text(message)

async def server_command(update: Update, context: CallbackContext) -> None:
    """Handle the /server command"""
    # Check if the update is a message or callback query
    if update.message is None:
        # try to get the message from the callback query
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text("Usage:\n/server list - List all configured servers\n/server status NAME - Show status of a specific server")
        return
    
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized access. Contact the bot administrator.")
        return
    
    # Parse arguments
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "Usage:\n"
            "/server list - List all configured servers\n"
            "/server status NAME - Show status of a specific server"
        )
        return
    
    subcommand = args[0].lower()
    
    if subcommand == "list":
        # List all configured servers
        if not CONFIG["general"].get("local_only", False) and "servers" in CONFIG:
            message = "🌐 Configured Servers:\n\n"
            
            for server_name, server_config in CONFIG["servers"].items():
                status = "✅ Connected" if server_name in SSH_CLIENTS else "❌ Disconnected"
                message += f"- {server_name} ({server_config['hostname']}): {status}\n"
        else:
            message = "No remote servers configured. Bot is in local-only mode."
        
        await update.message.reply_text(message)
    
    elif subcommand == "status" and len(args) > 1:
        # Show status of a specific server
        server_name = args[1]
        
        if server_name not in CONFIG.get("servers", {}):
            await update.message.reply_text(f"Unknown server: {server_name}")
            return
        
        message = f"📊 Status of {server_name}\n\n"
        
        # Check connection status
        client = SSH_CLIENTS.get(server_name)
        if client and client.get_transport() and client.get_transport().is_active():
            message += "Connection: ✅ Connected\n\n"
            
            # Get system info
            success, uptime = await SSHManager.execute_command(
                server_name, 
                "uptime -p", 
                client
            )
            
            if success:
                message += f"Uptime: {uptime}\n"
            
            # Get load average
            success, load = await SSHManager.execute_command(
                server_name, 
                "cat /proc/loadavg | awk '{print $1, $2, $3}'", 
                client
            )
            
            if success:
                load_values = load.split()
                message += f"Load: {load_values[0]} (1m), {load_values[1]} (5m), {load_values[2]} (15m)\n"
            
            # Get memory usage
            success, memory = await SSHManager.execute_command(
                server_name, 
                "free -h | grep Mem | awk '{print $3, $2}'", 
                client
            )
            
            if success:
                used, total = memory.split()
                message += f"Memory: {used} used / {total} total\n"
            
            # Get disk usage
            success, disk = await SSHManager.execute_command(
                server_name, 
                "df -h / | tail -1 | awk '{print $3, $2, $5}'", 
                client
            )
            
            if success:
                used, total, percentage = disk.split()
                message += f"Disk: {used} used / {total} total ({percentage})\n"
            
            # Check if fail2ban is running
            success, fail2ban_status = await SSHManager.execute_command(
                server_name, 
                "systemctl is-active fail2ban || echo 'inactive'", 
                client
            )
            
            if success:
                status = "✅ Running" if fail2ban_status.strip() == "active" else "❌ Not running"
                message += f"fail2ban: {status}\n"
            
            # Check if SSH is running
            success, ssh_status = await SSHManager.execute_command(
                server_name, 
                "systemctl is-active ssh || echo 'inactive'", 
                client
            )
            
            if success:
                status = "✅ Running" if ssh_status.strip() == "active" else "❌ Not running"
                message += f"SSH: {status}\n"
        
        else:
            message += "Connection: ❌ Disconnected\n"
            message += "\nTrying to reconnect..."
            
            # Try to reconnect
            client = await SSHManager.connect_to_server(
                server_name, 
                CONFIG["servers"][server_name]
            )
            
            if client:
                SSH_CLIENTS[server_name] = client
                message += " ✅ Connected successfully!"
            else:
                message += " ❌ Failed to connect."
        
        await update.message.reply_text(message)
    
    else:
        await update.message.reply_text(
            "Usage:\n"
            "/server list - List all configured servers\n"
            "/server status NAME - Show status of a specific server"
        )

async def fail2ban_command(update: Update, context: CallbackContext) -> None:
    """Handle the /fail2ban command"""
    # verify if the update is a message or callback query
    if update.message is None:
        # try to get the message from the callback query
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "Usage:\n"
                "/fail2ban all - Show all banned IPs\n"
                "/fail2ban all_ips - Show all banned IPs\n"
                "/fail2ban list [server] - List fail2ban jails\n"
                "/fail2ban status JAIL [server] - Show banned IPs in a jail\n"
                "/fail2ban ban IP JAIL [server] - Ban an IP in a jail\n"
                "/fail2ban unban IP JAIL [server] - Unban an IP from a jail"
            )
        return
        
    user_id = update.effective_user.id
    if not is_authorized(user_id) or not is_admin_user(user_id):
        await update.message.reply_text("Unauthorized access. Admin privileges required.")
        return
    
    # Parse arguments
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "Usage:\n"
            "/fail2ban all - Show all banned IPs\n"
            "/fail2ban all_ips - Show all banned IPs\n"
            "/fail2ban list [server] - List fail2ban jails\n"
            "/fail2ban status JAIL [server] - Show banned IPs in a jail\n"
            "/fail2ban ban IP JAIL [server] - Ban an IP in a jail\n"
            "/fail2ban unban IP JAIL [server] - Unban an IP from a jail"
        )
        return
    
    subcommand = args[0].lower()
    
    # Check if the subcommand is valid
    if subcommand == "list":
        # List all fail2ban jails
        server_name = args[1] if len(args) > 1 else None
        
        # Check if server name is valid
        if server_name and server_name not in CONFIG.get("servers", {}):
            await update.message.reply_text(f"Unknown server: {server_name}")
            return
        
        success, jails = await Fail2BanManager.list_jails(server_name)
        
        # check if jails are valid
        if success and jails:
            message = f"🔒 fail2ban jails on {server_name or 'localhost'}:\n\n"
            message += "\n".join([f"- {jail}" for jail in jails])
        else:
            message = f"No fail2ban jails found on {server_name or 'localhost'}."
        
        await update.message.reply_text(message)
    
    # Check if the subcommand is valid
    elif subcommand == "all" or subcommand == "all_ips":
        # Show all banned IPs from all jails
        server_name = args[1] if len(args) > 1 else None
        
        if server_name and server_name not in CONFIG.get("servers", {}):
            await update.message.reply_text(f"Unknown server: {server_name}")
            return
        
        all_ips = await Fail2BanManager.get_all_banned_ips(server_name)
        
        if all_ips:
            message = f"🛑 All banned IPs on {server_name or 'localhost'}:\n\n"
            
            for jail, ips in all_ips.items():
                message += f"Jail '{jail}':\n"
                if ips:
                    for ip in ips:
                        hostname = None
                        if CONFIG["customization"].get("resolve_hostnames", True):
                            try:
                                hostname = socket.gethostbyaddr(ip)[0]
                            except (socket.herror, socket.gaierror):
                                pass
                        
                        message += f"- {ip}"
                        if hostname:
                            message += f" ({hostname})"
                        message += "\n"
                else:
                    message += "- No banned IPs\n"
                message += "\n"
            
            await update.message.reply_text(message)
        else:
            await update.message.reply_text(f"No banned IPs found on {server_name or 'localhost'}.")
    
    # Check if the subcommand is valid
    elif subcommand == "status" and len(args) > 1:
        # Show banned IPs in a jail
        jail = args[1]
        server_name = args[2] if len(args) > 2 else None
        
        # Check if server name is valid
        if server_name and server_name not in CONFIG.get("servers", {}):
            await update.message.reply_text(f"Unknown server: {server_name}")
            return
        
        success, ips = await Fail2BanManager.get_banned_ips(jail, server_name)
        
        # check if ips are valid
        if success:
            if ips:
                message = f"🛑 Banned IPs in jail '{jail}' on {server_name or 'localhost'}:\n\n"
                
                for ip in ips:
                    hostname = None
                    if CONFIG["customization"].get("resolve_hostnames", True):
                        try:
                            hostname = socket.gethostbyaddr(ip)[0]
                        except (socket.herror, socket.gaierror):
                            pass
                    
                    message += f"- {ip}"
                    if hostname:
                        message += f" ({hostname})"
                    message += "\n"
                
                # Add unban buttons
                buttons = []
                for ip in ips[:5]:  # Limit to 5 buttons
                    buttons.append([
                        InlineKeyboardButton(
                            f"Unban {ip}", 
                            callback_data=f"unban_{server_name or 'local'}_{jail}_{ip}"
                        )
                    ])
                
                await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(buttons))
            else:
                await update.message.reply_text(f"No IPs banned in jail '{jail}' on {server_name or 'localhost'}.")
        else:
            await update.message.reply_text(f"Failed to get banned IPs from jail '{jail}'.")
    
    # Check if the subcommand is valid
    elif subcommand == "ban" and len(args) > 2:
        # Ban an IP in a jail
        ip = args[1]
        jail = args[2]
        server_name = args[3] if len(args) > 3 else None
        
        # Check if server name is valid
        if server_name and server_name not in CONFIG.get("servers", {}):
            await update.message.reply_text(f"Unknown server: {server_name}")
            return
        
        success, result = await Fail2BanManager.ban_ip(ip, jail, server_name)
        
        if success:
            await update.message.reply_text(f"✅ Successfully banned {ip} in jail '{jail}' on {server_name or 'localhost'}.")
        else:
            await update.message.reply_text(f"❌ Failed to ban {ip}: {result}")
    
    # Check if the subcommand is valid
    elif subcommand == "unban" and len(args) > 2:
        # Unban an IP from a jail
        jail = args[1]  # first parameter die jail
        ip = args[2]    # second parameter die ip 
        server_name = args[3] if len(args) > 3 else None    # third parameter die server_name
        
        # Check if server name is valid 
        if server_name and server_name not in CONFIG.get("servers", {}):
            await update.message.reply_text(f"Unknown server: {server_name}")
            return
        
        # Debug log
        logger.debug(f"Executing unban from command with jail={jail}, ip={ip}, server={server_name}")
        
        success, result = await Fail2BanManager.unban_ip(ip, jail, server_name)
        
        if success:
            await update.message.reply_text(f"✅ Successfully unbanned {ip} from jail '{jail}' on {server_name or 'localhost'}.")
        else:
            await update.message.reply_text(f"❌ Failed to unban {jail}: {result}")
    
    else:
        await update.message.reply_text(
            "Usage:\n"
            "/fail2ban all - Show all banned IPs\n"
            "/fail2ban all_ips - Show all banned IPs\n"
            "/fail2ban list [server] - List fail2ban jails\n"
            "/fail2ban status JAIL [server] - Show banned IPs in a jail\n"
            "/fail2ban ban IP JAIL [server] - Ban an IP in a jail\n"
            "/fail2ban unban IP JAIL [server] - Unban an IP from a jail"
        )

async def permanent_bans_command(update: Update, context: CallbackContext) -> None:
    """Handle the /perm_bans command"""
    user_id = update.effective_user.id
    if not is_authorized(user_id) or not is_admin_user(user_id):
        await update.message.reply_text("Unauthorized access. Admin privileges required.")
        return
    
    # Parse arguments
    args = context.args
    
    if not args or args[0].lower() == "list":
        # List all permanent bans
        perm_bans = await Fail2BanManager.list_permanent_bans()
        
        if not perm_bans:
            await update.message.reply_text("No permanent IP bans configured.")
            return
        
        message = "🔒 Permanent IP Bans:\n\n"
        for ip, data in perm_bans.items():
            timestamp = data.get("timestamp", "Unknown date")
            reason = data.get("reason", "No reason specified")
            banned_by = data.get("banned_by", "Unknown")
            
            message += f"- {ip}\n"
            message += f"  Banned on: {timestamp}\n"
            message += f"  Reason: {reason}\n"
            message += f"  Banned by: {banned_by}\n\n"
        
        await update.message.reply_text(message)
    
    elif args[0].lower() == "add" and len(args) > 1:
        # Add a permanent ban
        ip = args[1]
        reason = " ".join(args[2:]) if len(args) > 2 else "Manual permanent ban"
        
        success, result = await Fail2BanManager.ban_ip_permanently(ip, reason, user_id)
        
        if success:
            await update.message.reply_text(f"✅ {result}")
        else:
            await update.message.reply_text(f"❌ {result}")
    
    elif args[0].lower() == "remove" and len(args) > 1:
        # Remove a permanent ban
        ip = args[1]
        success, result = await Fail2BanManager.remove_permanent_ban(ip)
        
        if success:
            await update.message.reply_text(f"✅ {result}")
        else:
            await update.message.reply_text(f"❌ {result}")
    
    else:
        # Show help
        await update.message.reply_text(
            "Usage:\n"
            "/perm_bans list - List all permanent bans\n"
            "/perm_bans add IP [reason] - Add a permanent ban\n"
            "/perm_bans remove IP - Remove a permanent ban"
        )

async def mute_command(update: Update, context: CallbackContext) -> None:
    """Handle the /mute command"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized access. Contact the bot administrator.")
        return
    
    global NOTIFICATION_MUTED, MUTE_UNTIL
    
    # Parse arguments
    args = context.args
    minutes = 30  # Default
    
    if args and args[0].isdigit():
        minutes = min(int(args[0]), 1440)  # Limit to 24 hours
    
    NOTIFICATION_MUTED = True
    MUTE_UNTIL = time.time() + minutes * 60
    
    await update.message.reply_text(f"🔇 Notifications muted for {minutes} minutes.")

async def unmute_command(update: Update, context: CallbackContext) -> None:
    """Handle the /unmute command"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized access. Contact the bot administrator.")
        return
    
    global NOTIFICATION_MUTED
    
    NOTIFICATION_MUTED = False
    
    await update.message.reply_text("🔊 Notifications unmuted.")

async def button_callback(update: Update, context: CallbackContext) -> None:
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await query.edit_message_text(text="Unauthorized access. Contact the bot administrator.")
        return
    
    data = query.data
    
    if data.startswith("unban_"):
        # Parse callback data
        parts = data.split("_", 3)
        if len(parts) != 4:
            await query.edit_message_text(text="Invalid callback data.")
            return
        
        _, server, jail, ip = parts
        server_name = None if server == "local" else server
        
        # Admin check for unban operations
        if not is_admin_user(user_id):
            await query.edit_message_text(text="Admin privileges required for unban operations.")
            return
        
        # Unban the IP
        logger.debug(f"Unbanning IP {ip} from jail {jail} on server {server_name or 'localhost'}")
        success, result = await Fail2BanManager.unban_ip(ip, jail, server_name)
        
        if success:
            await query.edit_message_text(
                text=f"✅ Successfully unbanned {ip} from jail '{jail}' on {server_name or 'localhost'}."
            )
        else:
            await query.edit_message_text(
                text=f"❌ Failed to unban {ip}: {result}"
            )
    
    elif data.startswith("perm_ban_"):
        # Permanent Ban-Logik
        if not is_admin_user(user_id):
            await query.edit_message_text(text="Admin privileges required for permanent bans.")
            return
        
        # Parse callback data
        parts = data.split("_", 3)
        if len(parts) != 4:
            await query.edit_message_text(text="Invalid callback data.")
            return
        
        _, server, jail, ip = parts
        server_name = None if server == "local" else server
        
        # Permanent ban durchführen
        success, result = await Fail2BanManager.ban_ip_permanently(
            ip, 
            reason=f"Permanent ban from jail {jail}",
            user_id=user_id
        )
        
        if success:
            await query.edit_message_text(
                text=f"🔒 Permanently banned {ip} across all servers and jails.\n\n"
                     f"This IP will be automatically re-banned even after fail2ban restarts."
            )
        else:
            await query.edit_message_text(
                text=f"⚠️ Partial permanent ban for {ip}: {result}"
            )

def is_authorized(user_id: int) -> bool:
    """Check if a user is authorized to use the bot"""
    admin_users = CONFIG.get("telegram", {}).get("admin_users", [])
    viewer_users = CONFIG.get("telegram", {}).get("viewer_users", [])
    
    return user_id in admin_users or user_id in viewer_users

def is_admin_user(user_id: int) -> bool:
    """Check if a user has admin privileges"""
    admin_users = CONFIG.get("telegram", {}).get("admin_users", [])
    return user_id in admin_users

async def setup_local_watchers():
    """Set up local log file watchers"""
    ssh_log = CONFIG["local"].get("ssh_log")
    fail2ban_log = CONFIG["local"].get("fail2ban_log")
    
    if ssh_log and os.path.exists(ssh_log):
        FileWatcher.start_watching(ssh_log, process_ssh_log_line)
    
    if fail2ban_log and os.path.exists(fail2ban_log):
        FileWatcher.start_watching(fail2ban_log, process_fail2ban_log_line)

async def start_monitoring():
    """Start the monitoring process"""
    global BOT_INSTANCE
    
    # Initialize Telegram bot
    bot_token = CONFIG["telegram"].get("bot_token")
    if not bot_token or bot_token == "YOUR_BOT_TOKEN":
        logger.error("Telegram bot token not configured")
        return False
    
    try:
        BOT_INSTANCE = telegram.Bot(token=bot_token)
        logger.info("Telegram bot initialized")
    except Exception as e:
        logger.error(f"Error initializing Telegram bot: {e}")
        return False
    
    # Set up local file watchers
    await setup_local_watchers()
    
    # Stelle sicher, dass alle permanenten Bans aktiv sind
    logger.info("Ensuring permanent bans are active...")
    await Fail2BanManager.ensure_permanent_bans()
    
    # Set up remote monitoring if not in local-only mode
    if not CONFIG["general"].get("local_only", False) and "servers" in CONFIG:
        for server_name, server_config in CONFIG["servers"].items():
            logger.info(f"Setting up monitoring for {server_name}")
            asyncio.create_task(setup_remote_watcher(server_name, server_config))
    
    return True

async def stop_monitoring():
    """Stop the monitoring process"""
    global RUNNING
    
    RUNNING = False
    
    # Stop file watchers
    FileWatcher.stop_watching()
    
    # Close SSH connections
    for server_name, client in SSH_CLIENTS.items():
        if client:
            client.close()
            logger.info(f"Closed SSH connection to {server_name}")
    
    SSH_CLIENTS.clear()
    
    logger.info("Monitoring stopped")

async def run_telegram_bot():
    """Run the Telegram bot"""
    global RUNNING  # Hier an den Anfang der Funktion verschieben
    
    bot_token = CONFIG["telegram"].get("bot_token")
    if not bot_token or bot_token == "YOUR_BOT_TOKEN":
        logger.error("Telegram bot token not configured")
        return
    
    # Initialize the Application
    application = Application.builder().token(bot_token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("login_history", login_history_command))
    application.add_handler(CommandHandler("server", server_command))
    application.add_handler(CommandHandler("fail2ban", fail2ban_command))
    application.add_handler(CommandHandler("perm_bans", permanent_bans_command))
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("unmute", unmute_command))
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    asyncio.create_task(Fail2BanManager.ensure_permanent_bans())

    try:
        # Start the bot
        await application.initialize()
        await application.start()
        
        # Notify admin that the bot has started
        admin_users = CONFIG["telegram"].get("admin_users", [])
        if admin_users:
            try:
                message = f"🚀 SecureBot v{__version__} started"
                for admin_id in admin_users:
                    await BOT_INSTANCE.send_message(chat_id=admin_id, text=message)
            except Exception as e:
                logger.error(f"Error sending startup notification: {e}")
        
        # Run the bot until the application is stopped
        try:
            await application.updater.start_polling()
            logger.info("Telegram bot is running")
            
            # Keep the bot running
            while RUNNING:
                await asyncio.sleep(1)
        
        except telegram.error.Conflict as e:
            logger.error(f"Bot conflict detected: {e}")
            logger.error("Another instance of this bot is already running. Shutting down.")
            # Signal hauptprogramm to exit
            RUNNING = False
            return
        
        except Exception as e:
            logger.error(f"Unexpected error in bot polling: {e}")
            RUNNING = False
            return
    
    finally:
        # Stop the bot
        await application.stop()
        await application.shutdown()
        logger.info("Telegram bot stopped")

async def run_daemon():
    """Run the bot as a daemon"""
    logger.info("Starting bot in daemon mode")
    
    try:
        # Start monitoring
        if await start_monitoring():
            # Set up local file watchers
            await setup_local_watchers()
            
            # As Backup for local log files, we can use periodic checks
            if CONFIG["local"].get("fail2ban_log") and os.path.exists(CONFIG["local"].get("fail2ban_log")):
                logger.info(f"Setting up periodic checks for local fail2ban log")
                asyncio.create_task(periodic_check_log(
                    "localhost", 
                    CONFIG["local"].get("fail2ban_log"), 
                    process_fail2ban_log_line, 
                    interval=5
                ))
            
            # As Backup for local log files, we can use periodic checks
            if CONFIG["local"].get("ssh_log") and os.path.exists(CONFIG["local"].get("ssh_log")):
                logger.info(f"Setting up periodic checks for local SSH log")
                asyncio.create_task(periodic_check_log(
                    "localhost", 
                    CONFIG["local"].get("ssh_log"), 
                    process_ssh_log_line, 
                    interval=5
                ))
            
            # Run the Telegram bot
            await run_telegram_bot()
        
        # Stop monitoring
        await stop_monitoring()
    
    except Exception as e:
        logger.error(f"Fatal error in daemon mode: {e}")
        await stop_monitoring()
        raise

def handle_signal(signum, frame):
    """Handle termination signals"""
    global RUNNING
    
    logger.info(f"Received signal {signum}, shutting down...")
    RUNNING = False
    
    # stop all notifiers immediately
    FileWatcher.stop_watching()
    
    # close all SSH connections
    for server_name, client in SSH_CLIENTS.items():
        if client:
            try:
                client.close()
                logger.info(f"Closed SSH connection to {server_name}")
            except:
                pass
    # stop asyncio Event-Loop for next run
    if asyncio.get_event_loop().is_running():
        asyncio.get_event_loop().stop()
    
    # when SIGTERM signal is received, exit immediately
    if signum == signal.SIGTERM:
        logger.info("Terminating immediately due to SIGTERM")
        sys.exit(0)
        
def main():
    """Main function"""
    global CONFIG
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="SecureBot - Telegram Security Bot")
    parser.add_argument(
        "-d", "--daemon", 
        action="store_true", 
        help="Run as a daemon"
    )
    parser.add_argument(
        "-c", "--config", 
        type=str, 
        help="Path to the configuration file"
    )
    parser.add_argument(
        "-g", "--generate-config", 
        action="store_true", 
        help="Generate a default configuration file"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Increase verbosity"
    )
    parser.add_argument(
        "-t", "--test", 
        action="store_true", 
        help="Run in test mode (no actual actions)"
    )
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"SecureBot v{__version__}"
    )
    parser.add_argument(
        "-l", "--log", 
        type=str, 
        help="Path to log file"
    )
    parser.add_argument(
        "--setup", 
        action="store_true", 
        help="Run interactive setup"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.log:
        file_handler = logging.FileHandler(args.log)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        logging.getLogger().addHandler(file_handler)
    
    # Generate default configuration if requested
    if args.generate_config:
        config_path = args.config
        
        if not config_path:
            config_path = os.path.expanduser("~/.securebot.conf")
        
        # Generate and save the configuration
        default_config = ConfigManager.generate_config()
        if ConfigManager.save_config(default_config, config_path):
            print(f"Default configuration generated at {config_path}")
        else:
            print("Failed to generate configuration file")
        
        return
    
    # Run interactive setup if requested
    if args.setup:
        print("Interactive setup not implemented yet")
        return
    
    # Load configuration
    config_path = args.config
    
    if not config_path:
        # Try to load from default locations
        user_config = os.path.expanduser("~/.securebot.conf")
        if os.path.exists(user_config):
            config_path = user_config
        elif os.path.exists("/etc/securebot.conf"):
            config_path = "/etc/securebot.conf"
        else:
            print("No configuration file found. Use --generate-config to create one.")
            return
    
    # Load the configuration
    CONFIG = ConfigManager.load_config(config_path)
    
    if not CONFIG:
        print(f"Failed to load configuration from {config_path}")
        return
    
    # Validate the configuration
    valid, errors = ConfigManager.validate_config(CONFIG)
    if not valid:
        print("Configuration validation failed:")
        for error in errors:
            print(f"- {error}")
        return
    
    # Set log level from configuration
    log_level = CONFIG["general"].get("log_level", "INFO")
    logging.getLogger().setLevel(getattr(logging, log_level))
    
    # Run in test mode if requested
    if args.test:
        print("Running in test mode. No actual actions will be performed.")
        return
    
    # Run as daemon or in foreground
    if args.daemon:
        # Run as daemon
        try:
            asyncio.run(run_daemon())
        except KeyboardInterrupt:
            print("Bot stopped by user")
        except Exception as e:
            print(f"Error: {e}")
            # Exitcode 1 für Fehler
            sys.exit(1)
    else:
        # Run in foreground
        try:
            asyncio.run(run_daemon())
        except KeyboardInterrupt:
            print("Bot stopped by user")
        except Exception as e:
            print(f"Error: {e}")
            # Exitcode 1 für Fehler
            sys.exit(1)

if __name__ == "__main__":
    main()
