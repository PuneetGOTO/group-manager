from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# 用户-群组关联表（多对多关系）
group_members = db.Table('group_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'), primary_key=True),
    db.Column('role', db.String(20), default='member'),  # 角色: admin, moderator, member
    db.Column('joined_at', db.DateTime, default=datetime.utcnow),
    db.Column('discord_roles', db.Text, nullable=True)  # 存储Discord角色ID，以逗号分隔
)

class User(db.Model, UserMixin):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    profile_image = db.Column(db.String(255), default='images/default_profile.png')
    bio = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Discord集成相关字段
    discord_id = db.Column(db.String(64), unique=True, nullable=True)
    discord_username = db.Column(db.String(100), nullable=True)
    discord_avatar = db.Column(db.String(255), nullable=True)
    discord_access_token = db.Column(db.String(255), nullable=True)
    discord_refresh_token = db.Column(db.String(255), nullable=True)
    discord_token_expires = db.Column(db.DateTime, nullable=True)
    
    # 关系
    owned_groups = db.relationship('Group', backref='owner', lazy=True)
    groups = db.relationship('Group', secondary=group_members, lazy='dynamic')
    posts = db.relationship('Post', backref='author', lazy=True)
    
    @property
    def password(self):
        raise AttributeError('密码不是可读属性')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_role_in_group(self, group_id):
        """获取用户在群组中的角色"""
        stmt = db.select(group_members.c.role).where(
            (group_members.c.user_id == self.id) & 
            (group_members.c.group_id == group_id)
        )
        result = db.session.execute(stmt).first()
        return result[0] if result else None
    
    def can_manage_group(self, group_id):
        """检查用户是否有权限管理群组
        
        权限条件：用户是群组的所有者或者是管理员角色
        
        Args:
            group_id: 群组ID
            
        Returns:
            布尔值，表示是否有权限
        """
        from app.models.group import Group
        
        # 如果用户是系统管理员，直接授权
        if self.is_admin:
            return True
            
        # 检查是否是群组所有者
        group = Group.query.get(group_id)
        if group and group.owner_id == self.id:
            return True
            
        # 检查是否是群组管理员
        role = self.get_role_in_group(group_id)
        return role == 'admin'
    
    def is_connected_to_discord(self):
        """检查用户是否已连接Discord账号"""
        return bool(self.discord_id)
    
    def disconnect_discord(self):
        """断开Discord账号连接"""
        self.discord_id = None
        self.discord_username = None
        self.discord_avatar = None
        self.discord_access_token = None
        self.discord_refresh_token = None
        self.discord_token_expires = None
        db.session.commit()
    
    def get_join_date(self, group_id):
        """获取用户加入群组的日期"""
        stmt = db.select(group_members.c.joined_at).where(
            (group_members.c.user_id == self.id) & 
            (group_members.c.group_id == group_id)
        )
        result = db.session.execute(stmt).first()
        return result[0] if result else None
        
    def get_discord_roles(self, group_id):
        """获取用户在特定群组中的Discord角色ID列表"""
        stmt = db.select(group_members.c.discord_roles).where(
            (group_members.c.user_id == self.id) & 
            (group_members.c.group_id == group_id)
        )
        result = db.session.execute(stmt).first()
        
        if result and result[0]:
            return result[0].split(',')
        return []
    
    def update_discord_roles(self, group_id, roles):
        """更新用户在特定群组中的Discord角色
        
        Args:
            group_id: 群组ID
            roles: 角色ID列表或逗号分隔的字符串
        """
        if isinstance(roles, list):
            roles_str = ','.join(roles)
        else:
            roles_str = roles
            
        # 更新用户角色
        stmt = db.update(group_members).where(
            (group_members.c.user_id == self.id) & 
            (group_members.c.group_id == group_id)
        ).values(discord_roles=roles_str)
        
        db.session.execute(stmt)
        db.session.commit()
    
    @property
    def discord_token_info(self):
        """临时兼容旧代码，将discord_token_info映射到discord_access_token"""
        # 记录访问日志，帮助识别哪里在使用这个旧属性
        from flask import current_app
        import traceback
        stack = traceback.extract_stack()
        caller = stack[-2]  # 调用者的信息
        current_app.logger.warning(
            f"发现对已弃用的discord_token_info属性的访问！"
            f"位置: {caller.filename}:{caller.lineno} in {caller.name}"
        )
        
        # 返回一个包含access_token的字典，而不是直接返回字符串
        # 这样可以兼容期望调用.get()方法的代码
        if self.discord_access_token:
            return {'access_token': self.discord_access_token}
        return None
    
    def __repr__(self):
        return f'<User {self.username}>'
