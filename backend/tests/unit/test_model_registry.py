from app.common.database import Base
from app.common.model_registry import load_all_models


def test_model_registry_loads_all_business_tables() -> None:
    load_all_models()

    expected = {
        "audit_logs",
        "chunks",
        "conversations",
        "document_assets",
        "document_chunks",
        "document_tasks",
        "documents",
        "export_tasks",
        "favorites",
        "knowledge_base_permissions",
        "knowledge_bases",
        "messages",
        "model_providers",
        "models",
        "notifications",
        "permissions",
        "refresh_tokens",
        "retrieval_test_datasets",
        "retrieval_test_runs",
        "role_permissions",
        "roles",
        "user_roles",
        "users",
    }
    assert set(Base.metadata.tables) == expected
