"""Discord API客户端"""
import requests
import json
import urllib.parse
from datetime import datetime, timedelta
from .config import (
    DISCORD_API_ENDPOINT, DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI,
    DISCORD_BOT_TOKEN, DISCORD_BOT_PERMISSIONS, DISCORD_AUTHORIZATION_BASE_URL, DISCORD_SCOPES, DISCORD_TOKEN_URL
)

class DiscordClient:
    """Discord API交互客户端"""
    
    @staticmethod
    def get_auth_url(state=None, use_login_redirect=False):
        """获取Discord OAuth授权URL"""
        from .config import DISCORD_AUTHORIZATION_BASE_URL, DISCORD_SCOPES, DISCORD_CLIENT_ID, DISCORD_BOT_PERMISSIONS
        
        # 确保client_id是字符串格式
        client_id = str(DISCORD_CLIENT_ID) if DISCORD_CLIENT_ID else '1353003948948066395'
        
        # 使用配置的权限值
        permissions = DISCORD_BOT_PERMISSIONS if DISCORD_BOT_PERMISSIONS else "826484758"
        
        # 使用官方的Discord OAuth2 URL格式
        # 参考: https://discord.com/developers/docs/topics/oauth2
        if use_login_redirect:
            # 构建通过登录页面的OAuth流程（类似Dyno的方式）
            scope = 'email identify guilds guilds.channels.read bot applications.entitlements activities.invites.write'
            # 先创建基本的授权URL
            auth_url = f"https://discord.com/oauth2/authorize?client_id={client_id}&scope={scope}&permissions={permissions}&response_type=code"
            
            # 添加重定向URI和状态参数
            auth_url += f"&redirect_uri={urllib.parse.quote(DISCORD_REDIRECT_URI)}"
            if state:
                auth_url += f"&state={state}"
                
            # 将整个URL编码并通过登录页面重定向
            encoded_auth_url = urllib.parse.quote(auth_url)
            full_auth_url = f"https://discord.com/login?redirect_to={encoded_auth_url}"
            return full_auth_url
        else:
            # 使用标准的官方Discord授权URL（推荐方式）
            scope = 'email identify guilds guilds.channels.read bot applications.entitlements activities.invites.write'
            auth_url = f"https://discord.com/oauth2/authorize?client_id={client_id}&scope={scope}&permissions={permissions}&response_type=code"
            
            # 添加重定向URI (需要URL编码)
            auth_url += f"&redirect_uri={urllib.parse.quote(DISCORD_REDIRECT_URI)}"
            
            # 添加状态参数
            if state:
                auth_url += f"&state={state}"
                
            return auth_url
    
    @staticmethod
    def exchange_code(code):
        """用授权码换取访问令牌"""
        from .config import DISCORD_TOKEN_URL
        
        data = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': DISCORD_REDIRECT_URI,
            'scope': ' '.join(['identify', 'email', 'guilds', 'guilds.channels.read', 'bot', 'applications.entitlements', 'activities.invites.write'])
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.post(DISCORD_TOKEN_URL, data=data, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取Discord访问令牌失败: {response.status_code} - {response.text}")
    
    @staticmethod
    def get_user_info(access_token):
        """获取Discord用户信息"""
        url = f"{DISCORD_API_ENDPOINT}/users/@me"
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取Discord用户信息失败: {response.status_code} - {response.text}")
    
    @staticmethod
    def get_user_guilds(access_token):
        """获取用户所在的Discord服务器列表"""
        url = f"{DISCORD_API_ENDPOINT}/users/@me/guilds"
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取用户服务器列表失败: {response.status_code} - {response.text}")
    
    @staticmethod
    def get_guild_members(guild_id):
        """获取服务器成员列表 (需要Bot令牌)"""
        if not DISCORD_BOT_TOKEN:
            raise Exception("缺少Discord机器人令牌")
            
        url = f"{DISCORD_API_ENDPOINT}/guilds/{guild_id}/members?limit=1000"
        headers = {
            'Authorization': f'Bot {DISCORD_BOT_TOKEN}'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取服务器成员列表失败: {response.status_code} - {response.text}")
    
    @staticmethod
    def refresh_token(refresh_token):
        """刷新访问令牌"""
        from .config import DISCORD_TOKEN_URL
        
        data = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.post(DISCORD_TOKEN_URL, data=data, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"刷新Discord令牌失败: {response.status_code} - {response.text}")
