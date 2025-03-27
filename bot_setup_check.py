#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Discord机器人设置检查工具
用于验证机器人的权限和服务器设置是否正确
"""

import os
import sys
import requests
import argparse
from dotenv import load_dotenv
import colorama
from colorama import Fore, Style
import sqlite3
import pathlib

# 初始化彩色输出
colorama.init()

def print_success(message):
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")

def print_error(message):
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")

def print_warning(message):
    print(f"{Fore.YELLOW}! {message}{Style.RESET_ALL}")

def print_info(message):
    print(f"{Fore.BLUE}i {message}{Style.RESET_ALL}")

def print_title(message):
    print(f"\n{Fore.CYAN}=== {message} ==={Style.RESET_ALL}")

def check_bot_token(token):
    """检查机器人令牌是否有效"""
    print_title("检查机器人令牌")
    
    if not token or token.strip() == "":
        print_error("未提供机器人令牌")
        return False
    
    # 确保令牌格式正确
    if not token.startswith("Bot "):
        token = f"Bot {token}"
    
    # 请求机器人信息验证令牌
    headers = {
        "Authorization": token
    }
    
    try:
        response = requests.get("https://discord.com/api/v10/users/@me", headers=headers)
        
        if response.status_code == 200:
            bot_info = response.json()
            print_success(f"令牌有效 - 机器人名称: {bot_info.get('username')}#{bot_info.get('discriminator', '')}")
            return True
        else:
            print_error(f"令牌无效 - 状态码: {response.status_code}")
            if response.status_code == 401:
                print_info("这通常意味着令牌不正确或已过期")
            return False
    except Exception as e:
        print_error(f"验证令牌时出错: {str(e)}")
        return False

def check_guild_membership(token, guild_id):
    """检查机器人是否已加入指定的服务器"""
    print_title(f"检查服务器成员资格 (服务器ID: {guild_id})")
    
    if not token.startswith("Bot "):
        token = f"Bot {token}"
    
    headers = {
        "Authorization": token
    }
    
    try:
        # 获取机器人加入的所有服务器
        response = requests.get("https://discord.com/api/v10/users/@me/guilds", headers=headers)
        
        if response.status_code != 200:
            print_error(f"无法获取机器人的服务器列表 - 状态码: {response.status_code}")
            return False
        
        guilds = response.json()
        
        # 检查指定的服务器ID是否在列表中
        found = False
        for guild in guilds:
            if guild.get("id") == guild_id:
                found = True
                print_success(f"机器人已加入服务器 - 名称: {guild.get('name')}")
                break
        
        if not found:
            print_error("机器人未加入指定的服务器")
            print_info("请通过OAuth2邀请链接将机器人添加到您的服务器:")
            print_info(f"https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands")
            return False
        
        return True
    except Exception as e:
        print_error(f"检查服务器成员资格时出错: {str(e)}")
        return False

def check_channel_permissions(token, guild_id):
    """检查机器人是否有权限查看服务器中的频道"""
    print_title("检查频道权限")
    
    if not token.startswith("Bot "):
        token = f"Bot {token}"
    
    headers = {
        "Authorization": token
    }
    
    try:
        # 获取服务器的频道列表
        response = requests.get(f"https://discord.com/api/v10/guilds/{guild_id}/channels", headers=headers)
        
        if response.status_code != 200:
            print_error(f"无法获取频道列表 - 状态码: {response.status_code}")
            if response.status_code == 403:
                print_info("这通常意味着机器人没有足够的权限")
            return False
        
        channels = response.json()
        
        # 检查是否有文本频道
        text_channels = [ch for ch in channels if ch.get("type") == 0]
        
        if text_channels:
            print_success(f"发现 {len(text_channels)} 个文本频道")
            print_info("前5个频道:")
            for i, channel in enumerate(text_channels[:5]):
                print_info(f"  - #{channel.get('name')} (ID: {channel.get('id')})")
            return True
        else:
            print_warning("未发现任何文本频道")
            return False
    except Exception as e:
        print_error(f"检查频道权限时出错: {str(e)}")
        return False

def get_guilds_from_database():
    """从数据库中获取可用的Discord服务器信息"""
    try:
        # 尝试找到数据库文件
        db_paths = [
            os.path.join(os.getcwd(), "app.db"),
            os.path.join(os.getcwd(), "instance", "app.db"),
            os.path.join(os.path.dirname(os.getcwd()), "app.db"),
            os.path.join(os.path.dirname(os.getcwd()), "instance", "app.db")
        ]
        
        db_path = None
        for path in db_paths:
            if os.path.exists(path):
                db_path = path
                break
        
        if not db_path:
            print_warning("无法找到数据库文件，无法自动获取服务器信息")
            return []
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 尝试获取群组信息
        cursor.execute("SELECT id, name, discord_id FROM `group` WHERE discord_id IS NOT NULL AND discord_id != ''")
        groups = cursor.fetchall()
        
        # 如果没有找到群组表，可能是因为表名不同
        if not groups:
            print_warning("在数据库中未找到群组信息")
            return []
        
        guilds = []
        for group in groups:
            guilds.append({
                "id": str(group[0]),
                "name": group[1],
                "discord_id": group[2]
            })
        
        conn.close()
        
        if guilds:
            print_success(f"从数据库中找到 {len(guilds)} 个Discord服务器")
        
        return guilds
    except Exception as e:
        print_error(f"从数据库获取服务器信息时出错: {str(e)}")
        return []

def main():
    """主函数"""
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="检查Discord机器人设置和权限")
    parser.add_argument("--token", help="Discord机器人令牌")
    parser.add_argument("--guild", help="Discord服务器ID")
    args = parser.parse_args()
    
    # 加载.env文件中的环境变量
    load_dotenv()
    
    # 获取令牌和服务器ID
    token = args.token or os.getenv("DISCORD_BOT_TOKEN")
    guild_id = args.guild or os.getenv("DISCORD_GUILD_ID")
    
    # 如果从命令行和环境变量都没有获取到guild_id，尝试从数据库获取
    if not guild_id:
        print_info("正在尝试从数据库中获取Discord服务器信息...")
        guilds = get_guilds_from_database()
        
        if guilds:
            print_info("找到以下Discord服务器:")
            for i, guild in enumerate(guilds):
                print_info(f"{i+1}. {guild['name']} (ID: {guild['discord_id']})")
            
            # 自动选择第一个服务器
            guild_id = guilds[0]['discord_id']
            print_info(f"自动选择第一个服务器: {guilds[0]['name']} (ID: {guild_id})")
        
    if not token:
        print_error("未提供机器人令牌。使用 --token 参数或在.env文件中设置DISCORD_BOT_TOKEN")
        print_info("如何获取机器人令牌:")
        print_info("1. 前往 https://discord.com/developers/applications")
        print_info("2. 选择您的应用或创建一个新应用")
        print_info("3. 在左侧菜单中选择'Bot'")
        print_info("4. 点击'Reset Token'或复制已有令牌")
        print_info("5. 将令牌添加到.env文件: DISCORD_BOT_TOKEN=您的令牌")
        return
    
    if not guild_id:
        print_error("未提供服务器ID。使用 --guild 参数或在.env文件中设置DISCORD_GUILD_ID")
        print_info("如何获取服务器ID:")
        print_info("1. 在Discord中启用开发者模式 (用户设置 → 高级 → 开发者模式)")
        print_info("2. 右键点击服务器图标")
        print_info("3. 选择'复制ID'")
        print_info("4. 将ID添加到.env文件: DISCORD_GUILD_ID=您的服务器ID")
        print_info("\n或直接使用参数运行: python bot_setup_check.py --guild 您的服务器ID")
        return
    
    # 执行检查
    print_info("开始检查Discord机器人设置...")
    
    if check_bot_token(token):
        if check_guild_membership(token, guild_id):
            check_channel_permissions(token, guild_id)
    
    print_info("\n检查完成。")

if __name__ == "__main__":
    main()
