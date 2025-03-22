from flask import Flask, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    return """
    <h1>测试服务器</h1>
    <p>服务器正常运行在 127.0.0.1:8080</p>
    <p><a href="/test-redirect">测试重定向</a></p>
    <p><a href="/test-discord">测试Discord URL</a></p>
    """

@app.route('/test-redirect')
def test_redirect():
    return redirect(url_for('index'))

@app.route('/test-discord')
def test_discord():
    auth_url = "https://discord.com/oauth2/authorize?client_id=1353003948948066395&permissions=289613846&response_type=code&redirect_uri=http%3A%2F%2Flocalhost%3A1500%2Fapi%2Fauth%2Fdiscord%2Fredirect&integration_type=0&scope=identify+guilds+bot+email+guilds.members.read+applications.commands"
    return redirect(auth_url)

@app.route('/api/auth/discord/redirect')
def discord_redirect():
    # 模拟回调处理
    return """
    <h1>Discord授权回调</h1>
    <p>成功接收到Discord的授权码</p>
    <p><a href="/">返回首页</a></p>
    """

if __name__ == '__main__':
    print("正在启动测试服务器...")
    print("访问: http://localhost:1500/")
    app.run(host='localhost', port=1500, debug=True)
