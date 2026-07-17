# 应用配置模块
# 使用 pydantic-settings 从环境变量加载配置
# 所有 Secret 通过环境变量在运行时注入，不硬编码


from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    应用配置类
    所有配置项通过环境变量或 .env 文件加载
    敏感信息（数据库密码、密钥等）不设置默认值，必须从环境变量提供
    """

    # ============================================================
    # 应用基本信息
    # ============================================================
    app_name: str = "智能知识库平台"
    app_version: str = "0.1.0"
    debug: bool = False  # 生产环境必须为 False

    # ============================================================
    # CORS 配置：允许跨域访问的域名列表
    # ============================================================
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:80"]

    # ============================================================
    # 数据库配置：PostgreSQL 连接信息
    # ============================================================
    # 数据库连接 URL（异步驱动 asyncpg）
    # 格式：postgresql+asyncpg://用户名:密码@主机:端口/数据库名
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/knowledge_base"

    # ============================================================
    # Redis 配置：缓存和任务队列
    # ============================================================
    redis_url: str = "redis://localhost:6379/0"

    # ============================================================
    # 安全配置：JWT 签名密钥和 Token 过期时间
    # ============================================================
    # JWT 签名密钥（生产环境必须通过环境变量设置，不能使用默认值）
    secret_key: str = "change-me-in-production-use-a-random-secret-key"
    # Access Token 过期时间（分钟）
    access_token_expire_minutes: int = 30
    # Refresh Token 过期时间（天）
    refresh_token_expire_days: int = 7

    # ============================================================
    # 文件存储配置
    # ============================================================
    # 文件存储根目录
    storage_root: str = "./storage"
    # 上传文件大小限制（字节，默认 100MB）
    max_upload_size: int = 104857600

    # ============================================================
    # 模型配置：LLM API 密钥（不设置默认值，不记录到日志）
    # ============================================================
    # 模型 API 密钥（必须从环境变量注入）
    model_api_key: str = ""

    # ============================================================
    # 文档处理（员工 4）
    # ============================================================
    max_upload_files: int = 20
    allowed_upload_extensions: str = (
        ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.md,.markdown,.txt,.log,.rst,.org,"
        ".csv,.tsv,.html,.htm,.xml,.json,.epub,.odt,.ods,.odp,.rtf,"
        ".jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff,.eml"
    )
    libreoffice_bin: str = "soffice"
    libreoffice_timeout_seconds: int = 120
    tesseract_bin: str = "tesseract"
    tesseract_timeout_seconds: int = 60
    ocr_default_languages: str = "chi_sim+eng"
    chunk_size_default: int = 800
    chunk_overlap_default: int = 120
    chunk_size_min: int = 200
    chunk_size_max: int = 4000
    chunk_overlap_min: int = 0
    embedding_dimensions: int = 8
    worker_inline: bool = True

    # ============================================================
    # Pydantic Settings 配置
    # ============================================================
    model_config = {
        # 从 .env 文件加载环境变量（如果存在）
        "env_file": ".env",
        # .env 文件不存在时不报错
        "env_file_encoding": "utf-8",
        # 环境变量名大小写敏感
        "case_sensitive": False,
    }

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size

    @property
    def allowed_extensions(self) -> set[str]:
        return {
            ext.strip().lower()
            for ext in self.allowed_upload_extensions.split(",")
            if ext.strip()
        }


# 全局配置实例
settings = Settings()
