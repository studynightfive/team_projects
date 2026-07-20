"""本地 RAG 演示种子：管理员、知识库、权限、可选 DeepSeek/OpenAI Provider。

用法（backend 目录，库已启动）：
  uv run python -m scripts.seed_rag_demo
  uv run python -m scripts.seed_rag_demo --provider deepseek --api-key sk-xxx
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from sqlalchemy import select, text

# 触发 ORM 表注册
import app.documents.models  # noqa: F401
import app.rag.search.repository  # noqa: F401
from app.common.database import async_session_factory, engine
from app.common.models import KnowledgeBasePermission
from app.common.seed import seed_default_admin, seed_permissions
from app.knowledge.models import KnowledgeBase
from app.models.repository import Model, ModelProvider
from app.models.security import encrypt_api_key


async def ensure_schema() -> None:
    await engine.dispose()
    from app.common.database import Base

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)


async def seed(
    *,
    provider_code: str | None,
    api_key: str | None,
    base_url: str | None,
    chat_model_name: str,
    embedding_model_name: str,
) -> dict[str, str]:
    await ensure_schema()
    async with async_session_factory() as db:
        await seed_permissions(db)
        admin = await seed_default_admin(db, username="admin", password="admin123")

        kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.name == "RAG演示知识库")
    )
        kb = kb_result.scalar_one_or_none()
        if kb is None:
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name="RAG演示知识库",
                description="本地联调上传/检索/问答",
                status="active",
                chunk_size=400,
                chunk_overlap=40,
            )
            db.add(kb)
            await db.flush()

        perm_q = await db.execute(
            select(KnowledgeBasePermission).where(
                KnowledgeBasePermission.subject_type == "user",
                KnowledgeBasePermission.subject_id == admin.id,
                KnowledgeBasePermission.kb_id == kb.id,
            )
        )
        if perm_q.scalar_one_or_none() is None:
            db.add(
                KnowledgeBasePermission(
                    id=str(uuid.uuid4()),
                    subject_type="user",
                    subject_id=admin.id,
                    kb_id=kb.id,
                    access_level="admin",
                )
            )

        chat_model_id = ""
        embed_model_id = ""
        if provider_code and api_key:
            url = base_url or {
                "deepseek": "https://api.deepseek.com",
                "openai": "https://api.openai.com/v1",
                "ollama": "http://127.0.0.1:11434/v1",
            }.get(provider_code, "https://api.openai.com/v1")

            provider = await db.get(ModelProvider, provider_code)
            if provider is None:
                provider = ModelProvider(
                    code=provider_code,
                    display_name=provider_code,
                    base_url=url,
                    enabled=True,
                )
                db.add(provider)
            else:
                provider.base_url = url
                provider.enabled = True

            enc = encrypt_api_key(api_key)
            chat = (
                await db.execute(
                    select(Model).where(
                        Model.provider_code == provider_code,
                        Model.kind == "chat",
                        Model.model_name == chat_model_name,
                    )
                )
            ).scalar_one_or_none()
            if chat is None:
                chat = Model(
                    id=str(uuid.uuid4()),
                    provider_code=provider_code,
                    model_name=chat_model_name,
                    kind="chat",
                    api_key_encrypted=enc,
                    enabled=True,
                )
                db.add(chat)
            else:
                chat.api_key_encrypted = enc
                chat.enabled = True
            await db.flush()
            chat_model_id = chat.id

            emb = (
                await db.execute(
                    select(Model).where(
                        Model.provider_code == provider_code,
                        Model.kind == "embedding",
                        Model.model_name == embedding_model_name,
                    )
                )
            ).scalar_one_or_none()
            if emb is None and provider_code != "deepseek":
                # DeepSeek 当前无独立 embedding；继续用 local stub
                emb = Model(
                    id=str(uuid.uuid4()),
                    provider_code=provider_code,
                    model_name=embedding_model_name,
                    kind="embedding",
                    api_key_encrypted=enc,
                    dimensions=1536,
                    distance="cosine",
                    enabled=True,
                )
                db.add(emb)
                await db.flush()
            if emb is not None:
                embed_model_id = emb.id

        await db.commit()
        return {
            "admin": "admin / admin123",
            "kb_id": kb.id,
            "chat_model_id": chat_model_id or "(未配置，问答需先配 Provider)",
            "embedding_model_id": embed_model_id or "local",
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed local RAG demo data")
    parser.add_argument("--provider", choices=["deepseek", "openai", "ollama"], default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--chat-model", default=None)
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    args = parser.parse_args()

    chat_defaults = {
        "deepseek": "deepseek-chat",
        "openai": "gpt-4o-mini",
        "ollama": "qwen2.5:7b",
    }
    chat_model = args.chat_model or (chat_defaults.get(args.provider or "", "gpt-4o-mini"))

    result = asyncio.run(
        seed(
            provider_code=args.provider,
            api_key=args.api_key,
            base_url=args.base_url,
            chat_model_name=chat_model,
            embedding_model_name=args.embedding_model,
        )
    )
    print("RAG demo seed OK")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
