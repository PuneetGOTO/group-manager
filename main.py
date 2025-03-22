from app import create_app, db
import logging
import traceback
import sys
import os

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 创建应用实例
app = create_app()

# 初始化数据库
with app.app_context():
    app.logger.info("正在初始化数据库...")
    try:
        db.create_all()
        app.logger.info("数据库表创建成功")
    except Exception as e:
        app.logger.error(f"数据库初始化失败: {str(e)}", exc_info=True)

# 在生产环境中捕获并记录错误
@app.errorhandler(500)
def handle_500_error(e):
    app.logger.error('500 error occurred: %s', str(e))
    return '500 Internal Server Error - Check logs for details', 500

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error('Unhandled exception: %s', str(e), exc_info=True)
    return '500 Internal Server Error - Check logs for details', 500

if __name__ == '__main__':
    try:
        # 使用127.0.0.1而不是0.0.0.0，以确保正确解析重定向URL
        app.logger.info("正在启动应用服务器，监听于 http://127.0.0.1:8080/")
        app.run(host='127.0.0.1', port=8080, debug=True)
    except Exception as e:
        print(f"服务器启动失败: {str(e)}")
        traceback.print_exc()
