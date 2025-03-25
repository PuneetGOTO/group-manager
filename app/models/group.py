from app import db
from datetime import datetime
import uuid

class Group(db.Model):
    """群组模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    avatar = db.Column(db.String(255), default='default_group.jpg')
    banner = db.Column(db.String(255), default='default_banner.jpg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=True)
    invite_code = db.Column(db.String(16), unique=True, nullable=True)
    
    # 外键
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Discord集成
    discord_id = db.Column(db.String(100), unique=True, nullable=True)
    
    # 关系
    posts = db.relationship('Post', backref='group', lazy=True, cascade="all, delete-orphan")
    events = db.relationship('Event', backref='group', lazy=True, cascade="all, delete-orphan")
    user_members = db.relationship('User', secondary='group_members', lazy='dynamic')
    
    def __init__(self, name, owner_id, description=None, is_public=True, **kwargs):
        self.name = name
        self.owner_id = owner_id
        self.description = description
        self.is_public = is_public
        self.invite_code = str(uuid.uuid4())[:16] if not is_public else None
        
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def generate_invite_code(self):
        """生成新的邀请码"""
        self.invite_code = str(uuid.uuid4())[:16]
        return self.invite_code
    
    def get_members_count(self):
        """获取群组成员数量"""
        return self.user_members.count()
    
    def get_admin_members(self):
        """获取群组管理员"""
        # 使用字符串引用避免循环导入
        admin_members = []
        admins_query = db.session.execute(
            db.text("SELECT user_id FROM group_members WHERE group_id = :group_id AND role = 'admin'"),
            {"group_id": self.id}
        ).fetchall()
        
        if admins_query:
            from app.models.user import User
            admin_ids = [admin[0] for admin in admins_query]
            admin_members = User.query.filter(User.id.in_(admin_ids)).all()
        
        return admin_members
    
    def is_admin(self, user):
        """检查用户是否是该群组的管理员
        
        Args:
            user: 用户对象
            
        Returns:
            bool: 是否是管理员
        """
        # 首先检查是否是群组拥有者
        if user.id == self.owner_id:
            return True
            
        # 然后检查是否是群组管理员
        admin_query = db.session.execute(
            db.text("SELECT 1 FROM group_members WHERE group_id = :group_id AND user_id = :user_id AND role = 'admin'"),
            {"group_id": self.id, "user_id": user.id}
        ).fetchone()
        
        return admin_query is not None
    
    def __repr__(self):
        return f'<Group {self.name}>'
