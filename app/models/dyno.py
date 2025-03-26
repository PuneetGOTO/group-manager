"""Dyno功能模型"""
from app import db
from datetime import datetime

class AutoModSetting(db.Model):
    """自动审核系统设置"""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    enabled = db.Column(db.Boolean, default=False)
    
    # 反垃圾邮件设置
    spam_enabled = db.Column(db.Boolean, default=False)
    spam_action = db.Column(db.String(20), default='delete')  # delete, warn, mute, kick, ban
    spam_threshold = db.Column(db.Integer, default=5)
    
    # 不良内容过滤
    filter_enabled = db.Column(db.Boolean, default=False)
    filter_words = db.Column(db.Text, default='')  # 以逗号分隔的关键词
    filter_action = db.Column(db.String(20), default='delete')
    
    # 链接过滤
    link_filter_enabled = db.Column(db.Boolean, default=False)
    allowed_domains = db.Column(db.Text, default='')  # 以逗号分隔的允许域名
    link_filter_action = db.Column(db.String(20), default='delete')
    
    # 大写字母审核
    caps_filter_enabled = db.Column(db.Boolean, default=False)
    caps_percentage = db.Column(db.Integer, default=70)  # 大写字母百分比阈值
    caps_min_length = db.Column(db.Integer, default=10)  # 最小字符数
    
    # 重复消息审核
    duplicate_filter_enabled = db.Column(db.Boolean, default=False)
    duplicate_threshold = db.Column(db.Integer, default=3)  # 允许的重复消息数
    duplicate_timeframe = db.Column(db.Integer, default=60)  # 时间窗口(秒)
    
    # 慢速模式
    slowmode_enabled = db.Column(db.Boolean, default=False)
    slowmode_seconds = db.Column(db.Integer, default=5)  # 消息间隔秒数
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 反向关系
    group = db.relationship('Group', backref=db.backref('automod_setting', uselist=False))
    
    def __repr__(self):
        return f'<AutoModSetting {self.id} for Group {self.group_id}>'


class WelcomeMessage(db.Model):
    """欢迎和告别消息设置"""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    welcome_enabled = db.Column(db.Boolean, default=False)
    welcome_channel_id = db.Column(db.String(64), nullable=True)
    welcome_message = db.Column(db.Text, default='欢迎 {user} 加入 {server}！')
    
    goodbye_enabled = db.Column(db.Boolean, default=False)
    goodbye_channel_id = db.Column(db.String(64), nullable=True)
    goodbye_message = db.Column(db.Text, default='{user} 离开了 {server}。')
    
    dm_welcome_enabled = db.Column(db.Boolean, default=False)
    dm_welcome_message = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 反向关系
    group = db.relationship('Group', backref=db.backref('welcome_message', uselist=False))
    
    def __repr__(self):
        return f'<WelcomeMessage {self.id} for Group {self.group_id}>'


class CustomCommand(db.Model):
    """自定义命令"""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    name = db.Column(db.String(32), nullable=False)
    response = db.Column(db.Text, nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 反向关系
    group = db.relationship('Group', backref=db.backref('custom_commands', lazy=True))
    creator = db.relationship('User', backref=db.backref('created_commands', lazy=True))
    
    def __repr__(self):
        return f'<CustomCommand {self.name} for Group {self.group_id}>'


class LevelSystem(db.Model):
    """等级系统设置"""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    enabled = db.Column(db.Boolean, default=False)
    xp_per_message = db.Column(db.Integer, default=15)  # 每条消息获得的经验值
    xp_cooldown = db.Column(db.Integer, default=60)  # 经验值获取冷却时间(秒)
    level_multiplier = db.Column(db.Float, default=1.5)  # 等级提升系数
    level_announcement = db.Column(db.Boolean, default=True)  # 是否公开宣布等级提升
    level_channel_id = db.Column(db.String(64), nullable=True)  # 等级公告频道ID
    level_roles_enabled = db.Column(db.Boolean, default=False)  # 是否启用等级角色
    level_roles = db.Column(db.Text, default='')  # 格式：等级:角色ID,等级:角色ID
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 反向关系
    group = db.relationship('Group', backref=db.backref('level_system', uselist=False))
    levels = db.relationship('UserLevel', backref='system', lazy=True)
    
    def __repr__(self):
        return f'<LevelSystem {self.id} for Group {self.group_id}>'


class UserLevel(db.Model):
    """用户等级"""
    id = db.Column(db.Integer, primary_key=True)
    level_system_id = db.Column(db.Integer, db.ForeignKey('level_system.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    discord_id = db.Column(db.String(64), nullable=False)  # Discord用户ID
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=0)
    last_xp_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 反向关系
    user = db.relationship('User', backref=db.backref('levels', lazy=True))
    
    __table_args__ = (
        db.UniqueConstraint('level_system_id', 'user_id', name='unique_user_level'),
    )
    
    def __repr__(self):
        return f'<UserLevel Level {self.level} XP {self.xp} for User {self.user_id}>'


class LogSetting(db.Model):
    """服务器日志设置"""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    enabled = db.Column(db.Boolean, default=False)
    log_channel_id = db.Column(db.String(64), nullable=True)
    
    # 日志类型设置
    log_joins_leaves = db.Column(db.Boolean, default=True)
    log_message_edits = db.Column(db.Boolean, default=True)
    log_message_deletes = db.Column(db.Boolean, default=True)
    log_role_changes = db.Column(db.Boolean, default=True)
    log_channel_changes = db.Column(db.Boolean, default=True)
    log_nickname_changes = db.Column(db.Boolean, default=True)
    log_bans_unbans = db.Column(db.Boolean, default=True)
    log_voice_changes = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 反向关系
    group = db.relationship('Group', backref=db.backref('log_setting', uselist=False))
    
    def __repr__(self):
        return f'<LogSetting {self.id} for Group {self.group_id}>'


class MusicSetting(db.Model):
    """音乐播放设置"""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    enabled = db.Column(db.Boolean, default=False)
    default_volume = db.Column(db.Integer, default=50)  # 默认音量百分比
    dj_role_id = db.Column(db.String(64), nullable=True)  # DJ角色ID
    auto_play = db.Column(db.Boolean, default=False)  # 自动播放
    announce_songs = db.Column(db.Boolean, default=True)  # 宣布歌曲
    restrictions_enabled = db.Column(db.Boolean, default=False)  # 启用限制
    max_queue_length = db.Column(db.Integer, default=100)  # 最大队列长度
    max_song_length = db.Column(db.Integer, default=600)  # 最大歌曲长度(秒)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 反向关系
    group = db.relationship('Group', backref=db.backref('music_setting', uselist=False))
    
    def __repr__(self):
        return f'<MusicSetting {self.id} for Group {self.group_id}>'


# 系统命令模型
class SystemCommand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    usage = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # manager, mod, info, fun, moderator, roles, tags, giveaways, game
    enabled = db.Column(db.Boolean, default=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    
    # 关系
    group = db.relationship('Group', backref=db.backref('system_commands', lazy='dynamic'))
    
    def __repr__(self):
        return f'<SystemCommand {self.name}>'


# 系统命令类别设置
class CommandCategorySetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # manager, mod, info, fun, moderator, roles, tags, giveaways, game
    enabled = db.Column(db.Boolean, default=True)
    
    # 关系
    group = db.relationship('Group', backref=db.backref('command_category_settings', lazy='dynamic'))
    
    def __repr__(self):
        return f'<CommandCategorySetting {self.category}>'
        
    # 联合唯一约束
    __table_args__ = (
        db.UniqueConstraint('group_id', 'category', name='_group_category_uc'),
    )


class DiscordBot(db.Model):
    """Discord机器人配置"""
    id = db.Column(db.Integer, primary_key=True)
    bot_token = db.Column(db.String(100), nullable=True)
    bot_name = db.Column(db.String(100), nullable=True)
    activated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=False)
    last_activated = db.Column(db.DateTime, nullable=True)
    last_status_check = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='offline')  # online, offline, error
    error_message = db.Column(db.Text, nullable=True)
    
    # 关联的群组ID（可为空，表示全局机器人）
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    group = db.relationship('Group', backref=db.backref('discord_bot', lazy=True))
    
    # 机器人频道设置
    channel_ids = db.Column(db.Text, nullable=True)  # 逗号分隔的频道ID
    
    # 机器人权限设置
    permissions = db.Column(db.String(20), default='8')  # 8表示管理员权限
    
    # 机器人设置
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DiscordBot {self.id}>'
    
    def activate(self):
        """激活机器人"""
        self.is_active = True
        self.last_activated = datetime.utcnow()
        self.status = 'online'
        db.session.commit()
    
    def deactivate(self):
        """停用机器人"""
        self.is_active = False
        self.status = 'offline'
        db.session.commit()
    
    def update_status(self, status, error_message=None):
        """更新机器人状态"""
        self.status = status
        self.last_status_check = datetime.utcnow()
        if error_message:
            self.error_message = error_message
        db.session.commit()
            
    def can_manage(self, user):
        """检查用户是否可以管理此机器人
        
        Args:
            user: 用户模型对象
            
        Returns:
            bool: 是否可以管理
        """
        # 如果用户是管理员，允许管理所有机器人
        if user.is_admin:
            return True
            
        # 如果机器人关联了群组，检查用户是否是群组管理员
        if self.group_id:
            return self.group.is_admin(user)
            
        # 默认情况下，只有管理员可以管理机器人
        return False
