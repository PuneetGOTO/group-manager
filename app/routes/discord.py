"""Discord集成路由"""
from flask import Blueprint, redirect, url_for, flash, session, request, render_template, current_app
from flask_login import login_required, current_user
from app.discord.client import DiscordClient
from app.models import User, Group
from app.models.user import group_members
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

@discord_bp.route('/guild/<guild_id>/sync_members')
@login_required
def sync_guild_members(guild_id):
    """同步Discord服务器成员到群组"""
    if not current_user.is_connected_to_discord():
        flash('请先连接Discord账号', 'warning')
        return redirect(url_for('user.settings'))
    
    # 获取关联的群组
    group = Group.query.filter_by(discord_id=guild_id).first()
    if not group:
        flash('未找到关联的群组', 'danger')
        return redirect(url_for('discord.guilds'))
    
    # 检查权限
    if group.owner_id != current_user.id:
        flash('只有群组创建者可以同步成员', 'warning')
        return redirect(url_for('groups.view', group_id=group.id))
    
    try:
        # 获取Discord服务器成员
        members = DiscordClient.get_guild_members(
            current_user.discord_access_token,
            guild_id
        )
        
        sync_count = 0
        for member in members:
            user_data = member.get('user', {})
            discord_id = user_data.get('id')
            
            if not discord_id:
                continue
                
            # 尝试查找已有用户
            user = User.query.filter_by(discord_id=discord_id).first()
            
            # 获取用户实际显示名称和角色
            discord_username = user_data.get('username', '')
            nickname = member.get('nick')  # Discord中设置的昵称
            display_name = nickname or discord_username  # 优先使用昵称
            
            # 收集用户角色ID列表
            role_ids = member.get('roles', [])
            
            # 如果没有找到，创建一个新用户
            if not user:
                # 为Discord用户生成随机密码
                import secrets
                random_password = secrets.token_hex(16)
                
                # 创建新用户，使用实际用户名
                user = User(
                    username=display_name,  # 使用真实显示名称而不是ID
                    email=f"discord_{discord_id}@placeholder.com",  # 占位邮箱
                    password=random_password,  # 设置随机密码
                    discord_id=discord_id,
                    discord_username=display_name,
                    discord_avatar=f"https://cdn.discordapp.com/avatars/{discord_id}/{user_data.get('avatar')}.png" if user_data.get('avatar') else None
                )
                db.session.add(user)
                db.session.flush()  # 确保用户有ID
            else:
                # 更新现有用户的Discord用户名
                user.discord_username = display_name
                if user_data.get('avatar'):
                    user.discord_avatar = f"https://cdn.discordapp.com/avatars/{discord_id}/{user_data.get('avatar')}.png"
            
            # 检查用户是否已经在群组中
            stmt = db.select(group_members).where(
                (group_members.c.user_id == user.id) & 
                (group_members.c.group_id == group.id)
            )
            existing_membership = db.session.execute(stmt).first()
            
            # 如果不在群组中，添加用户到群组
            if not existing_membership:
                # 判断角色 - 更复杂的角色处理
                is_owner = member.get('owner', False)
                is_admin = False
                
                # 将Discord角色ID转换为角色名并存储
                discord_roles = ','.join([str(role_id) for role_id in role_ids]) if role_ids else ''
                
                # 检查是否为管理员 - 根据身份组判断
                if discord_roles and any(r in ['owner', 'administrator'] for r in role_ids):
                    is_admin = True
                
                # 设置用户在群组中的角色
                role = 'admin' if (is_owner or is_admin) else 'member'
                
                # 添加到群组，同时存储Discord角色信息
                stmt = group_members.insert().values(
                    user_id=user.id,
                    group_id=group.id,
                    role=role,
                    joined_at=datetime.utcnow(),
                    discord_roles=discord_roles  # 存储Discord角色ID列表
                )
                db.session.execute(stmt)
                sync_count += 1
            else:
                # 更新现有成员的角色信息
                discord_roles = ','.join([str(role_id) for role_id in role_ids]) if role_ids else ''
                stmt = group_members.update().where(
                    (group_members.c.user_id == user.id) & 
                    (group_members.c.group_id == group.id)
                ).values(
                    discord_roles=discord_roles
                )
                db.session.execute(stmt)
        
        db.session.commit()
        flash(f'成功同步了 {sync_count} 名成员', 'success')
    
    except Exception as e:
        db.session.rollback()
        error_message = str(e)
        current_app.logger.error(f"同步Discord成员错误: {error_message}")
        
        # 提供更友好的错误提示
        if "403" in error_message and "Missing Access" in error_message:
            flash('同步成员失败: Discord机器人缺少访问权限。请在Discord开发者门户中开启"Server Members Intent"权限，并确保机器人已经被添加到服务器。', 'danger')
        elif "401" in error_message:
            flash('同步成员失败: 授权失败，您可能需要重新连接Discord账号。', 'danger')
        else:
            flash(f'同步成员失败: {error_message}', 'danger')
    
    return redirect(url_for('groups.view', group_id=group.id))
