from app import create_app
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 创建应用实例
app = create_app()

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
    app.run(host='0.0.0.0', port=8080)
