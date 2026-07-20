#!/bin/bash
# ============================================================
# 智能知识库平台 - 全服务健康检查脚本
# 用途：检查所有 5 个服务的健康状态
# 用法：bash scripts/health-check.sh
# 退出码：0 = 全部健康, 1 = 存在不健康的服务
# ============================================================

set -euo pipefail

# 颜色定义（用于终端输出）
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # 无颜色

# 健康检查结果统计
PASSED=0
FAILED=0
TOTAL=6

# Docker Compose 文件路径
COMPOSE_FILE="deploy/docker-compose.yml"
ENV_FILE="deploy/env/.env"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

echo "============================================================"
echo "  智能知识库平台 - 健康检查"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
echo ""

# ----------------------------------------------------------
# 检查 Docker 是否运行
# ----------------------------------------------------------
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}[失败]${NC} Docker 未运行，无法执行健康检查"
        exit 1
    fi
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}[失败]${NC} 缺少本地配置文件: $ENV_FILE"
        exit 1
    fi
}

# ----------------------------------------------------------
# 检查 Web 服务（Nginx）
# 预期：访问 http://localhost:80/ 返回 200
# ----------------------------------------------------------
check_web() {
    echo -n "检查 Web 服务 (Nginx)... "
    if curl --max-time 5 -s -o /dev/null -w "%{http_code}" http://localhost:80/ 2>/dev/null | grep -q "200\|304"; then
        echo -e "${GREEN}通过${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}失败${NC} - Web 服务不可访问"
        FAILED=$((FAILED + 1))
    fi
}

# ----------------------------------------------------------
# 检查 API Server 服务（FastAPI 存活检查）
# 预期：GET /api/v1/health/live 返回 200
# ----------------------------------------------------------
check_api_live() {
    echo -n "检查 API Server 存活状态... "
    if curl --max-time 5 -s http://localhost:80/api/v1/health/live 2>/dev/null | grep -q '"status":"ok"'; then
        echo -e "${GREEN}通过${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}失败${NC} - API Server 存活检查失败"
        FAILED=$((FAILED + 1))
    fi
}

# ----------------------------------------------------------
# 检查 API Server 就绪状态
# 预期：GET /api/v1/health/ready 返回 200
# ----------------------------------------------------------
check_api_ready() {
    echo -n "检查 API Server 就绪状态... "
    if READY_RESPONSE=$(curl --max-time 5 -fsS http://localhost:80/api/v1/health/ready 2>/dev/null) && \
       echo "$READY_RESPONSE" | grep -q '"status":"ok"'; then
        echo -e "${GREEN}通过${NC}"
        PASSED=$((PASSED + 1))
    elif echo "$READY_RESPONSE" | grep -q '"status":"degraded"'; then
        echo -e "${YELLOW}降级${NC} - 部分依赖不可用"
        FAILED=$((FAILED + 1))
    else
        echo -e "${RED}失败${NC} - API Server 就绪检查失败"
        FAILED=$((FAILED + 1))
    fi
}

# ----------------------------------------------------------
# 检查 PostgreSQL 服务
# 预期：pg_isready 返回 accepting connections
# ----------------------------------------------------------
check_postgres() {
    echo -n "检查 PostgreSQL 服务... "
    if "${COMPOSE[@]}" exec -T postgres pg_isready -U postgres 2>/dev/null | grep -q "accepting connections"; then
        echo -e "${GREEN}通过${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}失败${NC} - PostgreSQL 不可用"
        FAILED=$((FAILED + 1))
    fi
}

# ----------------------------------------------------------
# 检查 Redis 服务
# 预期：redis-cli ping 返回 PONG
# ----------------------------------------------------------
check_redis() {
    echo -n "检查 Redis 服务... "
    if "${COMPOSE[@]}" exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        echo -e "${GREEN}通过${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}失败${NC} - Redis 不可用"
        FAILED=$((FAILED + 1))
    fi
}

# ----------------------------------------------------------
# 检查 Worker 服务
# 预期：Worker 进程存在
# ----------------------------------------------------------
check_worker() {
    echo -n "检查 Worker 服务... "
    if [ "$(docker inspect --format '{{.State.Health.Status}}' kb-worker 2>/dev/null)" = "healthy" ]; then
        echo -e "${GREEN}通过${NC}（ARQ 进程健康）"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}失败${NC} - Worker 未运行"
        FAILED=$((FAILED + 1))
    fi
}

# ----------------------------------------------------------
# 主流程
# ----------------------------------------------------------
main() {
    # 检查 Docker 是否运行
    check_docker

    # 检查各服务是否在运行中
    RUNNING_SERVICES=$("${COMPOSE[@]}" ps --services --status running 2>/dev/null | wc -l)

    if [ "$RUNNING_SERVICES" -lt 5 ]; then
        echo -e "${YELLOW}警告：部分服务未运行，仅检查已启动的服务${NC}"
        echo ""
    fi

    # 执行各项健康检查
    check_web
    check_api_live
    check_api_ready
    check_postgres
    check_redis
    check_worker

    # 输出检查结果汇总
    echo ""
    echo "============================================================"
    echo "  检查结果：${PASSED}/${TOTAL} 通过"
    if [ "$FAILED" -gt 0 ]; then
        echo -e "  ${RED}${FAILED} 项检查失败${NC}"
        echo "============================================================"
        exit 1
    else
        echo -e "  ${GREEN}全部服务健康${NC}"
        echo "============================================================"
        exit 0
    fi
}

# 执行主流程
main
