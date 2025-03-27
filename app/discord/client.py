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
        
        # 构建基本授权URL - 使用discord.com而不是discord.com/api
        auth_url = f"https://discord.com/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&scope={scope}&permissions={permissions}&response_type=code&integration_type=0"
        
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
        from flask import current_app
        
        # 尝试使用用户访问令牌
        url = f"{DISCORD_API_ENDPOINT}/guilds/{guild_id}/members?limit=1000"
        
        # 首先尝试使用用户访问令牌
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        try:
            current_app.logger.debug(f"尝试使用用户令牌获取服务器成员: {url}")
            response = requests.get(url, headers=headers)
            current_app.logger.debug(f"用户令牌响应状态码: {response.status_code}")
            
            # 如果使用用户令牌失败，尝试使用机器人令牌
            if response.status_code != 200 and DISCORD_BOT_TOKEN:
                current_app.logger.info(f"使用用户令牌获取成员失败，尝试使用机器人令牌: {response.status_code}")
                headers = {
                    'Authorization': f'Bot {DISCORD_BOT_TOKEN}'
                }
                
                # 检查机器人权限
                current_app.logger.debug(f"机器人令牌: {'已配置' if DISCORD_BOT_TOKEN else '未配置'}")
                current_app.logger.debug(f"机器人权限: {DISCORD_BOT_PERMISSIONS}")
                
                response = requests.get(url, headers=headers)
                current_app.logger.debug(f"机器人令牌响应状态码: {response.status_code}")
                current_app.logger.debug(f"响应内容: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"获取服务器成员列表失败: {response.status_code} - {response.text}"
                current_app.logger.error(error_msg)
                
                # 提供更有帮助的错误信息
                if response.status_code == 403:
                    current_app.logger.error("错误原因: 机器人缺少访问权限。请确保机器人已添加到服务器并具有'Server Members Intent'权限")
                elif response.status_code == 401:
                    current_app.logger.error("错误原因: 授权失败。请检查令牌是否有效，或用户是否有'guilds.members.read'OAuth2权限")
                
                raise Exception(error_msg)
                
        except requests.RequestException as e:
            error_msg = f"请求Discord API时出错: {str(e)}"
            current_app.logger.error(error_msg)
            raise Exception(error_msg)
    
    @staticmethod
    def get_guild_channels(guild_id):
        """获取Discord服务器的频道列表"""
        url = f"{DISCORD_API_ENDPOINT}/guilds/{guild_id}/channels"
        
        # 使用机器人令牌访问
        headers = {
            'Authorization': f'Bot {DISCORD_BOT_TOKEN}'
        }
        
        try:
            current_app.logger.debug(f"正在请求Discord服务器频道列表: {url}")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                channels = response.json()
                # 按类型和名称排序
                channels.sort(key=lambda x: (x.get('type', 0), x.get('name', '')))
                return channels
            else:
                error_msg = f"获取服务器频道列表失败: {response.status_code} - {response.text[:100]}"
                current_app.logger.error(error_msg)
                return []
        except Exception as e:
            current_app.logger.error(f"获取Discord服务器频道异常: {str(e)}")
            return []
    
    @staticmethod
    def get_guild_roles(guild_id):
        """获取Discord服务器的角色列表"""
        url = f"{DISCORD_API_ENDPOINT}/guilds/{guild_id}/roles"
        
        # 使用机器人令牌访问
        headers = {
            'Authorization': f'Bot {DISCORD_BOT_TOKEN}'
        }
        
        try:
            current_app.logger.debug(f"正在请求Discord服务器角色列表: {url}")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                roles = response.json()
                # 按位置排序（Discord中角色的显示顺序）
                roles.sort(key=lambda x: x.get('position', 0), reverse=True)
                return roles
            else:
                error_msg = f"获取服务器角色列表失败: {response.status_code} - {response.text[:100]}"
                current_app.logger.error(error_msg)
                return []
        except Exception as e:
            current_app.logger.error(f"获取Discord服务器角色异常: {str(e)}")
            return []
    
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
