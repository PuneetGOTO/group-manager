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
    
    if not token:
        print_error("未提供机器人令牌。使用 --token 参数或在.env文件中设置DISCORD_BOT_TOKEN")
        return
    
    if not guild_id:
        print_error("未提供服务器ID。使用 --guild 参数或在.env文件中设置DISCORD_GUILD_ID")
        return
    
    # 执行检查
    print_info("开始检查Discord机器人设置...")
    
    if check_bot_token(token):
        if check_guild_membership(token, guild_id):
            check_channel_permissions(token, guild_id)
    
    print_info("\n检查完成。")

if __name__ == "__main__":
    main()
