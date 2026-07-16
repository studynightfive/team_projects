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
# Git 短提交 SHA（用于不可变标签）
COMMIT_SHA=$(git rev-parse --short HEAD)
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
  -t api-server:"${VERSION}" \
  -t api-server:"${COMMIT_SHA}" \
  --build-arg BUILD_VERSION="${VERSION}" \
  --build-arg BUILD_SHA="${COMMIT_SHA}" \
  .

# 记录镜像 SHA256
API_SHA256=$(docker inspect api-server:"${VERSION}" --format='{{.Id}}')
echo "API Server 镜像 SHA256: ${API_SHA256}"

# ============================================================
# 构建 Worker 镜像
# ============================================================
echo ""
echo "=== 构建 Worker 镜像 ==="
docker build -f deploy/docker/worker.Dockerfile \
  -t worker:"${VERSION}" \
  -t worker:"${COMMIT_SHA}" \
  --build-arg BUILD_VERSION="${VERSION}" \
  --build-arg BUILD_SHA="${COMMIT_SHA}" \
  .

WORKER_SHA256=$(docker inspect worker:"${VERSION}" --format='{{.Id}}')
echo "Worker 镜像 SHA256: ${WORKER_SHA256}"

# ============================================================
# 构建 Web 镜像
# ============================================================
echo ""
echo "=== 构建 Web 镜像 ==="
docker build -f deploy/docker/web.Dockerfile \
  -t web:"${VERSION}" \
  -t web:"${COMMIT_SHA}" \
  --build-arg BUILD_VERSION="${VERSION}" \
  --build-arg BUILD_SHA="${COMMIT_SHA}" \
  .

WEB_SHA256=$(docker inspect web:"${VERSION}" --format='{{.Id}}')
echo "Web 镜像 SHA256: ${WEB_SHA256}"

# ============================================================
# 验证镜像
# ============================================================
echo ""
echo "=== 验证镜像 ==="

# 验证 API Server 镜像可启动
echo "验证 API Server..."
docker run --rm api-server:"${VERSION}" python -c "print('API Server OK')" 2>/dev/null && \
  echo "API Server 镜像验证通过" || echo "API Server 镜像验证失败"

# 验证 Worker 镜像可启动
echo "验证 Worker..."
docker run --rm worker:"${VERSION}" python -c "print('Worker OK')" 2>/dev/null && \
  echo "Worker 镜像验证通过" || echo "Worker 镜像验证失败"

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
echo "  api-server: ${API_SHA256}"
echo "  worker:     ${WORKER_SHA256}"
echo "  web:        ${WEB_SHA256}"
echo ""
echo "标签:"
echo "  api-server:${VERSION}  api-server:${COMMIT_SHA}"
echo "  worker:${VERSION}      worker:${COMMIT_SHA}"
echo "  web:${VERSION}         web:${COMMIT_SHA}"
echo ""
echo "推送镜像到仓库:"
echo "  docker tag api-server:${VERSION} registry.example.com/api-server:${VERSION}"
echo "  docker push registry.example.com/api-server:${VERSION}"