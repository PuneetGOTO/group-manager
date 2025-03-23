"""添加discord_roles字段到group_members表

这个脚本手动执行数据库迁移，为group_members表添加discord_roles字段。
"""
from flask import current_app
from flask.cli import with_appcontext
import click
import sqlalchemy as sa
from sqlalchemy import text

@click.command('add-discord-roles')
@with_appcontext
def add_discord_roles():
    """添加discord_roles列到group_members表"""
    from app import db
    
    try:
        # 检查列是否已存在
        with db.engine.connect() as conn:
            # SQLite语法检查列是否存在
            result = conn.execute(text(
                "SELECT count(*) FROM pragma_table_info('group_members') WHERE name='discord_roles'"
            )).scalar()
            
            if result == 0:
                # 列不存在，添加列
                conn.execute(text(
                    "ALTER TABLE group_members ADD COLUMN discord_roles TEXT"
                ))
                click.echo("✅ 成功添加discord_roles列到group_members表")
            else:
                click.echo("ℹ️ discord_roles列已存在，无需添加")
            
            conn.commit()
    except Exception as e:
        click.echo(f"❌ 迁移出错: {str(e)}")
        raise e

if __name__ == "__main__":
    # 导入应用 - 确保在主要代码前导入
    from app import create_app
    app = create_app()
    
    # 在应用上下文中运行命令
    with app.app_context():
        add_discord_roles()
