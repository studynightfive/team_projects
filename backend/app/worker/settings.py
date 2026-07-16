# Worker 任务队列配置（占位）
# 使用 arq（基于 Redis 的异步任务队列）
# 详细实现：员工4 和员工5 在文档处理和导出模块中完成

from arq.connections import RedisSettings


# ============================================================
# Worker 配置类
# ============================================================
class WorkerSettings:
    """
    arq Worker 配置
    定义 Redis 连接、任务函数和队列参数
    """

    # Redis 连接配置
    # 通过环境变量 REDIS_URL 设置，默认连接本地 Redis
    redis_settings = RedisSettings(
        host="redis",
        port=6379,
        database=0,
    )

    # 任务函数注册（占位，员工4 和员工5 后续添加）
    # 格式：'任务名称': 任务函数
    functions: list = [
        # 文档处理任务：
        # 'convert_document': convert_document_task,     # 员工4 实现
        # 'ocr_process': ocr_process_task,               # 员工4 实现
        # 'chunk_and_index': chunk_and_index_task,       # 员工4 实现
        # 导出任务：
        # 'export_document': export_document_task,       # 员工5 实现
    ]

    # 任务超时配置（秒）
    job_timeout: int = 3600  # 单个任务最长执行 1 小时
    keep_result: int = 3600  # 任务结果保留 1 小时
    max_jobs: int = 10       # 同时执行的最大任务数
