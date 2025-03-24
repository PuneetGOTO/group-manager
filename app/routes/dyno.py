"""Dyno功能路由"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import (
    Group, User, AutoModSetting, WelcomeMessage, 
    CustomCommand, LevelSystem, UserLevel, LogSetting, MusicSetting, SystemCommand
)
from app.discord.client import DiscordClient
import json
from datetime import datetime
import requests

dyno_bp = Blueprint('dyno', __name__)

# 辅助函数：检查用户是否有管理组的权限
def check_group_admin(group_id):
    """检查当前用户是否是指定群组的管理员"""
    group = Group.query.get_or_404(group_id)
    
    # 检查用户是否是群组所有者
    if group.owner_id == current_user.id:
        return True
    
    # 检查用户是否是群组管理员
    user_role = current_user.get_role_in_group(group.id)
    if user_role in ['admin', 'moderator']:
        return True
    
    flash('您没有权限管理此群组的Dyno功能', 'danger')
    return False

# Dyno主页 - 显示所有可用功能
@dyno_bp.route('/group/<int:group_id>/dyno')
@login_required
def dashboard(group_id):
    """Dyno功能仪表板"""
    group = Group.query.get_or_404(group_id)
    
    # 检查组是否连接到Discord
    if not group.discord_id:
        flash('此群组尚未连接到Discord服务器', 'warning')
        return redirect(url_for('groups.view', group_id=group_id))
    
    # 检查用户是否连接了Discord
    if not current_user.is_connected_to_discord():
        flash('请先连接您的Discord账号', 'warning')
        return redirect(url_for('discord.connect'))
    
    # 获取当前群组的各项Dyno设置
    automod = AutoModSetting.query.filter_by(group_id=group_id).first()
    welcome = WelcomeMessage.query.filter_by(group_id=group_id).first()
    level_system = LevelSystem.query.filter_by(group_id=group_id).first()
    log_setting = LogSetting.query.filter_by(group_id=group_id).first()
    music_setting = MusicSetting.query.filter_by(group_id=group_id).first()
    custom_commands = CustomCommand.query.filter_by(group_id=group_id).all()
    
    # 如果设置不存在，创建默认设置
    if not automod:
        automod = AutoModSetting(group_id=group_id)
        db.session.add(automod)
    
    if not welcome:
        welcome = WelcomeMessage(group_id=group_id)
        db.session.add(welcome)
    
    if not level_system:
        level_system = LevelSystem(group_id=group_id)
        db.session.add(level_system)
    
    if not log_setting:
        log_setting = LogSetting(group_id=group_id)
        db.session.add(log_setting)
    
    if not music_setting:
        music_setting = MusicSetting(group_id=group_id)
        db.session.add(music_setting)
    
    db.session.commit()
    
    # 检查当前用户是否有管理权限
    has_admin = check_group_admin(group_id)
    
    return render_template(
        'dyno/dashboard.html',
        group=group,
        automod=automod,
        welcome=welcome,
        level_system=level_system,
        log_setting=log_setting,
        music_setting=music_setting,
        custom_commands=custom_commands,
        has_admin=has_admin
    )

# AutoMod设置
@dyno_bp.route('/group/<int:group_id>/dyno/automod', methods=['GET', 'POST'])
@login_required
def automod(group_id):
    """自动审核系统设置"""
    if not check_group_admin(group_id):
        return redirect(url_for('dyno.dashboard', group_id=group_id))
    
    group = Group.query.get_or_404(group_id)
    automod = AutoModSetting.query.filter_by(group_id=group_id).first()
    
    if not automod:
        automod = AutoModSetting(group_id=group_id)
        db.session.add(automod)
        db.session.commit()
    
    if request.method == 'POST':
        # 更新AutoMod设置
        automod.enabled = 'enabled' in request.form
        
        # 反垃圾邮件设置
        automod.spam_enabled = 'spam_enabled' in request.form
        automod.spam_action = request.form.get('spam_action', 'delete')
        try:
            automod.spam_threshold = int(request.form.get('spam_threshold', 5))
        except ValueError:
            automod.spam_threshold = 5
        
        # 不良内容过滤
        automod.filter_enabled = 'filter_enabled' in request.form
        automod.filter_words = request.form.get('filter_words', '')
        automod.filter_action = request.form.get('filter_action', 'delete')
        
        # 链接过滤
        automod.link_filter_enabled = 'link_filter_enabled' in request.form
        automod.allowed_domains = request.form.get('allowed_domains', '')
        automod.link_filter_action = request.form.get('link_filter_action', 'delete')
        
        # 大写字母审核
        automod.caps_filter_enabled = 'caps_filter_enabled' in request.form
        try:
            automod.caps_percentage = int(request.form.get('caps_percentage', 70))
            automod.caps_min_length = int(request.form.get('caps_min_length', 10))
        except ValueError:
            automod.caps_percentage = 70
            automod.caps_min_length = 10
        
        # 重复消息审核
        automod.duplicate_filter_enabled = 'duplicate_filter_enabled' in request.form
        try:
            automod.duplicate_threshold = int(request.form.get('duplicate_threshold', 3))
            automod.duplicate_timeframe = int(request.form.get('duplicate_timeframe', 60))
        except ValueError:
            automod.duplicate_threshold = 3
            automod.duplicate_timeframe = 60
        
        # 慢速模式
        automod.slowmode_enabled = 'slowmode_enabled' in request.form
        try:
            automod.slowmode_seconds = int(request.form.get('slowmode_seconds', 5))
        except ValueError:
            automod.slowmode_seconds = 5
        
        automod.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('自动审核系统设置已更新', 'success')
        return redirect(url_for('dyno.automod', group_id=group_id))
    
    return render_template('dyno/automod.html', group=group, automod=automod)

# 欢迎消息设置
@dyno_bp.route('/group/<int:group_id>/dyno/welcome', methods=['GET', 'POST'])
@login_required
def welcome(group_id):
    """欢迎和告别消息设置"""
    if not check_group_admin(group_id):
        return redirect(url_for('dyno.dashboard', group_id=group_id))
    
    group = Group.query.get_or_404(group_id)
    welcome = WelcomeMessage.query.filter_by(group_id=group_id).first()
    
    if not welcome:
        welcome = WelcomeMessage(group_id=group_id)
        db.session.add(welcome)
        db.session.commit()
    
    # 获取服务器的频道列表
    channels = []
    try:
        token = current_user.discord_access_token
        guild_id = group.discord_id
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(
            f'https://discord.com/api/v10/guilds/{guild_id}/channels',
            headers=headers
        )
        
        if response.status_code == 200:
            channels = response.json()
            # 过滤出文本频道
            channels = [ch for ch in channels if ch.get('type') == 0]
    except Exception as e:
        current_app.logger.error(f"获取Discord频道失败: {str(e)}")
    
    if request.method == 'POST':
        # 更新欢迎消息设置
        welcome.welcome_enabled = 'welcome_enabled' in request.form
        welcome.welcome_channel_id = request.form.get('welcome_channel_id', '')
        welcome.welcome_message = request.form.get('welcome_message', '欢迎 {user} 加入 {server}！')
        
        welcome.goodbye_enabled = 'goodbye_enabled' in request.form
        welcome.goodbye_channel_id = request.form.get('goodbye_channel_id', '')
        welcome.goodbye_message = request.form.get('goodbye_message', '{user} 离开了 {server}。')
        
        welcome.dm_welcome_enabled = 'dm_welcome_enabled' in request.form
        welcome.dm_welcome_message = request.form.get('dm_welcome_message', '')
        
        welcome.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('欢迎消息设置已更新', 'success')
        return redirect(url_for('dyno.welcome', group_id=group_id))
    
    return render_template('dyno/welcome.html', group=group, welcome=welcome, channels=channels)

# 自定义命令
@dyno_bp.route('/group/<int:group_id>/dyno/commands', methods=['GET', 'POST'])
@login_required
def commands(group_id):
    """自定义命令管理"""
    if not check_group_admin(group_id):
        return redirect(url_for('dyno.dashboard', group_id=group_id))
    
    group = Group.query.get_or_404(group_id)
    commands = CustomCommand.query.filter_by(group_id=group_id).all()
    
    if request.method == 'POST':
        # 添加新命令
        name = request.form.get('name', '').strip()
        if not name.startswith('!'):
            name = '!' + name
        
        response = request.form.get('response', '').strip()
        
        if not name or not response:
            flash('命令名称和响应内容不能为空', 'danger')
        elif CustomCommand.query.filter_by(group_id=group_id, name=name).first():
            flash(f'命令 "{name}" 已存在', 'danger')
        else:
            new_command = CustomCommand(
                group_id=group_id,
                name=name,
                response=response,
                created_by=current_user.id
            )
            db.session.add(new_command)
            db.session.commit()
            flash('自定义命令已添加', 'success')
        
        return redirect(url_for('dyno.commands', group_id=group_id))
    
    return render_template('dyno/commands.html', group=group, commands=commands)

# 删除自定义命令
@dyno_bp.route('/group/<int:group_id>/dyno/commands/delete/<int:command_id>', methods=['POST'])
@login_required
def delete_command(group_id, command_id):
    """删除自定义命令"""
    if not check_group_admin(group_id):
        return redirect(url_for('dyno.dashboard', group_id=group_id))
    
    command = CustomCommand.query.get_or_404(command_id)
    
    # 检查命令是否属于当前群组
    if command.group_id != group_id:
        flash('无法删除其他群组的命令', 'danger')
        return redirect(url_for('dyno.commands', group_id=group_id))
    
    db.session.delete(command)
    db.session.commit()
    
    flash('自定义命令已删除', 'success')
    return redirect(url_for('dyno.commands', group_id=group_id))

# 更新自定义命令
@dyno_bp.route('/group/<int:group_id>/dyno/commands/edit/<int:command_id>', methods=['POST'])
@login_required
def edit_command(group_id, command_id):
    """编辑自定义命令"""
    if not check_group_admin(group_id):
        return redirect(url_for('dyno.dashboard', group_id=group_id))
    
    command = CustomCommand.query.get_or_404(command_id)
    
    # 检查命令是否属于当前群组
    if command.group_id != group_id:
        flash('无法编辑其他群组的命令', 'danger')
        return redirect(url_for('dyno.commands', group_id=group_id))
    
    command.response = request.form.get('response', '').strip()
    command.enabled = 'enabled' in request.form
    command.updated_at = datetime.utcnow()
    
    db.session.commit()
    flash('自定义命令已更新', 'success')
    return redirect(url_for('dyno.commands', group_id=group_id))

# 等级系统设置
@dyno_bp.route('/group/<int:group_id>/dyno/levels', methods=['GET', 'POST'])
@login_required
def levels(group_id):
    """等级系统设置"""
    if not check_group_admin(group_id):
        return redirect(url_for('dyno.dashboard', group_id=group_id))
    
    group = Group.query.get_or_404(group_id)
    level_system = LevelSystem.query.filter_by(group_id=group_id).first()
    
    if not level_system:
        level_system = LevelSystem(group_id=group_id)
        db.session.add(level_system)
        db.session.commit()
    
    # 获取服务器的频道和角色列表
    channels = []
    roles = []
    try:
        token = current_user.discord_access_token
        guild_id = group.discord_id
        
        # 获取频道
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(
            f'https://discord.com/api/v10/guilds/{guild_id}/channels',
            headers=headers
        )
        
        if response.status_code == 200:
            channels = response.json()
            # 过滤出文本频道
            channels = [ch for ch in channels if ch.get('type') == 0]
        
        # 获取角色
        response = requests.get(
            f'https://discord.com/api/v10/guilds/{guild_id}/roles',
            headers=headers
        )
        
        if response.status_code == 200:
            roles = response.json()
    except Exception as e:
        current_app.logger.error(f"获取Discord频道或角色失败: {str(e)}")
    
    if request.method == 'POST':
        # 更新等级系统设置
        level_system.enabled = 'enabled' in request.form
        
        try:
            level_system.xp_per_message = int(request.form.get('xp_per_message', 15))
            level_system.xp_cooldown = int(request.form.get('xp_cooldown', 60))
            level_system.level_multiplier = float(request.form.get('level_multiplier', 1.5))
        except ValueError:
            level_system.xp_per_message = 15
            level_system.xp_cooldown = 60
            level_system.level_multiplier = 1.5
        
        level_system.level_announcement = 'level_announcement' in request.form
        level_system.level_channel_id = request.form.get('level_channel_id', '')
        
        level_system.level_roles_enabled = 'level_roles_enabled' in request.form
        
        # 处理等级角色
        level_roles = []
        for i in range(20):  # 最多20个等级角色
            level = request.form.get(f'level_{i}', '')
            role_id = request.form.get(f'role_{i}', '')
            
            if level and role_id:
                try:
                    level = int(level)
                    level_roles.append(f"{level}:{role_id}")
                except ValueError:
                    pass
        
        level_system.level_roles = ','.join(level_roles)
        level_system.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('等级系统设置已更新', 'success')
        return redirect(url_for('dyno.levels', group_id=group_id))
    
    # 解析当前等级角色设置
    level_roles = []
    if level_system.level_roles:
        for pair in level_system.level_roles.split(','):
            if ':' in pair:
                level, role_id = pair.split(':', 1)
                try:
                    level_roles.append({
                        'level': int(level),
                        'role_id': role_id
                    })
                except ValueError:
                    pass
    
    # 获取用户等级排行榜
    leaderboard = UserLevel.query.filter_by(level_system_id=level_system.id).order_by(UserLevel.level.desc(), UserLevel.xp.desc()).limit(10).all()
    
    return render_template(
        'dyno/levels.html',
        group=group,
        level_system=level_system,
        channels=channels,
        roles=roles,
        level_roles=level_roles,
        leaderboard=leaderboard
    )

# 服务器日志设置
@dyno_bp.route('/group/<int:group_id>/dyno/logs', methods=['GET', 'POST'])
@login_required
def logs(group_id):
    """服务器日志设置"""
    if not check_group_admin(group_id):
        return redirect(url_for('dyno.dashboard', group_id=group_id))
    
    group = Group.query.get_or_404(group_id)
    log_setting = LogSetting.query.filter_by(group_id=group_id).first()
    
    if not log_setting:
        log_setting = LogSetting(group_id=group_id)
        db.session.add(log_setting)
        db.session.commit()
    
    # 获取服务器的频道列表
    channels = []
    try:
        token = current_user.discord_access_token
        guild_id = group.discord_id
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(
            f'https://discord.com/api/v10/guilds/{guild_id}/channels',
            headers=headers
        )
        
        if response.status_code == 200:
            channels = response.json()
            # 过滤出文本频道
            channels = [ch for ch in channels if ch.get('type') == 0]
    except Exception as e:
        current_app.logger.error(f"获取Discord频道失败: {str(e)}")
    
    if request.method == 'POST':
        # 更新日志设置
        log_setting.enabled = 'enabled' in request.form
        log_setting.log_channel_id = request.form.get('log_channel_id', '')
        
        log_setting.log_joins_leaves = 'log_joins_leaves' in request.form
        log_setting.log_message_edits = 'log_message_edits' in request.form
        log_setting.log_message_deletes = 'log_message_deletes' in request.form
        log_setting.log_role_changes = 'log_role_changes' in request.form
        log_setting.log_channel_changes = 'log_channel_changes' in request.form
        log_setting.log_nickname_changes = 'log_nickname_changes' in request.form
        log_setting.log_bans_unbans = 'log_bans_unbans' in request.form
        log_setting.log_voice_changes = 'log_voice_changes' in request.form
        
        log_setting.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('服务器日志设置已更新', 'success')
        return redirect(url_for('dyno.logs', group_id=group_id))
    
    return render_template('dyno/logs.html', group=group, log_setting=log_setting, channels=channels)

# 音乐播放设置
@dyno_bp.route('/group/<int:group_id>/dyno/music', methods=['GET', 'POST'])
@login_required
def music(group_id):
    """音乐播放设置"""
    if not check_group_admin(group_id):
        return redirect(url_for('dyno.dashboard', group_id=group_id))
    
    group = Group.query.get_or_404(group_id)
    music_setting = MusicSetting.query.filter_by(group_id=group_id).first()
    
    if not music_setting:
        music_setting = MusicSetting(group_id=group_id)
        db.session.add(music_setting)
        db.session.commit()
    
    # 获取服务器的角色列表
    roles = []
    try:
        token = current_user.discord_access_token
        guild_id = group.discord_id
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(
            f'https://discord.com/api/v10/guilds/{guild_id}/roles',
            headers=headers
        )
        
        if response.status_code == 200:
            roles = response.json()
    except Exception as e:
        current_app.logger.error(f"获取Discord角色失败: {str(e)}")
    
    if request.method == 'POST':
        # 更新音乐设置
        music_setting.enabled = 'enabled' in request.form
        
        try:
            music_setting.default_volume = int(request.form.get('default_volume', 50))
        except ValueError:
            music_setting.default_volume = 50
        
        music_setting.dj_role_id = request.form.get('dj_role_id', '')
        music_setting.auto_play = 'auto_play' in request.form
        music_setting.announce_songs = 'announce_songs' in request.form
        music_setting.restrictions_enabled = 'restrictions_enabled' in request.form
        
        try:
            music_setting.max_queue_length = int(request.form.get('max_queue_length', 100))
            music_setting.max_song_length = int(request.form.get('max_song_length', 600))
        except ValueError:
            music_setting.max_queue_length = 100
            music_setting.max_song_length = 600
        
        music_setting.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('音乐播放设置已更新', 'success')
        return redirect(url_for('dyno.music', group_id=group_id))
    
    return render_template('dyno/music.html', group=group, music_setting=music_setting, roles=roles)

# 命令系统页面
@dyno_bp.route('/group/<int:group_id>/commands/categories')
@login_required
def command_categories(group_id):
    """命令系统页面"""
    group = Group.query.get_or_404(group_id)
    
    # 检查权限
    if not current_user.can_manage_group(group):
        flash('您没有权限管理此群组的Dyno设置', 'danger')
        return redirect(url_for('groups.view', group_id=group_id))
    
    # 获取Discord频道和角色信息
    channels = []
    roles = []
    
    if current_user.discord_connected and group.discord_guild_id:
        try:
            # 获取Discord频道
            channels = get_discord_channels(group.discord_guild_id)
            # 获取Discord角色
            roles = get_discord_roles(group.discord_guild_id)
        except Exception as e:
            current_app.logger.error(f"获取Discord信息时出错: {str(e)}")
            flash('获取Discord信息时出错，请确保您的Discord账号已连接并且拥有足够权限', 'warning')
    
    # 获取各类别的命令
    categories = ['manager', 'mod', 'info', 'fun', 'moderator', 'roles', 'tags', 'giveaways', 'game']
    commands_by_category = {}
    
    for category in categories:
        commands = SystemCommand.query.filter_by(group_id=group_id, category=category).all()
        commands_by_category[f"{category}_commands"] = commands
        
        # 如果没有命令，添加默认命令
        if not commands:
            default_commands = get_default_commands(category)
            for cmd in default_commands:
                new_command = SystemCommand(
                    name=cmd['name'],
                    description=cmd['description'],
                    usage=cmd['usage'],
                    category=category,
                    enabled=True,
                    group_id=group_id
                )
                db.session.add(new_command)
            
            db.session.commit()
            commands = SystemCommand.query.filter_by(group_id=group_id, category=category).all()
            commands_by_category[f"{category}_commands"] = commands
    
    return render_template(
        'dyno/command_categories.html',
        group=group,
        channels=channels,
        roles=roles,
        **commands_by_category
    )

@dyno_bp.route('/group/<int:group_id>/commands/settings/save', methods=['POST'])
@login_required
def save_command_settings(group_id):
    """保存命令设置"""
    group = Group.query.get_or_404(group_id)
    
    # 检查权限
    if not current_user.can_manage_group(group):
        return jsonify(success=False, error='您没有权限管理此群组的Dyno设置')
    
    try:
        data = request.get_json()
        commands = data.get('commands', [])
        
        for cmd in commands:
            command_id = cmd.get('id')
            enabled = cmd.get('enabled', False)
            
            command = SystemCommand.query.filter_by(id=command_id, group_id=group_id).first()
            if command:
                command.enabled = enabled
        
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        current_app.logger.error(f"保存命令设置时出错: {str(e)}")
        return jsonify(success=False, error=str(e))

def get_default_commands(category):
    """获取默认命令"""
    default_commands = {
        'manager': [
            {'name': 'addban', 'description': '添加用户到封禁列表', 'usage': '!addban @用户 [原因]'},
            {'name': 'announce', 'description': '发送服务器公告', 'usage': '!announce #频道 [内容]'},
            {'name': 'settings', 'description': '查看或更改服务器设置', 'usage': '!settings [模块名]'},
            {'name': 'setup', 'description': '设置机器人功能', 'usage': '!setup [模块名]'},
            {'name': 'ignore', 'description': '让机器人忽略某个频道', 'usage': '!ignore #频道'},
            {'name': 'ban', 'description': '封禁用户', 'usage': '!ban @用户 [原因]'},
            {'name': 'unban', 'description': '解除用户封禁', 'usage': '!unban @用户'},
        ],
        'mod': [
            {'name': 'warn', 'description': '警告用户', 'usage': '!warn @用户 [原因]'},
            {'name': 'warnings', 'description': '查看用户警告记录', 'usage': '!warnings @用户'},
            {'name': 'delwarn', 'description': '删除用户警告', 'usage': '!delwarn @用户 [警告ID]'},
            {'name': 'mute', 'description': '禁言用户', 'usage': '!mute @用户 [时长] [原因]'},
            {'name': 'unmute', 'description': '解除用户禁言', 'usage': '!unmute @用户'},
            {'name': 'kick', 'description': '踢出用户', 'usage': '!kick @用户 [原因]'},
            {'name': 'purge', 'description': '批量删除消息', 'usage': '!purge [数量]'},
        ],
        'info': [
            {'name': 'help', 'description': '显示命令帮助', 'usage': '!help [命令名]'},
            {'name': 'serverinfo', 'description': '显示服务器信息', 'usage': '!serverinfo'},
            {'name': 'userinfo', 'description': '显示用户信息', 'usage': '!userinfo @用户'},
            {'name': 'roleinfo', 'description': '显示角色信息', 'usage': '!roleinfo @角色'},
            {'name': 'channelinfo', 'description': '显示频道信息', 'usage': '!channelinfo #频道'},
            {'name': 'avatar', 'description': '显示用户头像', 'usage': '!avatar @用户'},
            {'name': 'ping', 'description': '测试机器人响应时间', 'usage': '!ping'},
        ],
        'fun': [
            {'name': '8ball', 'description': '问一个是非问题', 'usage': '!8ball [问题]'},
            {'name': 'gif', 'description': '搜索GIF动图', 'usage': '!gif [关键词]'},
            {'name': 'roll', 'description': '掷骰子', 'usage': '!roll [骰子数]d[面数]'},
            {'name': 'flip', 'description': '抛硬币', 'usage': '!flip'},
            {'name': 'cat', 'description': '随机猫咪图片', 'usage': '!cat'},
            {'name': 'dog', 'description': '随机狗狗图片', 'usage': '!dog'},
            {'name': 'joke', 'description': '随机笑话', 'usage': '!joke'},
        ],
        'moderator': [
            {'name': 'clean', 'description': '清理特定类型的消息', 'usage': '!clean [类型] [数量]'},
            {'name': 'slowmode', 'description': '设置慢速模式', 'usage': '!slowmode [秒数]'},
            {'name': 'lockdown', 'description': '锁定频道', 'usage': '!lockdown [时长]'},
            {'name': 'unlock', 'description': '解锁频道', 'usage': '!unlock'},
            {'name': 'addrole', 'description': '添加角色给用户', 'usage': '!addrole @用户 @角色'},
            {'name': 'removerole', 'description': '移除用户角色', 'usage': '!removerole @用户 @角色'},
            {'name': 'nickname', 'description': '修改用户昵称', 'usage': '!nickname @用户 [新昵称]'},
        ],
        'roles': [
            {'name': 'role', 'description': '分配或移除自助角色', 'usage': '!role [角色名]'},
            {'name': 'roles', 'description': '查看可用的自助角色', 'usage': '!roles'},
            {'name': 'autorole', 'description': '设置自动角色', 'usage': '!autorole @角色'},
            {'name': 'roleinfo', 'description': '查看角色信息', 'usage': '!roleinfo @角色'},
            {'name': 'createrole', 'description': '创建新角色', 'usage': '!createrole [名称] [颜色]'},
            {'name': 'deleterole', 'description': '删除角色', 'usage': '!deleterole @角色'},
        ],
        'tags': [
            {'name': 'tag', 'description': '查看一个标签', 'usage': '!tag [标签名]'},
            {'name': 'tags', 'description': '列出所有标签', 'usage': '!tags'},
            {'name': 'tagadd', 'description': '添加一个标签', 'usage': '!tagadd [标签名] [内容]'},
            {'name': 'tagdel', 'description': '删除一个标签', 'usage': '!tagdel [标签名]'},
            {'name': 'tagedit', 'description': '编辑一个标签', 'usage': '!tagedit [标签名] [新内容]'},
        ],
        'giveaways': [
            {'name': 'giveaway', 'description': '创建赠品活动', 'usage': '!giveaway [时长] [奖品]'},
            {'name': 'reroll', 'description': '重新抽取赠品获奖者', 'usage': '!reroll [消息ID]'},
            {'name': 'gcancel', 'description': '取消赠品活动', 'usage': '!gcancel [消息ID]'},
        ],
        'game': [
            {'name': 'trivia', 'description': '开始一个知识问答游戏', 'usage': '!trivia [类别]'},
            {'name': 'hangman', 'description': '开始一个猜单词游戏', 'usage': '!hangman'},
            {'name': 'tictactoe', 'description': '开始一个井字游戏', 'usage': '!tictactoe @用户'},
            {'name': 'connect4', 'description': '开始一个四子棋游戏', 'usage': '!connect4 @用户'},
            {'name': 'akinator', 'description': '开始阿基纳特猜人物游戏', 'usage': '!akinator'},
        ],
    }
    
    return default_commands.get(category, [])
