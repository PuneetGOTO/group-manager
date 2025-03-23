"""Discord OAuth配置"""
import os

# Discord API设置 - 使用环境变量，避免硬编码敏感信息
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'https://web-production-a67c.up.railway.app/discord/callback')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# 机器人权限设置
# 8代表管理员权限（Administrator）
DISCORD_BOT_PERMISSIONS = "8"

# OAuth授权范围 - 使用更全面的作用域配置
DISCORD_SCOPES = [
    'email',                    # 获取用户邮箱
    'identify',                 # 获取用户信息
    'guilds',                   # 获取用户所在的服务器列表
    'guilds.members.read',      # 读取服务器成员信息
    'guilds.join',              # 允许机器人加入用户的服务器
    'guilds.channels.read',     # 读取频道信息
    'bot',                      # 添加机器人到服务器
    'applications.commands'     # 允许应用程序命令
]

# Discord API端点
DISCORD_API_ENDPOINT = 'https://discord.com/api/v10'
DISCORD_AUTHORIZATION_BASE_URL = f'{DISCORD_API_ENDPOINT}/oauth2/authorize'
DISCORD_TOKEN_URL = f'{DISCORD_API_ENDPOINT}/oauth2/token'
