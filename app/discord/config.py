"""Discord OAuth配置"""
import os

# Discord API设置 - 使用环境变量，避免硬编码敏感信息
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'https://web-production-a67c.up.railway.app/discord/callback')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# 机器人权限设置
# 268643382代表用户指定的权限配置
DISCORD_BOT_PERMISSIONS = "268643382"

# OAuth授权范围 - 使用更全面的作用域配置
DISCORD_SCOPES = [
    'email',                    # 获取用户邮箱
    'identify',                 # 获取用户信息
    'guilds',                   # 获取用户所在的服务器列表
    'guilds.members.read',      # 读取服务器成员信息
    'bot',                      # 添加机器人到服务器
    'applications.commands'     # 允许应用程序命令
]

# Discord API端点
DISCORD_API_ENDPOINT = 'https://discord.com/api/v10'
DISCORD_AUTHORIZATION_BASE_URL = f'{DISCORD_API_ENDPOINT}/oauth2/authorize'
DISCORD_TOKEN_URL = f'{DISCORD_API_ENDPOINT}/oauth2/token'
