from app import create_app, db
from app.models.user import User
from sqlalchemy import func

app = create_app()

with app.app_context():
    # 使用 func.lower() 进行大小写不敏感的查询
    email = 'an920513@gmail.com'
    user = User.query.filter(func.lower(User.email) == func.lower(email)).first()
    if user:
        user.is_admin = True
        db.session.commit()
        print(f"用户 {user.username} (邮箱: {user.email}) 已被设置为系统管理员")
    else:
        print(f"未找到邮箱为 {email} 的用户")
