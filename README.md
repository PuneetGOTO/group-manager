# 群组管理系统

这是一个基于Flask的群组管理Web应用，旨在帮助用户创建和管理群组、事件和帖子。

## 功能

- 用户认证与管理
- 群组创建与管理
- 事件管理
- 帖子管理
- 通知系统

## 部署信息

此应用使用AWS Elastic Beanstalk部署，确保以下文件正确配置：

- `app.py` - 应用入口点
- `Procfile` - 指定应用如何运行
- `.ebextensions/` - Elastic Beanstalk配置
- `requirements.txt` - 项目依赖

## 本地开发

1. 创建虚拟环境: `python -m venv venv`
2. 激活环境: `venv\Scripts\activate` (Windows) 或 `source venv/bin/activate` (Linux/Mac)
3. 安装依赖: `pip install -r requirements.txt`
4. 运行应用: `python app.py`
