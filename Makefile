# ============================================================
# 智能知识库平台 - Makefile
# 用途：提供常用命令的快捷入口，减少记忆负担
# 用法：make <目标名称>
# 示例：make dev（启动开发环境）
# ============================================================

# 默认目标：显示帮助信息
.DEFAULT_GOAL := help

# 声明所有目标为伪目标（不产生同名文件）
.PHONY: help dev build test test-watch clean restart logs status shell

# Docker Compose 文件路径
COMPOSE_FILE := deploy/docker-compose.yml
COMPOSE_TEST_FILE := deploy/docker-compose.test.yml

# ----------------------------------------------------------
# 帮助：显示所有可用命令
# ----------------------------------------------------------
help:
	@echo "智能知识库平台 - 命令速查"
	@echo ""
	@echo "开发环境："
	@echo "  make dev           启动开发环境（postgres + redis）"
	@echo "  make dev-full      启动全部服务"
	@echo "  make build         构建所有 Docker 镜像"
	@echo "  make shell         进入 api-server 容器"
	@echo ""
	@echo "测试："
	@echo "  make test          运行完整容器测试"
	@echo "  make test-watch    运行前端测试（监听模式）"
	@echo ""
	@echo "日志和状态："
	@echo "  make logs          查看所有服务日志"
	@echo "  make status        查看所有服务状态"
	@echo "  make health        检查所有服务健康状态"
	@echo ""
	@echo "清理："
	@echo "  make clean         清理所有容器和卷"
	@echo "  make restart       重启所有服务"

# ----------------------------------------------------------
# 开发环境：仅启动 postgres 和 redis（前端和后端在宿主机运行）
# 使用场景：前端使用 Vite dev server，后端使用 uvicorn --reload
# ----------------------------------------------------------
dev:
	@echo "启动开发环境（postgres + redis）..."
	docker compose -f $(COMPOSE_FILE) up -d postgres redis
	@echo "开发环境已启动。"
	@echo "  前端：npm run dev:web          (http://localhost:5173)"
	@echo "  后端：uv run uvicorn ...       (http://localhost:8000)"
	@echo "  前端+API：npm run dev:web:api  (http://localhost:5173, 代理到 8000)"

# ----------------------------------------------------------
# 完整开发环境：启动全部 5 个服务
# 使用场景：验证 Docker 容器化部署是否正常
# ----------------------------------------------------------
dev-full:
	@echo "启动完整开发环境（全部 5 个服务）..."
	docker compose -f $(COMPOSE_FILE) up -d
	@echo "全部服务已启动。访问 http://localhost"

# ----------------------------------------------------------
# 构建：构建所有 Docker 镜像
# 使用场景：代码更新后重新构建镜像
# ----------------------------------------------------------
build:
	@echo "构建所有 Docker 镜像..."
	docker compose -f $(COMPOSE_FILE) build --no-cache
	@echo "镜像构建完成。"

# ----------------------------------------------------------
# 测试：运行完整容器测试
# 使用 docker-compose.test.yml 启动测试环境
# --abort-on-container-exit：测试完成后自动退出
# 退出码：测试通过返回 0，失败返回 1
# ----------------------------------------------------------
test:
	@echo "运行完整容器测试..."
	docker compose -f $(COMPOSE_TEST_FILE) up --build --abort-on-container-exit
	@echo "测试完成。"

# ----------------------------------------------------------
# 前端测试监听模式：文件变更时自动重新运行测试
# ----------------------------------------------------------
test-watch:
	@echo "启动前端测试监听模式..."
	npm run test:web:watch

# ----------------------------------------------------------
# 日志：查看所有服务日志
# --follow：持续输出，Ctrl+C 退出
# --tail=100：显示最近 100 行
# ----------------------------------------------------------
logs:
	docker compose -f $(COMPOSE_FILE) logs --tail=100 --follow

# ----------------------------------------------------------
# 状态：查看所有服务运行状态
# ----------------------------------------------------------
status:
	@echo "服务状态："
	@docker compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "健康检查："
	@bash scripts/health-check.sh

# ----------------------------------------------------------
# 健康检查：运行全服务健康检查脚本
# ----------------------------------------------------------
health:
	@bash scripts/health-check.sh

# ----------------------------------------------------------
# 进入容器：进入 api-server 容器的 shell
# ----------------------------------------------------------
shell:
	docker compose -f $(COMPOSE_FILE) exec api-server bash

# ----------------------------------------------------------
# 重启：重启所有服务
# ----------------------------------------------------------
restart:
	@echo "重启所有服务..."
	docker compose -f $(COMPOSE_FILE) restart
	@echo "服务已重启。"

# ----------------------------------------------------------
# 清理：停止所有容器并删除卷
# 警告：这会删除所有数据（包括数据库和文件存储）
# ----------------------------------------------------------
clean:
	@echo "警告：即将删除所有容器和数据卷！"
	@echo "按 Ctrl+C 取消，或等待 5 秒自动继续..."
	@sleep 5
	docker compose -f $(COMPOSE_FILE) down -v
	docker compose -f $(COMPOSE_TEST_FILE) down -v 2>/dev/null || true
	@echo "清理完成。"