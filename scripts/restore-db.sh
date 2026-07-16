#!/bin/bash
# 数据库恢复脚本

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Available backups:"
    ls -la ./backups/*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "Restoring database from: $BACKUP_FILE"
echo "WARNING: This will overwrite all existing data!"
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted"
    exit 1
fi

# 停止应用
docker-compose -f deploy/docker/docker-compose.dev.yml stop backend || true

# 恢复数据库
gunzip -c $BACKUP_FILE | PGPASSWORD=${DATABASE_PASSWORD:-rag_password} psql \
    -h ${DATABASE_HOST:-localhost} \
    -U ${DATABASE_USER:-rag_user} \
    -d postgres

# 启动应用
docker-compose -f deploy/docker/docker-compose.dev.yml start backend || true

echo "Database restored successfully!"
