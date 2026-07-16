# 构建脚本目录

此目录包含项目的各种构建和部署脚本。

## 脚本列表

| 脚本 | 说明 |
|------|------|
| init-db.sh | 初始化数据库 |
| seed-db.sh | 填充种子数据 |
| backup-db.sh | 备份数据库 |
| restore-db.sh | 恢复数据库 |
| health-check.sh | 健康检查 |
| deploy.sh | 部署脚本 |

## 使用方法

```bash
# 设置执行权限
chmod +x scripts/*.sh

# 运行初始化
./scripts/init-db.sh

# 运行健康检查
./scripts/health-check.sh
```
