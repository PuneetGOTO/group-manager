"""
向DiscordBot表添加bot_name字段的迁移脚本
"""
from app import db, create_app
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from flask_migrate import Migrate
from flask import current_app
import sys
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """执行数据库迁移，添加bot_name字段到DiscordBot表"""
    try:
        app = create_app()
        with app.app_context():
            # 创建迁移对象
            migrate = Migrate(app, db)
            
            # 获取数据库引擎
            engine = db.engine
            connection = engine.connect()
            
            # 检查字段是否已存在
            inspector = sa.inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('discord_bot')]
            
            if 'bot_name' not in columns:
                logger.info("添加bot_name字段到discord_bot表...")
                # 执行添加列的SQL
                connection.execute(sa.text(
                    "ALTER TABLE discord_bot ADD COLUMN bot_name VARCHAR(100)"
                ))
                logger.info("成功添加bot_name字段")
            else:
                logger.info("bot_name字段已存在，无需迁移")
                
            connection.close()
            logger.info("数据库迁移完成")
            return True
    except Exception as e:
        logger.error(f"迁移失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
