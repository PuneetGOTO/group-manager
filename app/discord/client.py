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
from flask import current_app

class DiscordClient:
    """Discord API交互客户端"""
    
    @staticmethod
    def get_auth_url(state=None, use_login_redirect=False):
        """获取Discord OAuth授权URL"""
        from .config import DISCORD_AUTHORIZATION_BASE_URL, DISCORD_SCOPES, DISCORD_CLIENT_ID, DISCORD_BOT_PERMISSIONS, DISCORD_REDIRECT_URI
        
        # 验证必需的凭据是否存在
        if not DISCORD_CLIENT_ID:
            current_app.logger.error("Discord客户端ID未设置，请在环境变量中配置DISCORD_CLIENT_ID")
            return None

        # 使用配置的权限值
        permissions = DISCORD_BOT_PERMISSIONS if DISCORD_BOT_PERMISSIONS else "268643382"
        
        # 正确编码scope列表，使用配置文件中定义的作用域
        scope = urllib.parse.quote(' '.join(DISCORD_SCOPES))
        
        # 构建基本授权URL
        auth_url = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&scope={scope}&permissions={permissions}&response_type=code&integration_type=0"
        
        # 添加重定向URI (确保已URL编码)
        auth_url += f"&redirect_uri={urllib.parse.quote(DISCORD_REDIRECT_URI)}"
        
        # 添加状态参数
        if state:
            auth_url += f"&state={state}"
            
        current_app.logger.info(f"生成的Discord授权URL: {auth_url}")
        return auth_url
    
    @staticmethod
    def exchange_code(code):
        """用授权码换取访问令牌"""
        from .config import DISCORD_TOKEN_URL, DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI, DISCORD_SCOPES
        
        # 验证必需的凭据是否存在
        if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
            current_app.logger.error("Discord凭据未设置，请在环境变量中配置DISCORD_CLIENT_ID和DISCORD_CLIENT_SECRET")
            return None
        
        data = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': DISCORD_REDIRECT_URI,
            'scope': ' '.join(DISCORD_SCOPES)  # 使用配置中定义的作用域列表
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
        
        current_app.logger.debug(f"正在请求Discord服务器列表: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                try:
                    # 尝试解析JSON响应
                    return response.json()
                except json.JSONDecodeError as e:
                    # 记录原始响应内容以便调试
                    current_app.logger.error(f"Discord API返回内容解析失败: {str(e)}")
                    current_app.logger.debug(f"响应内容: {response.text[:200]}...") # 只记录前200个字符避免日志过大
                    
                    # 尝试手动清理响应内容中的特殊字符
                    cleaned_text = response.text.replace('&', '&amp;')
                    try:
                        return json.loads(cleaned_text)
                    except:
                        raise Exception(f"Discord服务器列表JSON解析错误: {str(e)}")
            else:
                raise Exception(f"获取Discord服务器列表失败: {response.status_code} - {response.text}")
        except Exception as e:
            current_app.logger.error(f"获取Discord服务器列表异常: {str(e)}")
            raise
    
    @staticmethod
    def get_guild_members(access_token, guild_id):
        """获取服务器成员列表 (使用用户访问令牌或机器人令牌)"""
        # 尝试使用用户访问令牌
        url = f"{DISCORD_API_ENDPOINT}/guilds/{guild_id}/members?limit=1000"
        
        # 首先尝试使用用户访问令牌
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        response = requests.get(url, headers=headers)
        
        # 如果使用用户令牌失败，尝试使用机器人令牌
        if response.status_code != 200 and DISCORD_BOT_TOKEN:
            current_app.logger.info(f"使用用户令牌获取成员失败，尝试使用机器人令牌: {response.status_code}")
            headers = {
                'Authorization': f'Bot {DISCORD_BOT_TOKEN}'
            }
            response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            error_msg = f"获取服务器成员列表失败: {response.status_code} - {response.text}"
            current_app.logger.error(error_msg)
            raise Exception(error_msg)
    
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
