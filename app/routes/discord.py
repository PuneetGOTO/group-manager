"""Discord集成路由"""
from flask import Blueprint, redirect, url_for, flash, session, request, render_template
from flask_login import login_required, current_user
from app.discord.client import DiscordClient
from app.models import User, Group
from app import db
from datetime import datetime, timedelta
import json
import os
import secrets
import requests  # 添加直接使用requests

discord_bp = Blueprint('discord', __name__)

@discord_bp.route('/connect')
@login_required
def connect():
    """连接Discord账号"""
    # 生成随机状态用于验证
    state = secrets.token_hex(16)
    session['oauth_state'] = state
    
    # 重定向到Discord授权页面
    auth_url = DiscordClient.get_auth_url(state)
    return redirect(auth_url)

@discord_bp.route('/callback')
@login_required
def callback():
    """Discord OAuth回调处理"""
    # 验证状态参数
    state = request.args.get('state')
    stored_state = session.pop('oauth_state', None)
    
    if not state or state != stored_state:
        flash('授权验证失败，请重试', 'danger')
        return redirect(url_for('user.settings'))
    
    error = request.args.get('error')
    if error:
        flash(f'Discord授权错误: {error}', 'danger')
        return redirect(url_for('user.settings'))
    
    code = request.args.get('code')
    if not code:
        flash('未收到授权码，请重试', 'danger')
        return redirect(url_for('user.settings'))
    
    try:
        # 交换授权码获取访问令牌
        token_data = DiscordClient.exchange_code(code)
        
        # 获取Discord用户信息
        access_token = token_data['access_token']
        user_data = DiscordClient.get_user_info(access_token)
        
        # 更新用户的Discord关联信息
        current_user.discord_id = user_data['id']
        current_user.discord_username = f"{user_data['username']}#{user_data['discriminator']}" if 'discriminator' in user_data else user_data['username']
        current_user.discord_avatar = f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png" if user_data.get('avatar') else None
        current_user.discord_access_token = access_token
        current_user.discord_refresh_token = token_data.get('refresh_token')
        
        # 计算令牌过期时间
        expires_in = token_data.get('expires_in', 604800)  # 默认7天
        current_user.discord_token_expires = datetime.utcnow() + timedelta(seconds=expires_in)
        
        db.session.commit()
        flash('Discord账号已成功连接', 'success')
        
    except Exception as e:
        flash(f'连接Discord失败: {str(e)}', 'danger')
    
    return redirect(url_for('user.settings'))

@discord_bp.route('/disconnect')
@login_required
def disconnect():
    """断开Discord账号连接"""
    current_user.disconnect_discord()
    flash('Discord账号已断开连接', 'success')
    return redirect(url_for('user.settings'))

@discord_bp.route('/guilds')
@login_required
def guilds():
    """显示用户的Discord服务器列表"""
    if not current_user.is_connected_to_discord():
        flash('请先连接Discord账号', 'warning')
        return redirect(url_for('user.settings'))
    
    # 检查令牌是否过期
    if current_user.discord_token_expires and current_user.discord_token_expires <= datetime.utcnow():
        try:
            # 尝试刷新令牌
            token_data = DiscordClient.refresh_token(current_user.discord_refresh_token)
            current_user.discord_access_token = token_data['access_token']
            current_user.discord_refresh_token = token_data.get('refresh_token')
            expires_in = token_data.get('expires_in', 604800)
            current_user.discord_token_expires = datetime.utcnow() + timedelta(seconds=expires_in)
            db.session.commit()
        except:
            flash('Discord会话已过期，请重新连接', 'warning')
            return redirect(url_for('discord.connect'))
    
    try:
        # 直接使用requests，绕过DiscordClient类
        url = "https://discord.com/api/v10/users/@me/guilds"
        headers = {
            'Authorization': f'Bearer {current_user.discord_access_token}',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"API错误: {response.status_code}")
        
        # 确保我们可以安全地处理响应内容
        try:
            # 尝试手动修复常见的JSON解析问题
            content = response.content.decode('utf-8')
            # 替换可能导致问题的特殊字符
            content = content.replace('&', '_')
            # 尝试解析修复后的内容
            guilds = json.loads(content)
        except json.JSONDecodeError as e:
            # 如果仍然无法解析，则使用空列表
            guilds = []
            flash(f'解析Discord服务器列表时出错，可能无法显示所有服务器: {str(e)}', 'warning')
        
        return render_template('discord/guilds.html', guilds=guilds)
    
    except Exception as e:
        flash(f'获取Discord服务器列表失败: {str(e)}', 'danger')
        # 出错时也提供空列表，确保页面可以正常加载
        return render_template('discord/guilds.html', guilds=[])

@discord_bp.route('/guild/<guild_id>/import')
@login_required
def import_guild(guild_id):
    """将Discord服务器导入为群组"""
    if not current_user.is_connected_to_discord():
        flash('请先连接Discord账号', 'warning')
        return redirect(url_for('user.settings'))
    
    try:
        # 获取服务器详情
        guilds = DiscordClient.get_user_guilds(current_user.discord_access_token)
        guild = next((g for g in guilds if g['id'] == guild_id), None)
        
        if not guild:
            flash('未找到指定的Discord服务器', 'danger')
            return redirect(url_for('discord.guilds'))
        
        # 检查权限 - 用户必须是服务器管理员
        permissions = int(guild.get('permissions', 0))
        is_admin = (permissions & 0x8) == 0x8
        
        if not is_admin:
            flash('您需要拥有管理员权限才能导入此Discord服务器', 'warning')
            return redirect(url_for('discord.guilds'))
        
        # 检查是否已经导入过此服务器
        existing_group = Group.query.filter_by(discord_id=guild_id).first()
        if existing_group:
            flash('此Discord服务器已被导入，无需重复操作', 'info')
            return redirect(url_for('groups.view', group_id=existing_group.id))
        
        # 创建新群组
        new_group = Group(
            name=guild['name'],
            description=f"从Discord服务器'{guild['name']}'导入的群组",
            avatar=f"https://cdn.discordapp.com/icons/{guild_id}/{guild['icon']}.png" if guild.get('icon') else 'default_group.png',
            banner='default_banner.jpg',
            owner_id=current_user.id,
            discord_id=guild_id
        )
        
        # 保存到数据库
        db.session.add(new_group)
        db.session.commit()
        
        flash(f"Discord服务器 '{guild['name']}' 已成功导入为群组", 'success')
        return redirect(url_for('groups.view', group_id=new_group.id))
        
    except Exception as e:
        flash(f'导入Discord服务器失败: {str(e)}', 'danger')
        return redirect(url_for('discord.guilds'))
