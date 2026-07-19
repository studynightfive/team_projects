"""应用配置模块
使用 pydantic-settings 从环境变量加载配置
所有 Secret 通过环境变量在运行时注入，不硬编码
"""

from cryptography.fernet import Fernet
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
    auto_seed_demo_data: bool = True

    # ============================================================
    # CORS 配置
    # ============================================================
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:80"]

    # ============================================================
    # 数据库配置
    # ============================================================
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/knowledge_base"

    # ============================================================
    # Redis 配置
    # ============================================================
    redis_url: str = "redis://localhost:6379/0"

    # ============================================================
    # 安全配置
    # ============================================================
    secret_key: str = "change-me-in-production-use-a-random-secret-key"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ============================================================
    # 文件存储配置
    # ============================================================
    storage_root: str = "./storage"
    max_upload_size: int = 104857600
    # 员工4 documents 模块使用的别名（与 max_upload_size 同值）
    max_upload_bytes: int = 104857600

    # ============================================================
    # 模型配置
    # ============================================================
    model_api_key: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_chat_model: str = "deepseek-v4-pro"
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_embedding_model: str = "qwen3.7-text-embedding"
    qwen_embedding_dimensions: int = 1024
    rag_answer_max_context_chars: int = 12000
    rag_answer_max_tokens: int = 1200

    # ============================================================
    # 文档处理（员工 4）
    # ============================================================
    max_upload_files: int = 20
    allowed_upload_extensions: str = (
        ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.md,.markdown,.txt,.log,.rst,.org,"
        ".csv,.tsv,.html,.htm,.xml,.json,.epub,.odt,.ods,.odp,.rtf,"
        ".jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff,.eml"
    )
    # 员工4 documents 模块使用的别名（与 allowed_upload_extensions 同值）
    allowed_extensions: str = (
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
    # 员工5 扩展配置：模型密钥 Fernet 加密（提示词 01）
    # ============================================================
    model_key_fernet_key: str = ""
    model_provider_timeout_seconds: int = 10
    model_provider_max_retries: int = 1

    # ============================================================
    # 员工5 扩展配置：文档导出（提示词 05）
    # ============================================================
    export_storage_root: str = "./exports"
    export_default_ttl_hours: int = 24
    export_download_signing_key: str = ""
    export_task_timeout_seconds: int = 300
    export_task_max_retries: int = 2
    export_memory_peak_mb: int = 512

    # ============================================================
    # 员工5 扩展配置：RAG 与检索（提示词 02、03、04）
    # ============================================================
    embedding_default_dimensions: int = 1536
    embedding_default_distance: str = "cosine"
    rerank_default_top_n: int = 10
    retrieval_cache_ttl_seconds: int = 300
    rag_max_top_k: int = 30
    conversation_context_max_tokens: int = 8000

    # ============================================================
    # 员工5 扩展配置：SSE 流式问答（提示词 03）
    # ============================================================
    chat_sse_keepalive_seconds: int = 15
    chat_stream_flush_every_tokens: int = 20
    chat_auto_retry_max: int = 1

    # ============================================================
    # 员工5 扩展配置：命中率测试（提示词 06）
    # ============================================================
    retrieval_test_max_queries: int = 100
    retrieval_test_max_runtime_seconds: int = 1800
    retrieval_test_cache_ttl_seconds: int = 86400

    # ============================================================
    # Pydantic Settings 配置
    # ============================================================
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()

# ============================================================
# 派生工具
# ============================================================
_fernet_instance: Fernet | None = None
_fernet_warning_emitted: bool = False


def get_model_key_fernet() -> Fernet:
    global _fernet_instance, _fernet_warning_emitted

    if _fernet_instance is not None:
        return _fernet_instance

    raw = settings.model_key_fernet_key.strip()
    if raw:
        _fernet_instance = Fernet(
            raw.encode("utf-8") if not raw.endswith("=") else raw.encode("utf-8")
        )
        return _fernet_instance

    # 派生兜底
    import base64
    import hashlib

    import structlog

    if not _fernet_warning_emitted:
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
    raw = settings.export_download_signing_key.strip()
    if raw:
        return raw
    return f"export-signing-fallback:{settings.secret_key}"
