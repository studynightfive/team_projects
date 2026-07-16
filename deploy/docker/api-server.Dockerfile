# ============================================================
# 智能知识库平台 - API Server Dockerfile
# 用途：FastAPI 同步接口和 SSE 流式问答
# 部署方式：通过 Nginx 反向代理访问，不直接对外暴露
# 版本基线：Python 3.10.20（方案第13.1节）
# ============================================================

# ----------------------------------------------------------
# 阶段 1：构建阶段 - 安装 Python 依赖
# 使用 slim 镜像减小体积，精确版本锁定
# ----------------------------------------------------------
FROM python:3.10.20-slim AS builder

# 设置工作目录
WORKDIR /app

# 安装系统构建依赖（编译 Python 包时需要）
# 使用精确版本号，确保环境一致性
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 编译工具：gcc 用于编译 Python C 扩展
    gcc=4:12.2.0-3 \
    # libpq-dev：PostgreSQL 客户端库，asyncpg 编译需要
    libpq-dev=15.12-0+deb12u1 \
    # 清理 apt 缓存，减小镜像体积
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv 包管理器（精确版本 0.8.22）
# 使用 pip 安装 uv，用于后续的依赖管理
RUN pip install --no-cache-dir uv==0.8.22

# 复制后端项目配置文件
# 先复制依赖文件，利用 Docker 构建缓存：只有依赖变化时才重新安装
COPY backend/pyproject.toml backend/uv.lock* /app/backend/

# 安装 Python 依赖
# --frozen：严格使用 uv.lock 中的版本，不更新依赖
# --project backend：指定项目目录
RUN cd /app && uv sync --project backend --frozen --no-dev

# ----------------------------------------------------------
# 阶段 2：运行阶段 - 最终镜像
# 只包含运行时需要的文件，最小化攻击面
# ----------------------------------------------------------
FROM python:3.10.20-slim AS runtime

# 设置镜像元数据标签
LABEL app="knowledge-base-platform-api-server" \
      version="0.1.0" \
      description="智能知识库平台 - FastAPI API 服务"

# 设置工作目录
WORKDIR /app

# 安装运行时系统依赖（方案第13.2节 - 文档处理工具）
# 所有版本精确锁定，确保各环境行为一致
RUN apt-get update && apt-get install -y --no-install-recommends \
    # ----------------------------------------------------------
    # PostgreSQL 客户端库：运行时数据库连接需要
    # ----------------------------------------------------------
    libpq-dev=15.12-0+deb12u1 \
    # ----------------------------------------------------------
    # LibreOffice 24.2.7：旧 Office 格式和开放文档转换
    # 用于 .doc、.ppt、.xls 和 .odt/.ods/.odp 等格式
    # ----------------------------------------------------------
    libreoffice=4:24.2.7-1 \
    # ----------------------------------------------------------
    # Tesseract OCR 5.3.4：图片和扫描 PDF 文字识别
    # 安装中英文语言包
    # ----------------------------------------------------------
    tesseract-ocr=5.3.4-1 \
    tesseract-ocr-eng=1:4.1.0-2 \
    tesseract-ocr-chi-sim=1:4.1.0-2 \
    tesseract-ocr-chi-tra=1:4.1.0-2 \
    # ----------------------------------------------------------
    # Poppler 24.02.0：PDF 页面和文本提取工具
    # 提供 pdftotext、pdfinfo 等命令行工具
    # ----------------------------------------------------------
    poppler-utils=24.02.0-1 \
    # ----------------------------------------------------------
    # Ghostscript 10.02.1：PostScript 和 PDF 兼容处理
    # ----------------------------------------------------------
    ghostscript=10.02.1~dfsg-1 \
    # ----------------------------------------------------------
    # libmagic 5.45：MIME 类型识别（python-magic 的底层依赖）
    # 用于判断上传文件的实际类型，防止扩展名伪装
    # ----------------------------------------------------------
    libmagic1=1:5.45-1 \
    # ----------------------------------------------------------
    # Noto CJK 字体：中文、日文、韩文导出字体
    # 确保 PDF 和图片导出时中文正常显示
    # ----------------------------------------------------------
    fonts-noto-cjk=1:20220127+repack1-1 \
    # ----------------------------------------------------------
    # 其他工具
    # ----------------------------------------------------------
    curl=8.11.1-1~deb12u1 \
    # 清理 apt 缓存，减小镜像体积
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 uv 和 Python 虚拟环境
# 使用 --from=builder 从构建阶段复制文件，避免在运行时阶段重新安装
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# 复制后端应用代码
# 注意：.env 文件不复制到镜像中（通过 .dockerignore 排除）
COPY backend/ /app/backend/

# 创建非 root 用户运行应用（安全最佳实践）
# 方案第15.3节：上传目录禁止执行
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /sbin/nologin appuser && \
    # 创建文件存储目录
    mkdir -p /app/storage && \
    # 将应用目录的所有权赋予 appuser
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 暴露 API 端口 8000（仅内部网络，由 Nginx 代理访问）
# 不直接对外暴露，在 Docker Compose 中使用 expose 而非 ports
EXPOSE 8000

# 健康检查：每隔 30 秒检查一次 /api/v1/health/live 端点
# 超时 5 秒，连续失败 3 次标记为 unhealthy
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
  CMD curl -f http://localhost:8000/api/v1/health/live || exit 1

# 启动命令：使用 uvicorn 运行 FastAPI 应用
# --host 0.0.0.0：监听所有网络接口
# --port 8000：监听端口 8000
# --workers 1：单 Worker（容器编排层面扩展实例数）
# --log-level info：日志级别
CMD ["uv", "run", "--project", "backend", "uvicorn", "backend.app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]