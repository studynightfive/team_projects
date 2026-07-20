#!/bin/bash
# ============================================================
# 智能知识库平台 - 发布镜像构建脚本
# 用途：构建带不可变版本标签的 Docker 镜像
# 用法：bash scripts/build-release.sh <version>
# 示例：bash scripts/build-release.sh v1.0.0
# ============================================================

set -euo pipefail

# 版本号参数检查
if [ $# -lt 1 ]; then
    echo "用法: bash scripts/build-release.sh <version>"
    echo "示例: bash scripts/build-release.sh v1.0.0"
    exit 1
fi

VERSION="${1}"
if ! [[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
    echo "错误: 版本号必须使用 vX.Y.Z 形式"
    exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
    echo "错误: 发布镜像只能从干净的 Git 工作区构建"
    exit 1
fi
# Git 短提交 SHA（用于不可变标签）
COMMIT_SHA=$(git rev-parse --short HEAD)
IMMUTABLE_TAG="${VERSION}-${COMMIT_SHA}"
# 构建时间戳
BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "============================================================"
echo "  发布镜像构建"
echo "  版本: ${VERSION}"
echo "  提交: ${COMMIT_SHA}"
echo "  时间: ${BUILD_TIME}"
echo "============================================================"
echo ""

# ============================================================
# 构建 API Server 镜像
# ============================================================
echo "=== 构建 API Server 镜像 ==="
docker build -f deploy/docker/api-server.Dockerfile \
  --target runtime \
  --label org.opencontainers.image.version="${VERSION}" \
  --label org.opencontainers.image.revision="${COMMIT_SHA}" \
  --label org.opencontainers.image.created="${BUILD_TIME}" \
  -t knowledge-base-platform-api-server:"${VERSION}" \
  -t knowledge-base-platform-api-server:"${COMMIT_SHA}" \
  -t knowledge-base-platform-api-server:"${IMMUTABLE_TAG}" \
  .

# 记录镜像 SHA256
API_SHA256=$(docker inspect knowledge-base-platform-api-server:"${VERSION}" --format='{{.Id}}')
echo "API Server 镜像 SHA256: ${API_SHA256}"

# ============================================================
# 构建 Worker 镜像
# ============================================================
echo ""
echo "=== 构建 Worker 镜像 ==="
docker build -f deploy/docker/worker.Dockerfile \
  --label org.opencontainers.image.version="${VERSION}" \
  --label org.opencontainers.image.revision="${COMMIT_SHA}" \
  --label org.opencontainers.image.created="${BUILD_TIME}" \
  -t knowledge-base-platform-worker:"${VERSION}" \
  -t knowledge-base-platform-worker:"${COMMIT_SHA}" \
  -t knowledge-base-platform-worker:"${IMMUTABLE_TAG}" \
  .

WORKER_SHA256=$(docker inspect knowledge-base-platform-worker:"${VERSION}" --format='{{.Id}}')
echo "Worker 镜像 SHA256: ${WORKER_SHA256}"

# ============================================================
# 构建 Web 镜像
# ============================================================
echo ""
echo "=== 构建 Web 镜像 ==="
docker build -f deploy/docker/web.Dockerfile \
  --label org.opencontainers.image.version="${VERSION}" \
  --label org.opencontainers.image.revision="${COMMIT_SHA}" \
  --label org.opencontainers.image.created="${BUILD_TIME}" \
  -t knowledge-base-platform-web:"${VERSION}" \
  -t knowledge-base-platform-web:"${COMMIT_SHA}" \
  -t knowledge-base-platform-web:"${IMMUTABLE_TAG}" \
  .

WEB_SHA256=$(docker inspect knowledge-base-platform-web:"${VERSION}" --format='{{.Id}}')
echo "Web 镜像 SHA256: ${WEB_SHA256}"

# ============================================================
# 验证镜像
# ============================================================
echo ""
echo "=== 验证镜像 ==="

# 这里只验证运行镜像可导入应用；真实启动、迁移与健康检查由 Compose 发布门禁负责。
echo "验证 API Server 应用导入..."
docker run --rm --entrypoint /app/backend/.venv/bin/python \
  -e DATABASE_URL=postgresql+asyncpg://validation:validation@127.0.0.1/validation \
  -e SECRET_KEY=validation-only-secret-key-32-chars \
  knowledge-base-platform-api-server:"${VERSION}" \
  -c "import app.main; print('API Server OK')"
echo "API Server 应用导入验证通过"

echo "验证 Worker 配置导入..."
docker run --rm --entrypoint /app/backend/.venv/bin/python \
  -e DATABASE_URL=postgresql+asyncpg://validation:validation@127.0.0.1/validation \
  -e SECRET_KEY=validation-only-secret-key-32-chars \
  knowledge-base-platform-worker:"${VERSION}" \
  -c "import app.worker.settings; print('Worker OK')"
echo "Worker 配置导入验证通过"

echo "验证 Web..."
docker run --rm --entrypoint nginx knowledge-base-platform-web:"${VERSION}" -t
echo "Web 镜像验证通过"

# ============================================================
# 输出构建报告
# ============================================================
echo ""
echo "============================================================"
echo "  构建完成"
echo "============================================================"
echo "版本: ${VERSION}"
echo "提交: ${COMMIT_SHA}"
echo ""
echo "镜像 SHA256:"
echo "  knowledge-base-platform-api-server: ${API_SHA256}"
echo "  knowledge-base-platform-worker:     ${WORKER_SHA256}"
echo "  knowledge-base-platform-web:        ${WEB_SHA256}"
echo ""
echo "标签:"
echo "  knowledge-base-platform-api-server:${IMMUTABLE_TAG}"
echo "  knowledge-base-platform-worker:${IMMUTABLE_TAG}"
echo "  knowledge-base-platform-web:${IMMUTABLE_TAG}"
echo ""
echo "本地部署该版本:"
echo "  APP_VERSION=${VERSION#v} APP_IMAGE_TAG=${IMMUTABLE_TAG} docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml up -d --no-build"
