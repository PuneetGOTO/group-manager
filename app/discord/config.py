"""Discord OAuth配置"""
import os

# Discord API设置
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID', '')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET', '')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:5000/auth/discord/callback')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN', '')

# OAuth授权范围
DISCORD_SCOPES = [
    'identify',                # 获取用户信息
    'email',                   # 获取用户邮箱
    'guilds',                  # 获取用户所在的服务器列表
    'guilds.members.read',     # 读取服务器成员信息
    'bot'                      # 添加机器人到服务器
]

# Discord API端点
DISCORD_API_ENDPOINT = 'https://discord.com/api/v10'
DISCORD_AUTHORIZATION_BASE_URL = f'{DISCORD_API_ENDPOINT}/oauth2/authorize'
DISCORD_TOKEN_URL = f'{DISCORD_API_ENDPOINT}/oauth2/token'
