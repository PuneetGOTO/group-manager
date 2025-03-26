from app import db
from datetime import datetime

# 用户-活动关联表（多对多关系）
event_participants = db.Table('event_participants',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('status', db.String(20), default='attending'),  # 状态: attending, maybe, declined
    db.Column('registered_at', db.DateTime, default=datetime.utcnow)
)

class Event(db.Model):
    """群组活动模型"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(255))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=False)
    online_url = db.Column(db.String(255))
    max_participants = db.Column(db.Integer, default=0)  # 0 表示不限制
    
    # 外键
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    
    # 关系
    creator = db.relationship('User', backref='created_events')
    group = db.relationship('Group', backref='events')
    participants = db.relationship('User', secondary=event_participants, backref='events')
    
    def __init__(self, title, start_time, end_time, creator_id, group_id, **kwargs):
        self.title = title
        self.start_time = start_time
        self.end_time = end_time
        self.creator_id = creator_id
        self.group_id = group_id
        
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def get_participants_count(self):
        """获取活动参与者数量"""
        return db.session.query(event_participants).filter_by(event_id=self.id, status='attending').count()
    
    def is_full(self):
        """检查活动是否已满"""
        if self.max_participants == 0:
            return False
        return self.get_participants_count() >= self.max_participants
    
    def __repr__(self):
        return f'<Event {self.title}>'

class SystemEvent(db.Model):
    """系统事件记录模型，用于记录重要系统操作"""
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)  # 事件类型，例如: bot_activated, user_login, etc.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 可能为空，如果是系统自动操作
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(db.Text)  # JSON格式的事件数据
    
    # 关系
    user = db.relationship('User', backref='system_events')
    
    def __repr__(self):
        return f'<SystemEvent {self.event_type} by user_id={self.user_id} at {self.timestamp}>'
