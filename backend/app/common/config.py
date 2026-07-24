"""应用配置模块
使用 pydantic-settings 从环境变量加载配置
所有 Secret 通过环境变量在运行时注入，不硬编码
"""

from __future__ import annotations

from typing import Literal

from cryptography.fernet import Fernet
from pydantic import Field, model_validator
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
    app_environment: Literal["development", "test", "production"] = "development"
    testing: bool = False
    debug: bool = False  # 生产环境必须为 False
    auto_seed_demo_data: bool = False
    demo_seed_password: str = ""

    # ============================================================
    # CORS 配置
    # ============================================================
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:80"]

    # ============================================================
    # 数据库配置
    # ============================================================
    database_url: str

    # ============================================================
    # Redis 配置
    # ============================================================
    redis_url: str = "redis://localhost:6379/0"

    # ============================================================
    # 安全配置
    # ============================================================
    secret_key: str
    cookie_secure: bool = False
    business_timezone: str = "Asia/Shanghai"
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=365)

    # ============================================================
    # 文件存储配置
    # ============================================================
    storage_root: str = "./storage"
    max_upload_size: int = 104857600
    max_upload_request_bytes: int = 104857600
    # 员工4 documents 模块使用的别名（与 max_upload_size 同值）
    max_upload_bytes: int = 104857600

    # ============================================================
    # 模型配置
    # ============================================================
    model_api_key: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_chat_model: str = "deepseek-chat"
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_rerank_base_url: str = "https://dashscope.aliyuncs.com/compatible-api/v1"
    qwen_embedding_model: str = "text-embedding-v2"
    qwen_embedding_dimensions: int = 1536
    qwen_rerank_model: str = "qwen3-rerank"
    rag_answer_max_context_chars: int = 12000
    rag_answer_max_tokens: int = 1200
    rag_answer_cache_enabled: bool = True
    rag_answer_cache_ttl_seconds: int = Field(default=604800, ge=60, le=2592000)
    rag_answer_cache_similarity_threshold: float = Field(default=0.95, ge=0.85, le=1.0)
    rag_answer_cache_candidate_limit: int = Field(default=50, ge=1, le=200)

    # ============================================================
    # 文档处理（员工 4）
    # ============================================================
    max_upload_files: int = 20
    document_recycle_days: int = 30
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
    pdf_parse_timeout_seconds: int = Field(default=120, ge=1, le=3600)
    pdf_max_pages: int = Field(default=500, ge=1, le=10000)
    pdf_parse_memory_limit_mb: int = Field(default=512, ge=128, le=4096)
    archive_max_entries: int = 10000
    archive_max_entry_bytes: int = 134217728
    archive_max_uncompressed_bytes: int = 536870912
    archive_max_compression_ratio: int = 1000
    tesseract_bin: str = "tesseract"
    tesseract_timeout_seconds: int = 60
    ocr_default_languages: str = "chi_sim+eng"
    chunk_size_default: int = 800
    chunk_overlap_default: int = 120
    chunk_size_min: int = 200
    chunk_size_max: int = 4000
    chunk_overlap_min: int = 0
    embedding_dimensions: int = 8
    worker_inline: bool = False

    # ============================================================
    # 员工5 扩展配置：模型密钥 Fernet 加密（提示词 01）
    # ============================================================
    model_key_fernet_key: str = ""
    model_provider_timeout_seconds: int = Field(default=30, ge=1, le=300)
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
    # 员工5 扩展配置：Query Rewriting / Intent / Embeddings（提示词 02/06）
    # ============================================================
    # Query Rewriting (backend/app/rag/query_rewrite.py)
    rag_query_rewrite_enabled: bool = True
    rag_query_rewrite_model_id: str | None = None
    rag_query_rewrite_max_variants: int = 3

    # Intent Recognition (backend/app/rag/intent.py)
    rag_intent_llm_enabled: bool = True
    rag_intent_model_id: str | None = None

    # Embeddings 抽象层 (backend/app/rag/embeddings.py)
    indexing_embedding_model_id: str | None = None

    # ============================================================
    # 员工5 扩展配置：Vector Store 抽象（提示词 02 + 新增 Milvus 支持）
    # ============================================================
    # pgvector (默认) / milvus / dual (pgvector + milvus 双写)
    vector_backend: str = "pgvector"
    # Milvus
    milvus_uri: str = "http://localhost:19530"
    milvus_token: str = ""
    milvus_collection: str = "chunks"
    milvus_embedding_dim: int = 1536
    milvus_hnsw_m: int = 16
    milvus_hnsw_ef_construction: int = 64
    milvus_hnsw_ef_search: int = 64

    # ============================================================
    # 员工5 扩展配置：命中率测试（提示词 06）
    # ============================================================
    retrieval_test_max_queries: int = 100
    retrieval_test_max_runtime_seconds: int = 1800
    retrieval_test_cache_ttl_seconds: int = 86400

    @model_validator(mode="after")
    def validate_production_safety(self) -> Settings:
        """阻止缺少口令的演示播种，并强制生产环境使用安全配置。"""
        if len(self.secret_key) < 16:
            raise ValueError("SECRET_KEY 至少需要 16 位")
        if self.auto_seed_demo_data and len(self.demo_seed_password) < 12:
            raise ValueError("启用 AUTO_SEED_DEMO_DATA 时必须提供至少 12 位的 DEMO_SEED_PASSWORD")
        if self.app_environment == "production":
            if len(self.secret_key) < 32:
                raise ValueError("生产环境 SECRET_KEY 至少需要 32 位")
            if not self.cookie_secure:
                raise ValueError("生产环境必须设置 COOKIE_SECURE=true")
            if self.auto_seed_demo_data:
                raise ValueError("生产环境禁止设置 AUTO_SEED_DEMO_DATA=true")
            if not self.model_key_fernet_key.strip():
                raise ValueError("生产环境必须设置 MODEL_KEY_FERNET_KEY")
            if not self.export_download_signing_key.strip():
                raise ValueError("生产环境必须设置 EXPORT_DOWNLOAD_SIGNING_KEY")
        return self

    # ============================================================
    # Pydantic Settings 配置
    # ============================================================
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# 必填值由 BaseSettings 在运行时从环境变量或 .env 注入，静态签名无法表达该来源。
settings = Settings()  # type: ignore[call-arg]

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
            impact="SECRET_KEY 轮换后已落库的 API Key 将无法解密，生产环境必须独立配置",
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
