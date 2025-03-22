# 数据库迁移

这个目录包含数据库迁移脚本，使用Flask-Migrate自动生成。

## 生成迁移

当模型发生变化时，请运行以下命令生成迁移脚本：

```bash
flask db migrate -m "描述更改内容"
```

## 应用迁移

要将迁移应用到数据库，请运行：

```bash
flask db upgrade
```

## 回滚迁移

如果需要回滚到上一个版本，请运行：

```bash
flask db downgrade
```
