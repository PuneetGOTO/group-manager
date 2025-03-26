import requests
import sys
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('discord-test')

def test_discord_api(token, guild_id):
    """测试Discord API权限
    
    测试获取服务器信息和频道列表
    """
    # 清理令牌格式
    if token.startswith('Bot '):
        token = token[4:]
    token = token.strip(' "\'')
    
    # 准备请求头
    headers = {
        'Authorization': f'Bot {token}',
        'Content-Type': 'application/json'
    }
    
    # 测试1: 获取机器人自身信息
    logger.info("测试1: 获取机器人信息")
    try:
        response = requests.get(
            'https://discord.com/api/v10/users/@me',
            headers=headers
        )
        if response.status_code == 200:
            bot_info = response.json()
            logger.info(f"获取机器人信息成功: {bot_info.get('username')} (ID: {bot_info.get('id')})")
        else:
            logger.error(f"获取机器人信息失败: {response.status_code}")
            logger.error(f"响应: {response.text[:200]}")
    except Exception as e:
        logger.error(f"获取机器人信息出错: {str(e)}")
    
    # 测试2: 获取服务器列表
    logger.info("\n测试2: 获取服务器列表")
    try:
        response = requests.get(
            'https://discord.com/api/v10/users/@me/guilds',
            headers=headers
        )
        if response.status_code == 200:
            guilds = response.json()
            logger.info(f"获取服务器列表成功: {len(guilds)}个服务器")
            for guild in guilds:
                logger.info(f" - {guild.get('name')} (ID: {guild.get('id')})")
        else:
            logger.error(f"获取服务器列表失败: {response.status_code}")
            logger.error(f"响应: {response.text[:200]}")
    except Exception as e:
        logger.error(f"获取服务器列表出错: {str(e)}")
    
    # 测试3: 获取特定服务器的频道列表
    logger.info("\n测试3: 获取频道列表")
    try:
        url = f'https://discord.com/api/v10/guilds/{guild_id}/channels'
        logger.info(f"请求URL: {url}")
        logger.info(f"请求头: Authorization: Bot {token[:5]}***")
        
        response = requests.get(url, headers=headers)
        
        logger.info(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            channels = response.json()
            logger.info(f"获取频道列表成功: {len(channels)}个频道")
            
            for channel in channels:
                logger.info(f" - {channel.get('name')} (ID: {channel.get('id')}, 类型: {channel.get('type')})")
        else:
            logger.error(f"获取频道列表失败: {response.status_code}")
            logger.error(f"响应: {response.text}")
            logger.info("\n可能的原因:")
            logger.info("1. 机器人没有足够的权限")
            logger.info("2. 机器人令牌格式不正确")
            logger.info("3. 未启用必要的Intents")
            logger.info("解决方法:")
            logger.info("1. 检查Discord开发者门户中的OAuth2设置")
            logger.info("2. 确保勾选了'bot'范围")
            logger.info("3. 在'Bot'页面确保勾选了以下权限:")
            logger.info("   - View Channels")
            logger.info("   - Send Messages")
            logger.info("4. 在'Bot'页面的Privileged Gateway Intents部分:")
            logger.info("   - 启用SERVER MEMBERS INTENT")
            logger.info("   - 启用MESSAGE CONTENT INTENT")
    except Exception as e:
        logger.error(f"获取频道列表出错: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("没有提供命令行参数，切换到手动输入模式")
        token = input("请输入Discord机器人令牌: ")
        guild_id = input("请输入服务器ID (默认1280014596765126666): ") or "1280014596765126666"
    else:
        token = sys.argv[1]
        guild_id = sys.argv[2]
    
    logger.info(f"正在测试Discord API - 服务器ID: {guild_id}")
    test_discord_api(token, guild_id)
