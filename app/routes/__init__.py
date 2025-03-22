from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.groups import groups_bp
from app.routes.user import user_bp

# 导出所有蓝图，方便其他地方使用
__all__ = ['main_bp', 'auth_bp', 'groups_bp', 'user_bp']
