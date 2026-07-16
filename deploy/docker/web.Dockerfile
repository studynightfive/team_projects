# ============================================================
# 智能知识库平台 - Web Dockerfile
# 用途：构建后的 Vue 静态资源 + Nginx 反向代理
# 部署方式：对外暴露 80/443 端口，提供 SPA 和 API 代理
# 版本基线：Node.js 22.23.1、Nginx 1.28.0（方案第13.1节）
# ============================================================

# ----------------------------------------------------------
# 阶段 1：构建阶段 - 编译 Vue 前端应用
# 使用 Node.js 22.23.1 Alpine 镜像（体积小）
# ----------------------------------------------------------
FROM node:22.23.1-alpine AS builder

# 设置工作目录
WORKDIR /app

# 设置 Node.js 环境变量
# 生产构建模式
ENV NODE_ENV=production

# 复制 package.json 和 package-lock.json
# 先复制依赖文件，利用 Docker 构建缓存
COPY package.json package-lock.json ./

# 安装前端依赖
# npm ci 使用 package-lock.json 中的精确版本
RUN npm ci

# 复制前端源代码
COPY frontend/web/ ./frontend/web/
COPY frontend/web/vite.config.ts ./frontend/web/

# 构建前端应用
# 输出目录：frontend/web/dist/
RUN npm run build:web

# ----------------------------------------------------------
# 阶段 2：运行阶段 - Nginx 静态资源服务器
# 使用 Nginx 1.28.0 Alpine 镜像（体积小、安全）
# ----------------------------------------------------------
FROM nginx:1.28.0-alpine AS runtime

# 设置镜像元数据标签
LABEL app="knowledge-base-platform-web" \
      version="0.1.0" \
      description="智能知识库平台 - Web 前端 + Nginx 反向代理"

# 删除 Nginx 默认配置
# 使用自定义配置替代
RUN rm /etc/nginx/conf.d/default.conf

# 复制自定义 Nginx 配置
COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf

# 从构建阶段复制前端构建产物到 Nginx 静态资源目录
# 构建产物包含 Vue SPA 的 HTML、JS、CSS 和静态资源
COPY --from=builder /app/frontend/web/dist/ /usr/share/nginx/html/

# 暴露 Web 端口 80
# 生产环境通过外部 LB 或 Certbot 处理 TLS
EXPOSE 80

# 健康检查：检查 Nginx 是否正常响应
# 访问根路径，预期返回 200 或 304
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=5s \
  CMD curl -f http://localhost:80/ || exit 1

# Nginx 前台运行
# 使用 daemon off 让 Nginx 在前台运行（Docker 容器要求）
CMD ["nginx", "-g", "daemon off;"]