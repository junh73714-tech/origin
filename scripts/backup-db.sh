#!/bin/bash
# 数据库备份脚本

set -e

# 配置
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/rag_knowledge_${DATE}.sql.gz"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "Starting database backup..."
echo "Backup file: $BACKUP_FILE"

# 执行备份
PGPASSWORD=${DATABASE_PASSWORD:-rag_password} pg_dump \
    -h ${DATABASE_HOST:-localhost} \
    -U ${DATABASE_USER:-rag_user} \
    -d ${DATABASE_NAME:-rag_knowledge} \
    --clean \
    --if-exists \
    --create \
    | gzip > $BACKUP_FILE

# 检查备份文件
if [ -f $BACKUP_FILE ]; then
    SIZE=$(du -h $BACKUP_FILE | cut -f1)
    echo "Backup completed successfully! Size: $SIZE"

    # 保留最近 7 个备份
    cd $BACKUP_DIR
    ls -t | tail -n +8 | xargs -r rm
else
    echo "Backup failed!"
    exit 1
fi
