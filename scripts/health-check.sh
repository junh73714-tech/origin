#!/bin/bash
# 数据库健康检查脚本

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== RAG Knowledge 健康检查 ===${NC}"

FAILED=0

# 检查 PostgreSQL
echo -n "PostgreSQL: "
if PGPASSWORD=${DATABASE_PASSWORD:-rag_password} psql -h ${DATABASE_HOST:-localhost} -U ${DATABASE_USER:-rag_user} -d ${DATABASE_NAME:-rag_knowledge} -c '\q' 2>/dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    FAILED=1
fi

# 检查 Redis
echo -n "Redis: "
if redis-cli -h ${REDIS_HOST:-localhost} -p ${REDIS_PORT:-6379} ping 2>/dev/null | grep -q "PONG"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    FAILED=1
fi

# 检查 MinIO
echo -n "MinIO: "
if curl -s http://${MINIO_ENDPOINT:-localhost:9000}/minio/health/live > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    FAILED=1
fi

# 检查 OpenSearch
echo -n "OpenSearch: "
if curl -s http://${OPENSEARCH_HOST:-localhost}:${OPENSEARCH_PORT:-9200}/_cluster/health 2>/dev/null | grep -q "cluster_name"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    FAILED=1
fi

# 检查 API
echo -n "API: "
if curl -s http://localhost:8000/api/v1/health 2>/dev/null | grep -q "healthy"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    FAILED=1
fi

# 检查前端
echo -n "Frontend: "
if curl -s http://localhost:3000 2>/dev/null | grep -q "html"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    FAILED=1
fi

echo ""
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}所有服务健康!${NC}"
    exit 0
else
    echo -e "${RED}部分服务不健康，请检查!${NC}"
    exit 1
fi
