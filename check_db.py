"""
数据库检查工具，用于验证数据库结构和手动添加缺失的字段
"""
from app import create_app, db
from sqlalchemy import text, inspect

def check_column_exists(table_name, column_name):
    """检查指定的列是否存在于表中"""
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns

def add_discord_roles_column():
    """添加discord_roles列到group_members表"""
    if not check_column_exists('group_members', 'discord_roles'):
        print("添加 discord_roles 列到 group_members 表...")
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE group_members ADD COLUMN discord_roles TEXT"))
            conn.commit()
            print("✅ 成功添加discord_roles列")
    else:
        print("ℹ️ discord_roles列已存在")

def main():
    """主函数"""
    app = create_app()
    with app.app_context():
        print("检查数据库结构...")
        try:
            # 检查并添加discord_roles列
            add_discord_roles_column()
            
            # 检查User表是否包含discord_username
            if not check_column_exists('user', 'discord_username'):
                print("添加 discord_username 列到 user 表...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE user ADD COLUMN discord_username TEXT"))
                    conn.commit()
                    print("✅ 成功添加discord_username列")
            else:
                print("ℹ️ discord_username列已存在")
                
            print("数据库检查完成")
        except Exception as e:
            print(f"❌ 错误: {str(e)}")

if __name__ == "__main__":
    main()
