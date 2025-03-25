from app import create_app, db
from flask_migrate import upgrade

def migrate_database():
    """初始化数据库并应用所有迁移"""
    app = create_app()
    with app.app_context():
        # 应用所有迁移
        print("正在应用数据库迁移...")
        upgrade()
        print("数据库迁移已成功应用!")

if __name__ == '__main__':
    migrate_database()
