"""Dyno功能路由"""
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request, current_app, g, abort
from flask_login import login_required, current_user
from app import db
from app.models import (
    Group, User, AutoModSetting, WelcomeMessage, 
    CustomCommand, LevelSystem, UserLevel, LogSetting, MusicSetting, SystemCommand, DiscordBot, SystemEvent
)
from app.models.user import group_members
from app.discord.client import DiscordClient
import json
from datetime import datetime
import requests
import os

# 导入Discord相关的函数
from app.discord.bot_client import get_bot_info, start_bot_process, check_bot_status, get_guild_channels, get_bot_guilds

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

# 辅助函数：获取Discord频道列表
def get_discord_channels(guild_id):
    """获取Discord服务器的频道列表"""
    try:
        discord_client = DiscordClient()
        channels = discord_client.get_guild_channels(guild_id)
        return channels
    except Exception as e:
        current_app.logger.error(f"获取Discord频道时出错: {str(e)}")
        return []

# 辅助函数：获取Discord角色列表
def get_discord_roles(guild_id):
    """获取Discord服务器的角色列表"""
    try:
        discord_client = DiscordClient()
        roles = discord_client.get_guild_roles(guild_id)
        return roles
    except Exception as e:
        current_app.logger.error(f"获取Discord角色时出错: {str(e)}")
        return []

# 辅助函数：获取默认命令列表
def get_default_commands(category):
    """获取指定类别的默认命令列表"""
    default_commands = {
        'manager': [
            {'name': 'setup', 'description': '设置服务器的基本配置', 'usage': '!setup'},
            {'name': 'settings', 'description': '查看和修改机器人设置', 'usage': '!settings [模块]'},
            {'name': 'module', 'description': '启用或禁用模块', 'usage': '!module [enable/disable] [模块名]'}
        ],
        'mod': [
            {'name': 'ban', 'description': '封禁用户', 'usage': '!ban @用户 [原因]'},
            {'name': 'kick', 'description': '踢出用户', 'usage': '!kick @用户 [原因]'},
            {'name': 'mute', 'description': '禁言用户', 'usage': '!mute @用户 [时长] [原因]'}
        ],
        'info': [
            {'name': 'serverinfo', 'description': '显示服务器信息', 'usage': '!serverinfo'},
            {'name': 'userinfo', 'description': '显示用户信息', 'usage': '!userinfo [@用户]'},
            {'name': 'roleinfo', 'description': '显示角色信息', 'usage': '!roleinfo [角色名]'}
        ],
        'fun': [
            {'name': 'roll', 'description': '掷骰子', 'usage': '!roll [骰子数]d[面数]'},
            {'name': '8ball', 'description': '魔法8球', 'usage': '!8ball [问题]'},
            {'name': 'cat', 'description': '显示随机猫咪图片', 'usage': '!cat'}
        ],
        'moderator': [
            {'name': 'warn', 'description': '警告用户', 'usage': '!warn @用户 [原因]'},
            {'name': 'purge', 'description': '批量删除消息', 'usage': '!purge [数量] [@用户]'},
            {'name': 'slowmode', 'description': '设置慢速模式', 'usage': '!slowmode [秒数]'}
        ],
        'roles': [
            {'name': 'role', 'description': '添加或移除角色', 'usage': '!role [@用户] [角色名]'},
            {'name': 'autorole', 'description': '设置自动角色', 'usage': '!autorole [角色名]'},
            {'name': 'roleall', 'description': '给所有人添加角色', 'usage': '!roleall [角色名]'}
        ],
        'tags': [
            {'name': 'tag', 'description': '显示或创建标签', 'usage': '!tag [名称] [内容]'},
            {'name': 'taglist', 'description': '显示所有标签', 'usage': '!taglist'},
            {'name': 'tagdelete', 'description': '删除标签', 'usage': '!tagdelete [名称]'}
        ],
        'giveaways': [
            {'name': 'gcreate', 'description': '创建抽奖活动', 'usage': '!gcreate [时长] [奖品]'},
            {'name': 'gend', 'description': '结束抽奖活动', 'usage': '!gend [消息ID]'},
            {'name': 'greroll', 'description': '重新抽取获奖者', 'usage': '!greroll [消息ID]'}
        ],
        'game': [
            {'name': 'trivia', 'description': '开始问答游戏', 'usage': '!trivia [类别]'},
            {'name': 'hangman', 'description': '开始猜词游戏', 'usage': '!hangman [难度]'},
            {'name': 'tictactoe', 'description': '开始井字棋游戏', 'usage': '!tictactoe @用户'}
        ]
    }
    
    return default_commands.get(category, [])

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
    using_test_channels = False
    try:
        # 尝试获取机器人令牌
        bot = DiscordBot.query.filter_by(group_id=group_id, is_active=True).first()
        
        if bot and bot.bot_token:
            # 使用机器人令牌获取频道
            current_app.logger.info(f"使用机器人令牌获取频道列表，Guild ID: {group.discord_id}")
            guild_id = group.discord_id
            
            # 记录当前使用的Guild ID，帮助调试
            current_app.logger.info(f"使用的Discord服务器ID: {guild_id}")
            
            # 调试: 尝试列出机器人已加入的所有服务器
            try:
                from app.discord.bot_client import list_bot_guilds
                bot_guilds = list_bot_guilds(bot.bot_token)
                current_app.logger.info(f"机器人已加入的服务器列表: {bot_guilds}")
            except Exception as e:
                current_app.logger.warning(f"获取机器人已加入的服务器列表时出错: {str(e)}")
            
            # 使用我们修复过的函数获取频道
            from app.discord.bot_client import get_guild_channels
            channels_data = get_guild_channels(bot.bot_token, guild_id)
            
            if channels_data:
                # 转换成欢迎页面需要的格式
                channels = []
                for channel in channels_data:
                    if channel.get('type') == 0:  # 只包含文本频道
                        channels.append({
                            'id': channel.get('id'),
                            'name': f"#{channel.get('name')}",
                            'is_test': False
                        })
                current_app.logger.info(f"成功获取到 {len(channels)} 个频道")
            else:
                current_app.logger.warning("获取不到任何频道")
                using_test_channels = True
        else:
            current_app.logger.warning("没有找到活跃的机器人令牌，尝试使用用户令牌")
            # 没有机器人令牌，尝试使用用户令牌（旧方式）
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
                all_channels = response.json()
                # 过滤出文本频道
                channels = []
                for ch in all_channels:
                    if ch.get('type') == 0:  # 只包含文本频道
                        channels.append({
                            'id': ch.get('id'),
                            'name': f"#{ch.get('name')}",
                            'is_test': False
                        })
                current_app.logger.info(f"通过用户令牌获取到 {len(channels)} 个频道")
            else:
                current_app.logger.error(f"通过用户令牌获取频道失败: {response.status_code}")
                using_test_channels = True
    except Exception as e:
        current_app.logger.error(f"获取Discord频道失败: {str(e)}")
        using_test_channels = True
        
    # 如果没有获取到任何频道，添加一些测试频道
    if not channels or using_test_channels:
        current_app.logger.warning("所有方法均未获取到频道或有错误，添加测试频道")
        test_channels = [
            {'id': 'test1', 'name': '#测试频道1 (测试)', 'is_test': True},
            {'id': 'test2', 'name': '#测试频道2 (测试)', 'is_test': True},
            {'id': 'test3', 'name': '#测试频道3 (测试)', 'is_test': True}
        ]
        
        # 如果有真实频道，只在末尾添加测试频道；否则使用测试频道替代
        if channels:
            channels.extend(test_channels)
            current_app.logger.info(f"在{len(channels)-3}个真实频道后添加了3个测试频道")
        else:
            channels = test_channels
            current_app.logger.info("仅使用测试频道")
    
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
    if not current_user.can_manage_group(group.id):
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
    if not current_user.can_manage_group(group.id):
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

# BOT管理路由
@dyno_bp.route('/bot', methods=['GET'])
@login_required
def bot_dashboard():
    """Discord机器人管理面板"""
    # 查询全局机器人和用户关联群组的机器人
    global_bot = DiscordBot.query.filter_by(group_id=None).first()
    
    # 获取用户管理的群组
    user_groups = Group.query.filter(
        (Group.owner_id == current_user.id) |
        (Group.id.in_(db.session.query(group_members.c.group_id).filter(
            (group_members.c.user_id == current_user.id) &
            (group_members.c.role == 'admin')
        )))
    ).all()
    
    # 获取这些群组关联的机器人
    group_bots = DiscordBot.query.filter(DiscordBot.group_id.in_([g.id for g in user_groups])).all()
    
    # 为模板传递一个默认的bot变量
    bot = None
    
    return render_template('dyno/bot.html', 
                          global_bot=global_bot, 
                          group_bots=group_bots,
                          user_groups=user_groups,
                          bot=bot)

@dyno_bp.route('/bot/deactivate/<int:bot_id>', methods=['POST'])
@login_required
def deactivate_bot(bot_id):
    """停用Discord机器人"""
    bot = DiscordBot.query.get_or_404(bot_id)
    
    # 验证是否有权限管理此机器人
    if bot.group_id:
        group = Group.query.get_or_404(bot.group_id)
        if current_user.id != group.owner_id and current_user.get_role_in_group(group.id) != 'admin':
            flash('您没有权限管理此群组的机器人', 'danger')
            return redirect(url_for('dyno.bot_dashboard'))
    elif not current_user.is_admin:
        flash('只有管理员可以管理全局机器人', 'danger')
        return redirect(url_for('dyno.bot_dashboard'))
    
    try:
        # 在数据库中更新机器人状态
        bot.deactivate()
        
        # 停止Discord机器人进程
        from app.discord.bot_client import stop_bot_process
        
        if stop_bot_process():
            flash('机器人已成功停用，进程已终止', 'success')
        else:
            flash('机器人在数据库中已停用，但无法找到运行的进程', 'warning')
        
        return redirect(url_for('dyno.bot_dashboard'))
    except Exception as e:
        flash('停用机器人时发生错误: {}'.format(str(e)), 'danger')
        return redirect(url_for('dyno.bot_dashboard'))

@dyno_bp.route('/bot/check-status/<int:bot_id>', methods=['POST'])
@login_required
def check_bot_status(bot_id):
    """检查Discord机器人状态"""
    bot = DiscordBot.query.get_or_404(bot_id)
    
    # 验证是否有权限管理此机器人
    if bot.group_id:
        group = Group.query.get_or_404(bot.group_id)
        if not current_user.is_admin and current_user.id != group.owner_id and current_user.get_role_in_group(group.id) != 'admin':
            return jsonify({'success': False, 'message': '您没有权限管理此群组的机器人'})
    elif not current_user.is_admin:
        return jsonify({'success': False, 'message': '只有管理员可以管理全局机器人'})
    
    try:
        # 检查Discord机器人状态
        from app.discord.bot_client import check_bot_status as check_status
        
        status, error = check_status(bot.bot_token)
        
        if status == 'online':
            # 更新数据库状态
            bot.update_status('online')
            return jsonify({
                'success': True, 
                'status': 'online',
                'message': '机器人已连接到Discord并正常运行'
            })
        elif status == 'error':
            # 更新数据库状态
            bot.update_status('error', error)
            return jsonify({
                'success': False, 
                'status': 'error',
                'message': f'机器人状态检查失败: {error}'
            })
        else:
            # 更新数据库状态
            bot.update_status('offline')
            return jsonify({
                'success': False, 
                'status': 'offline',
                'message': '机器人未连接到Discord'
            })
    except Exception as e:
        return jsonify({
            'success': False, 
            'status': 'error',
            'message': f'检查机器人状态时发生错误: {str(e)}'
        })

@dyno_bp.route('/bot/activate', methods=['POST'])
@login_required
def activate_bot():
    """激活Discord机器人"""
    bot_id = request.form.get('bot_id')
    group_id = request.form.get('group_id')
    bot_token = request.form.get('bot_token')
    channel_data = request.form.get('channel_ids', '')
    selected_channels = request.form.get('selectedChannelsInput', '')
    
    current_app.logger.info(f"激活机器人，bot_id: {bot_id}, 群组ID: {group_id}, 频道数据长度: {len(channel_data) if channel_data else 0}")
    
    if not bot_token:
        flash('请提供机器人令牌', 'danger')
        return redirect(url_for('dyno.bot_dashboard'))
    
    # 记录用于调试
    current_app.logger.info(f"正在激活机器人，bot_id: {bot_id}, 群组ID: {group_id}, 频道数据类型: {type(channel_data).__name__}, 选中频道数据类型: {type(selected_channels).__name__}")
    
    # 处理频道数据 - 首先尝试使用selectedChannelsInput
    channel_ids = ''
    if selected_channels:
        try:
            # 尝试解析选中的频道数据
            channels_list = json.loads(selected_channels)
            # 提取ID用于机器人启动
            channel_ids = ','.join([ch['id'] for ch in channels_list if 'id' in ch])
            current_app.logger.info(f"从selectedChannelsInput解析到{len(channels_list)}个频道")
        except (json.JSONDecodeError, TypeError) as e:
            current_app.logger.error(f"解析selectedChannelsInput出错: {str(e)}")
            # 失败后回退到channel_data
            channel_ids = channel_data
    else:
        # 如果没有selectedChannelsInput，尝试解析channel_data
        try:
            # 尝试解析为JSON（新格式）
            channel_info = json.loads(channel_data)
            if isinstance(channel_info, dict):
                # 只提取ID用于机器人启动
                channel_ids = ','.join(channel_info.keys())
            elif isinstance(channel_info, list):
                # 列表格式
                channel_ids = ','.join([ch['id'] for ch in channel_info if 'id' in ch])
            current_app.logger.info(f"从channel_data解析频道ID: {channel_ids}")
        except (json.JSONDecodeError, AttributeError, TypeError):
            # 如果失败，假设为旧的逗号分隔格式
            channel_ids = channel_data
            current_app.logger.info(f"使用原始频道ID字符串: {channel_ids}")
    
    # 检查机器人令牌是否有效
    from app.discord.bot_client import get_bot_info
    bot_info = get_bot_info(bot_token)
    
    if not bot_info:
        flash('无效的机器人令牌', 'danger')
        return redirect(url_for('dyno.bot_dashboard'))
    
    # 如果提供了bot_id，直接更新该机器人
    if bot_id:
        try:
            bot_id = int(bot_id)
            # 检查bot_id是否存在
            existing_bot = DiscordBot.query.filter_by(id=bot_id).first()
            if existing_bot:
                # 验证权限
                if existing_bot.group_id and str(existing_bot.group_id) != str(group_id) and group_id is not None:
                    current_app.logger.warning(f"尝试更新不匹配的群组ID: 机器人群组 {existing_bot.group_id}, 请求群组 {group_id}")
                    group = Group.query.get(existing_bot.group_id)
                    if not group or (not current_user.is_admin and current_user.id != group.owner_id):
                        flash('您没有权限管理此机器人', 'danger')
                        return redirect(url_for('dyno.bot_dashboard'))
                elif not existing_bot.group_id and not current_user.is_admin:
                    flash('只有管理员可以管理全局机器人', 'danger')
                    return redirect(url_for('dyno.bot_dashboard'))
                
                # 更新机器人信息
                if bot_token:  # 只有当提供了新令牌时才更新
                    existing_bot.bot_token = bot_token
                    existing_bot.bot_name = bot_info.get('username', '未知机器人')
                existing_bot.status = 'online'
                existing_bot.channel_ids = channel_ids
                existing_bot.last_activated = datetime.now()
                existing_bot.activated_by = current_user.id
                
                db.session.commit()
                bot_id = existing_bot.id
                flash(f'机器人 {existing_bot.bot_name} 已成功激活', 'success')
                
                # 记录系统事件
                event = SystemEvent(
                    event_type='bot_activated',
                    user_id=current_user.id,
                    data=json.dumps({
                        'bot_id': existing_bot.id,
                        'bot_name': existing_bot.bot_name,
                        'group_id': existing_bot.group_id
                    })
                )
                db.session.add(event)
                db.session.commit()
            else:
                current_app.logger.warning(f"找不到bot_id为{bot_id}的机器人记录")
        except Exception as e:
            current_app.logger.error(f"处理bot_id时出错: {bot_id}, 错误: {str(e)}")
            # 继续执行常规流程
    # 根据群组ID处理不同类型的机器人
    if group_id == 'global':
        # 全局机器人
        if not current_user.is_admin:
            flash('只有管理员可以配置全局机器人', 'danger')
            return redirect(url_for('dyno.bot_dashboard'))
        
        # 检查是否已存在全局机器人
        existing_bot = DiscordBot.query.filter_by(group_id=None).first()
        
        if existing_bot:
            # 更新现有机器人
            existing_bot.bot_token = bot_token
            existing_bot.bot_name = bot_info.get('username', '未知机器人')
            existing_bot.status = 'online'
            existing_bot.channel_ids = channel_ids
            existing_bot.last_activated = datetime.now()
            existing_bot.activated_by = current_user.id
            
            db.session.commit()
            bot_id = existing_bot.id
        else:
            # 创建新的全局机器人
            new_bot = DiscordBot(
                bot_token=bot_token,
                bot_name=bot_info.get('username', '未知机器人'),
                status='online',
                channel_ids=channel_ids,
                last_activated=datetime.now(),
                activated_by=current_user.id
            )
            
            db.session.add(new_bot)
            db.session.commit()
            bot_id = new_bot.id
        
        flash(f'全局机器人 {bot_info.get("username", "未知机器人")} 已激活', 'success')
    else:
        # 群组机器人
        try:
            group_id = int(group_id)
        except (ValueError, TypeError):
            flash('无效的群组ID', 'danger')
            return redirect(url_for('dyno.bot_dashboard'))
        
        # 检查用户是否有权限激活此群组的机器人
        group = Group.query.get(group_id)
        if not group:
            flash('群组不存在', 'danger')
            return redirect(url_for('dyno.bot_dashboard'))
        
        if not current_user.is_admin and current_user.id != group.owner_id:
            flash('您没有权限为此群组激活机器人', 'danger')
            return redirect(url_for('dyno.bot_dashboard'))
        
        # 检查是否已存在该群组的机器人
        existing_bot = DiscordBot.query.filter_by(group_id=group_id).first()
        
        if existing_bot:
            # 更新现有机器人
            existing_bot.bot_token = bot_token
            existing_bot.bot_name = bot_info.get('username', '未知机器人')
            existing_bot.status = 'online'
            existing_bot.channel_ids = channel_ids
            existing_bot.last_activated = datetime.now()
            existing_bot.activated_by = current_user.id
            
            db.session.commit()
            bot_id = existing_bot.id
        else:
            # 创建新的群组机器人
            new_bot = DiscordBot(
                group_id=group_id,
                bot_token=bot_token,
                bot_name=bot_info.get('username', '未知机器人'),
                status='online',
                channel_ids=channel_ids,
                last_activated=datetime.now(),
                activated_by=current_user.id
            )
            
            db.session.add(new_bot)
            db.session.commit()
            bot_id = new_bot.id
        
        flash(f'群组 {group.name} 的机器人 {bot_info.get("username", "未知机器人")} 已激活', 'success')
    
    # 启动Discord机器人进程 - 只在这里统一启动一次
    current_app.logger.info(f"准备启动机器人，使用令牌，群组ID: {group_id}")
    success, pid = start_discord_bot(bot_token, channel_ids)
    if success:
        current_app.logger.info(f"成功启动机器人进程，PID: {pid}")
        return redirect(url_for('dyno.bot_dashboard'))
    else:
        flash('机器人启动失败', 'danger')
        return redirect(url_for('dyno.bot_dashboard'))

# 辅助函数：启动Discord机器人进程
def start_discord_bot(bot_token, channel_ids):
    """
    启动Discord机器人进程
    
    参数:
        bot_token: Discord机器人令牌
        channel_ids: 用逗号分隔的频道ID列表
        
    返回:
        (success, process_id): 成功状态和进程ID (如果成功)
    """
    try:
        from app.discord.bot_client import start_bot_process
        
        current_app.logger.info("正在启动Discord机器人进程...")
        process_id = start_bot_process(bot_token, channel_ids)
        
        if process_id:
            current_app.logger.info(f"Discord机器人进程已启动，PID: {process_id}")
            return True, process_id
        else:
            current_app.logger.error("启动机器人进程失败")
            return False, None
    except Exception as e:
        current_app.logger.error(f"启动机器人进程时出错: {str(e)}")
        return False, None

# Discord频道API路由
@dyno_bp.route('/api/discord/channels', methods=['POST'])
def get_discord_channels_api():
    """获取指定服务器的Discord频道列表，用于AJAX请求"""
    token = request.form.get('token')
    guild_id = request.form.get('guild_id')
    
    current_app.logger.info(f"收到频道请求，服务器ID: {guild_id}，令牌长度: {len(token) if token else 0}")
    
    if not token or not guild_id:
        current_app.logger.error("获取Discord频道列表：缺少令牌或服务器ID")
        return jsonify({'success': False, 'error': '缺少令牌或服务器ID'})
    
    # 清理令牌，确保格式一致
    token = token.strip()
    if token.startswith('Bot '):
        token = token[4:]
        
    current_app.logger.info(f"请求Discord频道列表，服务器ID: {guild_id}，令牌长度: {len(token)}")
    
    try:
        # 在此直接调用Discord API，不使用get_guild_channels函数
        # 确保令牌格式正确
        if not token.startswith('Bot '):
            token = f'Bot {token}'
        
        # 定义API URL
        url = f'https://discord.com/api/v10/guilds/{guild_id}/channels'
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        
        current_app.logger.info(f"请求Discord频道列表URL: {url}")
        
        response = requests.get(url, headers=headers)
        current_app.logger.info(f"API响应状态码: {response.status_code}")
        
        if response.status_code != 200:
            current_app.logger.error(f"获取频道列表失败: {response.status_code}")
            current_app.logger.error(f"响应内容: {response.text}")
            return jsonify({'success': False, 'error': f"API错误: HTTP {response.status_code}"})
            
        channels_data = response.json()
        current_app.logger.info(f"成功获取到 {len(channels_data)} 个原始频道")
        
        # 获取父频道（分类）映射
        categories = {}
        for channel in channels_data:
            if channel.get('type') == 4:  # 4 = 分类频道
                categories[channel.get('id')] = channel.get('name')
        
        # 格式化返回结果，仅返回文本频道和公告频道
        formatted_channels = []
        for channel in channels_data:
            channel_type = channel.get('type')
            # 仅包含文本(0)和公告(5)频道
            if channel_type in [0, 5]:
                parent_id = channel.get('parent_id')
                formatted_channels.append({
                    'id': channel.get('id'),
                    'name': channel.get('name'),
                    'type': channel_type,
                    'parent_id': parent_id,
                    'parent_name': categories.get(parent_id, '未分类')
                })
        
        # 记录一些返回的频道数据用于调试
        current_app.logger.info(f"过滤后返回 {len(formatted_channels)} 个可用频道")
        if formatted_channels:
            for i, ch in enumerate(formatted_channels[:3]):  # 只记录前3个避免日志过大
                current_app.logger.info(f"频道样例 {i+1}: ID={ch.get('id')}, 名称={ch.get('name')}, 类型={ch.get('type')}, 分类={ch.get('parent_name')}")
        
        response = jsonify({
            'success': True,
            'channels': formatted_channels
        })
        
        # 添加CORS头
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        
        return response
    except Exception as e:
        import traceback
        current_app.logger.error(f"获取Discord频道出错: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        
        response = jsonify({
            'success': False,
            'error': f"获取频道失败: {str(e)}",
            'detail': traceback.format_exc()
        })
        
        # 添加CORS头
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        
        return response

# Discord服务器API路由
@dyno_bp.route('/api/discord/guilds', methods=['POST'])
@login_required
def get_discord_guilds():
    """获取机器人所在的Discord服务器列表，用于AJAX请求"""
    token = request.form.get('token', '').strip()
    
    if not token:
        return jsonify({'success': False, 'error': '缺少机器人令牌'})
    
    # 确保令牌格式和内容正确（移除可能的引号和空格）
    token = token.strip('\'"')
    
    # 我们在bot_client.py中已经处理了Bot前缀添加，这里不需要再处理
    
    current_app.logger.info(f"处理后的令牌前10位: {token[:10]}...")
    current_app.logger.info(f"请求Discord服务器列表，令牌前5位: {token[:5]}...")
    
    try:
        # 从Discord API获取服务器列表
        current_app.logger.info("调用get_bot_guilds获取服务器...")
        guilds = get_bot_guilds(token)
        print(f"获取到 {len(guilds)} 个服务器")
        
        # 返回服务器列表
        current_app.logger.info(f"成功获取到 {len(guilds)} 个服务器")
        return jsonify({
            'success': True, 
            'guilds': guilds
        })
    except Exception as e:
        print(f"获取Discord服务器列表时出错: {str(e)}")
        current_app.logger.error(f"获取Discord服务器列表时出错: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

@dyno_bp.route('/api/bot/status', methods=['POST'])
@login_required
def check_bot_status_api():
    """检查Discord机器人状态，用于AJAX请求"""
    bot_id = request.form.get('bot_id')
    
    if not bot_id:
        return jsonify({'success': False, 'error': '缺少机器人ID'})
    
    try:
        bot = DiscordBot.query.get(bot_id)
        
        if not bot:
            return jsonify({'success': False, 'error': '找不到指定的机器人'})
        
        # 验证用户权限
        if bot.group_id:
            group = Group.query.get(bot.group_id)
            if not current_user.is_admin and current_user.id != group.owner_id and current_user.get_role_in_group(group.id) != 'admin':
                return jsonify({'success': False, 'error': '您没有权限查看此机器人状态'})
        elif not current_user.is_admin:
            return jsonify({'success': False, 'error': '只有管理员可以查看全局机器人状态'})
        
        # 检查实际状态
        from app.discord.bot_client import check_bot_status
        
        status, error = check_bot_status(bot.bot_token)
        
        # 更新数据库中的状态
        if status != bot.status:
            if status == 'online':
                bot.update_status('online')
            elif status == 'error':
                bot.update_status('error', error)
            else:
                bot.update_status('offline')
            db.session.commit()
        
        return jsonify({
            'success': True,
            'status': status,
            'message': error if error else '机器人状态已更新'
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'status': 'error',
            'message': f'检查机器人状态时发生错误: {str(e)}'
        })

@dyno_bp.route('/api/bot/info', methods=['POST'])
@dyno_bp.route('/api/dyno/bot-info', methods=['POST'])  # 添加兼容的路由
@login_required
def get_bot_info_api():
    """获取Discord机器人信息，用于AJAX请求"""
    data = request.get_json() or {}
    form_data = request.form
    
    # 兼容多种请求格式
    bot_id = data.get('bot_id') or form_data.get('bot_id')
    
    current_app.logger.info(f"获取机器人信息API被调用, bot_id: {bot_id}, 数据类型: {type(data)}")
    
    if not bot_id:
        current_app.logger.error("获取机器人信息API错误: 缺少机器人ID")
        return jsonify({'success': False, 'error': '缺少机器人ID'})
    
    try:
        bot = DiscordBot.query.get(bot_id)
        
        if not bot:
            return jsonify({'success': False, 'error': '找不到指定的机器人'})
        
        # 验证用户权限
        if bot.group_id:
            group = Group.query.get(bot.group_id)
            if not current_user.is_admin and current_user.id != group.owner_id and current_user.get_role_in_group(group.id) != 'admin':
                return jsonify({'success': False, 'error': '您没有权限查看此机器人信息'})
        elif not current_user.is_admin:
            return jsonify({'success': False, 'error': '只有管理员可以查看全局机器人信息'})
        
        # 获取机器人信息
        from app.discord.bot_client import get_bot_info
        
        bot_info = get_bot_info(bot.bot_token)
        
        if not bot_info:
            return jsonify({'success': False, 'error': '无法获取机器人信息，请检查令牌是否有效'})
        
        # 更新数据库中的机器人名称
        if bot_info.get('username') and bot_info.get('username') != bot.bot_name:
            bot.bot_name = bot_info.get('username')
            db.session.commit()
        
        return jsonify({
            'success': True,
            'bot_name': bot_info.get('username', bot.bot_name or '未知机器人'),
            'bot_id': bot_info.get('id'),
            'avatar': bot_info.get('avatar')
        })
    except Exception as e:
        current_app.logger.error(f"API获取机器人信息时出错: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
