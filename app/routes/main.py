from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user, login_required
from app.models import Group, Post, Event
from app import db
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """网站首页"""
    # 获取公开群组
    public_groups = Group.query.filter_by(is_public=True).order_by(Group.created_at.desc()).limit(5).all()
    
    if current_user.is_authenticated:
        # 获取用户的群组
        user_groups = current_user.groups
        
        # 获取用户群组的最新帖子
        recent_posts = Post.query.join(Group).filter(
            Group.id.in_([g.id for g in user_groups])
        ).order_by(Post.created_at.desc()).limit(10).all()
        
        # 获取即将到来的活动
        upcoming_events = Event.query.join(Group).filter(
            Group.id.in_([g.id for g in user_groups]),
            Event.start_time > datetime.utcnow(),
            Event.start_time < datetime.utcnow() + timedelta(days=7)
        ).order_by(Event.start_time).limit(5).all()
        
        return render_template('index.html', 
                               public_groups=public_groups,
                               user_groups=user_groups,
                               recent_posts=recent_posts,
                               upcoming_events=upcoming_events)
    
    return render_template('index.html', public_groups=public_groups)

@main_bp.route('/search')
def search():
    """搜索功能"""
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('main.index'))
    
    groups = Group.query.filter(
        (Group.name.ilike(f'%{query}%') | Group.description.ilike(f'%{query}%')) &
        Group.is_public
    ).all()
    
    return render_template('search.html', query=query, groups=groups)

@main_bp.route('/about')
def about():
    """关于页面"""
    return render_template('about.html')

@main_bp.app_errorhandler(404)
def page_not_found(e):
    """404错误页面"""
    return render_template('errors/404.html'), 404

@main_bp.app_errorhandler(500)
def internal_server_error(e):
    """500错误页面"""
    return render_template('errors/500.html'), 500
