from app import create_app, db
import os

def init_database():
    app = create_app()
    with app.app_context():
        # 检查数据库文件是否存在，如果存在则删除
        db_path = os.path.join(app.instance_path, 'site.db')
        if os.path.exists(db_path):
            print(f"删除现有数据库文件: {db_path}")
            os.remove(db_path)
        
        # 创建所有表
        print("创建数据库表...")
        db.create_all()
        print("数据库表已成功创建!")

if __name__ == '__main__':
    init_database()
