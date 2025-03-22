from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import current_user, login_required
from app.models import Group, Post, Comment, Event, User, group_members, event_participants
from app import db
from datetime import datetime
import os

groups_bp = Blueprint('groups', __name__)

@groups_bp.route('/')
@login_required
def index():
    """显示用户所有群组"""
    user_groups = current_user.groups
    owned_groups = current_user.owned_groups
    
    # 如果还是公开群组，也可以加入
    public_groups = Group.query.filter_by(is_public=True).all()
    
    return render_template('groups/index.html', 
                          user_groups=user_groups, 
                          owned_groups=owned_groups,
                          public_groups=public_groups)

@groups_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """创建新群组"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        is_public = True if request.form.get('is_public') == 'on' else False
        
        # 验证表单
        if not name:
            flash('群组名称不能为空', 'danger')
            return render_template('groups/create.html')
        
        # 创建新群组
        new_group = Group(
            name=name,
            description=description,
            is_public=is_public,
            owner_id=current_user.id
        )
        
        # 保存到数据库
        db.session.add(new_group)
        db.session.flush()  # 获取新群组ID
        
        # 将创建者添加为群组管理员
        stmt = group_members.insert().values(
            user_id=current_user.id,
            group_id=new_group.id,
            role='admin',
            joined_at=datetime.utcnow()
        )
        db.session.execute(stmt)
        
        db.session.commit()
        
        flash('群组创建成功', 'success')
        return redirect(url_for('groups.view', group_id=new_group.id))
    
    return render_template('groups/create.html')

@groups_bp.route('/<int:group_id>')
def view(group_id):
    """查看群组详情"""
    group = Group.query.get_or_404(group_id)
    
    # 非公开群组需要成员才能查看
    if not group.is_public and (not current_user.is_authenticated or group not in current_user.groups):
        flash('您没有权限查看该群组', 'warning')
        return redirect(url_for('groups.index'))
    
    # 获取群组的帖子
    posts = Post.query.filter_by(group_id=group_id).order_by(Post.created_at.desc()).all()
    
    # 获取群组的即将到来的活动
    upcoming_events = Event.query.filter_by(group_id=group_id).filter(
        Event.start_time > datetime.utcnow()
    ).order_by(Event.start_time).all()
    
    # 检查当前用户是否为管理员
    is_admin = False
    if current_user.is_authenticated and group in current_user.groups:
        user_role = current_user.get_role_in_group(group_id)
        is_admin = (user_role == 'admin' or group.owner_id == current_user.id)
    
    return render_template('groups/view.html', 
                          group=group, 
                          posts=posts, 
                          upcoming_events=upcoming_events,
                          is_admin=is_admin)

@groups_bp.route('/<int:group_id>/join')
@login_required
def join(group_id):
    """加入群组"""
    group = Group.query.get_or_404(group_id)
    
    # 检查用户是否已在群组中
    if group in current_user.groups:
        flash('您已经是该群组成员', 'info')
        return redirect(url_for('groups.view', group_id=group_id))
    
    # 检查群组是否公开
    if not group.is_public:
        invite_code = request.args.get('code')
        if not invite_code or invite_code != group.invite_code:
            flash('该群组需要邀请码才能加入', 'warning')
            return redirect(url_for('groups.index'))
    
    # 将用户添加到群组
    stmt = group_members.insert().values(
        user_id=current_user.id,
        group_id=group_id,
        role='member',
        joined_at=datetime.utcnow()
    )
    db.session.execute(stmt)
    db.session.commit()
    
    flash('成功加入群组', 'success')
    return redirect(url_for('groups.view', group_id=group_id))

@groups_bp.route('/<int:group_id>/leave')
@login_required
def leave(group_id):
    """离开群组"""
    group = Group.query.get_or_404(group_id)
    
    # 群组创建者不能离开
    if group.owner_id == current_user.id:
        flash('群组创建者不能离开群组，请先转让群组所有权', 'warning')
        return redirect(url_for('groups.view', group_id=group_id))
    
    # 检查用户是否在群组中
    if group not in current_user.groups:
        flash('您不是该群组成员', 'info')
        return redirect(url_for('groups.index'))
    
    # 移除用户与群组的关联
    stmt = group_members.delete().where(
        (group_members.c.user_id == current_user.id) & 
        (group_members.c.group_id == group_id)
    )
    db.session.execute(stmt)
    db.session.commit()
    
    flash('已成功离开群组', 'success')
    return redirect(url_for('groups.index'))

@groups_bp.route('/<int:group_id>/post/create', methods=['GET', 'POST'])
@login_required
def create_post(group_id):
    """创建群组帖子"""
    group = Group.query.get_or_404(group_id)
    
    # 检查用户是否在群组中
    if group not in current_user.groups:
        flash('只有群组成员可以发帖', 'warning')
        return redirect(url_for('groups.view', group_id=group_id))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        # 验证表单
        if not content:
            flash('帖子内容不能为空', 'danger')
            return render_template('groups/create_post.html', group=group)
        
        # 创建新帖子
        new_post = Post(
            title=title,
            content=content,
            author_id=current_user.id,
            group_id=group_id
        )
        
        # 保存到数据库
        db.session.add(new_post)
        db.session.commit()
        
        flash('帖子发布成功', 'success')
        return redirect(url_for('groups.view', group_id=group_id))
    
    return render_template('groups/create_post.html', group=group)

@groups_bp.route('/<int:group_id>/event/create', methods=['GET', 'POST'])
@login_required
def create_event(group_id):
    """创建群组活动"""
    group = Group.query.get_or_404(group_id)
    
    # 检查用户是否在群组中
    if group not in current_user.groups:
        flash('只有群组成员可以创建活动', 'warning')
        return redirect(url_for('groups.view', group_id=group_id))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        start_date = request.form.get('start_date')
        start_time = request.form.get('start_time')
        end_date = request.form.get('end_date')
        end_time = request.form.get('end_time')
        is_online = True if request.form.get('is_online') == 'on' else False
        online_url = request.form.get('online_url') if is_online else None
        max_participants = request.form.get('max_participants', 0)
        
        # 验证表单
        if not title or not start_date or not start_time or not end_date or not end_time:
            flash('带*的字段为必填项', 'danger')
            return render_template('groups/create_event.html', group=group)
        
        # 解析日期和时间
        start_datetime = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%d %H:%M')
        end_datetime = datetime.strptime(f'{end_date} {end_time}', '%Y-%m-%d %H:%M')
        
        # 检查日期有效性
        if start_datetime >= end_datetime:
            flash('结束时间必须晚于开始时间', 'danger')
            return render_template('groups/create_event.html', group=group)
        
        # 创建新活动
        new_event = Event(
            title=title,
            description=description,
            location=location,
            start_time=start_datetime,
            end_time=end_datetime,
            is_online=is_online,
            online_url=online_url,
            max_participants=max_participants,
            creator_id=current_user.id,
            group_id=group_id
        )
        
        # 保存到数据库
        db.session.add(new_event)
        db.session.flush()  # 获取新活动ID
        
        # 将创建者添加为参与者
        new_event.participants.append(current_user)
        
        db.session.commit()
        
        flash('活动创建成功', 'success')
        return redirect(url_for('groups.view', group_id=group_id))
    
    return render_template('groups/create_event.html', group=group)

@groups_bp.route('/<int:group_id>/settings', methods=['GET', 'POST'])
@login_required
def settings(group_id):
    """群组设置"""
    group = Group.query.get_or_404(group_id)
    
    # 检查权限 - 只有创建者或管理员可以访问
    if group.owner_id != current_user.id and current_user.get_role_in_group(group_id) != 'admin':
        flash('您没有权限修改群组设置', 'warning')
        return redirect(url_for('groups.view', group_id=group_id))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        is_public = True if request.form.get('is_public') == 'on' else False
        
        # 验证表单
        if not name:
            flash('群组名称不能为空', 'danger')
            return render_template('groups/settings.html', group=group)
        
        # 更新群组信息
        group.name = name
        group.description = description
        
        # 处理公开状态变更
        if group.is_public != is_public:
            group.is_public = is_public
            if not is_public and not group.invite_code:
                group.generate_invite_code()
            elif is_public:
                group.invite_code = None
        
        db.session.commit()
        
        flash('群组设置已更新', 'success')
        return redirect(url_for('groups.view', group_id=group_id))
    
    return render_template('groups/settings.html', group=group)

@groups_bp.route('/<int:group_id>/transfer-ownership', methods=['POST'])
@login_required
def transfer_ownership(group_id):
    """转让群组所有权"""
    group = Group.query.get_or_404(group_id)
    
    # 验证当前用户是否为群主
    if current_user.id != group.owner_id:
        flash('只有群主才能转让所有权', 'danger')
        return redirect(url_for('groups.settings', group_id=group_id))
    
    # 获取新群主ID
    new_owner_id = request.form.get('new_owner_id')
    if not new_owner_id:
        flash('请选择新的群主', 'warning')
        return redirect(url_for('groups.settings', group_id=group_id))
    
    # 验证新群主是否为群组成员
    new_owner = User.query.get(new_owner_id)
    if not new_owner or new_owner not in group.user_members:
        flash('选择的用户不是该群组的成员', 'danger')
        return redirect(url_for('groups.settings', group_id=group_id))
    
    # 转让所有权
    group.owner_id = new_owner.id
    
    # 确保新群主的角色为admin
    stmt = db.update(group_members).where(
        (group_members.c.group_id == group_id) & 
        (group_members.c.user_id == new_owner.id)
    ).values(role='admin')
    db.session.execute(stmt)
    
    db.session.commit()
    flash(f'群组所有权已转让给 {new_owner.username}', 'success')
    return redirect(url_for('groups.view', group_id=group_id))

@groups_bp.route('/<int:group_id>/delete', methods=['POST'])
@login_required
def delete(group_id):
    """删除群组"""
    group = Group.query.get_or_404(group_id)
    
    # 验证当前用户是否为群主
    if current_user.id != group.owner_id:
        flash('只有群主才能删除群组', 'danger')
        return redirect(url_for('groups.settings', group_id=group_id))
    
    # 获取确认信息
    confirm_name = request.form.get('confirm_name')
    
    # 验证确认信息是否正确
    if confirm_name != group.name:
        flash('群组名称不匹配，删除操作已取消', 'warning')
        return redirect(url_for('groups.settings', group_id=group_id))
    
    # 获取群组名称用于提示
    group_name = group.name
    
    # 删除群组（关联的帖子、评论、活动等会由SQLAlchemy的cascade自动处理）
    db.session.delete(group)
    db.session.commit()
    
    flash(f'群组"{group_name}"已永久删除', 'success')
    return redirect(url_for('groups.index'))

@groups_bp.route('/<int:group_id>/members')
@login_required
def members(group_id):
    """查看群组成员"""
    group = Group.query.get_or_404(group_id)
    
    # 非公开群组需要成员才能查看
    if not group.is_public and (not current_user.is_authenticated or group not in current_user.groups):
        flash('您没有权限查看该群组', 'warning')
        return redirect(url_for('groups.index'))
    
    # 获取所有成员及其角色
    members_query = db.session.query(User, group_members.c.role).join(
        group_members, User.id == group_members.c.user_id
    ).filter(group_members.c.group_id == group_id).all()
    
    # 提取User对象和角色信息
    members = []
    members_roles = {}
    for user, role in members_query:
        members.append(user)
        members_roles[user.id] = role
    
    # 检查当前用户是否为管理员
    is_admin = False
    if current_user.is_authenticated and group in current_user.groups:
        user_role = current_user.get_role_in_group(group_id)
        is_admin = (user_role == 'admin' or group.owner_id == current_user.id)
    
    return render_template('groups/members.html', 
                          group=group, 
                          members=members,
                          members_roles=members_roles,
                          is_admin=is_admin)

@groups_bp.route('/<int:group_id>/invite')
@login_required
def invite(group_id):
    """查看群组邀请链接"""
    group = Group.query.get_or_404(group_id)
    
    # 检查用户是否在群组中
    if group not in current_user.groups:
        flash('您不是该群组成员', 'warning')
        return redirect(url_for('groups.index'))
    
    # 如果群组是公开的，直接使用公开链接
    if group.is_public:
        invite_url = url_for('groups.view', group_id=group_id, _external=True)
    else:
        # 如果没有邀请码，生成一个
        if not group.invite_code:
            import uuid
            group.invite_code = str(uuid.uuid4())[:8]
            db.session.commit()
        
        invite_url = url_for('groups.join', group_id=group_id, code=group.invite_code, _external=True)
    
    return render_template('groups/invite.html', group=group, invite_url=invite_url)

@groups_bp.route('/<int:group_id>/update_settings', methods=['POST'])
@login_required
def update_settings(group_id):
    """更新群组设置"""
    group = Group.query.get_or_404(group_id)
    
    # 确保用户是群组管理员或所有者
    user_role = current_user.get_role_in_group(group_id)
    if not user_role or (user_role != 'admin' and group.owner_id != current_user.id):
        flash('您没有权限修改群组设置', 'danger')
        return redirect(url_for('groups.view', group_id=group_id))
    
    form_type = request.form.get('form_type')
    
    # 处理基本信息表单
    if form_type == 'basic':
        group.name = request.form.get('name', group.name)
        group.description = request.form.get('description', group.description)
        
        # 处理头像上传
        if 'avatar' in request.files and request.files['avatar'].filename:
            avatar = request.files['avatar']
            avatar_filename = f"group_{group_id}_avatar.{avatar.filename.split('.')[-1]}"
            avatar_path = os.path.join('app/static/uploads/avatars', avatar_filename)
            os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
            avatar.save(avatar_path)
            group.avatar = f"uploads/avatars/{avatar_filename}"
        
        # 处理横幅上传
        if 'banner' in request.files and request.files['banner'].filename:
            banner = request.files['banner']
            banner_filename = f"group_{group_id}_banner.{banner.filename.split('.')[-1]}"
            banner_path = os.path.join('app/static/uploads/banners', banner_filename)
            os.makedirs(os.path.dirname(banner_path), exist_ok=True)
            banner.save(banner_path)
            group.banner = f"uploads/banners/{banner_filename}"
        
        flash('群组基本信息已更新', 'success')
    
    # 处理隐私设置表单
    elif form_type == 'privacy':
        is_public = request.form.get('is_public') == 'true'
        group.is_public = is_public
        
        flash('群组隐私设置已更新', 'success')
    
    # 处理高级设置表单
    elif form_type == 'advanced':
        # 如果需要处理其他设置，可以在这里添加
        flash('群组高级设置已更新', 'success')
    
    db.session.commit()
    return redirect(url_for('groups.settings', group_id=group_id))

@groups_bp.route('/<int:group_id>/remove_member/<int:user_id>', methods=['GET'])
@login_required
def remove_member(group_id, user_id):
    """将成员移出群组"""
    group = Group.query.get_or_404(group_id)
    user = User.query.get_or_404(user_id)
    
    # 确保当前用户有权限移除成员（群主或管理员）
    user_role = current_user.get_role_in_group(group_id)
    
    # 检查移除权限：
    # 1. 群主可以移除任何人（除自己）
    # 2. 管理员只能移除普通成员，不能移除群主或其他管理员
    if not current_user.is_authenticated or not user_role:
        flash('您没有权限执行此操作', 'danger')
        return redirect(url_for('groups.members', group_id=group_id))
    
    if group.owner_id == user.id:
        flash('不能移除群主', 'danger')
        return redirect(url_for('groups.members', group_id=group_id))
    
    if user_role != 'admin' and group.owner_id != current_user.id:
        flash('只有群主和管理员可以移除成员', 'danger')
        return redirect(url_for('groups.members', group_id=group_id))
    
    # 管理员不能移除其他管理员
    if user_role == 'admin' and current_user.id != group.owner_id:
        user_to_remove_role = user.get_role_in_group(group_id)
        if user_to_remove_role == 'admin':
            flash('管理员不能移除其他管理员', 'danger')
            return redirect(url_for('groups.members', group_id=group_id))
    
    # 从群组中移除用户
    stmt = group_members.delete().where(
        (group_members.c.user_id == user.id) & 
        (group_members.c.group_id == group.id)
    )
    db.session.execute(stmt)
    db.session.commit()
    
    flash(f'已将用户 {user.username} 移出群组', 'success')
    return redirect(url_for('groups.members', group_id=group_id))

@groups_bp.route('/<int:group_id>/make_admin/<int:user_id>', methods=['GET'])
@login_required
def make_admin(group_id, user_id):
    """将成员设为管理员"""
    group = Group.query.get_or_404(group_id)
    user = User.query.get_or_404(user_id)
    
    # 只有群主可以设置管理员
    if current_user.id != group.owner_id:
        flash('只有群主可以设置管理员', 'danger')
        return redirect(url_for('groups.members', group_id=group_id))
    
    # 不能重复设置管理员
    user_role = user.get_role_in_group(group_id)
    if user_role == 'admin':
        flash('该用户已经是管理员', 'warning')
        return redirect(url_for('groups.members', group_id=group_id))
    
    # 更新用户角色为管理员
    stmt = group_members.update().where(
        (group_members.c.user_id == user.id) & 
        (group_members.c.group_id == group.id)
    ).values(role='admin')
    db.session.execute(stmt)
    db.session.commit()
    
    flash(f'已将用户 {user.username} 设为管理员', 'success')
    return redirect(url_for('groups.members', group_id=group_id))

@groups_bp.route('/<int:group_id>/remove_admin/<int:user_id>', methods=['GET'])
@login_required
def remove_admin(group_id, user_id):
    """取消管理员权限"""
    group = Group.query.get_or_404(group_id)
    user = User.query.get_or_404(user_id)
    
    # 只有群主可以取消管理员权限
    if current_user.id != group.owner_id:
        flash('只有群主可以取消管理员权限', 'danger')
        return redirect(url_for('groups.members', group_id=group_id))
    
    # 检查用户是否为管理员
    user_role = user.get_role_in_group(group_id)
    if user_role != 'admin':
        flash('该用户不是管理员', 'warning')
        return redirect(url_for('groups.members', group_id=group_id))
    
    # 更新用户角色为普通成员
    stmt = group_members.update().where(
        (group_members.c.user_id == user.id) & 
        (group_members.c.group_id == group.id)
    ).values(role='member')
    db.session.execute(stmt)
    db.session.commit()
    
    flash(f'已取消用户 {user.username} 的管理员权限', 'success')
    return redirect(url_for('groups.members', group_id=group_id))
