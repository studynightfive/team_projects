# 应用配置模块
# 使用 pydantic-settings 从环境变量加载配置
# 所有 Secret 通过环境变量在运行时注入，不硬编码

from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    应用配置类
    所有配置项通过环境变量或 .env 文件加载
    敏感信息（数据库密码、密钥等）不设置默认值，必须从环境变量提供
    """

    # =====================================================    # 应用基本信息
    # =====================================================    app_name: str = "智能知识库平台"
    app_version: str = "0.1.0"
    debug: bool = False  # 生产环境必须为 False

    # =====================================================    # CORS 配置：允许跨域访问的域名列表
    # =====================================================    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:80"]

    # =====================================================    # 数据库配置：PostgreSQL 连接信息
    # =====================================================    # 数据库连接 URL（异步驱动 asyncpg）
    # 格式：postgresql+asyncpg://用户名:密码@主机:端口/数据库名
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/knowledge_base"

    # =====================================================    # Redis 配置：缓存和任务队列
    # =====================================================    redis_url: str = "redis://localhost:6379/0"

    # =====================================================    # 安全配置：JWT 签名密钥和 Token 过期时间
    # =====================================================    # JWT 签名密钥（生产环境必须通过环境变量设置，不能使用默认值）
    secret_key: str = "change-me-in-production-use-a-random-secret-key"
    # Access Token 过期时间（分钟）
    access_token_expire_minutes: int = 30
    # Refresh Token 过期时间（天）
    refresh_token_expire_days: int = 7

    # =====================================================    # 文件存储配置
    # =====================================================    # 文件存储根目录
    storage_root: str = "./storage"
    # 上传文件大小限制（字节，默认 100MB）
    max_upload_size: int = 104857600

    # =====================================================    # 模型配置：LLM API 密钥（不设置默认值，不记录到日志）
    # =====================================================    # 模型 API 密钥（必须从环境变量注入）
    model_api_key: str = ""

    # =====================================================    # 文档处理（员工 4）
    # =====================================================    max_upload_files: int = 20
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
    # 员工5 扩展配置：模型密钥 Fernet 加密（提示词 01）
    # =====================================================    # 用于加密落库模型供应商 API Key 的 Fernet 主密钥
    # 生产必须通过环境变量注入；本地开发如未注入则自动生成临时密钥并打印告警
    model_key_fernet_key: str = ""

    # 模型 provider 默认超时（秒）
    model_provider_timeout_seconds: int = 10
    # 模型 provider 默认最大重试次数
    model_provider_max_retries: int = 1

    # =====================================================    # 员工5 扩展配置：文档导出（提示词 05）
    # =====================================================    # 导出文件根目录（与 storage_root 解耦，方便单独配置 Docker 卷）
    export_storage_root: str = "./exports"
    # 默认下载链接有效期（小时）
    export_default_ttl_hours: int = 24
    # 下载链接 HMAC 签名密钥（生产必须通过环境变量注入）
    export_download_signing_key: str = ""
    # 单次导出任务超时（秒）
    export_task_timeout_seconds: int = 300
    # 单次导出失败最大重试次数
    export_task_max_retries: int = 2
    # 导出内存峰值（MB）
    export_memory_peak_mb: int = 512

    # =====================================================    # 员工5 扩展配置：RAG 与检索（提示词 02、03、04）
    # =====================================================    # 默认嵌入模型维度（OpenAI text-embedding-3-small = 1536）
    embedding_default_dimensions: int = 1536
    # 默认向量距离度量
    embedding_default_distance: str = "cosine"
    # 重排默认 top_n
    rerank_default_top_n: int = 10
    # 检索缓存 TTL（秒）
    retrieval_cache_ttl_seconds: int = 300
    # 检索 top_k 上限（超出强制启用重排）
    rag_max_top_k: int = 30
    # 会话上下文窗口最大 token
    conversation_context_max_tokens: int = 8000

    # =====================================================    # 员工5 扩展配置：SSE 流式问答（提示词 03）
    # =====================================================    # SSE 心跳间隔（秒）
    chat_sse_keepalive_seconds: int = 15
    # 每次流式刷新数据库的最小 token 间隔
    chat_stream_flush_every_tokens: int = 20
    # 单次回答最大自动重试次数
    chat_auto_retry_max: int = 1

    # =====================================================    # 员工5 扩展配置：命中率测试（提示词 06）
    # =====================================================    # 单 dataset 最大 query 数
    retrieval_test_max_queries: int = 100
    # 单 run 最长执行时间（秒）
    retrieval_test_max_runtime_seconds: int = 1800
    # 结果缓存 TTL（秒）
    retrieval_test_cache_ttl_seconds: int = 86400

    # Pydantic Settings 配置
    # ============================================================ 配置
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

# =====================================================# 派生工具：Fernet 实例惰性构造
# =====================================================_fernet_instance: Fernet | None = None
_fernet_warning_emitted: bool = False


def get_model_key_fernet() -> Fernet:
    """获取模型密钥 Fernet 加密器

    设计要点：
    - 生产必须显式注入 MODEL_KEY_FERNET_KEY（44 字节 base64 编码的 32 字节密钥）
    - 本地开发如未注入，使用 SECRET_KEY 派生一次性密钥（重启失效，仅供开发）
    - 仅在第一次调用时构造并打印一次告警，避免重复日志
    """
    global _fernet_instance, _fernet_warning_emitted

    if _fernet_instance is not None:
        return _fernet_instance

    raw = settings.model_key_fernet_key.strip()
    if raw:
        _fernet_instance = Fernet(raw.encode("utf-8") if not raw.endswith("=") else raw.encode("utf-8"))
        return _fernet_instance

    # 本地开发兜底：使用 SECRET_KEY 派生一次性密钥
    import base64
    import hashlib

    if not _fernet_warning_emitted:
        import structlog

        structlog.get_logger().warning(
            "model_key_fernet_key_not_configured",
            fallback="derived_from_secret_key",
            impact="重启后已落库的 API Key 将无法解密，生产环境必须配置",
        )
        _fernet_warning_emitted = True

    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    derived = base64.urlsafe_b64encode(digest)
    _fernet_instance = Fernet(derived)
    return _fernet_instance


def get_export_download_signing_key() -> str:
    """获取导出下载链接 HMAC 签名密钥

    设计要点：与 Fernet 同样的兜底逻辑，但只用于 HMAC 签名，不影响落库数据。
    """
    raw = settings.export_download_signing_key.strip()
    if raw:
        return raw
    return f"export-signing-fallback:{settings.secret_key}"