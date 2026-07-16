#!/bin/bash
# 数据库初始化脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== RAG Knowledge 数据库初始化 ===${NC}"

# 等待数据库就绪
echo -e "${YELLOW}等待数据库服务...${NC}"
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if PGPASSWORD=$DATABASE_PASSWORD psql -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME -c '\q' 2>/dev/null; then
        echo -e "${GREEN}数据库连接成功!${NC}"
        break
    fi
    attempt=$((attempt + 1))
    echo "等待中... ($attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}错误: 数据库连接超时${NC}"
    exit 1
fi

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 运行迁移
echo -e "${YELLOW}运行数据库迁移...${NC}"
cd backend
alembic upgrade head

echo -e "${GREEN}数据库初始化完成!${NC}"
