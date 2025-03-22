from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        # 验证用户
        if not user or not user.check_password(password):
            flash('请检查邮箱和密码是否正确', 'danger')
            return render_template('auth/login.html')
        
        # 检查账户是否激活
        if not user.is_active:
            flash('该账户已被停用，请联系管理员', 'warning')
            return render_template('auth/login.html')
        
        # 登录用户 - 默认启用记住我功能，除非用户明确取消勾选
        login_user(user, remember=remember, duration=timedelta(days=30))
        
        # 更新最后访问时间
        user.last_seen = datetime.utcnow()
        db.session.commit()
        
        flash('登录成功！', 'success')
        
        # 重定向到登录前的页面或首页
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):  # 确保只接受相对URL
            return redirect(next_page)
        return redirect(url_for('main.index'))
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        # 表单验证
        if not username or not email or not password:
            flash('所有字段都必须填写', 'danger')
            return render_template('auth/register.html')
        
        if password != password_confirm:
            flash('两次输入的密码不一致', 'danger')
            return render_template('auth/register.html')
        
        # 检查用户名和邮箱是否已存在
        email_exists = User.query.filter_by(email=email).first()
        username_exists = User.query.filter_by(username=username).first()
        
        if email_exists:
            flash('该邮箱已被注册', 'danger')
            return render_template('auth/register.html')
        
        if username_exists:
            flash('该用户名已被使用', 'danger')
            return render_template('auth/register.html')
        
        # 创建新用户
        new_user = User(
            username=username,
            email=email,
            password=password
        )
        
        # 保存到数据库
        db.session.add(new_user)
        db.session.commit()
        
        flash('注册成功，请登录', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('您已成功登出', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    """请求重置密码"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        user = User.query.filter_by(email=email).first()
        if user:
            # 这里应该发送重置密码邮件的逻辑
            # 此处简化处理，仅做演示
            flash('如果该邮箱已注册，您将收到一封重置密码的邮件', 'info')
        else:
            # 为了安全，即使用户不存在也显示相同的消息
            flash('如果该邮箱已注册，您将收到一封重置密码的邮件', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password_request.html')
