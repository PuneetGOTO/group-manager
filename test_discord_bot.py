"""
测试Discord机器人连接的简单脚本
"""
import sys
import os
from dotenv import load_dotenv
from app.discord.bot_client import check_bot_status, start_bot_process, stop_bot_process

# 加载环境变量
load_dotenv()

def main():
    """主函数"""
    # 从命令行参数或环境变量获取令牌
    token = None
    
    if len(sys.argv) > 1:
        token = sys.argv[1]
    elif os.environ.get('DISCORD_BOT_TOKEN'):
        token = os.environ.get('DISCORD_BOT_TOKEN')
    
    if not token:
        print("错误：请提供Discord机器人令牌")
        print("用法: python test_discord_bot.py <机器人令牌>")
        print("或设置环境变量 DISCORD_BOT_TOKEN")
        return 1
    
    # 先检查机器人状态
    print("检查机器人状态...")
    status, error = check_bot_status(token)
    print(f"状态: {status}")
    if error:
        print(f"错误: {error}")
    
    if status == 'error':
        print("令牌验证失败，无法继续测试")
        return 1
    
    # 尝试启动机器人
    choice = input("\n是否尝试启动机器人进程？(y/n): ")
    if choice.lower() == 'y':
        print("正在启动机器人进程...")
        process_id = start_bot_process(token)
        
        if process_id:
            print(f"机器人进程已启动，PID: {process_id}")
            print("机器人现在应该已经连接到Discord")
            print("按Ctrl+C终止此脚本")
            
            try:
                # 保持脚本运行
                while True:
                    choice = input("\n输入'stop'停止机器人，'status'检查状态，'exit'退出: ")
                    if choice.lower() == 'stop':
                        stop_bot_process()
                        print("机器人已停止")
                    elif choice.lower() == 'status':
                        status, error = check_bot_status(token)
                        print(f"状态: {status}")
                        if error:
                            print(f"错误: {error}")
                    elif choice.lower() == 'exit':
                        stop_bot_process()
                        print("已停止机器人并退出")
                        break
            except KeyboardInterrupt:
                print("\n接收到中断信号，正在停止机器人...")
            finally:
                stop_bot_process()
                print("机器人进程已停止")
        else:
            print("启动机器人进程失败")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
