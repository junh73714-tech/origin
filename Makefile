# 企业级 RAG 知识问答平台
# Makefile - 统一开发命令

.PHONY: help
help: ## 显示帮助信息
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ==================== 环境管理 ====================

.env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example"; \
	fi

setup: .env ## 设置环境
	@echo "Setting up development environment..."
	@cd backend && uv sync
	@cd frontend && npm install
	@echo "Setup complete!"

# ==================== 开发环境 ====================

dev-up: ## 启动开发环境
	docker-compose -f deploy/docker/docker-compose.dev.yml up -d
	@echo "Services started. Access:"
	@echo "  - Frontend: http://localhost:3000"
	@echo "  - Backend:  http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"
	@echo "  - Grafana:  http://localhost:3100"

dev-down: ## 停止开发环境
	docker-compose -f deploy/docker/docker-compose.dev.yml down

dev-restart: dev-down dev-up ## 重启开发环境

logs: ## 查看日志
	docker-compose -f deploy/docker/docker-compose.dev.yml logs -f

logs-backend: ## 查看后端日志
	docker-compose -f deploy/docker/docker-compose.dev.yml logs -f backend

logs-frontend: ## 查看前端日志
	docker-compose -f deploy/docker/docker-compose.dev.yml logs -f frontend

# ==================== 数据库 ====================

migrate: ## 运行数据库迁移
	@echo "Running database migrations..."
	cd backend && alembic upgrade head

migrate-create: ## 创建新迁移
	@if [ -z "$(NAME)" ]; then \
		echo "Usage: make migrate-create NAME=your_migration_name"; \
		exit 1; \
	fi
	cd backend && alembic revision --autogenerate -m "$(NAME)"

migrate-down: ## 回滚一次迁移
	cd backend && alembic downgrade -1

migrate-history: ## 查看迁移历史
	cd backend && alembic history

seed: ## 初始化种子数据
	@echo "Seeding database..."
	cd backend && python -m app.db.seed

# ==================== 后端开发 ====================

backend-install: ## 安装后端依赖
	cd backend && uv sync

backend-run: ## 运行后端开发服务器
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backend-test: ## 运行后端测试
	cd backend && pytest tests/ -v --cov=app --cov-report=term-missing

backend-test-unit: ## 运行单元测试
	cd backend && pytest tests/unit/ -v

backend-test-integration: ## 运行集成测试
	cd backend && pytest tests/integration/ -v

backend-lint: ## 代码检查
	cd backend && ruff check app/ tests/
	cd backend && mypy app/ --ignore-missing-imports

backend-format: ## 代码格式化
	cd backend && ruff format app/ tests/
	cd backend && ruff check app/ tests/ --fix

# ==================== 前端开发 ====================

frontend-install: ## 安装前端依赖
	cd frontend && npm install

frontend-run: ## 运行前端开发服务器
	cd frontend && npm run dev

frontend-build: ## 构建前端
	cd frontend && npm run build

frontend-test: ## 运行前端测试
	cd frontend && npm run test

frontend-lint: ## 代码检查
	cd frontend && npm run lint

frontend-format: ## 代码格式化
	cd frontend && npm run format

# ==================== 测试 ====================

test: ## 运行所有测试
	@echo "Running backend tests..."
	$(MAKE) backend-test
	@echo "Running frontend tests..."
	$(MAKE) frontend-test

test-ci: ## CI 环境测试
	cd backend && pytest tests/ --junitxml=report.xml
	cd frontend && npm run test -- --coverage --ci

smoke-test: ## 冒烟测试
	@echo "Running smoke tests..."
	@curl -f http://localhost:8000/api/v1/health || (echo "Backend health check failed!" && exit 1)
	@curl -f http://localhost:3000 | grep -q "root" || (echo "Frontend health check failed!" && exit 1)
	@echo "Smoke tests passed!"

# ==================== 代码质量 ====================

lint: ## 代码检查
	$(MAKE) backend-lint
	$(MAKE) frontend-lint

format: ## 代码格式化
	$(MAKE) backend-format
	$(MAKE) frontend-format

# ==================== Docker ====================

docker-build: ## 构建 Docker 镜像
	docker build -f deploy/docker/Dockerfile.backend -t rag-knowledge-backend:latest ./backend
	docker build -f deploy/docker/Dockerfile.frontend -t rag-knowledge-frontend:latest ./frontend

docker-up: ## 生产环境启动
	docker-compose -f deploy/docker/docker-compose.prod.yml up -d

docker-down: ## 生产环境停止
	docker-compose -f deploy/docker/docker-compose.prod.yml down

# ==================== 清理 ====================

clean: ## 清理构建产物
	rm -rf backend/.pytest_cache
	rm -rf backend/.ruff_cache
	rm -rf backend/__pycache__
	rm -rf backend/app/**/__pycache__
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	rm -rf frontend/.vite

clean-all: clean ## 清理所有（包括 Docker）
	docker-compose -f deploy/docker/docker-compose.dev.yml down -v --remove-orphans

# ==================== 初始化 ====================

init: setup migrate seed ## 初始化项目（首次运行）
	@echo "Project initialized!"
	@echo "Start development: make dev-up"

reset-dev: clean-all init ## 重置开发环境
	$(MAKE) dev-up

# ==================== 文档 ====================

docs: ## 生成/查看文档
	@echo "API documentation available at: http://localhost:8000/docs"
	@echo "ReDoc documentation available at: http://localhost:8000/redoc"

# ==================== 发布 ====================

release-major: ## 主版本发布
	@echo "Releasing major version..."
	git tag v1.0.0
	git push origin v1.0.0

release-minor: ## 次版本发布
	@echo "Releasing minor version..."
	git tag v0.1.0
	git push origin v0.1.0

release-patch: ## 修订版发布
	@echo "Releasing patch version..."
	git tag v0.0.1
	git push origin v0.0.1
