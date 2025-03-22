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
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    profile_image = db.Column(db.String(255), default='default.jpg')
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # 关系
    owned_groups = db.relationship('Group', backref='owner', lazy=True)
    groups = db.relationship('Group', secondary=group_members, 
                            backref=db.backref('members', lazy='dynamic'))
    posts = db.relationship('Post', backref='author', lazy=True)
    
    def __init__(self, username, email, password, **kwargs):
        self.username = username
        self.email = email
        self.set_password(password)
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def set_password(self, password):
        """设置用户密码"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证用户密码"""
        return check_password_hash(self.password_hash, password)
    
    def get_user_groups(self):
        """获取用户所属的群组"""
        return self.groups
    
    def get_role_in_group(self, group_id):
        """获取用户在指定群组中的角色"""
        group_member = db.session.query(group_members).filter_by(
            user_id=self.id, group_id=group_id).first()
        return group_member.role if group_member else None
    
    def __repr__(self):
        return f'<User {self.username}>'
