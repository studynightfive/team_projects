# ============================================================
# 智能知识库平台 - Worker Dockerfile
# 用途：异步文档处理（转换、OCR、分段、索引）和导出任务
# 部署方式：不对外暴露端口，通过 Redis 队列接收任务
# 版本基线：Python 3.10.20（方案第13.1节）
# ============================================================

# ----------------------------------------------------------
# 阶段 1：构建阶段 - 安装 Python 依赖
# 与 API Server 使用相同的基础镜像和构建流程
# ----------------------------------------------------------
FROM python:3.10.20-slim AS builder

# 设置工作目录
WORKDIR /app

# 安装系统构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc=4:12.2.0-3 \
    libpq-dev=15.12-0+deb12u1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv 包管理器
RUN pip install --no-cache-dir uv==0.8.22

# 复制后端项目配置文件
COPY backend/pyproject.toml backend/uv.lock* /app/backend/

# 安装 Python 依赖
RUN cd /app && uv sync --project backend --frozen --no-dev

# ----------------------------------------------------------
# 阶段 2：运行阶段 - Worker 最终镜像
# 与 API Server 使用相同的系统依赖（文档处理工具）
# ----------------------------------------------------------
FROM python:3.10.20-slim AS runtime

# 设置镜像元数据标签
LABEL app="knowledge-base-platform-worker" \
      version="0.1.0" \
      description="智能知识库平台 - 异步任务 Worker"

# 设置工作目录
WORKDIR /app

# 安装运行时系统依赖（与 API Server 完全一致）
# 文档处理工具：LibreOffice、Tesseract OCR、Poppler、Ghostscript、libmagic
# 中文字体：Noto CJK Fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev=15.12-0+deb12u1 \
    libreoffice=4:24.2.7-1 \
    tesseract-ocr=5.3.4-1 \
    tesseract-ocr-eng=1:4.1.0-2 \
    tesseract-ocr-chi-sim=1:4.1.0-2 \
    tesseract-ocr-chi-tra=1:4.1.0-2 \
    poppler-utils=24.02.0-1 \
    ghostscript=10.02.1~dfsg-1 \
    libmagic1=1:5.45-1 \
    fonts-noto-cjk=1:20220127+repack1-1 \
    curl=8.11.1-1~deb12u1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 Python 依赖
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# 复制后端应用代码
COPY backend/ /app/backend/

# 创建非 root 用户
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /sbin/nologin appuser && \
    mkdir -p /app/storage && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# Worker 不对外暴露端口
# 通过 Redis 队列接收任务，不处理 HTTP 请求

# 健康检查：检查 Worker 进程是否存活
# 使用 pgrep 检查 arq Worker 进程是否存在
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
  CMD pgrep -f "arq" > /dev/null || exit 1

# 启动命令：使用 arq 启动 Worker
# arq 是 Redis 异步任务队列，用于处理文档转换、OCR、索引、导出等耗时任务
# Worker 启动后自动连接 Redis 并监听任务队列
CMD ["uv", "run", "--project", "backend", "arq", "backend.app.worker.settings.WorkerSettings"]