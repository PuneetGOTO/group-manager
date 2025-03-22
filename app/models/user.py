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
    db.Column('joined_at', db.DateTime, default=datetime.utcnow)
)

class User(db.Model, UserMixin):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    profile_image = db.Column(db.String(255), default='default_profile.png')
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
    comments = db.relationship('Comment', backref='author', lazy=True)
    
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
        stmt = db.select([group_members.c.role]).where(
            (group_members.c.user_id == self.id) & 
            (group_members.c.group_id == group_id)
        )
        result = db.session.execute(stmt).first()
        return result[0] if result else None
    
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
        
    def __repr__(self):
        return f'<User {self.username}>'
