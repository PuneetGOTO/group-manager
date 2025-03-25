"""
一个非常简单的Discord机器人测试脚本
这个脚本将尝试连接到Discord并打印出连接状态
"""
import discord
import asyncio
import sys
import os
import logging
import traceback
from dotenv import load_dotenv

# 设置更详细的日志记录
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)

# 加载环境变量
print("尝试加载环境变量...")
load_dotenv()
print(f"环境变量是否包含DISCORD_BOT_TOKEN: {'DISCORD_BOT_TOKEN' in os.environ}")

async def main(token):
    """主函数"""
    print(f"尝试使用提供的令牌连接到Discord...")
    print(f"令牌的前10个字符: {token[:10]}..." if token else "令牌为空!")
    
    # 设置意图 - 只使用非特权意图
    intents = discord.Intents.default()
    intents.message_content = False  # 禁用消息内容意图（这是特权意图）
    intents.members = False  # 禁用成员意图（这是特权意图）
    
    print("注意：已禁用特权意图。如需完整功能，请在Discord开发者门户中启用它们。")
    print(f"意图设置: {intents}")
    
    # 创建客户端
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        """当机器人连接到Discord时触发"""
        print(f'成功连接到Discord! 用户名: {client.user.name}, ID: {client.user.id}')
        print(f'机器人存在于 {len(client.guilds)} 个服务器中')
        
        # 列出所有服务器
        print("\n所在服务器列表:")
        for guild in client.guilds:
            print(f" - {guild.name} (ID: {guild.id})")
        
        # 关闭连接
        print("\n测试完成，将在5秒后断开连接...")
        await asyncio.sleep(5)
        await client.close()
    
    try:
        print("正在连接到Discord...")
        await client.start(token)
    except discord.LoginFailure as e:
        print(f"登录失败：令牌无效。错误详情: {str(e)}")
        print(f"令牌长度: {len(token)}")
    except Exception as e:
        print(f"连接时出错: {str(e)}")
        print("完整错误信息:")
        traceback.print_exc()

if __name__ == "__main__":
    print("脚本开始运行...")
    # 先尝试从命令行参数获取令牌
    if len(sys.argv) > 1:
        token = sys.argv[1]
        print("使用命令行参数中的令牌")
    # 否则尝试从环境变量获取令牌
    elif os.environ.get('DISCORD_BOT_TOKEN'):
        token = os.environ.get('DISCORD_BOT_TOKEN')
        print("正在使用环境变量中的令牌...")
    else:
        print("错误：请提供Discord机器人令牌")
        print("用法: python simple_bot_test.py <机器人令牌>")
        print("或在 .env 文件中设置 DISCORD_BOT_TOKEN 环境变量")
        sys.exit(1)
    
    try:
        asyncio.run(main(token))
    except KeyboardInterrupt:
        print("收到键盘中断，脚本退出")
    except Exception as e:
        print(f"运行时发生错误: {str(e)}")
        traceback.print_exc()
    
    print("脚本执行完毕")
