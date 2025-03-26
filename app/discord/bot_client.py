"""
Discord机器人客户端 - 负责与Discord API的实际连接和交互
"""
import discord
import logging
import asyncio
import os
import sys
import time
import json
import threading
import signal
import subprocess
from discord.ext import commands
from datetime import datetime
from dotenv import load_dotenv
import requests
from flask import current_app

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局变量，用于跟踪和管理机器人进程
DISCORD_BOT_PROCESS = None

class BotClient(commands.Bot):
    """扩展的Discord机器人客户端"""
    
    def __init__(self, token, command_prefix="!", intents=None):
        if intents is None:
            intents = discord.Intents.default()
            # 注意：需要在Discord开发者门户中启用这些特权意图
            intents.message_content = False  # 设置为False以避免特权意图错误
            intents.members = False  # 设置为False以避免特权意图错误
        
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.token = token
        self.start_time = datetime.utcnow()
    
    async def on_ready(self):
        """当机器人连接到Discord时触发"""
        logger.info(f'机器人已连接到Discord! 用户名: {self.user.name}, ID: {self.user.id}')
        logger.info(f'机器人存在于 {len(self.guilds)} 个服务器中')
        
        # 设置状态
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="群组管理系统"
        ))
    
    async def on_message(self, message):
        """当收到消息时触发"""
        # 忽略机器人自己的消息
        if message.author == self.user:
            return
            
        # 处理命令
        await self.process_commands(message)
    
    async def on_guild_join(self, guild):
        """当机器人加入新服务器时触发"""
        logger.info(f'机器人加入了新服务器: {guild.name} (ID: {guild.id})')
    
    async def on_guild_remove(self, guild):
        """当机器人被从服务器移除时触发"""
        logger.info(f'机器人被从服务器移除: {guild.name} (ID: {guild.id})')
    
    async def on_member_join(self, member):
        """当新成员加入服务器时触发"""
        logger.info(f'新成员加入: {member.name} (ID: {member.id}) 加入了 {member.guild.name}')
        # 这里可以添加欢迎消息和其他自动化功能
    
    async def on_member_remove(self, member):
        """当成员离开服务器时触发"""
        logger.info(f'成员离开: {member.name} (ID: {member.id}) 离开了 {member.guild.name}')
        # 这里可以添加告别消息和其他自动化功能

def run_bot(token):
    """运行Discord机器人"""
    try:
        # 创建机器人客户端
        bot = BotClient(token=token)
        
        # 添加基本命令
        @bot.command(name="ping")
        async def ping(ctx):
            """测试机器人是否在线"""
            await ctx.send(f"🏓 Pong! 延迟: {round(bot.latency * 1000)}ms")
        
        @bot.command(name="info")
        async def info(ctx):
            """显示机器人信息"""
            uptime = datetime.utcnow() - bot.start_time
            uptime_str = f"{uptime.days}天 {uptime.seconds//3600}小时 {(uptime.seconds//60)%60}分钟"
            
            embed = discord.Embed(
                title="Group Manager 机器人信息",
                color=discord.Color.blue()
            )
            embed.add_field(name="运行时间", value=uptime_str, inline=False)
            embed.add_field(name="服务器数量", value=str(len(bot.guilds)), inline=True)
            embed.add_field(name="延迟", value=f"{round(bot.latency * 1000)}ms", inline=True)
            embed.set_footer(text="由群组管理系统提供支持")
            
            await ctx.send(embed=embed)
        
        # 运行机器人
        bot.run(token)
    except Exception as e:
        logger.error(f"运行Discord机器人时出错: {str(e)}")
        return False
    
    return True

def start_bot_process(token, channel_ids=None):
    """启动Discord机器人进程
    
    Args:
        token: Discord机器人令牌
        channel_ids: 频道ID列表，逗号分隔的字符串
        
    Returns:
        进程ID或None（如果启动失败）
    """
    global DISCORD_BOT_PROCESS
    
    try:
        # 获取项目根目录
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        
        # 使用新的bot_runner.py脚本
        bot_runner_path = os.path.join(os.path.dirname(__file__), 'bot_runner.py')
        
        if not os.path.exists(bot_runner_path):
            logger.error(f"找不到机器人运行器脚本: {bot_runner_path}")
            return None
        
        # 准备环境变量
        env = os.environ.copy()
        env['DISCORD_BOT_TOKEN'] = token
        
        # 如果提供了频道ID，也设置到环境变量
        if channel_ids:
            env['DISCORD_BOT_CHANNEL_IDS'] = channel_ids
            logger.info(f"设置机器人频道: {channel_ids}")
        
        # 启动进程
        logger.info(f"正在启动Discord机器人进程...")
        
        # 在Windows上使用pythonw.exe来避免显示命令窗口
        if os.name == 'nt':
            cmd = ['pythonw', bot_runner_path]
        else:
            cmd = ['python3', bot_runner_path]
            
        DISCORD_BOT_PROCESS = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # 记录进程ID到文件
        pid_file = os.path.join(base_dir, 'discord_bot.pid')
        with open(pid_file, 'w') as f:
            f.write(str(DISCORD_BOT_PROCESS.pid))
        
        logger.info(f"Discord机器人进程已启动，PID: {DISCORD_BOT_PROCESS.pid}")
        return DISCORD_BOT_PROCESS.pid
        
    except Exception as e:
        logger.error(f"启动Discord机器人进程时出错: {str(e)}")
        return None

def stop_bot_process():
    """停止Discord机器人进程
    
    Returns:
        布尔值，表示是否成功停止进程
    """
    global DISCORD_BOT_PROCESS
    
    try:
        # 首先尝试使用全局变量中的进程
        if DISCORD_BOT_PROCESS:
            logger.info(f"正在停止Discord机器人进程 (PID: {DISCORD_BOT_PROCESS.pid})...")
            
            if os.name == 'nt':
                # Windows上使用taskkill来终止进程树
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(DISCORD_BOT_PROCESS.pid)])
            else:
                # Unix/Linux上使用kill命令
                os.kill(DISCORD_BOT_PROCESS.pid, signal.SIGTERM)
                
            DISCORD_BOT_PROCESS = None
            logger.info("Discord机器人进程已停止")
            return True
            
        # 如果全局变量中没有进程，尝试从PID文件中获取
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        pid_file = os.path.join(base_dir, 'discord_bot.pid')
        
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                try:
                    pid = int(f.read().strip())
                    logger.info(f"从PID文件中找到Discord机器人进程 (PID: {pid})...")
                    
                    if os.name == 'nt':
                        # Windows上使用taskkill
                        subprocess.call(['taskkill', '/F', '/T', '/PID', str(pid)])
                    else:
                        # Unix/Linux上使用kill命令
                        os.kill(pid, signal.SIGTERM)
                    
                    # 删除PID文件
                    os.remove(pid_file)
                    logger.info("Discord机器人进程已停止")
                    return True
                except (ValueError, ProcessLookupError):
                    # 无效的PID或者进程已经不存在
                    if os.path.exists(pid_file):
                        os.remove(pid_file)
                    logger.warning("找不到运行中的Discord机器人进程")
        
        logger.warning("没有找到运行中的Discord机器人进程")
        return False
            
    except Exception as e:
        logger.error(f"停止Discord机器人进程时出错: {str(e)}")
        return False

def check_bot_status(token):
    """
    检查Discord机器人的状态
    返回一个元组：(状态, 错误消息)
    状态可以是：'online', 'offline', 'error'
    """
    try:
        # 移除可能的前缀并确保正确的授权格式
        if token.startswith('Bot '):
            token = token[4:]
        
        # 确保令牌不包含引号或额外的空格
        token = token.strip(' "\'')
            
        headers = {
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json'
        }
        
        # 使用Discord API检查令牌是否有效
        response = requests.get(
            'https://discord.com/api/v10/users/@me',
            headers=headers
        )
        
        if response.status_code == 200:
            # 令牌有效，但还需要检查机器人是否真正在线
            bot_data = response.json()
            bot_name = bot_data.get('username', 'Unknown')
            logger.info(f"成功连接到Discord API，机器人名称: {bot_name}")
            
            # 1. 检查机器人进程是否在运行
            if DISCORD_BOT_PROCESS is None:
                return ('offline', "机器人进程未运行")
                
            # 2. 进一步检查连接状态 - 尝试获取机器人的Guilds列表
            try:
                guilds_response = requests.get(
                    'https://discord.com/api/v10/users/@me/guilds',
                    headers=headers,
                    timeout=5  # 添加超时参数
                )
                
                if guilds_response.status_code == 200:
                    # 真正连接到Discord
                    return ('online', None)
                else:
                    # API可访问但获取服务器列表失败
                    return ('offline', f"机器人可能已断开连接 (HTTP {guilds_response.status_code})")
            except requests.Timeout:
                return ('offline', "与Discord API通信超时")
            except Exception as e:
                return ('offline', f"检查连接状态时出错: {str(e)}")
        elif response.status_code == 401:
            # 令牌无效
            return ('error', "无效的机器人令牌")
        else:
            # 其他API错误
            return ('error', f"Discord API错误 (HTTP {response.status_code}): {response.text}")
    
    except Exception as e:
        logger.error(f"检查机器人状态时出错: {str(e)}")
        return ('error', str(e))

def get_guild_channels(token, guild_id):
    """获取Discord服务器的频道列表
    
    Args:
        token: Discord机器人令牌
        guild_id: Discord服务器ID
        
    Returns:
        list: 频道列表，每个频道包含id、name和type
    """
    import requests
    import logging
    from flask import current_app
    
    # 确保令牌格式正确
    if not token.startswith('Bot '):
        current_app.logger.info(f"添加Bot前缀到令牌...")
        token = f'Bot {token}'
    
    url = f'https://discord.com/api/v10/guilds/{guild_id}/channels'
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    current_app.logger.info(f"请求Discord频道列表URL: {url}")
    current_app.logger.info(f"请求头Authorization: {token[:15]}...")
    
    try:
        response = requests.get(url, headers=headers)
        current_app.logger.info(f"API响应状态码: {response.status_code}")
        
        if response.status_code != 200:
            current_app.logger.error(f"获取频道列表失败: {response.status_code}")
            current_app.logger.error(f"响应内容: {response.text}")
            return []
            
        channels = response.json()
        current_app.logger.info(f"成功获取到 {len(channels)} 个频道")
        
        # 获取父频道（分类）映射
        parent_map = {}
        for channel in channels:
            if channel.get('type') == 4:  # 4 = 分类频道
                parent_map[channel.get('id')] = channel.get('name')
        
        # 格式化返回结果，仅返回文本频道和语音频道
        formatted_channels = []
        for channel in channels:
            channel_type = channel.get('type')
            # 仅包含文本(0)和语音(2)频道
            if channel_type in [0, 2]:
                parent_id = channel.get('parent_id')
                formatted_channels.append({
                    'id': channel.get('id'),
                    'name': channel.get('name'),
                    'type': channel_type,
                    'parent_id': parent_id,
                    'parent_name': parent_map.get(parent_id, '未分类')
                })
        
        current_app.logger.info(f"过滤后返回 {len(formatted_channels)} 个可用频道")
        return formatted_channels
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"获取Discord频道时发生异常: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return []

def get_bot_guilds(token):
    """获取机器人所在的Discord服务器列表
    
    Args:
        token: Discord机器人令牌
        
    Returns:
        list: 服务器列表，每个服务器包含id和name
    """
    import requests
    import logging
    from flask import current_app
    
    # 确保令牌格式正确
    if not token.startswith('Bot '):
        current_app.logger.info(f"添加Bot前缀到令牌...")
        token = f'Bot {token}'
    
    url = 'https://discord.com/api/v10/users/@me/guilds'
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    current_app.logger.info(f"正在获取Discord服务器列表")
    current_app.logger.info(f"请求URL: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        current_app.logger.info(f"API响应状态码: {response.status_code}")
        
        if response.status_code != 200:
            current_app.logger.error(f"获取服务器列表失败: {response.status_code}")
            current_app.logger.error(f"响应内容: {response.text}")
            return []
            
        guilds = response.json()
        current_app.logger.info(f"成功获取到 {len(guilds)} 个服务器")
        
        # 格式化返回结果
        formatted_guilds = []
        for guild in guilds:
            formatted_guilds.append({
                'id': guild.get('id'),
                'name': guild.get('name')
            })
            
        return formatted_guilds
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"获取Discord服务器列表时发生异常: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return []

def get_guild_roles(token, guild_id):
    """获取Discord服务器的角色列表
    
    Args:
        token: Discord机器人令牌
        guild_id: Discord服务器ID
        
    Returns:
        list: 角色列表，每个角色包含id、name和color
    """
    import requests
    import logging
    from flask import current_app
    
    # 确保令牌格式正确
    if not token.startswith('Bot '):
        current_app.logger.info(f"添加Bot前缀到令牌...")
        token = f'Bot {token}'
    
    url = f'https://discord.com/api/v10/guilds/{guild_id}/roles'
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    current_app.logger.info(f"正在获取Discord服务器角色: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        current_app.logger.info(f"API响应状态码: {response.status_code}")
        
        if response.status_code != 200:
            current_app.logger.error(f"获取角色列表失败: {response.status_code}")
            current_app.logger.error(f"响应内容: {response.text}")
            return []
            
        roles = response.json()
        current_app.logger.info(f"成功获取Discord角色: {len(roles)}个")
        
        # 格式化返回结果，过滤掉@everyone角色
        formatted_roles = []
        for role in roles:
            # 跳过@everyone角色
            if role.get('name') != '@everyone':
                formatted_roles.append({
                    'id': role.get('id'),
                    'name': role.get('name'),
                    'color': role.get('color')
                })
                
        return formatted_roles
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"获取Discord角色时发生异常: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return []

def get_guild_members(token, guild_id, limit=1000):
    """获取Discord服务器的成员列表
    
    Args:
        token: Discord机器人令牌
        guild_id: Discord服务器ID
        limit: 返回的最大成员数
        
    Returns:
        list: 成员列表，每个成员包含id、username和roles
    """
    import requests
    import logging
    from flask import current_app
    
    # 确保令牌格式正确
    if not token.startswith('Bot '):
        current_app.logger.info(f"添加Bot前缀到令牌...")
        token = f'Bot {token}'
    
    url = f'https://discord.com/api/v10/guilds/{guild_id}/members?limit={limit}'
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    current_app.logger.info(f"正在获取Discord服务器成员: {guild_id}")
    
    try:
        response = requests.get(url, headers=headers)
        current_app.logger.info(f"API响应状态码: {response.status_code}")
        
        if response.status_code != 200:
            current_app.logger.error(f"获取成员列表失败: {response.status_code}")
            current_app.logger.error(f"响应内容: {response.text}")
            return []
            
        members = response.json()
        current_app.logger.info(f"成功获取Discord成员: {len(members)}个")
        
        # 格式化返回结果
        formatted_members = []
        for member in members:
            user = member.get('user', {})
            formatted_members.append({
                'id': user.get('id'),
                'username': user.get('username'),
                'roles': member.get('roles', [])
            })
                
        return formatted_members
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"获取Discord成员时发生异常: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return []

def get_bot_info(token):
    """获取Discord机器人信息
    
    Args:
        token: Discord机器人令牌
        
    Returns:
        dict: 机器人信息，包含id、username和avatar
    """
    import requests
    import logging
    from flask import current_app
    
    # 确保令牌格式正确
    if not token.startswith('Bot '):
        current_app.logger.info(f"添加Bot前缀到令牌...")
        token = f'Bot {token}'
    
    url = 'https://discord.com/api/v10/users/@me'
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    current_app.logger.info(f"正在获取Discord机器人信息")
    
    try:
        response = requests.get(url, headers=headers)
        current_app.logger.info(f"API响应状态码: {response.status_code}")
        
        if response.status_code != 200:
            current_app.logger.error(f"获取机器人信息失败: {response.status_code}")
            current_app.logger.error(f"响应内容: {response.text}")
            return None
            
        bot_info = response.json()
        current_app.logger.info(f"成功获取机器人信息: {bot_info.get('username')}")
        
        return {
            'id': bot_info.get('id'),
            'username': bot_info.get('username'),
            'avatar': bot_info.get('avatar')
        }
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"获取Discord机器人信息时发生异常: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return None
