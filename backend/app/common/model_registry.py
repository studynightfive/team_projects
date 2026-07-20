"""显式加载全部 SQLAlchemy 模型，供迁移元数据使用。"""

from importlib import import_module

_MODEL_MODULES = (
    "app.common.models",
    "app.documents.models",
    "app.exports.all",
    "app.favorites.models",
    "app.knowledge.models",
    "app.models.repository",
    "app.notifications.models",
    "app.rag.conversations.all",
    "app.rag.search.repository",
    "app.rag.tests.all",
)


def load_all_models() -> None:
    for module_name in _MODEL_MODULES:
        import_module(module_name)
