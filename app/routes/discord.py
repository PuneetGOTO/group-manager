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
            avatar='default_group.png',  # 使用默认图片避免URL错误
            banner='default_banner.jpg',
            owner_id=current_user.id,
            discord_id=guild_id
        )
        
        # 尝试设置Discord图标
        if guild.get('icon'):
            new_group.avatar = f"https://cdn.discordapp.com/icons/{guild_id}/{guild['icon']}.png"
        
        # 保存到数据库
        db.session.add(new_group)
        db.session.commit()
        
        flash(f"Discord服务器 '{guild['name']}' 已成功导入为群组", 'success')
        return redirect(url_for('groups.view', group_id=new_group.id))
        
    except Exception as e:
        flash(f'导入Discord服务器失败: {str(e)}', 'danger')
        return redirect(url_for('discord.guilds'))

@discord_bp.route('/sync-guild-members/<guild_id>')
@login_required
def sync_guild_members(guild_id):
    """同步Discord服务器成员到本地群组"""
    # 检查用户是否已连接Discord
    if not current_user.discord_id:
        flash('请先连接您的Discord账号', 'warning')
        return redirect(url_for('discord.connect'))
    
    # 查找对应的本地群组
    group = Group.query.filter_by(discord_id=guild_id).first()
    if not group:
        flash('未找到关联的群组', 'danger')
        return redirect(url_for('discord.guilds'))
    
    # 检查权限
    if group.owner_id != current_user.id:
        flash('只有群组创建者可以同步成员', 'warning')
        return redirect(url_for('groups.view', group_id=group.id))
    
    try:
        # 获取Discord服务器角色列表
        roles_map = DiscordClient.get_guild_roles(
            current_user.discord_access_token,
            guild_id
        )
        
        # 获取Discord服务器成员
        members = DiscordClient.get_guild_members(
            current_user.discord_access_token,
            guild_id
        )
        
        # 检查是否成功获取到成员
        if not members:
            flash('未能获取到Discord服务器成员，请确保机器人拥有正确的权限', 'warning')
            return redirect(url_for('groups.view', group_id=group.id))
        
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
            
            # 将Discord角色ID转换为角色名并存储
            discord_roles = ','.join([str(role_id) for role_id in role_ids]) if role_ids else ''
            
            # 是否为服务器所有者或管理员
            is_owner = member.get('owner', False)
            is_admin = False
            
            # 检查用户角色中是否包含管理员权限
            for role_id in role_ids:
                role_id_str = str(role_id)
                if role_id_str in roles_map:
                    role_data = roles_map[role_id_str]
                    # Discord权限中，管理员权限是8（或者包含管理员关键字）
                    permissions = role_data.get('permissions', 0)
                    # 确保permissions是整数
                    if isinstance(permissions, str):
                        try:
                            permissions = int(permissions)
                        except (ValueError, TypeError):
                            permissions = 0
                    
                    if permissions & 8 or 'admin' in role_data.get('name', '').lower():
                        is_admin = True
                        break
                        
            # 设置用户在群组中的角色
            role = 'admin' if (is_owner or is_admin) else 'member'
            
            # 如果不在群组中，添加用户到群组
            if not existing_membership:
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
                stmt = group_members.update().where(
                    (group_members.c.user_id == user.id) & 
                    (group_members.c.group_id == group.id)
                ).values(
                    discord_roles=discord_roles,
                    role=role  # 更新成员在平台中的角色
                )
                db.session.execute(stmt)
        
        db.session.commit()
        flash(f'成功同步了 {sync_count} 名成员，所有成员角色已更新', 'success')
    
    except Exception as e:
        db.session.rollback()
        error_message = str(e)
        current_app.logger.error(f"同步Discord成员错误: {error_message}")
        
        # 提供更友好的错误提示
        if "403" in error_message and "Missing Access" in error_message:
            flash('同步成员失败: Discord机器人缺少访问权限。请在Discord开发者门户中开启"Server Members Intent"权限，并确保机器人已经被添加到服务器。', 'danger')
        elif "401" in error_message:
            flash('同步成员失败: 认证失败，您可能需要重新连接Discord账号。', 'danger')
        else:
            flash(f'同步成员失败: {error_message}', 'danger')
    
    return redirect(url_for('groups.view', group_id=group.id))

@discord_bp.route('/sync-guild-members/<guild_id>')
@login_required
def sync_guild_members(guild_id):
    """同步Discord服务器成员到本地群组"""
    # 检查用户是否已连接Discord
    if not current_user.discord_id:
        flash('请先连接您的Discord账号', 'warning')
        return redirect(url_for('discord.connect'))
    
    # 查找对应的本地群组
    group = Group.query.filter_by(discord_id=guild_id).first()
    if not group:
        flash('未找到关联的群组', 'danger')
        return redirect(url_for('discord.guilds'))
    
    # 检查权限
    if group.owner_id != current_user.id:
        flash('只有群组创建者可以同步成员', 'warning')
        return redirect(url_for('groups.view', group_id=group.id))
    
    try:
        # 获取Discord服务器角色列表
        roles_map = DiscordClient.get_guild_roles(
            current_user.discord_access_token,
            guild_id
        )
        
        # 获取Discord服务器成员
        members = DiscordClient.get_guild_members(
            current_user.discord_access_token,
            guild_id
        )
        
        # 检查是否成功获取到成员
        if not members:
            flash('未能获取到Discord服务器成员，请确保机器人拥有正确的权限', 'warning')
            return redirect(url_for('groups.view', group_id=group.id))
        
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
            
            # 将Discord角色ID转换为角色名并存储
            discord_roles = ','.join([str(role_id) for role_id in role_ids]) if role_ids else ''
            
            # 是否为服务器所有者或管理员
            is_owner = member.get('owner', False)
            is_admin = False
            
            # 检查用户角色中是否包含管理员权限
            for role_id in role_ids:
                role_id_str = str(role_id)
                if role_id_str in roles_map:
                    role_data = roles_map[role_id_str]
                    # Discord权限中，管理员权限是8（或者包含管理员关键字）
                    permissions = role_data.get('permissions', 0)
                    # 确保permissions是整数
                    if isinstance(permissions, str):
                        try:
                            permissions = int(permissions)
                        except (ValueError, TypeError):
                            permissions = 0
                    
                    if permissions & 8 or 'admin' in role_data.get('name', '').lower():
                        is_admin = True
                        break
                        
            # 设置用户在群组中的角色
            role = 'admin' if (is_owner or is_admin) else 'member'
            
            # 如果不在群组中，添加用户到群组
            if not existing_membership:
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
                stmt = group_members.update().where(
                    (group_members.c.user_id == user.id) & 
                    (group_members.c.group_id == group.id)
                ).values(
                    discord_roles=discord_roles,
                    role=role  # 更新成员在平台中的角色
                )
                db.session.execute(stmt)
        
        db.session.commit()
        flash(f'成功同步了 {sync_count} 名成员，所有成员角色已更新', 'success')
    
    except Exception as e:
        db.session.rollback()
        error_message = str(e)
        current_app.logger.error(f"同步Discord成员错误: {error_message}")
        
        # 提供更友好的错误提示
        if "403" in error_message and "Missing Access" in error_message:
            flash('同步成员失败: Discord机器人缺少访问权限。请在Discord开发者门户中开启"Server Members Intent"权限，并确保机器人已经被添加到服务器。', 'danger')
        elif "401" in error_message:
            flash('同步成员失败: 认证失败，您可能需要重新连接Discord账号。', 'danger')
        else:
            flash(f'同步成员失败: {error_message}', 'danger')
    
    return redirect(url_for('groups.view', group_id=group.id))

@discord_bp.route('/guilds/<guild_id>/sync_roles')
@login_required
def sync_guild_roles(guild_id):
    """同步Discord服务器角色"""
    # 检查用户是否已连接Discord
    if not current_user.discord_id or not current_user.discord_access_token:
        flash('请先连接您的Discord账号', 'warning')
        return redirect(url_for('discord.connect'))
    
    # 查找对应的本地群组
    group = Group.query.filter_by(discord_id=guild_id).first()
    if not group:
        flash('未找到对应的群组', 'danger')
        return redirect(url_for('groups.list'))
    
    # 验证当前用户是否有权限管理该群组
    is_admin = current_user.id == group.owner_id or current_user.get_role_in_group(group.id) == 'admin'
    if not is_admin:
        flash('只有群组创建者可以同步角色', 'warning')
        return redirect(url_for('groups.view', group_id=group.id))
    
    try:
        # 获取服务器角色信息
        roles_map = DiscordClient.get_guild_roles(
            current_user.discord_access_token,
            guild_id
        )
        
        # 记录角色数量
        roles_count = len(roles_map)
        
        # 更新成员的Discord角色信息
        updated_count = 0
        
        # 获取服务器成员信息
        members_list = DiscordClient.get_guild_members(
            current_user.discord_access_token,
            guild_id
        )
        
        # 处理成员角色
        for member_data in members_list:
            # 获取用户Discord ID
            discord_user_id = member_data.get('user', {}).get('id')
            if not discord_user_id:
                continue
                
            # 查找对应的本地用户
            user = User.query.filter_by(discord_id=discord_user_id).first()
            if not user:
                continue
                
            # 获取成员角色
            role_ids = member_data.get('roles', [])
            if role_ids:
                # 将角色ID连接为字符串存储
                discord_roles = ','.join([str(role_id) for role_id in role_ids])
                
                # 更新用户在群组中的Discord角色
                stmt = group_members.update().where(
                    (group_members.c.user_id == user.id) &
                    (group_members.c.group_id == group.id)
                ).values(discord_roles=discord_roles)
                
                db.session.execute(stmt)
                updated_count += 1
        
        # 提交事务
        db.session.commit()
        
        flash(f'成功同步 {roles_count} 个Discord角色，更新了 {updated_count} 名成员的角色信息', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"同步Discord角色错误: {str(e)}")
        flash(f'同步Discord角色失败: {str(e)}', 'danger')
    
    return redirect(url_for('groups.roles', group_id=group.id))

@discord_bp.route('/guilds/<guild_id>/roles/create', methods=['POST'])
@login_required
def create_guild_role(guild_id):
    """创建Discord服务器角色"""
    # 检查用户是否已连接Discord
    if not current_user.discord_id or not current_user.discord_access_token:
        flash('请先连接您的Discord账号', 'warning')
        return redirect(url_for('discord.connect'))
    
    # 检查是否有该Guild对应的本地群组
    group = Group.query.filter_by(discord_id=guild_id).first()
    if not group:
        flash('未找到对应的群组', 'danger')
        return redirect(url_for('groups.list'))
    
    # 验证当前用户是否有权限管理该群组
    is_admin = current_user.id == group.owner_id or current_user.get_role_in_group(group.id) == 'admin'
    if not is_admin:
        flash('您没有管理此群组的权限', 'warning')
        return redirect(url_for('groups.view', group_id=group.id))
    
    # 检查机器人是否有权限
    has_bot_permission = DiscordClient.check_bot_permissions(guild_id)
    if not has_bot_permission:
        flash('Discord机器人没有管理此服务器的权限，请确保机器人已被添加到服务器并具有管理角色的权限', 'danger')
        return redirect(url_for('groups.roles', group_id=group.id))
    
    # 获取表单数据
    role_name = request.form.get('role_name', '').strip()
    color = request.form.get('color', '#000000').strip()
    mentionable = request.form.get('mentionable', 'off') == 'on'
    
    # 验证数据
    if not role_name:
        flash('角色名称不能为空', 'warning')
        return redirect(url_for('groups.roles', group_id=group.id))
    
    # 转换颜色格式
    if color.startswith('#'):
        color = int(color[1:], 16)
    else:
        color = 0
    
    try:
        # 创建角色
        role_data = DiscordClient.create_guild_role(
            guild_id=guild_id,
            role_name=role_name,
            color=color,
            mentionable=mentionable
        )
        
        flash(f'成功创建角色: {role_name}', 'success')
        
    except Exception as e:
        current_app.logger.error(f"创建Discord角色错误: {str(e)}")
        flash(f'创建角色失败: {str(e)}', 'danger')
    
    return redirect(url_for('groups.roles', group_id=group.id))

@discord_bp.route('/guilds/<guild_id>/roles/delete/<role_id>', methods=['POST'])
@login_required
def delete_guild_role(guild_id, role_id):
    """删除Discord服务器角色"""
    # 检查用户是否已连接Discord
    if not current_user.discord_id or not current_user.discord_access_token:
        flash('请先连接您的Discord账号', 'warning')
        return redirect(url_for('discord.connect'))
    
    # 检查是否有该Guild对应的本地群组
    group = Group.query.filter_by(discord_id=guild_id).first()
    if not group:
        flash('未找到对应的群组', 'danger')
        return redirect(url_for('groups.list'))
    
    # 验证当前用户是否有权限管理该群组
    is_admin = current_user.id == group.owner_id or current_user.get_role_in_group(group.id) == 'admin'
    if not is_admin:
        flash('您没有管理此群组的权限', 'warning')
        return redirect(url_for('groups.view', group_id=group.id))
    
    # 检查机器人是否有权限
    has_bot_permission = DiscordClient.check_bot_permissions(guild_id)
    if not has_bot_permission:
        flash('Discord机器人没有管理此服务器的权限，请确保机器人已被添加到服务器并具有管理角色的权限', 'danger')
        return redirect(url_for('groups.roles', group_id=group.id))
    
    try:
        # 获取角色信息
        roles_map = DiscordClient.get_guild_roles(None, guild_id)
        role_name = "未知角色"
        if role_id in roles_map:
            role_name = roles_map[role_id].get('name', role_name)
        
        # 删除角色
        DiscordClient.delete_guild_role(guild_id, role_id)
        
        flash(f'成功删除角色: {role_name}', 'success')
        
    except Exception as e:
        current_app.logger.error(f"删除Discord角色错误: {str(e)}")
        flash(f'删除角色失败: {str(e)}', 'danger')
    
    return redirect(url_for('groups.roles', group_id=group.id))

@discord_bp.route('/guilds/<guild_id>/roles/<role_id>/update', methods=['POST'])
@login_required
def update_guild_role(guild_id, role_id):
    """更新Discord服务器角色"""
    # 检查用户是否已连接Discord
    if not current_user.discord_id or not current_user.discord_access_token:
        flash('请先连接您的Discord账号', 'warning')
        return redirect(url_for('discord.connect'))
    
    # 检查是否有该Guild对应的本地群组
    group = Group.query.filter_by(discord_id=guild_id).first()
    if not group:
        flash('未找到对应的群组', 'danger')
        return redirect(url_for('groups.list'))
    
    # 验证当前用户是否有权限管理该群组
    is_admin = current_user.id == group.owner_id or current_user.get_role_in_group(group.id) == 'admin'
    if not is_admin:
        flash('您没有管理此群组的权限', 'warning')
        return redirect(url_for('groups.view', group_id=group.id))
    
    # 检查机器人是否有权限
    has_bot_permission = DiscordClient.check_bot_permissions(guild_id)
    if not has_bot_permission:
        flash('Discord机器人没有管理此服务器的权限，请确保机器人已被添加到服务器并具有管理角色的权限', 'danger')
        return redirect(url_for('groups.roles', group_id=group.id))
    
    # 获取表单数据
    role_name = request.form.get('role_name', '').strip()
    color = request.form.get('color', '#000000').strip()
    mentionable = request.form.get('mentionable', 'off') == 'on'
    
    # 验证数据
    if not role_name:
        flash('角色名称不能为空', 'warning')
        return redirect(url_for('groups.roles', group_id=group.id))
    
    # 转换颜色格式
    if color.startswith('#'):
        color = int(color[1:], 16)
    else:
        color = 0
    
    try:
        # 更新角色
        role_data = DiscordClient.update_guild_role(
            guild_id=guild_id,
            role_id=role_id,
            role_name=role_name,
            color=color,
            mentionable=mentionable
        )
        
        flash(f'成功更新角色: {role_name}', 'success')
        
    except Exception as e:
        current_app.logger.error(f"更新Discord角色错误: {str(e)}")
        flash(f'更新角色失败: {str(e)}', 'danger')
    
    return redirect(url_for('groups.roles', group_id=group.id))

@discord_bp.route('/debug/bot-permissions/<guild_id>')
@login_required
def debug_bot_permissions(guild_id):
    """调试页面：检查机器人权限"""
    # 确保用户有权访问
    group = Group.query.filter_by(discord_id=guild_id).first()
    if not group:
        flash('未找到对应的群组', 'danger')
        return redirect(url_for('groups.list'))
    
    # 验证当前用户是否有权限管理该群组
    is_admin = current_user.id == group.owner_id or current_user.get_role_in_group(group.id) == 'admin'
    if not is_admin:
        flash('您没有管理此群组的权限', 'warning')
        return redirect(url_for('groups.view', group_id=group.id))
    
    try:
        bot_token = os.getenv('DISCORD_BOT_TOKEN', '')
        masked_token = bot_token[:5] + '...' + bot_token[-5:] if len(bot_token) > 10 else 'Not configured'
        
        headers = {
            'Authorization': f'Bot {bot_token}'
        }
        
        # 尝试获取服务器信息
        result = {}
        result['guild_id'] = guild_id
        result['token_configured'] = bool(bot_token)
        result['masked_token'] = masked_token
        
        # 获取服务器信息
        api_url = f"{DiscordClient.DISCORD_API_ENDPOINT}/guilds/{guild_id}"
        result['api_url'] = api_url
        
        response = requests.get(api_url, headers=headers)
        result['status_code'] = response.status_code
        result['success'] = response.status_code == 200
        
        if response.status_code == 200:
            guild_data = response.json()
            result['guild_name'] = guild_data.get('name', 'Unknown')
            result['guild_owner_id'] = guild_data.get('owner_id', 'Unknown')
        else:
            result['error'] = response.text
        
        return render_template('discord/debug.html', 
                              group=group,
                              result=result,
                              is_admin=is_admin)
    except Exception as e:
        current_app.logger.error(f"调试Bot权限失败: {str(e)}")
        flash(f'调试失败: {str(e)}', 'danger')
        return redirect(url_for('groups.roles', group_id=group.id))

@discord_bp.route('/debug/user-attributes')
@login_required
def debug_user_attributes():
    """调试页面：显示当前用户的所有属性"""
    if not current_user.is_authenticated:
        flash('请先登录以访问此页面', 'warning')
        return redirect(url_for('auth.login'))
    
    # 获取用户对象的所有属性和方法
    user_attrs = {}
    
    # 获取类实例的所有属性（实例变量）
    for attr in dir(current_user):
        # 排除特殊方法和私有属性
        if not attr.startswith('_'):
            try:
                value = getattr(current_user, attr)
                
                # 如果是方法，标记为方法
                if callable(value):
                    user_attrs[attr] = "方法"
                else:
                    # 对于某些敏感字段，隐藏详细内容
                    if 'token' in attr.lower() or 'password' in attr.lower() or 'secret' in attr.lower():
                        user_attrs[attr] = f"{type(value).__name__} (已隐藏敏感内容)"
                    else:
                        # 尝试将值转换为字符串，最多显示100个字符
                        try:
                            str_value = str(value)
                            if len(str_value) > 100:
                                str_value = str_value[:100] + "..."
                            user_attrs[attr] = str_value
                        except:
                            user_attrs[attr] = f"{type(value).__name__} (无法显示)"
            except Exception as e:
                user_attrs[attr] = f"错误: {str(e)}"
    
    # 按字母顺序排序属性
    sorted_attrs = {k: user_attrs[k] for k in sorted(user_attrs.keys())}
    
    return render_template('discord/debug_user.html', 
                           user_attrs=sorted_attrs, 
                           user=current_user)

class DiscordClient:
    DISCORD_API_ENDPOINT = "https://discord.com/api/v10"
    DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

    @staticmethod
    def get_auth_url(state):
        """获取Discord授权页面的URL"""
        params = {
            'client_id': os.environ.get('DISCORD_CLIENT_ID'),
            'redirect_uri': os.environ.get('DISCORD_REDIRECT_URI'),
            'response_type': 'code',
            'scope': 'identify guilds',
            'state': state
        }
        return f"{DiscordClient.DISCORD_API_ENDPOINT}/oauth2/authorize?{requests.compat.urlencode(params)}"

    @staticmethod
    def exchange_code(code):
        """交换授权码获取访问令牌"""
        params = {
            'client_id': os.environ.get('DISCORD_CLIENT_ID'),
            'client_secret': os.environ.get('DISCORD_CLIENT_SECRET'),
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': os.environ.get('DISCORD_REDIRECT_URI')
        }
        response = requests.post(f"{DiscordClient.DISCORD_API_ENDPOINT}/oauth2/token", data=params)
        return response.json()

    @staticmethod
    def get_user_info(access_token):
        """获取Discord用户信息"""
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response = requests.get(f"{DiscordClient.DISCORD_API_ENDPOINT}/users/@me", headers=headers)
        return response.json()

    @staticmethod
    def refresh_token(refresh_token):
        """刷新访问令牌"""
        params = {
            'client_id': os.environ.get('DISCORD_CLIENT_ID'),
            'client_secret': os.environ.get('DISCORD_CLIENT_SECRET'),
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        response = requests.post(f"{DiscordClient.DISCORD_API_ENDPOINT}/oauth2/token", data=params)
        return response.json()

    @staticmethod
    def get_user_guilds(access_token):
        """获取用户的Discord服务器列表"""
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response = requests.get(f"{DiscordClient.DISCORD_API_ENDPOINT}/users/@me/guilds", headers=headers)
        return response.json()

    @staticmethod
    def get_guild_members(access_token, guild_id):
        """获取Discord服务器成员列表"""
        # 优先使用Bot令牌，这是获取服务器成员唯一可靠的方式
        if DiscordClient.DISCORD_BOT_TOKEN:
            headers = {
                'Authorization': f'Bot {DiscordClient.DISCORD_BOT_TOKEN}'
            }
        else:
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
        
        try:
            current_app.logger.info(f"正在获取Discord服务器成员: {guild_id}")
            response = requests.get(f"{DiscordClient.DISCORD_API_ENDPOINT}/guilds/{guild_id}/members?limit=1000", headers=headers)
            response.raise_for_status()  # 这会在HTTP错误时抛出异常
            
            members = response.json()
            current_app.logger.info(f"成功获取Discord成员: {len(members)}个")
            return members
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            error_message = f"获取Discord成员失败 - HTTP {status_code}"
            
            if status_code == 401:
                error_message += ": 认证失败，请检查Bot令牌是否有效"
            elif status_code == 403:
                error_message += ": 权限不足，请确保Bot拥有查看成员的权限"
            
            current_app.logger.error(error_message)
            # 返回空列表而不是抛出异常，这样同步过程不会完全中断
            return []
        except Exception as e:
            current_app.logger.error(f"获取Discord成员错误: {str(e)}")
            return []

    @staticmethod
    def get_guild_roles(access_token, guild_id):
        """获取Discord服务器的所有角色信息"""
        url = f"{DiscordClient.DISCORD_API_ENDPOINT}/guilds/{guild_id}/roles"
        
        # 优先使用bot令牌
        if DiscordClient.DISCORD_BOT_TOKEN:
            headers = {
                'Authorization': f'Bot {DiscordClient.DISCORD_BOT_TOKEN}'
            }
        else:
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
        
        try:
            current_app.logger.info(f"正在获取Discord服务器角色: {url}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            roles = response.json()
            
            # 将角色列表转换为ID到角色名称的映射
            roles_map = {str(role['id']): role for role in roles}
            current_app.logger.info(f"成功获取Discord角色: {len(roles)}个")
            return roles_map
        except Exception as e:
            current_app.logger.error(f"获取Discord角色错误: {str(e)}")
            raise e

    @classmethod
    def check_bot_permissions(cls, guild_id):
        """检查机器人是否有权限访问服务器"""
        try:
            if not cls.DISCORD_BOT_TOKEN:
                return False

            headers = {
                'Authorization': f'Bot {cls.DISCORD_BOT_TOKEN}'
            }
            
            # 尝试获取服务器信息
            response = requests.get(f"{cls.DISCORD_API_ENDPOINT}/guilds/{guild_id}", headers=headers)
            if response.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            current_app.logger.error(f"检查Bot权限失败: {str(e)}")
            return False

    @classmethod
    def create_guild_role(cls, guild_id, role_name, color=0, permissions=0, mentionable=True):
        """创建Discord服务器角色"""
        if not cls.DISCORD_BOT_TOKEN:
            raise ValueError("Discord Bot令牌未设置")
        
        headers = {
            'Authorization': f'Bot {cls.DISCORD_BOT_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # 准备角色数据
        data = {
            'name': role_name,
            'color': color,
            'permissions': permissions,
            'mentionable': mentionable
        }
        
        # 创建角色
        response = requests.post(
            f"{cls.DISCORD_API_ENDPOINT}/guilds/{guild_id}/roles",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200 or response.status_code == 201:
            return response.json()
        else:
            error_message = f"创建角色失败: HTTP {response.status_code} - {response.text}"
            current_app.logger.error(error_message)
            raise Exception(error_message)
    
    @classmethod
    def delete_guild_role(cls, guild_id, role_id):
        """删除Discord服务器角色"""
        if not cls.DISCORD_BOT_TOKEN:
            raise ValueError("Discord Bot令牌未设置")
        
        headers = {
            'Authorization': f'Bot {cls.DISCORD_BOT_TOKEN}'
        }
        
        # 删除角色
        response = requests.delete(
            f"{cls.DISCORD_API_ENDPOINT}/guilds/{guild_id}/roles/{role_id}",
            headers=headers
        )
        
        if response.status_code == 204:
            return True
        else:
            error_message = f"删除角色失败: HTTP {response.status_code} - {response.text}"
            current_app.logger.error(error_message)
            raise Exception(error_message)
    
    @classmethod
    def update_guild_role(cls, guild_id, role_id, role_name=None, color=None, permissions=None, mentionable=None):
        """更新Discord服务器角色"""
        if not cls.DISCORD_BOT_TOKEN:
            raise ValueError("Discord Bot令牌未设置")
        
        headers = {
            'Authorization': f'Bot {cls.DISCORD_BOT_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # 准备角色数据
        data = {}
        if role_name is not None:
            data['name'] = role_name
        if color is not None:
            data['color'] = color
        if permissions is not None:
            data['permissions'] = permissions
        if mentionable is not None:
            data['mentionable'] = mentionable
        
        # 更新角色
        response = requests.patch(
            f"{cls.DISCORD_API_ENDPOINT}/guilds/{guild_id}/roles/{role_id}",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            error_message = f"更新角色失败: HTTP {response.status_code} - {response.text}"
            current_app.logger.error(error_message)
            raise Exception(error_message)
