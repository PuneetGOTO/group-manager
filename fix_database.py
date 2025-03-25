import os
import sys
from app import create_app, db
from app.models.user import User
from app.models.group import Group
from sqlalchemy.exc import OperationalError

# 创建应用实例
app = create_app()

def initialize_database():
    """初始化数据库并创建所有表"""
    with app.app_context():
        try:
            # 检查数据库是否有表
            Group.query.first()
            print("数据库已经正确初始化，包含所需表结构。")
            return True
        except OperationalError:
            # 如果表不存在，创建所有表
            print("数据库结构不完整，正在创建所有表...")
            db.create_all()
            print("所有数据库表已成功创建!")
            return True
        except Exception as e:
            print(f"初始化数据库时发生错误: {e}")
            return False

def set_admin_user(email):
    """将指定邮箱的用户设置为管理员"""
    with app.app_context():
        try:
            user = User.query.filter(User.email.ilike(email)).first()
            if user:
                user.is_admin = True
                db.session.commit()
                print(f"用户 {user.username} (邮箱: {user.email}) 已被设置为系统管理员")
                return True
            else:
                print(f"未找到邮箱为 {email} 的用户")
                return False
        except Exception as e:
            print(f"设置管理员时发生错误: {e}")
            return False

if __name__ == "__main__":
    # 初始化数据库
    if initialize_database():
        # 如果提供了邮箱参数，设置该用户为管理员
        if len(sys.argv) > 1:
            set_admin_user(sys.argv[1])
        else:
            print("提示: 您可以通过运行 'python fix_database.py 您的邮箱' 来将自己设置为管理员")
