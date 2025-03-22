from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import current_user, login_required
from app.models import User, Group, Post, Event, event_participants
from app import db
from datetime import datetime
import os
from werkzeug.utils import secure_filename

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile')
@login_required
def profile():
    """显示当前用户的个人资料"""
    return render_template('user/profile.html', user=current_user)

@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """编辑个人资料"""
    if request.method == 'POST':
        username = request.form.get('username')
        bio = request.form.get('bio')
        
        # 验证表单
        if not username:
            flash('用户名不能为空', 'danger')
            return render_template('user/edit_profile.html')
        
        # 检查用户名是否已存在
        if username != current_user.username:
            user_exists = User.query.filter_by(username=username).first()
            if user_exists:
                flash('该用户名已被使用', 'danger')
                return render_template('user/edit_profile.html')
        
        # 更新个人资料
        current_user.username = username
        current_user.bio = bio
        
        # 处理头像上传
        if 'profile_image' in request.files:
            profile_image = request.files['profile_image']
            if profile_image.filename != '':
                # 确保上传目录存在
                upload_dir = os.path.join(os.getcwd(), 'app', 'static', 'uploads', 'profile_images')
                os.makedirs(upload_dir, exist_ok=True)
                
                # 保存文件
                filename = secure_filename(f"{current_user.id}_{profile_image.filename}")
                filepath = os.path.join(upload_dir, filename)
                profile_image.save(filepath)
                
                # 更新数据库中的头像路径
                current_user.profile_image = f"uploads/profile_images/{filename}"
        
        db.session.commit()
        
        flash('个人资料已更新', 'success')
        return redirect(url_for('user.profile'))
    
    return render_template('user/edit_profile.html')

@user_bp.route('/profile/<int:user_id>')
def view_profile(user_id):
    """查看其他用户的个人资料"""
    user = User.query.get_or_404(user_id)
    
    # 获取用户创建的公开群组
    public_groups = Group.query.filter_by(owner_id=user_id, is_public=True).all()
    
    # 获取当前登录用户和查看的用户共同所在的群组
    common_groups = []
    if current_user.is_authenticated:
        current_user_groups = {group.id: group for group in current_user.groups}
        user_groups = {group.id: group for group in user.groups}
        
        common_group_ids = set(current_user_groups.keys()) & set(user_groups.keys())
        common_groups = [user_groups[group_id] for group_id in common_group_ids]
    
    return render_template('user/view_profile.html', 
                          user=user, 
                          public_groups=public_groups,
                          common_groups=common_groups)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    """用户仪表盘"""
    # 获取用户的群组
    user_groups = current_user.groups
    
    # 获取用户所在群组的最新帖子
    recent_posts = Post.query.join(Group).filter(
        Group.id.in_([g.id for g in user_groups])
    ).order_by(Post.created_at.desc()).limit(10).all()
    
    # 获取用户的即将到来的活动
    upcoming_events = Event.query.join(
        event_participants, Event.id == event_participants.c.event_id
    ).filter(
        event_participants.c.user_id == current_user.id,
        Event.start_time > datetime.utcnow()
    ).order_by(Event.start_time).all()
    
    return render_template('user/dashboard.html',
                          user_groups=user_groups,
                          recent_posts=recent_posts,
                          upcoming_events=upcoming_events)

@user_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证表单
        if not current_password or not new_password or not confirm_password:
            flash('所有字段都必须填写', 'danger')
            return render_template('user/change_password.html')
        
        if new_password != confirm_password:
            flash('两次输入的新密码不一致', 'danger')
            return render_template('user/change_password.html')
        
        # 验证当前密码
        if not current_user.check_password(current_password):
            flash('当前密码不正确', 'danger')
            return render_template('user/change_password.html')
        
        # 更新密码
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('密码已成功修改', 'success')
        return redirect(url_for('user.profile'))
    
    return render_template('user/change_password.html')

@user_bp.route('/notifications')
@login_required
def notifications():
    """用户通知"""
    # 此处应该实现获取用户通知的逻辑
    # 暂时返回一个模板页面，显示没有通知
    return render_template('user/notifications.html')

@user_bp.route('/settings')
@login_required
def settings():
    """用户设置页面"""
    return render_template('user/settings.html')

@user_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    """更新用户个人资料"""
    username = request.form.get('username')
    bio = request.form.get('bio')
    profile_image = request.files.get('profile_image')
    
    # 验证用户名是否已被使用
    if username != current_user.username:
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('该用户名已被使用', 'danger')
            return redirect(url_for('user.settings'))
    
    # 更新用户信息
    current_user.username = username
    current_user.bio = bio
    
    # 处理头像上传
    if profile_image and profile_image.filename:
        filename = secure_filename(profile_image.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if ext in ['jpg', 'jpeg', 'png', 'gif']:
            # 生成唯一文件名
            new_filename = f"profile_{current_user.id}.{ext}"
            
            # 确保上传目录存在
            upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads', 'profiles')
            os.makedirs(upload_dir, exist_ok=True)
            
            # 保存文件
            file_path = os.path.join(upload_dir, new_filename)
            profile_image.save(file_path)
            
            # 更新数据库
            current_user.profile_image = f"uploads/profiles/{new_filename}"
        else:
            flash('不支持的图片格式，请上传jpg、jpeg、png或gif格式', 'warning')
    
    db.session.commit()
    flash('个人资料已更新', 'success')
    return redirect(url_for('user.settings', _anchor='profile'))

@user_bp.route('/update_account', methods=['POST'])
@login_required
def update_account():
    """更新用户账号设置"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # 验证当前密码
    if not current_user.check_password(current_password):
        flash('当前密码不正确', 'danger')
        return redirect(url_for('user.settings', _anchor='account'))
    
    # 验证新密码
    if new_password != confirm_password:
        flash('两次输入的密码不一致', 'danger')
        return redirect(url_for('user.settings', _anchor='account'))
    
    # 更新密码
    current_user.password = new_password
    db.session.commit()
    flash('密码已更新', 'success')
    return redirect(url_for('user.settings', _anchor='account'))

@user_bp.route('/update_notifications', methods=['POST'])
@login_required
def update_notifications():
    """更新用户通知设置"""
    # 这个功能可以在后续实现，现在仅返回设置页面
    flash('通知设置已更新', 'success')
    return redirect(url_for('user.settings', _anchor='notifications'))
