#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import discord
import asyncio
import traceback
import time
from datetime import datetime

# 设置日志记录
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, 'discord_bot.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('discord_bot')

class SimpleBot(discord.Client):
    """简单的Discord机器人客户端，用于验证连接和基本功能"""
    
    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True  # 需要在开发者门户中启用此特权意图
        super().__init__(intents=intents, *args, **kwargs)
        self.start_time = datetime.utcnow()
        
    async def on_ready(self):
        """当机器人成功连接到Discord时触发"""
        logger.info(f'机器人 {self.user.name} (ID: {self.user.id}) 已连接到Discord')
        logger.info(f'机器人加入的服务器:')
        for guild in self.guilds:
            logger.info(f'- {guild.name} (ID: {guild.id})')
        
        # 写入PID文件，供其他进程检查
        pid_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'discord_bot.pid')
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
    async def on_message(self, message):
        """当收到消息时触发"""
        # 忽略自己的消息
        if message.author == self.user:
            return
            
        # 简单的回复功能，仅用于测试
        if message.content.startswith('!ping'):
            await message.channel.send('Pong!')
            
        elif message.content.startswith('!info'):
            uptime = datetime.utcnow() - self.start_time
            hours, remainder = divmod(uptime.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            await message.channel.send(
                f'机器人运行状态:\n'
                f'- 运行时间: {int(hours)}小时 {int(minutes)}分钟 {int(seconds)}秒\n'
                f'- 服务器数量: {len(self.guilds)}\n'
                f'- 版本: GroupManager Discord Bot v1.0'
            )

def main():
    """主函数，负责启动机器人"""
    logger.info('正在启动Discord机器人...')
    
    # 从环境变量获取令牌
    token = os.environ.get('DISCORD_BOT_TOKEN')
    
    if not token:
        logger.error('未设置DISCORD_BOT_TOKEN环境变量')
        sys.exit(1)
    
    # 创建并启动机器人
    bot = SimpleBot()
    
    try:
        logger.info('正在尝试连接到Discord...')
        bot.run(token)
    except discord.errors.LoginFailure:
        logger.error('无法登录到Discord，令牌可能无效')
        sys.exit(1)
    except discord.errors.PrivilegedIntentsRequired:
        logger.error('需要在Discord开发者门户中启用特权意图')
        sys.exit(1)
    except Exception as e:
        logger.error(f'启动机器人时出错: {str(e)}')
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()
