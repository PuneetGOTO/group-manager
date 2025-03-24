from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from datetime import timedelta
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化扩展
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__)
    
    # 配置应用
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///site.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 记住我功能配置 - 设置为30天
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=60)  # 记住登录状态60天
    app.config['REMEMBER_COOKIE_SECURE'] = not app.debug  # 生产环境下使用HTTPS
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True  # 防止客户端JavaScript访问
    app.config['REMEMBER_COOKIE_REFRESH_EACH_REQUEST'] = True  # 每次请求刷新cookie
    app.config['REMEMBER_COOKIE_NAME'] = 'remember_token'  # 自定义cookie名称
    app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'  # 允许从外部链接进入时保持登录状态
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    
    # 配置登录管理器
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面'
    login_manager.login_message_category = 'info'
    
    # 注册蓝图
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.groups import groups_bp
    from app.routes.user import user_bp
    from app.routes.discord import discord_bp
    from app.routes.dyno import dyno_bp
    
    # 注册自定义模板过滤器
    @app.template_filter('bitwise_and')
    def bitwise_and(value, other):
        """执行位与操作"""
        if value is None or other is None:
            return False
        return bool(int(value) & int(other))
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(groups_bp, url_prefix='/groups')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(discord_bp, url_prefix='/discord')
    app.register_blueprint(dyno_bp, url_prefix='/dyno')
    
    return app
