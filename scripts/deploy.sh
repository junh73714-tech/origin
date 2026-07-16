#!/bin/bash
# 部署脚本

set -e

VERSION=${1:-latest}
ENV=${2:-production}

echo "=== RAG Knowledge 部署 ==="
echo "Version: $VERSION"
echo "Environment: $ENV"

# 拉取最新代码
echo "Pulling latest code..."
git pull origin main

# 构建镜像
echo "Building Docker images..."
docker build -f deploy/docker/Dockerfile.backend -t rag-knowledge-backend:$VERSION ./backend
docker build -f deploy/docker/Dockerfile.frontend -t rag-knowledge-frontend:$VERSION ./frontend

# 标记 latest
docker tag rag-knowledge-backend:$VERSION rag-knowledge-backend:latest
docker tag rag-knowledge-frontend:$VERSION rag-knowledge-frontend:latest

# 推送镜像
echo "Pushing images to registry..."
docker push rag-knowledge-backend:$VERSION
docker push rag-knowledge-frontend:$VERSION

# 更新容器
echo "Updating containers..."
docker-compose -f deploy/docker/docker-compose.$ENV.yml down
docker-compose -f deploy/docker/docker-compose.$ENV.yml up -d

# 健康检查
echo "Running health checks..."
sleep 10
./scripts/health-check.sh

echo "Deployment completed!"
