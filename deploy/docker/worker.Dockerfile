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
FROM python:3.10.20-slim-bookworm AS builder

# 设置工作目录
WORKDIR /app

# 安装系统构建依赖
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装与当前 uv.lock 和 CI 一致的 uv 版本
RUN pip install --no-cache-dir uv==0.11.26

# 复制后端项目配置文件
COPY backend/pyproject.toml backend/uv.lock* /app/backend/

# 安装 Python 依赖
RUN cd /app && uv sync --project backend --frozen --no-dev

# ----------------------------------------------------------
# 阶段 2：运行阶段 - Worker 最终镜像
# 与 API Server 使用相同的系统依赖（文档处理工具）
# ----------------------------------------------------------
FROM python:3.10.20-slim-bookworm AS runtime

# 设置镜像元数据标签
LABEL app="knowledge-base-platform-worker" \
      version="0.1.0" \
      description="智能知识库平台 - 异步任务 Worker"

# 设置工作目录
WORKDIR /app

# 安装运行时系统依赖（与 API Server 完全一致）
# 文档处理工具：LibreOffice、Tesseract OCR、Poppler、Ghostscript、libmagic
# 中文字体：Noto CJK Fonts
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
    libpq-dev \
    libreoffice \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    poppler-utils \
    ghostscript \
    libmagic1 \
    fonts-noto-cjk \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 uv 和已锁定的 Python 虚拟环境
COPY --from=builder /app/backend/.venv /app/backend/.venv
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# 复制后端应用代码
COPY backend/ /app/backend/

# 创建非 root 用户
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /sbin/nologin appuser && \
    mkdir -p /app/storage && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
ENV PYTHONPATH=/app/backend

USER appuser

# Worker 不对外暴露端口
# 通过 Redis 队列接收任务，不处理 HTTP 请求

# 健康检查：检查 Worker 进程是否存活
# 使用 Python 读取 PID 1 命令行，避免为健康检查额外安装 procps
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
  CMD ["/app/backend/.venv/bin/python", "-c", "from pathlib import Path; raise SystemExit(b'arq' not in Path('/proc/1/cmdline').read_bytes())"]

# 启动命令：使用 arq 启动 Worker
# arq 是 Redis 异步任务队列，用于处理文档转换、OCR、索引、导出等耗时任务
# Worker 启动后自动连接 Redis 并监听任务队列
CMD ["/app/backend/.venv/bin/arq", "app.worker.settings.WorkerSettings"]
